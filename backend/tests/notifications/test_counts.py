from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from job_scout.categories.models import Category
from job_scout.jobs.models import Job, JobEvent
from job_scout.notifications.service import event_counts, run_results
from tests.scraper.helpers import make_job

SINCE = datetime(2026, 11, 17, 10, 0, tzinfo=UTC)


@pytest.fixture
async def db(async_test_database_url: str) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    engine = create_async_engine(async_test_database_url)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        await session.execute(delete(JobEvent))
        await session.execute(delete(Job))
        category = await session.scalar(select(Category).where(Category.slug == "ict"))
        assert category is not None
        for external_id, source, event, when in [
            ("a", "seek", "new", SINCE + timedelta(minutes=5)),
            ("b", "seek", "new", SINCE + timedelta(minutes=6)),
            ("c", "seek", "closed", SINCE + timedelta(minutes=7)),
            ("d", "seek", "new", SINCE - timedelta(hours=1)),  # before this run
            ("e", "indeed", "updated", SINCE + timedelta(minutes=8)),  # not counted
            ("f", "indeed", "new", SINCE + timedelta(minutes=9)),
        ]:
            job = make_job(category.id, external_id)
            job.source = source
            session.add(job)
            await session.flush()
            session.add(
                JobEvent(job_id=job.id, category_id=category.id, event_type=event, occurred_at=when)
            )
        await session.commit()
    try:
        yield factory
    finally:
        async with factory() as session:
            await session.execute(delete(JobEvent))
            await session.execute(delete(Job))
            await session.commit()
        await engine.dispose()


async def test_event_counts_are_per_source_since_the_run_started(
    db: async_sessionmaker[AsyncSession],
) -> None:
    assert await event_counts(SINCE, db) == {"seek": (2, 1), "indeed": (1, 0)}


async def test_run_results_attach_counts_to_each_dag(
    db: async_sessionmaker[AsyncSession],
) -> None:
    results = await run_results(
        ["job_scout_seek_daily", "job_scout_iamexpat_daily"], int(SINCE.timestamp()), db
    )
    assert [(r.dag, r.state, r.new, r.closed) for r in results] == [
        ("job_scout_seek_daily", "success", 2, 1),
        ("job_scout_iamexpat_daily", "success", 0, 0),
    ]
