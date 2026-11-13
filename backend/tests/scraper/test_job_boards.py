from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from job_scout.core.errors import AppError
from job_scout.scraper import discovery, glassdoor, indeed
from job_scout.scraper.models import JobDraft

INDEED_JOB: dict[str, Any] = {
    "key": "abc123",
    "title": "Senior Software Engineer",
    "sourceEmployerName": "Everbridge",
    "dateOnIndeed": 1762041600000,  # 2025-11-02T00:00:00Z
    "description": {"html": "<p><b>About</b></p><ul><li>Python</li></ul>"},
    "location": {"countryCode": "NZ", "admin1Code": None, "city": "Auckland City"},
    "compensation": {
        "baseSalary": {"unitOfWork": "YEAR", "range": {"min": 100000, "max": 140000}},
        "currencyCode": "NZD",
    },
    "attributes": [{"key": "CF3CP"}],
}

GLASSDOOR_LISTING: dict[str, Any] = {
    "jobview": {
        "header": {
            "ageInDays": 2,
            "employerNameFromSearch": "Orion Health",
            "locationName": "Auckland, Auckland",
            "payCurrency": "NZD",
            "payPeriod": "ANNUAL",
            "payPeriodAdjustedPay": {"p10": 90000, "p90": 120000},
            "jobTypeKeys": ["fulltime"],
        },
        "job": {"jobTitleText": "Software Engineer", "listingId": 1009876543210},
    }
}


# --- Indeed ---------------------------------------------------------------------------------


def test_indeed_parse_search_returns_payloads_and_next_cursor() -> None:
    data = {
        "data": {
            "jobSearch": {
                "pageInfo": {"nextCursor": "CUR2"},
                "results": [{"job": INDEED_JOB}, {"job": None}],
            }
        }
    }
    payloads, cursor = indeed.parse_search(data)
    assert cursor == "CUR2"
    assert [p["id"] for p in payloads] == ["abc123"]
    assert payloads[0]["url"] == "https://nz.indeed.com/viewjob?jk=abc123"


def test_indeed_parse_search_without_job_search_is_a_source_error() -> None:
    with pytest.raises(AppError):
        indeed.parse_search({"errors": [{"message": "nope"}], "data": None})


def test_indeed_normalize_listing_maps_the_job() -> None:
    payload = indeed.parse_search({"data": {"jobSearch": {"results": [{"job": INDEED_JOB}]}}})[0][0]
    listing = indeed.normalize_listing(payload)
    assert listing.source == "indeed"
    assert listing.external_id == "abc123"
    assert listing.company_name == "Everbridge"
    assert listing.position == "Senior Software Engineer"
    assert listing.location == "Auckland City"
    assert listing.work_types == ["Full time"]
    assert listing.salary_label == "$100,000 - $140,000 per year"
    assert listing.pay_period == "Year"
    assert listing.listed_at == datetime(2025, 11, 2, tzinfo=UTC)
    assert listing.url == "https://nz.indeed.com/viewjob?jk=abc123"


def test_indeed_normalize_listing_without_pay() -> None:
    job = {**INDEED_JOB, "compensation": None, "attributes": []}
    payload = indeed.parse_search({"data": {"jobSearch": {"results": [{"job": job}]}}})[0][0]
    listing = indeed.normalize_listing(payload)
    assert listing.salary_label == ""
    assert listing.work_types == []


def test_indeed_build_description_turns_html_into_readable_text() -> None:
    payload = indeed.parse_search({"data": {"jobSearch": {"results": [{"job": INDEED_JOB}]}}})[0][0]
    assert indeed.build_description(payload) == "About\n• Python"


# --- Glassdoor ------------------------------------------------------------------------------


def test_glassdoor_parse_listing_flattens_and_dates_the_job() -> None:
    payload = glassdoor.parse_listing(GLASSDOOR_LISTING, today=date(2026, 11, 7))
    assert payload["id"] == "1009876543210"
    assert payload["datePosted"] == "2026-11-05"
    assert payload["url"] == "https://www.glassdoor.co.nz/job-listing/j?jl=1009876543210"


