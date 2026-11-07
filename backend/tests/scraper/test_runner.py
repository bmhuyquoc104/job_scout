from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any
from uuid import UUID

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from job_scout.categories.models import Category
from job_scout.jobs.models import Job
from job_scout.scraper import immigration_client, runner, seek_client
from job_scout.scraper.models import JobDraft
from tests.scraper.helpers import source_listing


async def test_scrape_commits_draft_before_enrichment_and_upserts_clean_job(
    scrape_db: tuple[async_sessionmaker[AsyncSession], UUID],
    fake_browser: None,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:

    run = getattr(runner, "run", None)
    assert callable(run), "run must exist"
    factory, category_id = scrape_db
    current = source_listing()

    async def fetch_page(_: object, __: Category, page: int) -> dict[str, Any]:
        return (
            {"data": [current.copy()], "totalCount": 1}
            if page == 1
            else {"data": [], "totalCount": 0}
        )

    async def accreditation(_: object, __: str) -> dict[str, Any]:
        return {
            "Title": "Results",
            "results": (
                '[{"field_schema":{"raw":['
                '{"APIColumn":"nzbn","Value":"942903"},'
                '{"APIColumn":"tradingName","Value":"Example Trading"}]}},'
                '{"field_schema":{"raw":['
                '{"APIColumn":"nzbn","Value":"wrong-result"},'
                '{"APIColumn":"tradingName","Value":"Wrong Trading"}]}}]'
            ),
        }

    async def no_sleep(_: float) -> None:
        return None

    monkeypatch.setattr(seek_client, "fetch_search_page", fetch_page)
    monkeypatch.setattr(immigration_client, "check_accreditation", accreditation)
    monkeypatch.setattr(asyncio, "sleep", no_sleep)

    with caplog.at_level(logging.INFO, logger="job_scout.scraper"):
        first = await run(factory, category_id)
    first_seen_at: datetime
    async with factory() as session:
        job = await session.scalar(select(Job).where(Job.external_id == "seek-1"))
        draft = await session.scalar(select(JobDraft).where(JobDraft.external_id == "seek-1"))
        assert job is not None and draft is not None
        assert job.nzbn == "942903"
        assert job.trading_name == "Example Trading"
        assert job.job_description == "Example teaser\n\n• Example point"
        assert draft.status == "accredited"
        first_seen_at = job.first_seen_at

    current["title"] = "Senior Data Engineer"
    current["teaser"] = "Updated teaser"
    second = await run(factory, category_id)

    async with factory() as session:
        jobs = (await session.scalars(select(Job))).all()
        drafts = (await session.scalars(select(JobDraft))).all()
        assert len(jobs) == 1
        assert len(drafts) == 1
        assert jobs[0].position == "Senior Data Engineer"
        assert jobs[0].first_seen_at == first_seen_at
        assert jobs[0].job_description == "Updated teaser\n\n• Example point"

    assert (first.fetched, first.accredited, first.failed) == (1, 1, 0)
    assert (second.fetched, second.accredited, second.failed) == (1, 1, 0)
    assert "Starting SEEK discovery for Information & Communication Technology (ict)" in caplog.text
    assert "SEEK page 1 for ict: 1 listing(s) returned" in caplog.text
    assert "Discovered listing 1 (seek-1): Data Engineer" in caplog.text
    assert "Enriching listing 1/1 (seek-1): Data Engineer" in caplog.text
    assert "Finished listing 1/1 (seek-1): accredited" in caplog.text


async def test_run_does_not_count_exhausted_drafts_as_new_failures(
    scrape_db: tuple[async_sessionmaker[AsyncSession], UUID],
    fake_browser: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    factory, category_id = scrape_db
    async with factory() as session:
        session.add(
            JobDraft(
                category_id=category_id,
                external_id="stuck",
                raw_payload=source_listing("stuck"),
                status="failed",
                attempts=3,
            )
        )
        await session.commit()

    async def fetch_page(_: object, __: Category, page: int) -> dict[str, Any]:
        return (
            {"data": [source_listing("stuck")], "totalCount": 1}
            if page == 1
            else {"data": [], "totalCount": 0}
        )

    async def never_called(*_: object) -> dict[str, str]:
        raise AssertionError("an exhausted draft must not be retried")

    monkeypatch.setattr(seek_client, "fetch_search_page", fetch_page)
    monkeypatch.setattr(immigration_client, "check_accreditation", never_called)

    summary = await runner.run(factory, category_id)

    assert (summary.fetched, summary.failed) == (1, 0)
