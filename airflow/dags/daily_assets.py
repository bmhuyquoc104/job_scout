from airflow.sdk import Asset, task

DAILY_DAGS = [
    "job_scout_seek_daily",
    "job_scout_employmenthero_daily",
    "job_scout_indeed_daily",
    "job_scout_glassdoor_daily",
    "job_scout_jobbank_daily",
    "job_scout_arbeitnow_daily",
    "job_scout_iamexpat_daily",
]


def daily_asset(dag_id: str) -> Asset:
    return Asset(f"job-scout://{dag_id}")


def finished(dag_id: str):
    """Last task of a daily DAG. It only runs when every category succeeded, so the asset
    updates only for a fully successful run; job_scout_summary waits for all of them."""
    asset = daily_asset(dag_id)

    @task(outlets=[asset], task_id="finished")
    def mark_finished(outlet_events=None, dag_run=None) -> None:
        outlet_events[asset].extra = {"started": int(dag_run.start_date.timestamp())}

    return mark_finished()


def summarize_events(events) -> dict:
    """Newest event per DAG. Keyed by asset name: an event sent through the REST API or UI has no
    source DAG, and an older day's leftover events must not stretch the duration."""
    latest = {}
    for event in events:
        dag_id = event.asset.name.removeprefix("job-scout://")
        if dag_id not in latest or event.timestamp > latest[dag_id].timestamp:
            latest[dag_id] = event
    return {
        "dags": sorted(latest),
        "started": min(
            int((e.extra or {}).get("started", e.timestamp.timestamp())) for e in latest.values()
        ),
        "finished": int(max(e.timestamp.timestamp() for e in latest.values())),
    }
