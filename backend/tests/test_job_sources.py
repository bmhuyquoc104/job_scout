"""Every job source is declared once, in `job_scout.jobs.sources`; these tests fail if any
place that has to know about a source (database, API, scrapers) is left behind."""

import re

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from job_scout.jobs.sources import JOB_SOURCES
from job_scout.scraper import discovery, enrichment


@pytest.mark.parametrize("table", ["job", "job_draft"])
async def test_database_check_allows_exactly_the_declared_sources(
    async_test_database_url: str, table: str
) -> None:
    engine = create_async_engine(async_test_database_url)
    try:
        async with engine.connect() as connection:
            definition = await connection.scalar(
                text(
                    "SELECT pg_get_constraintdef(oid) FROM pg_constraint "
                    "WHERE conrelid = CAST(:table AS regclass) AND contype = 'c' "
                    "AND pg_get_constraintdef(oid) LIKE '%source%'"
                ),
                {"table": table},
            )
    finally:
        await engine.dispose()
    assert set(re.findall(r"'([a-z_]+)'", definition)) == set(JOB_SOURCES)


@pytest.mark.parametrize("source", list(JOB_SOURCES))
def test_every_declared_source_can_be_scraped_and_enriched(source: str) -> None:
    assert source in enrichment.SOURCES
    assert callable(discovery.discoverer(source))


def test_unknown_source_is_rejected_instead_of_silently_scraped() -> None:
    with pytest.raises(KeyError):
        discovery.discoverer("nope")
