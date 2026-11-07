from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from job_scout.jobs.models import Job, JobEvent
from job_scout.scraper import discovery, persistence
from job_scout.scraper.models import JobDraft
from tests.scraper.helpers import make_job, source_listing


def enriched(external_id: str, **overrides: Any) -> dict[str, Any]:
    return {
        "external_id": external_id,
        "company_name": "Example Company",
        "position": "Data Engineer",
        "listed_at": "2026-10-15T02:00:00Z",
        "location": "Wellington",
        "work_arrangements": ["Hybrid"],
        "work_types": ["Full time"],
        "salary_label": "$100,000 per year",
        "pay_period": "Year",
        "url": f"https://www.seek.co.nz/job/{external_id}",
        "job_description": "A description",
        "nzbn": "942903",
        "trading_name": "Example Trading",
        **overrides,
    }


async def promote(
    scrape_db: tuple[async_sessionmaker[AsyncSession], UUID], external_id: str, **overrides: Any
) -> None:
    factory, category_id = scrape_db
    await persistence.save_outcome(
        factory,
        category_id,
        external_id,
        status="accredited",
        enriched_data=enriched(external_id, **overrides),
    )


async def events_for(factory: async_sessionmaker[AsyncSession], external_id: str) -> list[JobEvent]:
    async with factory() as session:
        return list(
            await session.scalars(
                select(JobEvent)
                .join(Job, Job.id == JobEvent.job_id)
                .where(Job.external_id == external_id)
                .order_by(JobEvent.occurred_at, JobEvent.id)
            )
        )


async def test_promoting_a_new_job_records_a_new_event(
    scrape_db: tuple[async_sessionmaker[AsyncSession], UUID],
) -> None:
    await promote(scrape_db, "ev-new")

    events = await events_for(scrape_db[0], "ev-new")

    assert [event.event_type for event in events] == ["new"]
    assert events[0].category_id == scrape_db[1]


async def test_promoting_unchanged_data_again_records_nothing(
    scrape_db: tuple[async_sessionmaker[AsyncSession], UUID],
) -> None:
    await promote(scrape_db, "ev-same")
    await promote(scrape_db, "ev-same")

    assert [e.event_type for e in await events_for(scrape_db[0], "ev-same")] == ["new"]


async def test_changed_fields_are_recorded_as_an_updated_event(
    scrape_db: tuple[async_sessionmaker[AsyncSession], UUID],
) -> None:
    await promote(scrape_db, "ev-changed")
    await promote(scrape_db, "ev-changed", salary_label="$120,000 per year", location="Auckland")

    events = await events_for(scrape_db[0], "ev-changed")

    assert [event.event_type for event in events] == ["new", "updated"]
    assert events[1].details == {
        "salary_label": {"old": "$100,000 per year", "new": "$120,000 per year"},
        "location": {"old": "Wellington", "new": "Auckland"},
    }


async def test_promoting_an_inactive_job_records_reopened(
    scrape_db: tuple[async_sessionmaker[AsyncSession], UUID],
) -> None:
    factory, _ = scrape_db
    await promote(scrape_db, "ev-back")
    async with factory() as session, session.begin():
        await session.execute(
            update(Job).where(Job.external_id == "ev-back").values(is_active=False)
        )

    await promote(scrape_db, "ev-back")

    assert [e.event_type for e in await events_for(factory, "ev-back")] == ["new", "reopened"]


async def test_reconcile_records_closed_once_and_reopened_for_returning_jobs(
    scrape_db: tuple[async_sessionmaker[AsyncSession], UUID],
) -> None:
    factory, category_id = scrape_db
    async with factory() as session, session.begin():
        gone = make_job(category_id, "ev-gone")
        back = make_job(category_id, "ev-returned")
        back.is_active = False
        still = make_job(category_id, "ev-still")
        session.add_all([gone, back, still])
        session.add_all(
            JobDraft(
                category_id=category_id,
                external_id=external_id,
                raw_payload=source_listing(external_id),
                last_seen_at=datetime(2026, 11, 1, 0, 0, 1, tzinfo=UTC),
            )
            for external_id in ("ev-returned", "ev-still")
        )
    scan_started_at = datetime(2026, 11, 1, tzinfo=UTC)

    await discovery.reconcile_active_jobs(factory, category_id, scan_started_at)
    await discovery.reconcile_active_jobs(factory, category_id, scan_started_at)

    assert [e.event_type for e in await events_for(factory, "ev-gone")] == ["closed"]
    assert [e.event_type for e in await events_for(factory, "ev-returned")] == ["reopened"]
    assert await events_for(factory, "ev-still") == []


async def test_promotion_stores_the_parsed_annual_salary(
    scrape_db: tuple[async_sessionmaker[AsyncSession], UUID],
) -> None:
    factory, _ = scrape_db
    await promote(scrape_db, "ev-salary", salary_label="$28 per hour")
    await promote(scrape_db, "ev-nosalary", salary_label="Competitive salary")

    async with factory() as session:
        hourly = await session.scalar(select(Job).where(Job.external_id == "ev-salary"))
        vague = await session.scalar(select(Job).where(Job.external_id == "ev-nosalary"))
    assert hourly is not None and vague is not None
    assert (hourly.annual_salary_min, hourly.annual_salary_max) == (58_240, 58_240)
    assert (vague.annual_salary_min, vague.annual_salary_max) == (None, None)

    await promote(scrape_db, "ev-salary", salary_label="$60,000 per year")
    async with factory() as session:
        raised = await session.scalar(select(Job).where(Job.external_id == "ev-salary"))
    assert raised is not None and raised.annual_salary_max == 60_000


async def test_promotion_stores_the_seniority_read_from_the_title(
    scrape_db: tuple[async_sessionmaker[AsyncSession], UUID],
) -> None:
    factory, _ = scrape_db
    await promote(scrape_db, "ev-senior", position="Senior Data Engineer")
    await promote(scrape_db, "ev-plain", position="Business Analyst")

    async with factory() as session:
        senior = await session.scalar(select(Job).where(Job.external_id == "ev-senior"))
        plain = await session.scalar(select(Job).where(Job.external_id == "ev-plain"))
    assert senior is not None and plain is not None
    assert (senior.seniority, plain.seniority) == ("senior", "unspecified")

    await promote(scrape_db, "ev-plain", position="Lead Business Analyst")
    async with factory() as session:
        promoted = await session.scalar(select(Job).where(Job.external_id == "ev-plain"))
    assert promoted is not None and promoted.seniority == "lead"
