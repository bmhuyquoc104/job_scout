from datetime import timedelta

import pendulum
from airflow.sdk import dag, task

# The backend has its own venv because its SQLAlchemy 2.1 conflicts with Airflow's pins.
BACKEND_PYTHON = "/opt/job-scout/.venv/bin/python"
EXTERNAL = {"python": BACKEND_PYTHON, "expect_airflow": False, "expect_pendulum": False}


@dag(
    dag_id="job_scout_immigration_policy_monthly",
    description="Fetch each country's immigration policy data (priority-occupation lists and thresholds; see FETCHERS in job_scout.green_list.sync), store it, and record changes.",
    schedule="0 3 1 * *",  # 1st of each month, 03:00 Pacific/Auckland
    start_date=pendulum.datetime(2026, 11, 2, tz="Pacific/Auckland"),
    catchup=False,
    max_active_runs=1,
    default_args={"retries": 2, "retry_delay": timedelta(minutes=10)},
    tags=["job-scout"],
)
def job_scout_immigration_policy_monthly():
    @task.external_python(**EXTERNAL)
    def countries() -> list[str]:
        from job_scout.green_list.sync import FETCHERS

        return list(FETCHERS)

    # One task per country, so one source being down does not stop the others.
    @task.external_python(**EXTERNAL)
    def sync_green_list(country: str) -> dict:
        import asyncio
        from dataclasses import asdict

        from job_scout.core.logging import configure_logging
        from job_scout.green_list.sync import sync_green_list as run

        configure_logging()
        # The first run only stores a baseline; later runs record new, removed and tier-changed roles.
        return {"country": country, **asdict(asyncio.run(run(country=country)))}

    # The mapped results arrive as an Airflow type the backend's Python cannot read; make a plain list.
    @task
    def gather(summaries) -> list[dict]:
        return list(summaries)

    # Only runs when every country synced, like the daily summary; a failed task is the failure signal.
    @task.external_python(**EXTERNAL)
    def notify(summaries: list[dict]) -> None:
        import asyncio
        import time

        from job_scout.notifications.service import PolicyResult, notify_policy

        results = [PolicyResult(**summary) for summary in summaries]
        asyncio.run(notify_policy(results, int(time.time())))

    notify(gather(sync_green_list.expand(country=countries())))


job_scout_immigration_policy_monthly()
