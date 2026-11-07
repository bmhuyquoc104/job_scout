FROM ghcr.io/astral-sh/uv:0.13.6 AS uv

FROM apache/airflow:3.3.2

USER root
COPY --from=uv /uv /uvx /usr/local/bin/
RUN mkdir -p /opt/job-scout /opt/ms-playwright && chown airflow:0 /opt/job-scout /opt/ms-playwright

# Layer order matters for build speed: the heavy steps (Python + dependencies, Chromium and its
# system libraries) only depend on these three files, so editing backend code does not redo them.
COPY --chown=airflow:0 backend/pyproject.toml backend/uv.lock backend/.python-version /opt/job-scout/

USER airflow
# The backend gets its own Python (from backend/.python-version, downloaded by uv) because
# Airflow's image tops out below it; external_python runs the tasks in this venv.
ENV UV_PROJECT_ENVIRONMENT=/opt/job-scout/.venv \
    UV_PYTHON_INSTALL_DIR=/opt/job-scout/python \
    PLAYWRIGHT_BROWSERS_PATH=/opt/ms-playwright
# Full path: the Airflow base image has an older uv earlier on PATH that only knows a 3.15 RC.
RUN /usr/local/bin/uv sync --project /opt/job-scout --locked --no-dev --no-install-project

USER root
RUN /opt/job-scout/.venv/bin/playwright install-deps chromium \
    && /opt/job-scout/.venv/bin/playwright install chromium \
    && chmod -R a+rX /opt/ms-playwright /opt/job-scout/python

# Source last: compose also mounts backend/src at runtime, so this layer is cheap to rebuild.
COPY --chown=airflow:0 backend/src /opt/job-scout/src

USER airflow
RUN /usr/local/bin/uv sync --project /opt/job-scout --locked --no-dev
