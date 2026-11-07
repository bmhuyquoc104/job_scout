from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from job_scout.scraper.models import JobDraft
from job_scout.scraper.persistence import save_drafts
from tests.scraper.helpers import source_listing


async def _status(factory: async_sessionmaker[AsyncSession]) -> str:
    async with factory() as session:
        return (await session.scalars(select(JobDraft.status))).one()


async def test_noisy_seek_fields_do_not_reset_a_completed_draft(
    scrape_db: tuple[async_sessionmaker[AsyncSession], UUID],
) -> None:
    factory, category_id = scrape_db
    first = {
        **source_listing("noisy"),
        "tracking": "a",
        "solMetadata": "x",
        "listingDateDisplay": "1d ago",
    }
    await save_drafts(factory, category_id, [("noisy", first)])
    async with factory() as session, session.begin():
        await session.execute(update(JobDraft).values(status="accredited"))

    # Only the per-request noise differs, so the draft must stay done.
    noisy = {**first, "tracking": "b", "solMetadata": "y", "listingDateDisplay": "2d ago"}
    await save_drafts(factory, category_id, [("noisy", noisy)])
    assert await _status(factory) == "accredited"

    # A real change still sends it back to be enriched.
    await save_drafts(factory, category_id, [("noisy", {**noisy, "teaser": "new text"})])
    assert await _status(factory) == "pending"
