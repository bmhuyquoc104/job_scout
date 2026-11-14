from collections.abc import AsyncIterator
from datetime import UTC, datetime

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from job_scout.categories.models import Category
from job_scout.database import get_session
from job_scout.jobs.models import Job, JobEvent
from job_scout.main import app


@pytest.fixture
async def api_context(
    async_test_database_url: str,
) -> AsyncIterator[tuple[AsyncClient, Category, list[Job]]]:
    engine = create_async_engine(async_test_database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        transaction = await session.begin()
        await session.execute(delete(Job))
        category = await session.scalar(select(Category).where(Category.slug == "ict"))
        assert category is not None
        # Deliberately varied so sort and filter tests can tell the jobs apart.
        varied = [
            # (location, arrangements, work types, salary label, annual min, annual max)
            ("Wellington", ["Hybrid"], ["Full time"], "$100,000 per year", 100_000, 100_000),
            ("Auckland", ["Remote"], ["Contract/Temp"], "$50 per hour", 104_000, 104_000),
            ("Christchurch", ["On-site"], ["Part time"], "Competitive salary", None, None),
        ]
        jobs = [
            Job(
                category_id=category.id,
                source="employmenthero" if index == 1 else "seek",  # job 1 is from the other source
                external_id=f"seek-{index}",
                company_name=f"Company {index}",
                location=location,
                work_arrangements=arrangements,
                work_types=work_types,
                salary_label=salary_label,
                pay_period="Year",
                annual_salary_min=salary_min,
                annual_salary_max=salary_max,
                position=f"Engineer {index}",
                job_description=f"Description {index}",
                url=f"https://www.seek.co.nz/job/{index}",
                nzbn=f"nzbn-{index}",
                trading_name=f"Trading {index}",
                listed_at=datetime(2026, 10, index + 1, tzinfo=UTC),
                is_active=index < 2,
                seniority=("senior", "junior", "senior")[index],
                visa_sponsor=index == 1,
            )
            for index, (
                location,
                arrangements,
                work_types,
                salary_label,
                salary_min,
                salary_max,
            ) in enumerate(varied)
        ]
        session.add_all(jobs)
        await session.flush()
        session.add_all(
            [
                JobEvent(
                    job_id=job.id,
                    category_id=category.id,
                    event_type=event_type,
                    occurred_at=datetime(2026, 10, day, tzinfo=UTC),
                )
                for job, event_type, day in (
                    (jobs[0], "new", 1),
                    (jobs[1], "new", 2),
                    (jobs[2], "new", 3),
                    (jobs[1], "reopened", 6),
                )
            ]
        )
        session.add_all(
            [
                # jobs[2] is closed now; jobs[1] closed once but reopened, so it is open.
                JobEvent(
                    job_id=jobs[2].id,
                    category_id=category.id,
                    event_type="closed",
                    occurred_at=datetime(2026, 10, 20, tzinfo=UTC),
                ),
                JobEvent(
                    job_id=jobs[1].id,
                    category_id=category.id,
                    event_type="closed",
                    occurred_at=datetime(2026, 10, 5, tzinfo=UTC),
                ),
            ]
        )
        await session.flush()

        async def override_session() -> AsyncIterator[AsyncSession]:
            yield session

        app.dependency_overrides[get_session] = override_session
        try:
            async with AsyncClient(
                transport=ASGITransport(app=app, raise_app_exceptions=False),
                base_url="http://test",
            ) as client:
                yield client, category, jobs
        finally:
            app.dependency_overrides.clear()
            await transaction.rollback()
    await engine.dispose()
