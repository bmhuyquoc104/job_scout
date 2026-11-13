from __future__ import annotations

from collections.abc import AsyncIterator
from uuid import UUID

import pytest
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from job_scout.categories.models import Category
from job_scout.jobs.models import Job
from job_scout.scraper import enrichment
from job_scout.scraper.models import JobDraft


@pytest.fixture
async def scrape_db(
    async_test_database_url: str,
) -> AsyncIterator[tuple[async_sessionmaker[AsyncSession], UUID]]:
    engine = create_async_engine(async_test_database_url)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        await session.execute(delete(JobDraft))
        await session.execute(delete(Job))
        category = await session.scalar(select(Category).where(Category.slug == "ict"))
        assert category is not None
        await session.commit()
        category_id = category.id
    try:
        yield factory, category_id
    finally:
        async with factory() as session:
            await session.execute(delete(JobDraft))
            await session.execute(delete(Job))
            await session.commit()
        await engine.dispose()


@pytest.fixture
def fake_browser(monkeypatch: pytest.MonkeyPatch) -> None:

    class Browser:
        async def new_page(self) -> object:
            return object()

        async def close(self) -> None:
            return None

    class Chromium:
        async def launch(self, *, headless: bool) -> Browser:
            assert headless is True
            return Browser()

    class Playwright:
        chromium = Chromium()

        async def __aenter__(self) -> Playwright:
            return self

        async def __aexit__(self, *_: object) -> None:
            return None

    class Http:
        async def close(self) -> None:
            return None

    async def no_description(*_: object) -> None:  # keep the search teaser; no network
        return None

    monkeypatch.setattr(enrichment, "async_playwright", Playwright, raising=False)
    monkeypatch.setattr(enrichment.chrome_http, "client", Http)
    monkeypatch.setattr(enrichment.seek_client, "fetch_description", no_description)
