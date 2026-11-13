from uuid import UUID

import pytest
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from job_scout.categories.models import Category
from job_scout.core.errors import AppError, ErrorCode
from job_scout.scraper import phases


@pytest.fixture
def test_database(
    scrape_db: tuple[async_sessionmaker[AsyncSession], UUID], monkeypatch: pytest.MonkeyPatch
) -> async_sessionmaker[AsyncSession]:
    factory, _ = scrape_db
    monkeypatch.setattr(phases, "session_factory", factory)
    return factory


async def test_the_daily_run_covers_every_enabled_category(
    test_database: async_sessionmaker[AsyncSession],
) -> None:
    assert await phases.enabled_category_slugs() == ["ict"]

    async with test_database() as session, session.begin():
        await session.execute(update(Category).where(Category.slug == "sales").values(enabled=True))
    try:
        assert await phases.enabled_category_slugs() == ["ict", "sales"]
    finally:
        async with test_database() as session, session.begin():
            await session.execute(
                update(Category).where(Category.slug == "sales").values(enabled=False)
            )


async def test_one_named_category_must_exist_and_be_enabled(
    test_database: async_sessionmaker[AsyncSession],
) -> None:
    assert await phases.enabled_category_slugs("ict") == ["ict"]

    for slug in ("accounting", "no-such-category"):  # seeded but disabled / unknown
        with pytest.raises(AppError) as error:
            await phases.enabled_category_slugs(slug)
        assert error.value.code is ErrorCode.CATEGORY_NOT_FOUND


async def test_employment_hero_covers_only_categories_with_a_sector_id(
    test_database: async_sessionmaker[AsyncSession],
) -> None:
    assert await phases.enabled_category_slugs(source="employmenthero") == ["ict"]

    async with test_database() as session, session.begin():
        await session.execute(update(Category).where(Category.slug == "sales").values(enabled=True))
    try:  # enabled, but Employment Hero has no sector id for it
        assert await phases.enabled_category_slugs(source="employmenthero") == ["ict"]
        with pytest.raises(AppError):
            await phases.enabled_category_slugs("sales", source="employmenthero")
    finally:
        async with test_database() as session, session.begin():
            await session.execute(
                update(Category).where(Category.slug == "sales").values(enabled=False)
            )


async def test_job_boards_search_once_per_country_and_save_under_its_ict_category(
    test_database: async_sessionmaker[AsyncSession],
) -> None:
    assert await phases.enabled_category_slugs(source="indeed") == ["ict"]

    async with test_database() as session, session.begin():
        await session.execute(
            update(Category).where(Category.slug.in_(["ict-au", "sales"])).values(enabled=True)
        )
    try:
        assert await phases.enabled_category_slugs(source="indeed") == ["ict", "ict-au"]
        assert await phases.enabled_category_slugs("ict-au", source="glassdoor") == ["ict-au"]
        assert await phases.enabled_category_slugs(source="seek") == ["ict", "ict-au", "sales"]
        with pytest.raises(AppError):  # "sales" has no IT search on the boards
            await phases.enabled_category_slugs("sales", source="indeed")
    finally:
        async with test_database() as session, session.begin():
            await session.execute(
                update(Category).where(Category.slug.in_(["ict-au", "sales"])).values(enabled=False)
            )


async def test_employment_hero_also_covers_the_australian_ict_category(
    test_database: async_sessionmaker[AsyncSession],
) -> None:
    async with test_database() as session, session.begin():
        await session.execute(
            update(Category).where(Category.slug == "ict-au").values(enabled=True)
        )
    try:
        assert await phases.enabled_category_slugs(source="employmenthero") == ["ict", "ict-au"]
    finally:
        async with test_database() as session, session.begin():
            await session.execute(
                update(Category).where(Category.slug == "ict-au").values(enabled=False)
            )
