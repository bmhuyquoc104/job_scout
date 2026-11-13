from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import pytest
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from job_scout.categories.models import Category
from job_scout.core.errors import AppError, ErrorCode
from job_scout.jobs.models import Job
from job_scout.scraper import enrichment, immigration_client, runner, seek_client
from job_scout.scraper.models import JobDraft
from tests.scraper.helpers import make_job, scrape_one, source_listing


async def test_unchanged_seek_payload_is_not_reenriched(
    scrape_db: tuple[async_sessionmaker[AsyncSession], UUID],
    fake_browser: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:

    factory, category_id = scrape_db
    description_calls = 0
    accreditation_calls = 0

    async def fetch_page(_: object, __: Category, page: int) -> dict[str, Any]:
        return (
            {"data": [source_listing("unchanged-job")], "totalCount": 1}
            if page == 1
            else {"data": [], "totalCount": 0}
        )

    async def accreditation(_: object, __: str) -> dict[str, str]:
        nonlocal accreditation_calls
        accreditation_calls += 1
        return {"Title": "No Results"}

    async def no_sleep(_: float) -> None:
        return None

    monkeypatch.setattr(seek_client, "fetch_search_page", fetch_page)
    monkeypatch.setattr(immigration_client, "check_accreditation", accreditation)
    monkeypatch.setattr(asyncio, "sleep", no_sleep)

    await runner.run(factory, category_id)
    second = await runner.run(factory, category_id)

    async with factory() as session:
        drafts = (await session.scalars(select(JobDraft))).all()
        assert len(drafts) == 1
        assert drafts[0].status == "ineligible"
    assert (description_calls, accreditation_calls) == (0, 1)
    assert second.fetched == 1
    assert second.ineligible == 1


async def test_enrichment_retries_failed_drafts_but_skips_completed_drafts(
    scrape_db: tuple[async_sessionmaker[AsyncSession], UUID],
    fake_browser: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:

    factory, category_id = scrape_db
    async with factory() as session:
        session.add_all(
            [
                JobDraft(
                    category_id=category_id,
                    external_id="retry-this",
                    raw_payload=source_listing("retry-this"),
                    status="failed",
                ),
                JobDraft(
                    category_id=category_id,
                    external_id="already-done",
                    raw_payload=source_listing("already-done"),
                    status="ineligible",
                ),
            ]
        )
        await session.commit()
    descriptions: list[str] = []

    async def accreditation(_: object, __: str) -> dict[str, str]:
        return {"Title": "No Results"}

    async def no_sleep(_: float) -> None:
        return None

    monkeypatch.setattr(immigration_client, "check_accreditation", accreditation)
    monkeypatch.setattr(asyncio, "sleep", no_sleep)

    summary = await enrichment.enrich(factory, category_id)

    async with factory() as session:
        retry = await session.scalar(select(JobDraft).where(JobDraft.external_id == "retry-this"))
        done = await session.scalar(select(JobDraft).where(JobDraft.external_id == "already-done"))
        assert retry is not None and retry.status == "ineligible"
        assert done is not None and done.status == "ineligible"
    assert descriptions == []
    assert (summary.fetched, summary.ineligible) == (1, 1)


async def test_non_accredited_result_preserves_existing_clean_job(
    scrape_db: tuple[async_sessionmaker[AsyncSession], UUID],
    fake_browser: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:

    run = getattr(runner, "run", None)
    assert callable(run), "run must exist"
    factory, category_id = scrape_db
    async with factory() as session:
        session.add(make_job(category_id, "seek-2", "Existing job"))
        await session.commit()

    async def fetch_page(_: object, __: Category, page: int) -> dict[str, Any]:
        return (
            {"data": [source_listing("seek-2")], "totalCount": 1}
            if page == 1
            else {"data": [], "totalCount": 0}
        )

    async def accreditation(_: object, __: str) -> dict[str, str]:
        return {"Title": "No Results"}

    async def no_sleep(_: float) -> None:
        return None

    monkeypatch.setattr(seek_client, "fetch_search_page", fetch_page)
    monkeypatch.setattr(immigration_client, "check_accreditation", accreditation)
    monkeypatch.setattr(asyncio, "sleep", no_sleep)

    summary = await run(factory, category_id)

    async with factory() as session:
        job = await session.scalar(select(Job).where(Job.external_id == "seek-2"))
        draft = await session.scalar(select(JobDraft).where(JobDraft.external_id == "seek-2"))
        assert job is not None and draft is not None
        assert job.position == "Existing job"
        assert job.job_description == "Old description"
        assert job.is_active is True
        assert draft.status == "ineligible"
    assert (summary.ineligible, summary.eligible) == (1, 0)


async def test_exhausted_accreditation_retries_are_recorded_as_failure(
    scrape_db: tuple[async_sessionmaker[AsyncSession], UUID],
    fake_browser: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:

    run = getattr(runner, "run", None)
    assert callable(run), "run must exist"
    factory, category_id = scrape_db
    async with factory() as session:
        session.add(make_job(category_id, "seek-immigration-fail", "Existing role"))
        await session.commit()

    async def fetch_page(_: object, __: Category, page_number: int) -> dict[str, Any]:
        return (
            {"data": [source_listing("seek-immigration-fail")], "totalCount": 1}
            if page_number == 1
            else {"data": [], "totalCount": 0}
        )

    async def accreditation(_: object, __: str) -> dict[str, str]:
        raise AppError(ErrorCode.SCRAPE_SOURCE_ERROR)

    async def no_sleep(_: float) -> None:
        return None

    monkeypatch.setattr(seek_client, "fetch_search_page", fetch_page)
    monkeypatch.setattr(immigration_client, "check_accreditation", accreditation)
    monkeypatch.setattr(asyncio, "sleep", no_sleep)

    summary = await run(factory, category_id)

    async with factory() as session:
        job = await session.scalar(select(Job).where(Job.external_id == "seek-immigration-fail"))
        draft = await session.scalar(
            select(JobDraft).where(JobDraft.external_id == "seek-immigration-fail")
        )
        assert job is not None and draft is not None
        assert job.position == "Existing role"
        assert draft.status == "failed"
        assert draft.error_code == "scrape_source_error"
    assert summary.failed == 1
    assert summary.ineligible == 0


async def test_bad_immigration_payload_is_recorded_and_does_not_overwrite_job(
    scrape_db: tuple[async_sessionmaker[AsyncSession], UUID],
    fake_browser: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:

    run = getattr(runner, "run", None)
    assert callable(run), "run must exist"
    factory, category_id = scrape_db
    async with factory() as session:
        session.add(make_job(category_id, "seek-3", "Existing job"))
        await session.commit()

    async def fetch_page(_: object, __: Category, page: int) -> dict[str, Any]:
        return (
            {"data": [source_listing("seek-3")], "totalCount": 1}
            if page == 1
            else {"data": [], "totalCount": 0}
        )

    async def accreditation(_: object, __: str) -> dict[str, str]:
        return {"Title": "Results", "results": "not-json"}

    async def no_sleep(_: float) -> None:
        return None

    monkeypatch.setattr(seek_client, "fetch_search_page", fetch_page)
    monkeypatch.setattr(immigration_client, "check_accreditation", accreditation)
    monkeypatch.setattr(asyncio, "sleep", no_sleep)

    summary = await run(factory, category_id)

    async with factory() as session:
        job = await session.scalar(select(Job).where(Job.external_id == "seek-3"))
        draft = await session.scalar(select(JobDraft).where(JobDraft.external_id == "seek-3"))
        assert job is not None and draft is not None
        assert job.position == "Existing job"
        assert draft.status == "failed"
        assert draft.error_code == "scrape_source_error"
        assert draft.error_message == "A job source could not be processed."
    assert summary.failed == 1


async def test_accredited_listing_without_any_description_is_recorded_as_failed(
    scrape_db: tuple[async_sessionmaker[AsyncSession], UUID],
    fake_browser: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    draft, job = await scrape_one(
        scrape_db,
        monkeypatch,
        listing={**source_listing("seek-empty"), "teaser": "", "bulletPoints": []},
        accredited=True,
    )

    assert draft.status == "failed"
    assert draft.error_code == "scrape_source_error"
    assert job is None


async def test_unexpected_enrichment_bug_is_recorded_as_internal_error(
    scrape_db: tuple[async_sessionmaker[AsyncSession], UUID],
    fake_browser: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    draft, job = await scrape_one(
        scrape_db,
        monkeypatch,
        listing=source_listing("seek-bug"),
        accredited=True,
        accreditation_error=KeyError("bug"),
    )

    assert draft.status == "failed"
    assert draft.error_code == "internal_error"
    assert draft.error_message == "An unexpected error occurred."
    assert job is None


async def test_app_error_keeps_its_own_code_when_recorded_on_the_draft(
    scrape_db: tuple[async_sessionmaker[AsyncSession], UUID],
    fake_browser: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    draft, _ = await scrape_one(
        scrape_db,
        monkeypatch,
        listing=source_listing("seek-app-error"),
        accredited=True,
        accreditation_error=AppError(ErrorCode.CATEGORY_NOT_FOUND),
    )

    assert draft.error_code == "category_not_found"


async def test_failed_enrichment_increments_attempts(
    scrape_db: tuple[async_sessionmaker[AsyncSession], UUID],
    fake_browser: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    draft, _ = await scrape_one(
        scrape_db,
        monkeypatch,
        listing=source_listing("seek-attempts"),
        accredited=True,
        accreditation_error=AppError(ErrorCode.SCRAPE_SOURCE_ERROR),
    )

    assert (draft.status, draft.attempts) == ("failed", 1)


async def test_drafts_that_exhausted_their_attempts_are_not_retried(
    scrape_db: tuple[async_sessionmaker[AsyncSession], UUID],
    fake_browser: None,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    factory, category_id = scrape_db
    async with factory() as session:
        session.add_all(
            JobDraft(
                category_id=category_id,
                external_id=external_id,
                raw_payload=source_listing(external_id),
                status="failed",
                attempts=attempts,
            )
            for external_id, attempts in (
                ("exhausted", enrichment.MAX_ENRICH_ATTEMPTS),
                ("retry", 1),
            )
        )
        await session.commit()
    checked: list[str] = []

    async def accreditation(_: object, company: str) -> dict[str, str]:
        checked.append(company)
        return {"Title": "No Results"}

    async def no_sleep(_: float) -> None:
        return None

    monkeypatch.setattr(immigration_client, "check_accreditation", accreditation)
    monkeypatch.setattr(asyncio, "sleep", no_sleep)

    summary = await enrichment.enrich(factory, category_id)

    assert summary.fetched == 1
    assert len(checked) == 1
    assert "1 draft(s) for ict failed 3 times" in caplog.text
    async with factory() as session:
        done = await session.scalar(select(JobDraft).where(JobDraft.external_id == "retry"))
        stuck = await session.scalar(select(JobDraft).where(JobDraft.external_id == "exhausted"))
        assert done is not None and done.status == "ineligible"
        assert stuck is not None and (stuck.status, stuck.attempts) == ("failed", 3)


async def _seed_pending(
    factory: async_sessionmaker[AsyncSession], category_id: UUID, *external_ids: str
) -> None:
    async with factory() as session:
        for index, external_id in enumerate(external_ids):
            session.add(
                JobDraft(
                    category_id=category_id,
                    external_id=external_id,
                    raw_payload=source_listing(external_id),
                    first_seen_at=datetime(2026, 11, 1, 0, index, tzinfo=UTC),
                )
            )
        await session.commit()


async def test_same_company_is_looked_up_once_per_run(
    scrape_db: tuple[async_sessionmaker[AsyncSession], UUID],
    fake_browser: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    factory, category_id = scrape_db
    await _seed_pending(factory, category_id, "dup-a", "dup-b")
    looked_up: list[str] = []

    async def accreditation(_: object, company: str) -> dict[str, str]:
        looked_up.append(company)
        return {"Title": "Results"}

    async def no_sleep(_: float) -> None:
        return None

    monkeypatch.setattr(immigration_client, "check_accreditation", accreditation)
    monkeypatch.setattr(asyncio, "sleep", no_sleep)

    summary = await enrichment.enrich(factory, category_id)

    assert looked_up == ["Example Company"]
    assert (summary.fetched, summary.eligible, summary.failed) == (2, 2, 0)


async def test_failed_lookup_is_not_cached_for_the_same_company(
    scrape_db: tuple[async_sessionmaker[AsyncSession], UUID],
    fake_browser: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    factory, category_id = scrape_db
    await _seed_pending(factory, category_id, "flaky-a", "flaky-b")
    looked_up: list[str] = []

    async def accreditation(_: object, company: str) -> dict[str, str]:
        looked_up.append(company)
        if len(looked_up) == 1:
            raise AppError(ErrorCode.SCRAPE_SOURCE_ERROR)
        return {"Title": "No Results"}

    async def no_sleep(_: float) -> None:
        return None

    monkeypatch.setattr(immigration_client, "check_accreditation", accreditation)
    monkeypatch.setattr(asyncio, "sleep", no_sleep)

    summary = await enrichment.enrich(factory, category_id)

    assert len(looked_up) == 2
    assert (summary.failed, summary.ineligible) == (1, 1)


async def test_accredited_job_description_comes_from_the_search_result(
    scrape_db: tuple[async_sessionmaker[AsyncSession], UUID],
    fake_browser: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    listing = {
        **source_listing("seek-text"),
        "teaser": "Short   teaser",
        "bulletPoints": ["First point", "Second point"],
    }

    draft, job = await scrape_one(scrape_db, monkeypatch, listing=listing, accredited=True)

    assert draft.status == "eligible"
    assert job is not None
    assert job.job_description == "Short teaser\n\n• First point\n• Second point"


async def test_accredited_seek_job_gets_the_full_description(
    scrape_db: tuple[async_sessionmaker[AsyncSession], UUID],
    fake_browser: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def full(_: object, __: str, ___: str) -> str:
        return "Full ad text"

    monkeypatch.setattr(seek_client, "fetch_description", full)
    _, job = await scrape_one(
        scrape_db, monkeypatch, listing=source_listing("seek-full"), accredited=True
    )

    assert job is not None and job.job_description == "Full ad text"


async def test_seek_job_keeps_the_teaser_when_the_full_description_fails(
    scrape_db: tuple[async_sessionmaker[AsyncSession], UUID],
    fake_browser: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def blocked(_: object, __: str, ___: str) -> str:
        raise AppError(ErrorCode.SCRAPE_SOURCE_ERROR, "blocked")

    monkeypatch.setattr(seek_client, "fetch_description", blocked)
    _, job = await scrape_one(
        scrape_db, monkeypatch, listing=source_listing("seek-teaser"), accredited=True
    )

    assert job is not None and job.job_description != "Full ad text" and job.job_description


async def test_listing_in_a_country_without_an_employer_check_is_promoted_without_one(
    scrape_db: tuple[async_sessionmaker[AsyncSession], UUID],
    fake_browser: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    factory, _ = scrape_db
    async with factory() as session:
        au = await session.scalar(select(Category).where(Category.slug == "ict-au"))
        assert au is not None
        au.enabled = True
        session.add(
            JobDraft(
                category_id=au.id,
                external_id="au-1",
                raw_payload=source_listing("au-1"),
                status="pending",
            )
        )
        await session.commit()
        au_id = au.id

    async def no_sleep(_: float) -> None:
        return None

    async def never_called(*_: object) -> None:
        raise AssertionError("Immigration NZ must not be asked about an Australian listing")

    countries: list[str] = []

    async def full(_: object, __: str, country: str) -> str:
        countries.append(country)
        return "Full Australian ad"

    monkeypatch.setattr(asyncio, "sleep", no_sleep)
    monkeypatch.setattr(immigration_client, "check_accreditation", never_called)
    monkeypatch.setattr(enrichment, "async_playwright", never_called, raising=False)
    monkeypatch.setattr(seek_client, "fetch_description", full)

    try:
        summary = await enrichment.enrich(factory, au_id)
    finally:  # the test database is shared, so leave the category off for other tests
        async with factory() as session, session.begin():
            await session.execute(
                update(Category).where(Category.id == au_id).values(enabled=False)
            )

    async with factory() as session:
        job = await session.scalar(select(Job).where(Job.external_id == "au-1"))
    assert summary.eligible == 1
    assert job is not None and job.category_id == au_id
    assert job.url == "https://www.seek.com.au/job/au-1"
    assert job.job_description == "Full Australian ad" and countries == ["AU"]
