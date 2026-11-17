from datetime import timedelta

import pendulum
from airflow.sdk import Param, dag, task, task_group
from daily_assets import finished

# The backend has its own venv because its SQLAlchemy 2.1 conflicts with Airflow's pins.
BACKEND_PYTHON = "/opt/job-scout/.venv/bin/python"
EXTERNAL = {"python": BACKEND_PYTHON, "expect_airflow": False, "expect_pendulum": False}
# One category at a time: each enrich launches Chromium for the Immigration NZ lookup.
ONE_AT_A_TIME = {**EXTERNAL, "max_active_tis_per_dagrun": 1}


@dag(
    dag_id="job_scout_employmenthero_daily",
    description="Employment Hero: read each category's job pages, reconcile, check employer eligibility.",
    schedule="0 17 * * *",  # all daily DAGs start together, Asia/Ho_Chi_Minh
    start_date=pendulum.datetime(2026, 11, 7, tz="Asia/Ho_Chi_Minh"),
    catchup=False,
    max_active_runs=1,
    default_args={"retries": 2, "retry_delay": timedelta(minutes=5)},
    # "all" = every enabled category Employment Hero covers; or the slug of one of them.
    params={"category": Param("all", type="string", pattern="^[a-z0-9-]+$")},
    tags=["job-scout"],
)
def job_scout_employmenthero_daily():
    @task.external_python(**EXTERNAL)
    def enabled_categories(category: str) -> list[str]:
        import asyncio

        from job_scout.core.logging import configure_logging
        from job_scout.scraper.phases import enabled_category_slugs

        configure_logging()
        return asyncio.run(
            enabled_category_slugs(None if category == "all" else category, "employmenthero")
        )

    @task.external_python(**ONE_AT_A_TIME)
    def discover(category: str) -> str:
        import asyncio

        from job_scout.core.logging import configure_logging
        from job_scout.scraper.phases import discover_phase

        configure_logging()
        return asyncio.run(discover_phase(category, "employmenthero"))

    @task.external_python(**ONE_AT_A_TIME)
    def reconcile(category: str, scan_started_at: str) -> None:
        import asyncio

        from job_scout.core.logging import configure_logging
        from job_scout.scraper.phases import reconcile_phase

        configure_logging()
        asyncio.run(reconcile_phase(category, scan_started_at, "employmenthero"))

    @task.external_python(**ONE_AT_A_TIME)
    def enrich(category: str) -> None:
        import asyncio

        from job_scout.core.logging import configure_logging
        from job_scout.scraper.phases import enrich_phase

        configure_logging()
        summary = asyncio.run(enrich_phase(category, "employmenthero"))
        # Some bad listings are skipped (each is retried next run, up to 3 times); only a run
        # where every listing failed means something systemic, so only that fails the task.
        if summary.failed and summary.failed == summary.fetched:
            raise RuntimeError(f"all {summary.failed} listing(s) failed enrichment")

    # A failed discovery stops only its own category's chain: a partial scan never reconciles.
    @task_group
    def sync(category: str):
        scan_started_at = discover(category)
        reconcile(category, scan_started_at) >> enrich(category)

    sync.expand(category=enabled_categories("{{ params.category }}")) >> finished("job_scout_employmenthero_daily")


job_scout_employmenthero_daily()
