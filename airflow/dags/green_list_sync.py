from datetime import timedelta

import pendulum
from airflow.sdk import dag, task

# The backend has its own venv because its SQLAlchemy 2.1 conflicts with Airflow's pins.
BACKEND_PYTHON = "/opt/job-scout/.venv/bin/python"
EXTERNAL = {"python": BACKEND_PYTHON, "expect_airflow": False, "expect_pendulum": False}


@dag(
    dag_id="job_scout_green_list_monthly",
    description="Fetch Immigration NZ's Green List, store it, and record tier changes.",
    schedule="0 3 1 * *",  # 1st of each month, 03:00 Pacific/Auckland
    start_date=pendulum.datetime(2026, 11, 2, tz="Pacific/Auckland"),
    catchup=False,
    max_active_runs=1,
    default_args={"retries": 2, "retry_delay": timedelta(minutes=10)},
    tags=["job-scout"],
)
def job_scout_green_list_monthly():
    @task.external_python(**EXTERNAL)
    def sync_green_list() -> dict:
        import asyncio
        from dataclasses import asdict

        from job_scout.core.logging import configure_logging
        from job_scout.green_list.sync import sync_green_list as run

        configure_logging()
        # The first run only stores a baseline; later runs record new, removed and tier-changed roles.
        return asdict(asyncio.run(run()))

    sync_green_list()


job_scout_green_list_monthly()
