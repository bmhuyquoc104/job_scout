from datetime import timedelta

import pendulum
from airflow.sdk import Param, dag, task, task_group

# The backend has its own venv because its SQLAlchemy 2.1 conflicts with Airflow's pins.
BACKEND_PYTHON = "/opt/job-scout/.venv/bin/python"
EXTERNAL = {"python": BACKEND_PYTHON, "expect_airflow": False, "expect_pendulum": False}
# One category at a time: each enrich launches Chromium for the Immigration NZ lookup.
ONE_AT_A_TIME = {**EXTERNAL, "max_active_tis_per_dagrun": 1}


def job_board_dag(source: str, title: str, schedule: str):
    """Same shape as the Employment Hero DAG: discover -> reconcile -> enrich, per category."""

    @dag(
        dag_id=f"job_scout_{source}_daily",
        description=f"{title}: read the IT search, reconcile, check employer eligibility.",
        schedule=schedule,  # Asia/Ho_Chi_Minh, after the SEEK (06:00) and Employment Hero (07:00) runs
        start_date=pendulum.datetime(2026, 11, 7, tz="Asia/Ho_Chi_Minh"),
        catchup=False,
        max_active_runs=1,
        default_args={"retries": 2, "retry_delay": timedelta(minutes=5)},
        # The search is "IT", so jobs are saved under each enabled country's ICT category.
        # "all" = every such category; or the slug of one (e.g. ict-au).
        params={"category": Param("all", type="string", pattern="^[a-z0-9-]+$")},
        tags=["job-scout"],
    )
    def job_board_daily():
        @task.external_python(**EXTERNAL)
        def enabled_categories(category: str, source: str) -> list[str]:
            import asyncio

            from job_scout.core.logging import configure_logging
            from job_scout.scraper.phases import enabled_category_slugs

            configure_logging()
            return asyncio.run(
                enabled_category_slugs(None if category == "all" else category, source)
            )

        @task.external_python(**ONE_AT_A_TIME)
        def discover(category: str, source: str) -> str:
            import asyncio

            from job_scout.core.logging import configure_logging
            from job_scout.scraper.phases import discover_phase

            configure_logging()
            return asyncio.run(discover_phase(category, source))

        @task.external_python(**ONE_AT_A_TIME)
        def reconcile(category: str, scan_started_at: str, source: str) -> None:
            import asyncio

            from job_scout.core.logging import configure_logging
            from job_scout.scraper.phases import reconcile_phase

            configure_logging()
            asyncio.run(reconcile_phase(category, scan_started_at, source))

        @task.external_python(**ONE_AT_A_TIME)
        def enrich(category: str, source: str) -> None:
            import asyncio

            from job_scout.core.logging import configure_logging
            from job_scout.scraper.phases import enrich_phase

            configure_logging()
            summary = asyncio.run(enrich_phase(category, source))
            if summary.failed:
                raise RuntimeError(f"{summary.failed} listing(s) failed enrichment")

        # A failed discovery stops only its own category's chain: a partial scan never reconciles.
        @task_group
        def sync(category: str):
            scan_started_at = discover(category, source)
            reconcile(category, scan_started_at, source) >> enrich(category, source)

        sync.expand(category=enabled_categories("{{ params.category }}", source))

    return job_board_daily()


indeed_daily = job_board_dag("indeed", "Indeed", "0 8 * * *")
glassdoor_daily = job_board_dag("glassdoor", "Glassdoor", "0 9 * * *")
jobbank_daily = job_board_dag("jobbank", "Job Bank (Canada)", "0 10 * * *")
arbeitnow_daily = job_board_dag("arbeitnow", "Arbeitnow (Germany)", "0 11 * * *")
