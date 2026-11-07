# Project guidance

## Monorepo

- Backend: Python 3.15 managed with `uv`, FastAPI, async SQLAlchemy 2.1 + `asyncpg`, PostgreSQL 18+, Alembic, Ruff, pytest, and PostgreSQL 18 Testcontainers.
- Frontend: React + TypeScript + Vite + Material UI, managed with pnpm; preserve the Catppuccin Mocha theme in the MUI theme rather than hand-written component CSS.
- PostgreSQL schema changes must be made through reversible Alembic migrations; never edit the database schema manually.
- Use PostgreSQL `uuidv7()` server defaults for all application primary keys; use UUID foreign keys. Never use SQLite. Database tests must use Testcontainers with `postgres:18-alpine`, not a developer or application database.
- Use the domain-oriented layout in `backend/src/job_scout/`; keep routers, schemas, models, and services inside their owning domain.

## Async and data

- Do not use blocking network or database I/O inside `async def`; use async clients and `AsyncSession`.
- Reuse async HTTP clients within a scrape run, close browser/client/session resources, and do not hold a database transaction open while waiting on an external site.
- Preserve the `category` → `job_draft` → clean `job` flow. Draft source payloads before enrichment; only promote accredited records. Do not mark jobs inactive after an incomplete scrape.
- Keep the current Immigration NZ decision rule: exact `Title == "No Results"` means not accredited; any other response is accepted and the first result is used for NZBN/trading name. Store the full response for audit.

## Errors and exceptions

- Centralize application exception classes, stable error codes, and safe client-facing messages in `backend/src/job_scout/core/errors.py`.
- Register FastAPI exception handlers centrally with `add_exception_handler`; use the shared JSON error response shape.
- Routes and services must raise typed application exceptions. Do not create ad-hoc `HTTPException(detail=...)` messages or return raw exception text.
- Normalize request-validation errors centrally. Log unexpected exception details server-side and return only the catalog's safe internal-error message to clients.
- Persist only centralized error codes and safe messages in drafts; keep stack traces and raw third-party diagnostics in logs, not API responses.

## Quality checks

- Write a focused test first for each behavior change, run it to confirm the expected failure, then implement and rerun it.
- Use pytest for backend behavior and the project's async HTTPX `ASGITransport` fixture for API tests.
- Run `uv run ruff check src tests migrations ../frontend/e2e --config pyproject.toml` and `uv run ruff format --check src tests migrations ../frontend/e2e --config pyproject.toml` from `backend/`.
- Run `uv run pytest` from `backend/`; tests start an isolated PostgreSQL 18 Testcontainer and apply Alembic migrations automatically. Docker must be running. Frontend changes must pass `pnpm lint` and `pnpm build` from `frontend/`.
- Never commit unless explicitly requested. Keep `.env`, local databases, `node_modules`, build output, and agent workspaces out of source control.

## Agent and model selection

- Never select, pin, or override an AI model, including for subagents. Use only the model the user configured for the current session. Use another named model only after the user explicitly gives permission; model availability or a skill's recommendation is not permission.

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

When the user types `/graphify`, use the installed graphify skill or instructions before doing anything else.

Rules:
- Always use Graphify first when locating, searching, tracing, or checking repository files. If `graphify-out/graph.json` exists, run `graphify query "<question>"` before grep, other searches, or source-file reads; use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. If the graph is missing, build it with Graphify before searching. After Graphify locates the relevant files/lines, read the raw files directly when needed to verify or edit their contents. Include this rule in every subagent prompt that explores code.
- Dirty graphify-out/ files are expected after hooks or incremental updates; dirty graph files are not a reason to skip graphify. Only skip graphify if the task is about stale or incorrect graph output, or the user explicitly says not to use it.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
- A committed graphify-out/graph.json is rewritten whole on every build, so a large diff to it in a pull request is expected. Do not flag it as churn or suggest skipping the graph rebuild or its hooks.
