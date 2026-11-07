from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from job_scout.scraper.discovery import discoverer, reconcile_active_jobs
from job_scout.scraper.enrichment import enrich
from job_scout.scraper.models import JobDraft
from job_scout.scraper.summary import ScrapeSummary


async def run(
    session_factory: async_sessionmaker[AsyncSession], category_id: UUID, source: str = "seek"
) -> ScrapeSummary:
    discovery = await discoverer(source)(session_factory, category_id)
    await reconcile_active_jobs(session_factory, category_id, discovery.scan_started_at, source)
    enrichment = await enrich(session_factory, category_id, source)

    async with session_factory() as session:
        outcomes = (
            await session.execute(
                select(JobDraft.status, func.count())
                .where(
                    JobDraft.category_id == category_id,
                    JobDraft.source == source,
                    JobDraft.last_seen_at >= discovery.scan_started_at,
                )
                .group_by(JobDraft.status)
            )
        ).all()
    counts = dict(outcomes)
    return ScrapeSummary(
        category_id=category_id,
        fetched=discovery.fetched,
        accredited=counts.get("accredited", 0),
        not_accredited=counts.get("not_accredited", 0),
        failed=enrichment.failed,
    )
