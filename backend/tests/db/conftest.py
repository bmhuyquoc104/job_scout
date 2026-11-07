from collections.abc import AsyncIterator

import asyncpg
import pytest


@pytest.fixture
async def connection(sync_test_database_url: str) -> AsyncIterator[asyncpg.Connection]:
    connection = await asyncpg.connect(sync_test_database_url)
    try:
        yield connection
    finally:
        await connection.close()
