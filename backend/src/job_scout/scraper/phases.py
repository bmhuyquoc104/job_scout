from datetime import datetime
from uuid import UUID

from sqlalchemy import select

from job_scout.categories.models import Category
from job_scout.core.countries import COUNTRIES
from job_scout.core.errors import AppError, ErrorCode
from job_scout.database import session_factory
from job_scout.scraper.discovery import discoverer, reconcile_active_jobs
from job_scout.scraper.enrichment import enrich
from job_scout.scraper.runner import run
from job_scout.scraper.summary import ScrapeSummary


async def _category_id(slug: str) -> UUID:
    async with session_factory() as session:
        category = await session.scalar(
            select(Category).where(Category.slug == slug, Category.enabled.is_(True))
        )
    if category is None:
        raise AppError(ErrorCode.CATEGORY_NOT_FOUND)
    return category.id


# The job boards are searched for "IT", so each country's ICT category is where that search lands.
BOARD_CLASSIFICATION = "6281"


async def enabled_category_slugs(only: str | None = None, source: str = "seek") -> list[str]:
    """Categories a run covers: all enabled ones (that the source has), or just `only`."""
    query = select(Category.slug).where(Category.enabled.is_(True)).order_by(Category.slug)
    if source == "employmenthero":
        query = query.where(Category.employmenthero_sector_id.is_not(None))
    elif source in ("indeed", "glassdoor"):
        query = query.where(Category.seek_classification_id == BOARD_CLASSIFICATION)
    elif source == "jobbank":  # Canada's government board, searched for IT jobs by NOC code
        query = query.where(
            Category.country == "CA", Category.seek_classification_id == BOARD_CLASSIFICATION
        )
    elif source == "arbeitnow":  # Germany's free job API, filtered to IT jobs
        query = query.where(
            Category.country == "DE", Category.seek_classification_id == BOARD_CLASSIFICATION
        )
    elif source == "seek":
        query = query.where(Category.country.in_([c for c, v in COUNTRIES.items() if v.seek_host]))
    async with session_factory() as session:
        slugs = list(await session.scalars(query))
    if only is None:
        return slugs
    if only not in slugs:
        raise AppError(ErrorCode.CATEGORY_NOT_FOUND)
    return [only]


async def discover_phase(slug: str, source: str = "seek") -> str:
    """Save listings as drafts; return the scan start time for the reconcile phase."""
    summary = await discoverer(source)(session_factory, await _category_id(slug))
    return summary.scan_started_at.isoformat()


async def reconcile_phase(slug: str, scan_started_at: str, source: str = "seek") -> None:
    """Mark jobs seen in the scan active and all others inactive."""
    category_id = await _category_id(slug)
    try:
        scan_start = datetime.fromisoformat(scan_started_at)
    except ValueError as exc:
        raise AppError(ErrorCode.INVALID_SCAN_TIMESTAMP, repr(scan_started_at)) from exc
    await reconcile_active_jobs(session_factory, category_id, scan_start, source)


async def enrich_phase(slug: str, source: str = "seek") -> ScrapeSummary:
    return await enrich(session_factory, await _category_id(slug), source)


async def run_all_phases(slug: str, source: str = "seek") -> ScrapeSummary:
    return await run(session_factory, await _category_id(slug), source)