def test_glassdoor_normalize_listing_maps_the_job() -> None:
    payload = glassdoor.parse_listing(GLASSDOOR_LISTING, today=date(2026, 11, 7))
    listing = glassdoor.normalize_listing(payload)
    assert listing.source == "glassdoor"
    assert listing.external_id == "1009876543210"
    assert listing.company_name == "Orion Health"
    assert listing.position == "Software Engineer"
    assert listing.location == "Auckland, Auckland"
    assert listing.work_types == ["Full time"]
    assert listing.salary_label == "$90,000 - $120,000 per year"
    assert listing.pay_period == "Year"
    assert listing.listed_at == datetime(2026, 11, 5, tzinfo=UTC)


def test_glassdoor_build_description_turns_html_into_readable_text() -> None:
    payload = glassdoor.parse_listing(GLASSDOOR_LISTING, today=date(2026, 11, 7))
    payload["description"] = "<div><h2>Description</h2><p>We&rsquo;re hiring.</p></div>"
    assert glassdoor.build_description(payload) == "Description\nWe’re hiring."


# --- Discovery (shared) ---------------------------------------------------------------------


def fake_pages(*pages: list[dict[str, Any]], fail_after: int | None = None) -> Any:
    async def pages_gen(_: object, __: str) -> AsyncIterator[list[dict[str, Any]]]:
        for number, page in enumerate(pages):
            if fail_after is not None and number >= fail_after:
                raise AppError(discovery.ErrorCode.SCRAPE_SOURCE_ERROR, "boom")
            yield page

    return pages_gen


class _NoClient:
    async def __aenter__(self) -> object:
        return object()

    async def __aexit__(self, *_: object) -> None:
        return None


@pytest.fixture(autouse=True)
def no_real_clients(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(indeed, "client", lambda country: _NoClient())
    monkeypatch.setattr(glassdoor, "client", lambda country: _NoClient())

    async def no_sleep(_: float) -> None:
        return None

    monkeypatch.setattr(discovery.asyncio, "sleep", no_sleep)


@pytest.mark.parametrize(("source", "module"), [("indeed", indeed), ("glassdoor", glassdoor)])
async def test_discovery_saves_drafts_for_every_listed_job(
    scrape_db: tuple[async_sessionmaker[AsyncSession], UUID],
    monkeypatch: pytest.MonkeyPatch,
    source: str,
    module: Any,
) -> None:
    factory, category_id = scrape_db
    page1 = [{"id": "a", "title": "A"}, {"id": "b", "title": "B"}]
    page2 = [{"id": "b", "title": "B"}, {"id": "c", "title": "C"}]  # b repeats across pages
    monkeypatch.setattr(module, "pages", fake_pages(page1, page2))

    summary = await discovery.discover_job_board(factory, category_id, source)

    async with factory() as session:
        drafts = (await session.scalars(select(JobDraft).order_by(JobDraft.external_id))).all()
    assert [(d.source, d.external_id, d.status) for d in drafts] == [
        (source, "a", "pending"),
        (source, "b", "pending"),
        (source, "c", "pending"),
    ]
    assert summary.fetched == 3


async def test_discovery_fails_closed_when_a_page_cannot_be_read(
    scrape_db: tuple[async_sessionmaker[AsyncSession], UUID], monkeypatch: pytest.MonkeyPatch
) -> None:
    factory, category_id = scrape_db
    monkeypatch.setattr(indeed, "pages", fake_pages([{"id": "a"}], [{"id": "b"}], fail_after=1))

    with pytest.raises(AppError):
        await discovery.discover_job_board(factory, category_id, "indeed")


async def test_discovery_fails_closed_when_the_first_page_has_no_jobs(
    scrape_db: tuple[async_sessionmaker[AsyncSession], UUID], monkeypatch: pytest.MonkeyPatch
) -> None:
    factory, category_id = scrape_db
    monkeypatch.setattr(glassdoor, "pages", fake_pages([]))

    with pytest.raises(AppError):
        await discovery.discover_job_board(factory, category_id, "glassdoor")


def test_indeed_links_and_search_follow_the_country() -> None:
    data = {"data": {"jobSearch": {"results": [{"job": INDEED_JOB}]}}}

    payloads, _ = indeed.parse_search(data, "AU")

    assert payloads[0]["url"] == "https://au.indeed.com/viewjob?jk=abc123"
    assert '"Australia"' in indeed.build_query(None, "AU")
    assert '"New Zealand"' in indeed.build_query(None)


def test_glassdoor_links_follow_the_country() -> None:
    payload = glassdoor.parse_listing(GLASSDOOR_LISTING, date(2026, 11, 7), "AU")

    assert payload["url"].startswith("https://www.glassdoor.com.au/job-listing/j?jl=")
