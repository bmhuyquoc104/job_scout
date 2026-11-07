"""Async HTTP for the job boards that reject clients without a real browser TLS fingerprint."""

import asyncio
from typing import Any

from curl_cffi.requests import AsyncSession, Response

from job_scout.core.errors import AppError, ErrorCode

MAX_ATTEMPTS = 3


def client(headers: dict[str, str] | None = None) -> AsyncSession:
    return AsyncSession(impersonate="chrome", timeout=30, headers=headers)


async def request(http: AsyncSession, method: str, url: str, **kwargs: Any) -> Response:
    """One request, retried on network errors, 429 and 5xx; any other failure is final."""
    for attempt in range(MAX_ATTEMPTS):
        try:
            response = await http.request(method, url, **kwargs)  # type: ignore[arg-type]
            status = response.status_code
        except Exception as exc:  # curl_cffi raises its own transport errors
            response, status, error = None, 0, repr(exc)
        else:
            error = f"status {status}"
        if response is not None and status == 200:
            return response
        transient = status in (0, 429) or status >= 500
        if not transient or attempt == MAX_ATTEMPTS - 1:
            hint = " (blocked)" if status in (403, 429) else ""
            raise AppError(ErrorCode.SCRAPE_SOURCE_ERROR, f"{url} failed: {error}{hint}")
        await asyncio.sleep(2 * 2**attempt)
    raise AssertionError("unreachable")
