---
name: add-country
description: Add a new country (job boards + immigration policy) to job_scout. Use when the user asks to add, research or extend a country such as Canada or Germany.
---

# Add a country

Do these in order. Report findings to the user after steps 1-2 and wait before building.

## 1. Research the job boards (no code yet)
- Pick the country's top 5 job boards (check the country's own state board, Indeed, Glassdoor, LinkedIn, local leaders).
- Make ONE plain sample search per board with `curl_cffi` (`impersonate="chrome"`, as in `scraper/chrome_http.py`), from the scratchpad.
- Per board record: status, whether results/JSON-LD/IDs are in the HTML, whether a detail page has the full description, and whether the posting shows sponsorship (e.g. Canada's Job Bank flags LMIA-approved employers).
- A 403/captcha is a "no". Never spoof app user-agents, borrow keys or otherwise get around a block.
- Tell the user which boards are scrapable, ranked.

## 2. Research the immigration policy
- Find the official source (government site, not law-firm blogs) for: priority/shortage occupation list, salary thresholds, and any employer sponsor/accreditation register.
- Check each is fetchable and parseable by script; note the page's update cadence. Policy is refreshed monthly (see `green_list` sync + `airflow/dags/green_list_sync.py` + the monthly cron in `scrape.yml`).
- If the rule is not a list (e.g. a salary threshold), say so; it needs its own model rather than `GreenListRole`.

## 3. Build (after the user picks boards)
1. `core/countries.py`: add the `Country`; make SEEK fields optional if the country has no SEEK.
2. Alembic migration inserting the country's categories (reversible; `uuidv7()` defaults). Then apply it locally, enable the category, run the country's green-list sync, and restart the backend container (see AGENTS.md) so the user can see it in the local UI.
3. Occupation/policy parser in `green_list/` plus its sync entry; register in `green_list/__main__.py`.
4. Each chosen board in `scraper/discovery.py` JOB_BOARDS + `scraper/enrichment.py` SOURCES (+ `jobs/sources.py` and a `source` constraint migration if it is a new source). `tests/test_job_sources.py` fails if one is missed.
5. Employer check in `scraper/enrichment.py` if the country has one (set `employer_check=True`).
6. Workflows/DAGs: `.github/workflows/scrape.yml` and `airflow/dags/`.
7. Frontend: country switcher, labels, currency/salary format; regenerate `frontend/src/api/schema.d.ts`.
8. Tests first (see AGENTS.md quality checks); run backend + frontend checks.
