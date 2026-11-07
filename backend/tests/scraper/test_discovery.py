from __future__ import annotations

import asyncio
from typing import Any
from uuid import UUID

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from job_scout.categories.models import Category
from job_scout.core.errors import AppError, ErrorCode
from job_scout.jobs.models import Job
from job_scout.scraper import discovery, immigration_client, runner, seek_client
from job_scout.scraper.models import JobDraft
from tests.scraper.helpers import make_job, source_listing


async def test_discovery_persists_pending_drafts_without_enrichment(
    scrape_db: tuple[async_sessionmaker[AsyncSession], UUID],
    monkeypatch: pytest.MonkeyPatch,
) -> None:

    factory, category_id = scrape_db
    calls: list[int] = []

    async def fetch_page(_: object, __: Category, page: int) -> dict[str, Any]:
        calls.append(page)
        return (
            {"data": [source_listing("discovered-only")], "totalCount": 1}
            if page == 1
            else {"data": [], "totalCount": 0}
        )

    async def unexpected_enrichment(*_: object) -> str:
        raise AssertionError("discovery must not enrich listings")

    monkeypatch.setattr(seek_client, "fetch_search_page", fetch_page)
    monkeypatch.setattr(immigration_client, "check_accreditation", unexpected_enrichment)

    summary = await discovery.discover(factory, category_id)

    async with factory() as session:
        draft = await session.scalar(
            select(JobDraft).where(JobDraft.external_id == "discovered-only")
        )
        assert draft is not None
        assert draft.raw_payload["title"] == "Data Engineer"
        assert draft.status == "pending"
    assert calls == [1, 2]
    assert summary.fetched == 1
    assert summary.scan_started_at.tzinfo is not None


