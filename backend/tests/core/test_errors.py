from httpx import AsyncClient
from pytest import LogCaptureFixture

from job_scout.core.errors import AppError, ErrorCode


async def test_http_not_found_uses_central_error_response(client: AsyncClient) -> None:
    response = await client.get("/__test/missing")

    assert response.status_code == 404
    assert response.json() == {"error": {"code": "not_found", "message": "Resource not found."}}


async def test_application_error_uses_catalog_status_and_message(client: AsyncClient) -> None:
    response = await client.get("/__test/app-error")

    assert response.status_code == 404
    assert response.json() == {"error": {"code": "job_not_found", "message": "Job not found."}}


async def test_request_validation_uses_central_error_response(client: AsyncClient) -> None:
    response = await client.get("/__test/validation?count=not-an-integer")

    assert response.status_code == 422
    assert response.json() == {
        "error": {"code": "validation_error", "message": "Request validation failed."}
    }


async def test_unexpected_error_is_logged_and_redacted(
    client: AsyncClient, caplog: LogCaptureFixture
) -> None:
    response = await client.get("/__test/unhandled")

    assert response.status_code == 500
    assert response.json() == {
        "error": {"code": "internal_error", "message": "An unexpected error occurred."}
    }
    assert "secret database connection string" not in response.text
    assert "Unhandled request exception" in caplog.text


def test_app_error_exposes_catalog_message_and_keeps_detail_for_logs() -> None:
    error = AppError(ErrorCode.SCRAPE_SOURCE_ERROR, "totalCount was 'x'")

    assert error.message == "A job source could not be processed."
    assert error.detail == "totalCount was 'x'"
    assert "totalCount" in str(error)


async def test_error_detail_is_never_sent_to_clients() -> None:
    from job_scout.core.exception_handlers import app_error_handler

    response = await app_error_handler(
        None,
        AppError(ErrorCode.SCRAPE_SOURCE_ERROR, "secret internal detail"),  # type: ignore[arg-type]
    )

    assert b"secret" not in response.body
    assert response.status_code == 502
