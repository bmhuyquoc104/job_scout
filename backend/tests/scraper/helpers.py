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
from job_scout.scraper import immigration_client, runner, seek_client
from job_scout.scraper.models import JobDraft


def make_job(category_id: UUID, external_id: str, position: str = "Old role") -> Job:
    return Job(
        category_id=category_id,
        external_id=external_id,
        company_name="Old company",
        location="Wellington",
        work_arrangements=["On-site"],
        work_types=["Full time"],
        salary_label="$80,000 per year",
        pay_period="Year",
        position=position,
        job_description="Old description",
        url=f"https://www.seek.co.nz/job/{external_id}",
        nzbn="old-nzbn",
        trading_name="Old trading name",
        listed_at=datetime(2026, 10, 1, tzinfo=UTC),
    )


def source_listing(external_id: str = "seek-1") -> dict[str, Any]:
    return {
        "id": external_id,
        "companyName": "Example Company",
        "advertiser": {"description": "Fallback Company"},
        "title": "Data Engineer",
        "locations": [{"label": "Wellington"}],
        "workArrangements": {"data": [{"label": {"text": "Hybrid"}}]},
        "workTypes": ["Full time"],
        "salaryLabel": "$120,000 per year",
        "listingDate": "2026-10-15T02:00:00Z",
        "teaser": "Example teaser",
        "bulletPoints": ["Example point"],
    }


async def scrape_one(
    scrape_db: tuple[async_sessionmaker[AsyncSession], UUID],
    monkeypatch: pytest.MonkeyPatch,
    *,
    listing: dict[str, Any],
    accredited: bool,
    accreditation_error: Exception | None = None,
) -> tuple[JobDraft, Job | None]:
    factory, category_id = scrape_db

    async def fetch_page(_: object, __: Category, page: int) -> dict[str, Any]:
        return {"data": [listing], "totalCount": 1} if page == 1 else {"data": [], "totalCount": 0}

    async def accreditation(_: object, __: str) -> dict[str, str]:
        if accreditation_error is not None:
            raise accreditation_error
        return {"Title": "Results" if accredited else "No Results"}

    async def no_sleep(_: float) -> None:
        return None

    monkeypatch.setattr(seek_client, "fetch_search_page", fetch_page)
    monkeypatch.setattr(immigration_client, "check_accreditation", accreditation)
    monkeypatch.setattr(asyncio, "sleep", no_sleep)

    await runner.run(factory, category_id)

    async with factory() as session:
        draft = await session.scalar(select(JobDraft).where(JobDraft.external_id == listing["id"]))
        job = await session.scalar(select(Job).where(Job.external_id == listing["id"]))
    assert draft is not None
    return draft, job
