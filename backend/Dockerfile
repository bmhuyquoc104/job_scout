FROM ghcr.io/astral-sh/uv:0.13.6 AS uv

FROM python:3.15-slim
COPY --from=uv /uv /uvx /usr/local/bin/
WORKDIR /app
ENV UV_PROJECT_ENVIRONMENT=/app/.venv \
    UV_PYTHON_DOWNLOADS=never \
    PATH="/app/.venv/bin:$PATH"
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --locked --no-dev --no-install-project
COPY backend/ ./
RUN uv sync --locked --no-dev
# Non-root at runtime; the venv and code stay root-owned and world-readable.
RUN useradd --system --create-home app
USER app
# Default for hosting (Render sets PORT); docker compose overrides this. Migrations run separately, not on boot.
CMD ["sh", "-c", "exec uvicorn job_scout.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
