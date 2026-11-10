from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from uuid import UUID

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from job_scout.core.errors import AppError, ErrorCode
from job_scout.jobs.models import Job
from job_scout.scraper import discovery, employmenthero, immigration_client, runner
from job_scout.scraper.models import JobDraft
from tests.scraper.helpers import make_job, source_listing


def list_page(*slugs: str) -> str:
    links = "".join(f'<a href="/nz/jobs/position/{slug}/">x</a>' for slug in slugs)
    return f'<html><a href="https://employmenthero.com/nz/jobs/position/{slugs[0]}/">y</a>{links}</html>'


def job_page(title: str = "Data Engineer", **overrides: object) -> str:
    posting = {
        "@context": "https://schema.org",
        "@type": "JobPosting",
        "title": title,
        "datePosted": "2026-11-02",
        "employmentType": "FULL_TIME",
        "description": "<p><strong>About</strong></p><p>Build pipelines.</p><ul><li>SQL</li></ul>",
        "hiringOrganization": {"@type": "Organization", "name": "Acme Ltd"},
        "jobLocation": {
            "@type": "Place",
            "address": {"addressLocality": "Hamilton Lake", "addressRegion": "Waikato"},
        },
        "baseSalary": {
            "@type": "MonetaryAmount",
            "currency": "NZD",
            "value": {"minValue": 110000, "maxValue": 150000, "unitText": "YEAR"},
        },
        **overrides,
    }
    other = {"@type": "BreadcrumbList"}
    return (
        f'<script type="application/ld+json">{json.dumps(other)}</script>'
        f'<script type="application/ld+json">{json.dumps(posting)}</script>'
    )


def test_parse_job_slugs_dedupes_and_keeps_order() -> None:
    assert employmenthero.parse_job_slugs(list_page("a-1", "b-2")) == ["a-1", "b-2"]
    assert employmenthero.parse_job_slugs("<html>no jobs</html>") == []


def test_parse_job_posting_adds_id_and_url() -> None:
    payload = employmenthero.parse_job_posting(job_page(), "acme-data-engineer-x1")
    assert payload["id"] == "acme-data-engineer-x1"
    assert payload["url"] == "https://employmenthero.com/nz/jobs/position/acme-data-engineer-x1/"
    assert payload["title"] == "Data Engineer"


def test_parse_job_posting_without_a_posting_is_a_source_error() -> None:
    with pytest.raises(AppError):
        employmenthero.parse_job_posting("<html>blocked</html>", "slug")


def test_normalize_listing_maps_the_posting() -> None:
    payload = employmenthero.parse_job_posting(job_page(), "slug-1")
    listing = employmenthero.normalize_listing(payload)
    assert listing.source == "employmenthero"
    assert listing.external_id == "slug-1"
    assert listing.company_name == "Acme Ltd"
    assert listing.position == "Data Engineer"
    assert listing.location == "Hamilton Lake, Waikato"
    assert listing.work_types == ["Full time"]
    assert listing.salary_label == "$110,000 - $150,000 per year"
    assert listing.pay_period == "Year"
    assert listing.listed_at == datetime(2026, 11, 2, tzinfo=UTC)
    assert listing.url.endswith("/slug-1/")


def test_normalize_listing_without_salary_or_location() -> None:
    payload = employmenthero.parse_job_posting(
        job_page(baseSalary=None, jobLocation=None, jobLocationType="TELECOMMUTE"), "slug-2"
    )
    listing = employmenthero.normalize_listing(payload)
    assert listing.salary_label == ""
    assert listing.location == ""
    assert listing.work_arrangements == ["Remote"]


def test_build_description_turns_html_into_readable_text() -> None:
    payload = employmenthero.parse_job_posting(job_page(), "slug-3")
    assert employmenthero.build_description(payload) == "About\nBuild pipelines.\n• SQL"


@pytest.fixture
def eh_site(monkeypatch: pytest.MonkeyPatch) -> dict[str, str]:
    """Fake Employment Hero: pages by number (1-based) and job pages by slug."""
    site: dict[str, str] = {}

    async def fetch_list(_: httpx.AsyncClient, sector_id: int, page: int) -> str:
        assert sector_id == 18
        return site.get(f"page{page}", "<html></html>")

    async def fetch_job(_: httpx.AsyncClient, slug: str) -> str:
        if slug not in site:
            raise AppError(ErrorCode.SCRAPE_SOURCE_ERROR, "boom")
        return site[slug]

    async def no_sleep(_: float) -> None:
        return None

    monkeypatch.setattr(employmenthero, "fetch_list_page", fetch_list)
    monkeypatch.setattr(employmenthero, "fetch_job_page", fetch_job)
    monkeypatch.setattr(asyncio, "sleep", no_sleep)
    return site


