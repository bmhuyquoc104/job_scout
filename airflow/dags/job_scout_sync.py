from datetime import timedelta

import pendulum
from airflow.sdk import Param, dag, task, task_group

# The backend has its own venv because its SQLAlchemy 2.1 conflicts with Airflow's pins.
BACKEND_PYTHON = "/opt/job-scout/.venv/bin/python"
EXTERNAL = {"python": BACKEND_PYTHON, "expect_airflow": False, "expect_pendulum": False}
# One category at a time: each enrich launches Chromium, and SEEK / Immigration NZ get one client.
ONE_AT_A_TIME = {**EXTERNAL, "max_active_tis_per_dagrun": 1}


@dag(
    dag_id="job_scout_daily_sync",
    description="For each enabled category: discover SEEK listings, reconcile active jobs, enrich changed drafts.",
    schedule="0 2 * * *",
    start_date=pendulum.datetime(2026, 10, 18, tz="Pacific/Auckland"),
    catchup=False,
    max_active_runs=1,
    default_args={"retries": 2, "retry_delay": timedelta(minutes=5)},
    # "all" = every enabled category; or the slug of one enabled category.
    params={"category": Param("all", type="string", pattern="^[a-z0-9-]+$")},
    tags=["job-scout"],
)
def job_scout_daily_sync():
    @task.external_python(**EXTERNAL)
    def enabled_categories(category: str) -> list[str]:
        import asyncio

        from job_scout.core.logging import configure_logging
        from job_scout.scraper.phases import enabled_category_slugs

        configure_logging()
        return asyncio.run(enabled_category_slugs(None if category == "all" else category))

    @task.external_python(**ONE_AT_A_TIME)
    def discover(category: str) -> str:
        import asyncio

        from job_scout.core.logging import configure_logging
        from job_scout.scraper.phases import discover_phase

        configure_logging()
        return asyncio.run(discover_phase(category))

    @task.external_python(**ONE_AT_A_TIME)
    def reconcile(category: str, scan_started_at: str) -> None:
        import asyncio

        from job_scout.core.logging import configure_logging
        from job_scout.scraper.phases import reconcile_phase

        configure_logging()
        asyncio.run(reconcile_phase(category, scan_started_at))

    @task.external_python(**ONE_AT_A_TIME)
    def enrich(category: str) -> None:
        import asyncio

        from job_scout.core.logging import configure_logging
        from job_scout.scraper.phases import enrich_phase

        configure_logging()
        summary = asyncio.run(enrich_phase(category))
        if summary.failed:
            raise RuntimeError(f"{summary.failed} listing(s) failed enrichment")

    # A failed category stops only its own chain (a partial scan never reconciles), not the others.
    @task_group
    def sync(category: str):
        scan_started_at = discover(category)
        reconcile(category, scan_started_at) >> enrich(category)

    sync.expand(category=enabled_categories("{{ params.category }}"))


job_scout_daily_sync()
