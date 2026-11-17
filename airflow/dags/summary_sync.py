import pendulum
from airflow.sdk import dag, task
from daily_assets import DAILY_DAGS, daily_asset, summarize_events

BACKEND_PYTHON = "/opt/job-scout/.venv/bin/python"
EXTERNAL = {"python": BACKEND_PYTHON, "expect_airflow": False, "expect_pendulum": False}


@dag(
    dag_id="job_scout_summary",
    description="Post the Discord summary once every daily DAG has succeeded.",
    schedule=[daily_asset(dag_id) for dag_id in DAILY_DAGS],
    start_date=pendulum.datetime(2026, 11, 17, tz="Asia/Ho_Chi_Minh"),
    catchup=False,
    max_active_runs=1,
    tags=["job-scout"],
)
def job_scout_summary():
    @task
    def collect(triggering_asset_events=None) -> dict:
        return summarize_events(e for events in triggering_asset_events.values() for e in events)

    @task.external_python(**EXTERNAL)
    def notify(info: dict) -> None:
        import asyncio

        from job_scout.notifications.service import notify_run, run_results

        async def post() -> None:
            results = await run_results(info["dags"], info["started"])
            await notify_run(results, info["started"], info["finished"])

        asyncio.run(post())

    notify(collect())


job_scout_summary()
