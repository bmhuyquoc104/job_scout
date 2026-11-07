import asyncio
from typing import Any

import httpx
from pydantic import BaseModel, ValidationError

from job_scout.core.errors import AppError, ErrorCode
from job_scout.green_list.parsing import RoleRecord, parse_record

URL = "https://www.immigration.govt.nz/_list-collection-search/api/as/v1/engines/--engine--/search.json"
LIST_IDENTIFIER = "list-4ded06ebc2"  # the Green List's id in Immigration NZ's list search
PAGE_SIZE = 300  # the whole list (about 215 roles) fits in one page
MAX_ATTEMPTS = 3


class _Page(BaseModel):
    total_pages: int
    total_results: int


class _Meta(BaseModel):
    page: _Page


class _Response(BaseModel):
    meta: _Meta
    results: list[dict[str, Any]]


async def fetch_green_list(http: httpx.AsyncClient) -> list[RoleRecord]:
    """Fetch every Green List role. Raises rather than return a partial list, because a partial
    list would make the sync look like roles had been removed."""
    payload = {
        "query": "",
        "filters": {"all": [{"identifier": LIST_IDENTIFIER}], "none": [], "any": []},
        "page": {"size": PAGE_SIZE, "current": 1},
        "sort": [{"title": "asc"}],
    }
    for attempt in range(MAX_ATTEMPTS):
        try:
            response = await http.post(URL, json=payload)
            response.raise_for_status()
            break
        except (httpx.TransportError, httpx.HTTPStatusError) as exc:
            status = exc.response.status_code if isinstance(exc, httpx.HTTPStatusError) else 0
            transient = status == 0 or status == 429 or status >= 500
            if not transient or attempt == MAX_ATTEMPTS - 1:
                raise AppError(
                    ErrorCode.SCRAPE_SOURCE_ERROR, f"Green List request failed: {exc!r}"
                ) from exc
            await asyncio.sleep(2 * 2**attempt)
    try:
        body = _Response.model_validate(response.json())
    except (ValueError, ValidationError) as exc:
        raise AppError(
            ErrorCode.SCRAPE_SOURCE_ERROR, f"Unexpected Green List response: {exc}"
        ) from exc
    page = body.meta.page
    if page.total_pages != 1 or page.total_results != len(body.results) or not body.results:
        raise AppError(
            ErrorCode.SCRAPE_SOURCE_ERROR,
            f"Incomplete Green List: {len(body.results)} of {page.total_results} roles, "
            f"{page.total_pages} page(s)",
        )
    return [parse_record(record) for record in body.results]