async def test_discovery_saves_drafts_for_every_listed_job(
    scrape_db: tuple[async_sessionmaker[AsyncSession], UUID], eh_site: dict[str, str]
) -> None:
    factory, category_id = scrape_db
    eh_site.update(page1=list_page("job-a", "job-b"), page2=list_page("job-c"))
    eh_site.update({"job-a": job_page("A"), "job-b": job_page("B"), "job-c": job_page("C")})

    summary = await discovery.discover_employmenthero(factory, category_id)

    async with factory() as session:
        drafts = (await session.scalars(select(JobDraft).order_by(JobDraft.external_id))).all()
    assert [(d.source, d.external_id, d.status) for d in drafts] == [
        ("employmenthero", "job-a", "pending"),
        ("employmenthero", "job-b", "pending"),
        ("employmenthero", "job-c", "pending"),
    ]
    assert drafts[0].raw_payload["title"] == "A"
    assert summary.fetched == 3


async def test_discovery_fails_closed_when_a_job_page_cannot_be_read(
    scrape_db: tuple[async_sessionmaker[AsyncSession], UUID], eh_site: dict[str, str]
) -> None:
    factory, category_id = scrape_db
    eh_site.update(page1=list_page("job-a", "job-missing"), **{"job-a": job_page()})

    with pytest.raises(AppError):
        await discovery.discover_employmenthero(factory, category_id)


async def test_discovery_skips_a_job_that_was_taken_down_after_listing(
    scrape_db: tuple[async_sessionmaker[AsyncSession], UUID],
    eh_site: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    factory, category_id = scrape_db
    eh_site.update(page1=list_page("job-a", "job-gone"), **{"job-a": job_page()})

    async def fetch_job(_: httpx.AsyncClient, slug: str) -> str | None:
        return eh_site.get(slug)  # None = the page 404s

    monkeypatch.setattr(employmenthero, "fetch_job_page", fetch_job)

    summary = await discovery.discover_employmenthero(factory, category_id)

    assert summary.fetched == 1


async def test_discovery_fails_closed_when_the_first_page_has_no_jobs(
    scrape_db: tuple[async_sessionmaker[AsyncSession], UUID], eh_site: dict[str, str]
) -> None:
    factory, category_id = scrape_db
    with pytest.raises(AppError):
        await discovery.discover_employmenthero(factory, category_id)


async def test_full_run_promotes_only_accredited_employers(
    scrape_db: tuple[async_sessionmaker[AsyncSession], UUID],
    eh_site: dict[str, str],
    fake_browser: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    factory, category_id = scrape_db
    eh_site.update(page1=list_page("ok-job", "no-job"))
    eh_site["ok-job"] = job_page("Good job", hiringOrganization={"name": "Accredited Ltd"})
    eh_site["no-job"] = job_page("Other job", hiringOrganization={"name": "Unknown Ltd"})

    async def accreditation(_: object, company: str) -> dict[str, str]:
        return {"Title": "Results" if company == "Accredited Ltd" else "No Results"}

    monkeypatch.setattr(immigration_client, "check_accreditation", accreditation)

    summary = await runner.run(factory, category_id, source="employmenthero")

    async with factory() as session:
        jobs = (await session.scalars(select(Job))).all()
    assert [(j.source, j.external_id, j.position) for j in jobs] == [
        ("employmenthero", "ok-job", "Good job")
    ]
    assert jobs[0].job_description.startswith("About")
    assert jobs[0].url == "https://employmenthero.com/nz/jobs/position/ok-job/"
    assert (summary.accredited, summary.not_accredited, summary.failed) == (1, 1, 0)


async def test_reconcile_only_closes_jobs_from_its_own_source(
    scrape_db: tuple[async_sessionmaker[AsyncSession], UUID],
) -> None:
    factory, category_id = scrape_db
    seek_job = make_job(category_id, "same")
    eh_job = make_job(category_id, "same")
    eh_job.source = "employmenthero"
    async with factory() as session:
        session.add_all([seek_job, eh_job])
        await session.commit()

    # A scan of one source that sees nothing must not touch the other source's jobs.
    await discovery.reconcile_active_jobs(
        factory, category_id, datetime(2026, 11, 1, tzinfo=UTC), source="employmenthero"
    )

    async with factory() as session:
        states = {j.source: j.is_active for j in (await session.scalars(select(Job))).all()}
    assert states == {"seek": True, "employmenthero": False}


async def test_a_seek_draft_with_the_same_id_does_not_count_as_seen_for_employment_hero(
    scrape_db: tuple[async_sessionmaker[AsyncSession], UUID],
) -> None:
    factory, category_id = scrape_db
    eh_job = make_job(category_id, "same")
    eh_job.source = "employmenthero"
    async with factory() as session:
        session.add_all(
            [
                eh_job,
                JobDraft(
                    category_id=category_id,
                    source="seek",
                    external_id="same",
                    raw_payload=source_listing("same"),
                ),
            ]
        )
        await session.commit()

    await discovery.reconcile_active_jobs(
        factory, category_id, datetime(2000, 1, 1, tzinfo=UTC), source="employmenthero"
    )

    async with factory() as session:
        job = await session.scalar(select(Job))
    assert job is not None and job.is_active is False
