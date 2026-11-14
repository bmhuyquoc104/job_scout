from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from job_scout.categories.models import Category
from job_scout.database import get_session
from job_scout.jobs.models import Job
from job_scout.main import app


@pytest.fixture
async def compare_client(async_test_database_url: str) -> AsyncIterator[AsyncClient]:
    engine = create_async_engine(async_test_database_url)
    async with async_sessionmaker(engine, expire_on_commit=False)() as session:
        transaction = await session.begin()
        await session.execute(delete(Job))
        categories = {
            c.slug: c.id
            for c in await session.scalars(select(Category))
            if c.slug.startswith("ict")
        }
        # (category, source, title, annual min, annual max, active)
        for index, (slug, source, title, low, high, active) in enumerate(
            [
                ("ict", "seek", "Software Engineer", 100_000, 120_000, True),
                ("ict", "indeed", "Senior Software Engineer", 140_000, 160_000, True),
                ("ict", "seek", "Registered Nurse", 80_000, 90_000, True),
                ("ict-au", "seek", "Software Engineer", 150_000, 150_000, True),
                ("ict-ca", "jobbank", "Software Engineer", None, None, False),
            ]
        ):
            session.add(
                Job(
                    category_id=categories[slug],
                    source=source,
                    external_id=f"j{index}",
                    company_name="Acme",
                    location="x",
                    position=title,
                    job_description="",
                    url=f"https://example.com/{index}",
                    annual_salary_min=low,
                    annual_salary_max=high,
                    is_active=active,
                )
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
                yield client
        finally:
            app.dependency_overrides.clear()
            await transaction.rollback()
    await engine.dispose()


async def test_a_job_title_is_compared_across_every_country(compare_client: AsyncClient) -> None:
    response = await compare_client.get("/api/compare/jobs", params={"title": "Software Engineer"})

    assert response.status_code == 200
    body = response.json()
    by_country = {c["country"]: c for c in body["countries"]}
    assert sorted(by_country) == ["AU", "CA", "DE", "NZ"]
    nz, au = by_country["NZ"], by_country["AU"]
    assert (nz["open_jobs"], nz["with_salary"]) == (2, 2)  # the nurse is not this job
    assert (nz["median_salary_min"], nz["median_salary_max"]) == (120_000, 140_000)
    assert nz["by_source"] == {"indeed": 1, "seek": 1}
    assert (au["open_jobs"], au["median_salary_min"], au["currency"]) == (1, 150_000, "$")
    assert by_country["CA"]["open_jobs"] == 0  # its one job is closed
    assert (by_country["DE"]["open_jobs"], by_country["DE"]["currency"]) == (0, "€")
    assert by_country["CA"]["median_salary_min"] is None


async def test_the_title_is_required(compare_client: AsyncClient) -> None:
    assert (await compare_client.get("/api/compare/jobs")).status_code == 422
