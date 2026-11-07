from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from job_scout.categories.models import Category
from job_scout.jobs.models import Job
from job_scout.scraper import discovery, runner, seek_client
from job_scout.scraper.models import JobDraft
from tests.scraper.helpers import make_job, source_listing


async def test_reconcile_reactivates_seen_jobs_and_inactivates_absent_jobs(
    scrape_db: tuple[async_sessionmaker[AsyncSession], UUID],
) -> None:
    from datetime import timedelta

    factory, category_id = scrape_db
    scan_started_at = datetime.now(UTC)
    async with factory() as session:
        seen_job = make_job(category_id, "seen-again")
        seen_job.is_active = False
        absent_job = make_job(category_id, "not-seen")
        session.add_all(
            [
                seen_job,
                absent_job,
                JobDraft(
                    category_id=category_id,
                    external_id="seen-again",
                    raw_payload=source_listing("seen-again"),
                    last_seen_at=scan_started_at + timedelta(seconds=1),
                ),
                JobDraft(
                    category_id=category_id,
                    external_id="not-seen",
                    raw_payload=source_listing("not-seen"),
                    last_seen_at=scan_started_at - timedelta(days=1),
                ),
            ]
        )
        await session.commit()

    await discovery.reconcile_active_jobs(factory, category_id, scan_started_at)

    async with factory() as session:
        seen_job = await session.scalar(select(Job).where(Job.external_id == "seen-again"))
        absent_job = await session.scalar(select(Job).where(Job.external_id == "not-seen"))
        assert seen_job is not None and seen_job.is_active is True
        assert absent_job is not None and absent_job.is_active is False


async def test_empty_complete_scrape_marks_jobs_inactive_without_deleting_them(
    scrape_db: tuple[async_sessionmaker[AsyncSession], UUID],
    fake_browser: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:

    run = getattr(runner, "run", None)
    assert callable(run), "run must exist"
    factory, category_id = scrape_db
    async with factory() as session:
        session.add_all([make_job(category_id, "old-1"), make_job(category_id, "old-2")])
        await session.commit()

    async def empty_page(_: object, __: Category, page: int) -> dict[str, Any]:
        assert page == 1
        return {"data": [], "totalCount": 0}

    async def no_sleep(_: float) -> None:
        return None

    monkeypatch.setattr(seek_client, "fetch_search_page", empty_page)
    monkeypatch.setattr(asyncio, "sleep", no_sleep)

    summary = await run(factory, category_id)

    async with factory() as session:
        jobs = (await session.scalars(select(Job).order_by(Job.external_id))).all()
        assert [job.external_id for job in jobs] == ["old-1", "old-2"]
        assert all(not job.is_active for job in jobs)
    assert summary.fetched == 0
