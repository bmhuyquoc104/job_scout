from datetime import UTC, date, datetime, time, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import ColumnElement, Text, case, cast, func, not_, or_, select
from sqlalchemy.dialects.postgresql import array
from sqlalchemy.ext.asyncio import AsyncSession

from job_scout.categories.service import require_enabled_category
from job_scout.core.errors import AppError, ErrorCode
from job_scout.jobs.models import Job, JobEvent, JobEventType
from job_scout.jobs.schemas import (
    JobDetail,
    JobFacets,
    JobListItem,
    JobQuery,
    PaginatedJobs,
    SourceBreakdown,
    SourceCount,
)

# Closing time of the current closure; NULL while the job is open (even if it closed before).
_closed_at = case(
    (
        Job.is_active.is_(False),
        select(func.max(JobEvent.occurred_at))
        .where(JobEvent.job_id == Job.id, JobEvent.event_type == JobEventType.CLOSED)
        .correlate(Job)
        .scalar_subquery(),
    ),
    else_=None,
).label("closed_at")


def _contains(column: ColumnElement[str], term: str) -> ColumnElement[bool]:
    escaped = term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return column.ilike(f"%{escaped}%", escape="\\")


def _day_start(day: date) -> datetime:
    return datetime.combine(day, time.min, tzinfo=UTC)


_salary_midpoint = func.coalesce(
    (Job.annual_salary_min + Job.annual_salary_max) / 2.0,
    Job.annual_salary_max,
    Job.annual_salary_min,
)
_SORT_KEYS: dict[str, ColumnElement[Any]] = {
    "position": func.lower(Job.position),
    "company": func.lower(Job.company_name),
    "location": func.lower(Job.location),
    "arrangement": cast(Job.work_arrangements, Text),
    "work_type": cast(Job.work_types, Text),
    "status": Job.is_active,
    "salary": _salary_midpoint,
    "listed": Job.listed_at,
    "source": Job.source,
}


def _filters(category_id: UUID, query: JobQuery) -> list[ColumnElement[bool]]:
    filters = [Job.category_id == category_id]
    if query.status != "all":
        filters.append(Job.is_active.is_(query.status == "open"))
    if query.source:
        filters.append(Job.source == query.source)
    for column, term in (
        (Job.position, query.position),
        (Job.company_name, query.company),
        (Job.location, query.location),
    ):
        if term:
            filters.append(_contains(column, term))
    if query.arrangement:
        filters.append(Job.work_arrangements.has_any(array(query.arrangement)))
    if query.work_type:
        filters.append(Job.work_types.has_any(array(query.work_type)))
    has_salary = or_(Job.annual_salary_min.is_not(None), Job.annual_salary_max.is_not(None))
    if query.salary == "listed":
        filters.append(has_salary)
    elif query.salary == "unlisted":
        filters.append(not_(has_salary))
    if query.min_salary is not None:
        filters.append(
            func.coalesce(Job.annual_salary_max, Job.annual_salary_min) >= query.min_salary
        )
    if query.listed_from:
        filters.append(Job.listed_at >= _day_start(query.listed_from))
    if query.listed_to:
        filters.append(Job.listed_at < _day_start(query.listed_to + timedelta(days=1)))
    return filters


async def list_category_jobs(
    session: AsyncSession, category_id: UUID, query: JobQuery
) -> PaginatedJobs:
    category = await require_enabled_category(session, category_id)

    filters = _filters(category_id, query)
    total = await session.scalar(select(func.count()).select_from(Job).where(*filters)) or 0
    key = _SORT_KEYS[query.sort]
    primary = key.asc() if query.order == "asc" else key.desc()
    rows = (
        await session.execute(
            select(Job, _closed_at)
            .where(*filters)
            # Missing values sort last in both directions; ties fall back to newest first.
            .order_by(primary.nulls_last(), Job.listed_at.desc().nulls_last(), Job.id.desc())
            .limit(query.limit)
            .offset(query.offset)
        )
    ).all()
    return PaginatedJobs(
        items=[
            JobListItem.model_validate(job).model_copy(update={"closed_at": closed_at})
            for job, closed_at in rows
        ],
        total=total,
        limit=query.limit,
        offset=query.offset,
        category_name=category.name,
        category_slug=category.slug,
    )


async def get_job_facets(session: AsyncSession, category_id: UUID) -> JobFacets:
    await require_enabled_category(session, category_id)
    rows = (
        await session.execute(
            select(Job.work_arrangements, Job.work_types).where(Job.category_id == category_id)
        )
    ).all()
    return JobFacets(
        arrangements=sorted({value for arrangements, _ in rows for value in arrangements}),
        work_types=sorted({value for _, work_types in rows for value in work_types}),
    )


async def get_job(session: AsyncSession, job_id: UUID) -> JobDetail:
    row = (await session.execute(select(Job, _closed_at).where(Job.id == job_id))).one_or_none()
    if row is None:
        raise AppError(ErrorCode.JOB_NOT_FOUND)
    job, closed_at = row
    return JobDetail.model_validate(job).model_copy(update={"closed_at": closed_at})


async def get_source_breakdown(session: AsyncSession, category_id: UUID) -> SourceBreakdown:
    await require_enabled_category(session, category_id)
    rows = (
        await session.execute(
            select(Job.source, func.count())
            .where(Job.category_id == category_id, Job.is_active.is_(True))
            .group_by(Job.source)
            .order_by(func.count().desc(), Job.source)
        )
    ).all()
    return SourceBreakdown(
        sources=[SourceCount(source=source, count=count) for source, count in rows],
        total_open=sum(count for _, count in rows),
    )