async def test_pagination_continues_until_seek_returns_zero_total_count(
    scrape_db: tuple[async_sessionmaker[AsyncSession], UUID],
    fake_browser: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:

    run = getattr(runner, "run", None)
    assert callable(run), "run must exist"
    factory, category_id = scrape_db
    calls: list[int] = []

    async def fetch_page(_: object, __: Category, page: int) -> dict[str, Any]:
        calls.append(page)
        if page < 3:
            return {"data": [source_listing(f"seek-page-{page}")], "totalCount": 1}
        return {"data": [], "totalCount": 0}

    async def accreditation(_: object, __: str) -> dict[str, str]:
        return {"Title": "No Results"}

    async def no_sleep(_: float) -> None:
        return None

    monkeypatch.setattr(seek_client, "fetch_search_page", fetch_page)
    monkeypatch.setattr(immigration_client, "check_accreditation", accreditation)
    monkeypatch.setattr(asyncio, "sleep", no_sleep)

    summary = await run(factory, category_id)

    async with factory() as session:
        drafts = (await session.scalars(select(JobDraft).order_by(JobDraft.external_id))).all()
        assert [draft.external_id for draft in drafts] == ["seek-page-1", "seek-page-2"]
    assert calls == [1, 2, 3]
    assert summary.fetched == 2


async def test_pagination_stops_at_maximum_page_limit(
    scrape_db: tuple[async_sessionmaker[AsyncSession], UUID],
    fake_browser: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import httpx

    from job_scout.core.errors import AppError

    run = getattr(runner, "run", None)
    assert callable(run), "run must exist"
    factory, category_id = scrape_db
    calls: list[int] = []
    monkeypatch.setattr(discovery, "MAX_SEEK_PAGES", 2)

    async def fetch_page(_: object, __: Category, page: int) -> dict[str, Any]:
        calls.append(page)
        if page > 2:
            raise httpx.ConnectError("the sentinel page was never returned")
        return {"data": [source_listing(f"seek-page-{page}")], "totalCount": 1}

    async def accreditation(_: object, __: str) -> dict[str, str]:
        return {"Title": "No Results"}

    async def no_sleep(_: float) -> None:
        return None

    monkeypatch.setattr(seek_client, "fetch_search_page", fetch_page)
    monkeypatch.setattr(immigration_client, "check_accreditation", accreditation)
    monkeypatch.setattr(asyncio, "sleep", no_sleep)

    with pytest.raises(AppError):
        await run(factory, category_id)

    assert calls == [1, 2]


async def test_pagination_failure_does_not_inactivate_unseen_jobs(
    scrape_db: tuple[async_sessionmaker[AsyncSession], UUID],
    fake_browser: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import httpx

    from job_scout.core.errors import AppError

    run = getattr(runner, "run", None)
    assert callable(run), "run must exist"
    factory, category_id = scrape_db
    async with factory() as session:
        session.add(make_job(category_id, "old-unseen"))
        await session.commit()

    async def fetch_page(_: object, __: Category, page: int) -> dict[str, Any]:
        if page == 1:
            return {"data": [source_listing("seek-current")], "totalCount": 23}
        raise httpx.ConnectError("simulated SEEK outage")

    async def accreditation(_: object, __: str) -> dict[str, str]:
        return {"Title": "No Results"}

    async def no_sleep(_: float) -> None:
        return None

    monkeypatch.setattr(seek_client, "fetch_search_page", fetch_page)
    monkeypatch.setattr(immigration_client, "check_accreditation", accreditation)
    monkeypatch.setattr(asyncio, "sleep", no_sleep)

    with pytest.raises(AppError):
        await run(factory, category_id)

    async with factory() as session:
        job = await session.scalar(select(Job).where(Job.external_id == "old-unseen"))
        assert job is not None
        assert job.is_active is True


async def test_repeated_nonempty_pages_fail_closed_instead_of_looping_forever(
    scrape_db: tuple[async_sessionmaker[AsyncSession], UUID],
    fake_browser: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from job_scout.core.errors import AppError

    run = getattr(runner, "run", None)
    assert callable(run), "run must exist"
    factory, category_id = scrape_db
    calls: list[int] = []

    async def repeated_page(_: object, __: Category, page_number: int) -> dict[str, Any]:
        calls.append(page_number)
        if page_number > 2:
            raise AssertionError("repeated page was requested instead of failing closed")
        return {"data": [source_listing("repeated")], "totalCount": 46}

    async def accreditation(_: object, __: str) -> dict[str, str]:
        return {"Title": "No Results"}

    async def no_sleep(_: float) -> None:
        return None

    monkeypatch.setattr(seek_client, "fetch_search_page", repeated_page)
    monkeypatch.setattr(immigration_client, "check_accreditation", accreditation)
    monkeypatch.setattr(asyncio, "sleep", no_sleep)

    with pytest.raises(AppError):
        await run(factory, category_id)

    assert calls == [1, 2]


async def test_discovery_logs_which_response_check_failed(
    scrape_db: tuple[async_sessionmaker[AsyncSession], UUID],
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    factory, category_id = scrape_db

    async def fetch_page(_: object, __: Category, ___: int) -> dict[str, Any]:
        return {"data": [], "totalCount": "many"}

    monkeypatch.setattr(seek_client, "fetch_search_page", fetch_page)

    with pytest.raises(AppError) as error:
        await discovery.discover(factory, category_id)

    assert error.value.code is ErrorCode.SCRAPE_SOURCE_ERROR
    assert "totalCount" in caplog.text


async def test_drafts_are_saved_once_per_seek_page(
    scrape_db: tuple[async_sessionmaker[AsyncSession], UUID],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    factory, category_id = scrape_db
    batches: list[int] = []
    original = discovery.save_drafts

    async def spy(session_factory: object, cat_id: UUID, rows: list[tuple[str, dict]]) -> None:
        batches.append(len(rows))
        await original(session_factory, cat_id, rows)

    async def fetch_page(_: object, __: Category, page: int) -> dict[str, Any]:
        if page > 2:
            return {"data": [], "totalCount": 0}
        return {
            "data": [source_listing(f"p{page}-{n}") for n in range(3)],
            "totalCount": 6,
        }

    monkeypatch.setattr(discovery, "save_drafts", spy)
    monkeypatch.setattr(seek_client, "fetch_search_page", fetch_page)

    summary = await discovery.discover(factory, category_id)

    assert batches == [3, 3]
    assert summary.fetched == 6
    async with factory() as session:
        assert len((await session.scalars(select(JobDraft))).all()) == 6


async def test_changed_payload_resets_attempts_and_makes_a_draft_pending_again(
    scrape_db: tuple[async_sessionmaker[AsyncSession], UUID],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    factory, category_id = scrape_db
    async with factory() as session:
        session.add(
            JobDraft(
                category_id=category_id,
                external_id="reset-me",
                raw_payload={**source_listing("reset-me"), "title": "Old title"},
                status="failed",
                attempts=3,
            )
        )
        await session.commit()

    async def fetch_page(_: object, __: Category, page: int) -> dict[str, Any]:
        return (
            {"data": [source_listing("reset-me")], "totalCount": 1}
            if page == 1
            else {"data": [], "totalCount": 0}
        )

    monkeypatch.setattr(seek_client, "fetch_search_page", fetch_page)

    await discovery.discover(factory, category_id)

    async with factory() as session:
        draft = await session.scalar(select(JobDraft).where(JobDraft.external_id == "reset-me"))
        assert draft is not None
        assert (draft.status, draft.attempts) == ("pending", 0)
