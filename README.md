# Job Scout

Local-first job browser and SEEK / Immigration New Zealand scraper. It collects ICT jobs from SEEK, keeps only the ones from employers on Immigration NZ's accredited list, and shows them in a React UI (Material UI, Catppuccin Mocha theme).

## Requirements

- Docker with the Compose plugin (the supported way to run everything)
- Only for working outside Docker or running the checks: Python 3.15 with [`uv`](https://docs.astral.sh/uv/), and Node.js 26+ with pnpm

## Quick start (Docker)

```sh
cp .env.example .env
docker-compose up -d
```

One command starts everything: the database, migrations, API, UI and Airflow. The first run builds the images and takes several minutes (the Airflow image is about 5 GB because it installs Chromium); later runs reuse them and start in seconds. Plain `up -d` only builds an image that doesn't exist yet. Add `--build` after changing dependencies, `backend/.python-version` or a Dockerfile; builds are layered so code-only changes don't redo the heavy steps. **Give Docker at least 4 GB of memory** (Docker Desktop → Settings → Resources). The idle stack already uses about 1.3 GB, and the enrich phase launches Chromium on top of that. With less, containers get killed with exit code 137 (`docker inspect <container> --format '{{.State.OOMKilled}}'` prints `true`).

### Where to open things

| What                      | URL                                                | Login                              |
| ------------------------- | -------------------------------------------------- | ---------------------------------- |
| **Web UI** (job browser)  | <http://localhost:5173>                            | none                               |
| **API** + interactive docs | <http://localhost:8000/docs> (health: `/health`)  | none                               |
| **Airflow** (scheduler UI) | <http://localhost:8080>                           | `airflow` / `local_dev_only`       |
| PostgreSQL                | `127.0.0.1:5432`, database `job_scout`            | `job_scout` / `local_dev_only`     |

The Airflow login comes from `AIRFLOW_ADMIN_USERNAME` / `AIRFLOW_ADMIN_PASSWORD` in `.env`. The UI shows jobs only after a scrape has run (see below).

### Services

| Service                                                     | What it does                                        |
| ----------------------------------------------------------- | --------------------------------------------------- |
| `postgres`                                                  | PostgreSQL 18, the application database            |
| `migrate`                                                   | Runs `alembic upgrade head`, then exits             |
| `backend`                                                   | FastAPI on Python 3.15, reloads on code changes     |
| `frontend`                                                  | Vite dev server (Node 26, pnpm)                     |
| `airflow-db`                                                | PostgreSQL 16, Airflow's own metadata database      |
| `airflow-init`                                              | One-time Airflow setup (DB migration, admin user), then exits |
| `airflow-apiserver`, `-scheduler`, `-dag-processor`, `-triggerer` | The Airflow 3.3.2 components                  |

- Start order is enforced by health checks: `postgres` → `migrate` → `backend` (healthy) → `frontend`; Airflow waits for `airflow-db`, `airflow-init` and `migrate`. Check them with `docker-compose ps`.
- `backend/src`, `backend/migrations` and `frontend/` are mounted, so edits show up without a rebuild. Rebuild (`up -d --build`) only after changing dependencies or a Dockerfile. If Docker misses a file change (common on macOS), run `docker-compose restart backend`.
- Data lives in the `postgres_data` and `airflow_db_data` volumes. They survive `docker-compose down`; `docker-compose down -v` deletes them.
- All published ports are bound to `127.0.0.1` only.
- Stop everything with `docker-compose down`.

## Running the scraper

The enrich phase needs a Chromium browser for the Immigration NZ lookup, which only the Airflow image includes. Use one of:

- **Airflow (recommended, also the daily schedule):** see the next section. It is already running after `docker-compose up -d`.
- **Locally:** `cd backend && uv sync && uv run playwright install chromium`, then

  ```sh
  uv run job_scout_scrape --category ict      # discover → reconcile → enrich
  uv run job_scout_scrape --category ict --phase discover
  ```

  `python -m job_scout.scraper` is equivalent. Make sure `DATABASE_URL` in `.env` points at the Compose database (`localhost:5432`).

How a run works:

1. **discover** — fetches SEEK pages until SEEK reports `totalCount: 0` and saves every listing as a `job_draft` (one transaction per page). Unchanged listings are only marked as seen. A failed or partial discovery stops the run before the next phase.
2. **reconcile** — marks clean jobs that were seen in the scan active and all others inactive. It only runs after discovery succeeds.
3. **enrich** — for each new or changed draft, checks Immigration NZ (each company is looked up once per run) and, if accredited, promotes the draft to a clean `job`. A draft that fails is retried on later runs up to 3 times (`MAX_ENRICH_ATTEMPTS`), then left alone until SEEK changes it; the log warns how many gave up.

**Job history.** Every change to a clean job is appended to the `job_event` table, which is the source for trend charts: `new` (first promoted), `updated` (a tracked field changed; `details` holds `{field: {old, new}}`), `closed` (no longer listed) and `reopened` (listed again). Running the pipeline again on unchanged data writes no events. Events are never edited, and are deleted only together with their job.

The Immigration NZ rule is unchanged: exact `Title == "No Results"` means not accredited, anything else is accepted, and the full response is stored for audit. Every phase exits non-zero if any listing failed in that run.

**Job descriptions.** SEEK job pages sit behind a Cloudflare bot check, so the scraper does not load them at all. A job's description is built from what SEEK's public search results already include: the one-sentence `teaser` plus the advertiser's `bulletPoints` (typically 200–500 characters). It is a summary, not the full ad; the job detail page links to the original SEEK listing for the rest. A listing with neither field fails enrichment.

## Categories

SEEK groups jobs into *classifications*. All 27 SEEK NZ classifications are in the `category` table, but **only ICT is enabled**; the others are there, switched off, so you can turn them on one at a time. Only enabled categories are scraped by the daily run and shown in the UI.

```sh
# turn a category on (any slug from `SELECT slug FROM category`), or off again
docker exec jobs-postgres-1 psql -U job_scout -d job_scout -c "UPDATE category SET enabled = true WHERE slug = 'trades-services'"
```

- The next daily run (or a manual **Trigger DAG**, optionally with that slug as the `category` parameter) scrapes it. A large category's first run takes roughly 40–60 minutes, because every new listing needs an Immigration NZ lookup; later runs only handle what changed.
- Local runs take the slug too: `uv run job_scout_scrape --category trades-services`.
- When more than one category is enabled, the Job postings and Diagrams pages show a **Category** picker that keeps you on the same view. The Dashboard lists them all.
- The list of classifications and ids comes from SEEK's own search results (`classifications` on each listing); the search API has no endpoint that lists them. A new classification would need a new row (a migration), with its SEEK id.

## Airflow (daily sync)

Airflow starts with everything else (`docker-compose up -d`). Open <http://localhost:8080> and sign in with `airflow` / `local_dev_only` (or the values in `.env`).

**To load jobs for the first time:** open the `job_scout_daily_sync` DAG and click **Trigger DAG**. A full run takes a while because enrichment checks each new listing. Then refresh the web UI at <http://localhost:5173>.

The DAG also runs by itself at 02:00 `Pacific/Auckland`. It first lists the **enabled categories** (see *Categories* below), then runs `discover → reconcile → enrich` for each one, one category at a time, each task retried twice, five minutes apart. A category that fails stops only its own chain, not the others. When triggering it by hand, the `category` parameter is `all` (default) or the slug of one enabled category.

- Tasks run as Python functions (`@task.external_python`) inside the backend's own virtualenv in the Airflow image. That venv runs Python 3.15 while Airflow itself stays on its own Python 3.13, and it is separate because Airflow pins an older SQLAlchemy than the backend needs. The `discover` task returns the scan time to `reconcile` through XCom.
- `backend/src` is mounted into the image, so backend code changes apply without a rebuild. Rebuild (`docker-compose build`) after changing dependencies, `backend/.python-version` or a Dockerfile, then `docker-compose up -d`.
- Run history lives in Airflow's own metadata database; no sync-run table is needed in the application schema.

## Local development without Docker for the app

Run only PostgreSQL in Docker and the app on the host:

```sh
cp .env.example .env
docker-compose up -d postgres
cd backend && uv sync && uv run alembic upgrade head && uv run job_scout_backend   # API on :8000
cd frontend && pnpm install --frozen-lockfile && pnpm dev                          # UI on :5173
```

After a schema change run `uv run alembic upgrade head` again. Schema changes are always Alembic migrations that can be reversed.

## Development checks

Backend tests start an isolated `postgres:18-alpine` Testcontainer (Docker must be running) and never touch your database.

```sh
cd backend
uv run pytest
uv run ruff check src tests migrations ../frontend/e2e --config pyproject.toml
uv run ruff format --check src tests migrations ../frontend/e2e --config pyproject.toml
```

```sh
cd frontend
pnpm lint
pnpm build
```

- The browser-flow test (`frontend/e2e/test_spa.py`) runs with the backend tests; it starts Vite and needs `uv run playwright install chromium`.
- The frontend's API types are generated from FastAPI's OpenAPI schema into `frontend/src/api/schema.d.ts`. After changing a response schema, run `pnpm gen:api` from `frontend/` and keep the result.

## Job sources

Every job has a `source`, shown in the **Source** column (filterable and sortable) and on the job page. Each source has its own DAG, so a failure in one never stops the other, and each only opens/closes its own jobs.

| Source | DAG | Schedule | How |
|---|---|---|---|
| SEEK | `job_scout_daily_sync` | 02:00 | SEEK's search API (teaser + bullet points) |
| Employment Hero | `job_scout_employmenthero_daily` | 04:00 | its public job pages (full description) |

Employment Hero is read from its HTML pages only (the filtered list `?job_sector_ids=<id>`, then each job page's `JobPosting` data), one request per second. Its `/wp-json/` API is disallowed by its `robots.txt` and is never used. A category is crawled there when it has an `employmenthero_sector_id` (ICT = 18). Both sources run the same Immigration NZ accreditation check, and only accredited employers become jobs. By hand: `docker-compose exec backend python -m job_scout.scraper --category ict --source employmenthero`.

The same job advertised on both sources is shown twice (no de-duplication yet).

## Green List

Immigration NZ's [Green List](https://www.immigration.govt.nz/work/requirements-for-work-visas/green-list-occupations-qualifications-and-skills/green-list-roles-jobs-we-need-people-for-in-new-zealand/) (about 215 roles, each **Tier 1** = straight to residence or **Tier 2** = work to residence) is fetched every month and stored, and the **Green List** tab in the UI shows it.

- **Monthly sync:** the Airflow DAG `job_scout_green_list_monthly` runs on the 1st of each month at 03:00 `Pacific/Auckland`. It calls the Immigration NZ list search the page itself uses (one POST returns the whole list), so no browser is involved. Run it by hand with **Trigger DAG**, or `docker-compose exec backend python -m job_scout.green_list`.
- **Tables:** `green_list_role` (one row per role: title, ANZSCO code, industry, tier, pathway, requirements, the full record for audit, `is_active`) and `green_list_event` (history).
- **Changes:** each sync compares with the stored list and records `tier_changed` (with the old and new tier), `new`, `removed` and `restored`. The very first sync is a *baseline* and records no events, so the history starts at "nothing changed yet". Running it again with no change writes nothing.
- **Safe by design:** a response that is incomplete (more than one page, fewer roles than the site reports, a role without a tier) or that shrinks the list by more than half is refused, so a broken fetch can never look like roles being removed. Removed roles stay in the table as inactive.
- **UI:** the tab shows the tier options with counts (*All*, *Tier 1*, *Tier 2*), a **Changes in the last 90 days** panel, search and an industry filter. A role that moved tier carries a "was 2" marker, and clicking a role shows its pathway and requirements as plain text.
- **API:** `GET /api/green-list` (roles + counts) and `GET /api/green-list/changes?days=90`.

## Using the jobs table

The web UI has a side navigation (a slim icon rail that expands over the page when hovered or focused) with two views for the selected category: **Job postings** and **Diagrams** (on narrow screens it opens from the *Menu* button, and the *Job Scout* title returns to the category overview). *Job postings* (<http://localhost:5173> → *View jobs*, or the nav) shows **all** jobs, open and closed, newest first.

- **Sort:** click a column header to sort by it, and click again to reverse; or use ⋮ → *Sort by ASC / DESC*. Jobs with no value for the column (for example no salary) always sort last.
- **Filter:** open a column's ⋮ menu to filter that column. Filters on different columns combine, and each filtered column gets a dot in its header. Active filters also appear as removable chips above the table, with *Clear all*. Position, company and location are case-insensitive "contains" searches; arrangement and work type are checklists (a job matches if it has any ticked value); status is All / Open / Closed; the date filter is an inclusive listed-from / listed-to range.
- **Salary:** the posted text is free-form ("$110,000 – $135,000 per year", "$28 per hour", "Competitive salary"), so each job also gets an *estimated annual NZD range* parsed from it (hourly × 2080, daily × 260, weekly × 52, monthly × 12). It shows as "≈ $58k / yr" under the text, and powers the *Salary* filter (has a figure / no figure), *Min salary* (the top of the job's range must reach it) and salary sorting. Labels without a dollar figure get no estimate.
- **URL:** sort, filters and page are kept in the address bar, so a view can be bookmarked or shared. Sorting and filtering run on the server, so they cover every job, not just the visible page.

## Trend charts

The **Diagrams** view (side nav) shows trend charts for the selected period (last 7, 30 or 90 days), rebuilt from the `job_event` history:

- **Open jobs:** jobs still listed at the end of each day (a running total of new + reopened − closed).
- **New and closed:** how many jobs appeared and disappeared each day.
- **Open jobs by seniority:** a pie of the open jobs split by level, as of the last day shown. SEEK has no seniority field, so the level is read from the job title: *graduate/intern*, *junior*, *mid-level*, *senior*, *lead/principal*, *management* (head of, director, chief, and manager titles that run teams, such as "Engineering Manager"), or *not stated* when the title names no level, which is most titles. Project, product and delivery managers are normal ICT roles, so they are not counted as management. Stored on each job as `seniority`. The legend lists every count and share; hover a slice or legend row (or use the arrow keys) to read it out.
- **Jobs by location:** ranked bars of open jobs per region, biggest first (the top 8 regions plus one "Other" bar; the Table view lists them all). SEEK locations read "Suburb, Region" or just "Region", so the region is the last part of the label ("Newmarket, Auckland" counts towards Auckland).

Every chart has a **Table** view with the same numbers, a hover tooltip that lists every series for that day, and keyboard support (focus a chart, then use the left/right arrow keys). Days use New Zealand time.

**History only goes back to when events were first recorded**, so the charts start short and grow with each daily run; the page says when history starts. Colors are not Catppuccin's pastels: they were checked for colour-blind safety and contrast on the dark surface and live in `frontend/src/theme.ts` (`chartColors`).

## Project layout

```text
backend/src/job_scout/
  main.py          FastAPI app
  categories/      categories (models, schemas, service, router)
  jobs/            clean jobs the UI reads
  green_list/      Immigration NZ Green List: monthly fetch, tier-change history, API
  scraper/         the scrape pipeline: discovery, enrichment, persistence, clients, entry point
  core/            errors, exception handlers, logging
airflow/           DAG and Airflow image
frontend/          React + TypeScript + Vite + MUI
```

## Configuration

Copy `.env.example` to `.env` and change values if needed. `LOG_LEVEL` (default `INFO`) controls logging for the API, the scraper and the Airflow tasks. Never commit `.env` or real secrets. Hosting is deferred until the local workflow is settled.
