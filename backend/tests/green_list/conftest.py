import json
from collections.abc import AsyncIterator
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from job_scout.database import get_session
from job_scout.green_list.models import GreenListRole
from job_scout.main import app

TIER_1 = "Tier 1 role eligible for straight to residence"
TIER_2 = "Tier 2 role eligible for work to residence"


def inz_record(
    record_id: str = "1001",
    title: str = "Software Engineer",
    tier: str = TIER_1,
    anzsco: str = "ANZSCO 261313",
    industry: str = "ICT, electronics and telecommunications",
    pathway: str = "<p>To be eligible you must be:</p><ul><li>working here</li></ul>",
    requirements: str = (
        "<p>You must have one of the following:</p>\n"
        "<ul>\n<li>A degree.</li>\n<li>Or a diploma.</li>\n</ul>"
    ),
    degrees: str = "<p>Not needed.</p>",
    note: str = "None",
) -> dict[str, Any]:
    """A record shaped like the Immigration NZ search response."""
    fields = [
        {"ID": 25, "Title": anzsco, "Type": "PlainText", "ColumnIndex": 1, "Value": tier},
        {
            "ID": 24,
            "Title": "ANZSCO number",
            "Type": "PlainText",
            "ColumnIndex": 2,
            "Value": anzsco,
        },
        {"ID": 22, "Title": "Industry", "Type": "PlainText", "ColumnIndex": 3, "Value": industry},
        {"ID": 26, "Title": "Pathway to residence", "Type": "PlainText", "Value": pathway},
        {"ID": 27, "Title": "Green List requirements", "Type": "PlainText", "Value": requirements},
        {"ID": 28, "Title": "Washington and Sydney Accord engineering degrees", "Value": degrees},
        {"Title": "Note", "Value": note},  # some entries carry only these keys
        {"ID": 23, "Title": "Role", "Type": "Title", "IsTitle": True, "Value": title},
    ]
    return {
        "identifier": {"raw": "list-4ded06ebc2"},
        "record_id": {"raw": record_id},
        "title": {"raw": title},
        "field_schema": {"raw": json.dumps(fields)},
    }


@pytest.fixture
async def green_db(async_test_database_url: str) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    engine = create_async_engine(async_test_database_url)
    factory = async_sessionmaker(engine, expire_on_commit=False)

    async def clear() -> None:
        async with factory() as session, session.begin():
            await session.execute(delete(GreenListRole))  # events follow their role

    await clear()
    try:
        yield factory
    finally:
        await clear()
        await engine.dispose()


@pytest.fixture
async def green_api(
    green_db: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncClient]:
    async def override_session() -> AsyncIterator[AsyncSession]:
        async with green_db() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test"
        ) as client:
            yield client
    finally:
        app.dependency_overrides.clear()
