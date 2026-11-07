from collections import defaultdict
from collections.abc import Iterable
from datetime import date, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from job_scout.categories.service import require_enabled_category
from job_scout.jobs.models import Job, JobEvent
from job_scout.jobs.schemas import TrendPoint, TrendSeries
from job_scout.scraper.normalization import SENIORITY_LEVELS

TIMEZONE = "Pacific/Auckland"
# What each event does to the number of open jobs ("updated" changes nothing).
_OPEN_DELTA = {"new": 1, "reopened": 1, "closed": -1}

# (local day, seniority, event type, how many)
EventRow = tuple[date, str, str, int]


def build_trend(rows: Iterable[EventRow], today: date, days: int) -> TrendSeries:
    """Replay events into a daily series of open jobs, new jobs and closures.

    The window is the last `days` days, but it starts at the first event if that is later,
    and events from before the window still count towards its starting total.
    """
    by_day: dict[date, list[EventRow]] = defaultdict(list)
    for row in rows:
        by_day[row[0]].append(row)
    levels = list(SENIORITY_LEVELS)
    if not by_day:
        return TrendSeries(points=[], seniority_levels=levels, history_starts=None)

    first_day = min(by_day)
    emit_from = max(today - timedelta(days=days - 1), first_day)
    running = dict.fromkeys(levels, 0)
    points: list[TrendPoint] = []
    day = first_day
    while day <= today:
        new = closed = 0
        for _, seniority, event_type, count in by_day.get(day, []):
            level = seniority if seniority in running else "unspecified"
            running[level] += _OPEN_DELTA.get(event_type, 0) * count
            new += count if event_type == "new" else 0
            closed += count if event_type == "closed" else 0
        if day >= emit_from:
            points.append(
                TrendPoint(
                    date=day,
                    total_open=sum(running.values()),
                    new=new,
                    closed=closed,
                    by_seniority=dict(running),
                )
            )
        day += timedelta(days=1)
    return TrendSeries(points=points, seniority_levels=levels, history_starts=first_day)


async def get_trends(session: AsyncSession, category_id: UUID, days: int) -> TrendSeries:
    await require_enabled_category(session, category_id)
    local_day = func.date(func.timezone(TIMEZONE, JobEvent.occurred_at))
    rows = (
        await session.execute(
            select(local_day, Job.seniority, JobEvent.event_type, func.count())
            .join(Job, Job.id == JobEvent.job_id)
            .where(JobEvent.category_id == category_id)
            .group_by(local_day, Job.seniority, JobEvent.event_type)
        )
    ).all()
    today = await session.scalar(select(func.date(func.timezone(TIMEZONE, func.now()))))
    return build_trend([tuple(row) for row in rows], today, days)  # type: ignore[arg-type]
