from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from job_scout.database import get_session
from job_scout.jobs import compare, locations, service, trends
from job_scout.jobs.schemas import (
    CategoryVisaStats,
    CountryVisaStats,
    JobComparison,
    JobDetail,
    JobFacets,
    JobQuery,
    LocationBreakdown,
    PaginatedJobs,
    SourceBreakdown,
    SourceOption,
    TrendSeries,
)
from job_scout.jobs.sources import JOB_SOURCES

router = APIRouter(tags=["jobs"])
SessionDep = Annotated[AsyncSession, Depends(get_session)]


@router.get("/categories/{category_id}/jobs", response_model=PaginatedJobs)
async def get_category_jobs(
    category_id: UUID, session: SessionDep, query: Annotated[JobQuery, Query()]
) -> PaginatedJobs:
    return await service.list_category_jobs(session, category_id, query)


@router.get("/categories/{category_id}/jobs/facets", response_model=JobFacets)
async def get_category_job_facets(category_id: UUID, session: SessionDep) -> JobFacets:
    return await service.get_job_facets(session, category_id)


@router.get("/categories/{category_id}/stats/trends", response_model=TrendSeries)
async def get_category_trends(
    category_id: UUID,
    session: SessionDep,
    days: Annotated[int, Query(ge=7, le=365)] = 30,
) -> TrendSeries:
    return await trends.get_trends(session, category_id, days)


@router.get("/categories/{category_id}/stats/locations", response_model=LocationBreakdown)
async def get_category_locations(category_id: UUID, session: SessionDep) -> LocationBreakdown:
    return await locations.get_location_breakdown(session, category_id)


@router.get("/categories/{category_id}/stats/sources", response_model=SourceBreakdown)
async def get_category_sources(category_id: UUID, session: SessionDep) -> SourceBreakdown:
    return await service.get_source_breakdown(session, category_id)


@router.get("/categories/{category_id}/stats/visa-sponsorship", response_model=CategoryVisaStats)
async def get_category_visa_stats(category_id: UUID, session: SessionDep) -> CategoryVisaStats:
    return await service.get_visa_stats(session, category_id)


@router.get("/sources", response_model=list[SourceOption])
async def get_sources() -> list[SourceOption]:
    return [SourceOption(source=source, label=label) for source, label in JOB_SOURCES.items()]


@router.get("/jobs/{job_id}", response_model=JobDetail)
async def get_job(job_id: UUID, session: SessionDep) -> JobDetail:
    return await service.get_job(session, job_id)


@router.get("/stats/visa-sponsorship", response_model=list[CountryVisaStats])
async def get_visa_sponsorship(session: SessionDep) -> list[CountryVisaStats]:
    return await compare.visa_by_country(session)


@router.get("/compare/jobs", response_model=JobComparison)
async def compare_jobs(
    session: SessionDep, title: Annotated[str, Query(min_length=1, max_length=200)]
) -> JobComparison:
    return await compare.compare_job(session, title)
