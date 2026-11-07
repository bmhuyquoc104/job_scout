from collections import Counter
from collections.abc import Iterable
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from job_scout.categories.service import require_enabled_category
from job_scout.jobs.models import Job
from job_scout.jobs.schemas import LocationBreakdown, LocationCount
from job_scout.scraper.normalization import region_of


def build_location_breakdown(rows: Iterable[tuple[str, int]]) -> LocationBreakdown:
    """Roll (location label, jobs) up into regions: biggest first, ties by name."""
    regions: Counter[str] = Counter()
    for location, count in rows:
        regions[region_of(location)] += count
    ordered = sorted(regions.items(), key=lambda item: (-item[1], item[0]))
    return LocationBreakdown(
        regions=[LocationCount(region=region, count=count) for region, count in ordered],
        total_open=sum(regions.values()),
    )


async def get_location_breakdown(session: AsyncSession, category_id: UUID) -> LocationBreakdown:
    await require_enabled_category(session, category_id)
    rows = (
        await session.execute(
            select(Job.location, func.count())
            .where(Job.category_id == category_id, Job.is_active.is_(True))
            .group_by(Job.location)
        )
    ).all()
    return build_location_breakdown([(location, count) for location, count in rows])
