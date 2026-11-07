import pytest
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient

from job_scout.core.errors import AppError, ErrorCode
from job_scout.main import app


async def validation_probe(count: int) -> dict[str, int]:
    return {"count": count}


async def missing_probe() -> None:
    raise HTTPException(status_code=404, detail="do not expose this detail")


async def app_error_probe() -> None:
    raise AppError(ErrorCode.JOB_NOT_FOUND)


async def unhandled_probe() -> None:
    raise RuntimeError("secret database connection string")


app.add_api_route("/__test/validation", validation_probe, methods=["GET"])
app.add_api_route("/__test/missing", missing_probe, methods=["GET"])
app.add_api_route("/__test/app-error", app_error_probe, methods=["GET"])
app.add_api_route("/__test/unhandled", unhandled_probe, methods=["GET"])


@pytest.fixture
async def client() -> AsyncClient:
    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://test",
    ) as test_client:
        yield test_client
