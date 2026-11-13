import asyncio
from typing import Any

import httpx
from curl_cffi.requests import AsyncSession
from pydantic import BaseModel, ConfigDict, Field, StrictInt, ValidationError, model_validator

from job_scout.categories.models import Category
from job_scout.core.countries import COUNTRIES
from job_scout.core.errors import AppError, ErrorCode
from job_scout.scraper import chrome_http
from job_scout.scraper.employmenthero import build_description

DETAIL_QUERY = "query($id: ID!){ jobDetails(id:$id){ job{ content(platform: WEB) } } }"
DETAIL_HEADERS = {"seek-request-brand": "seek", "x-seek-site": "chalice"}
MAX_ATTEMPTS = 3


class SearchPage(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    total_count: StrictInt = Field(alias="totalCount", ge=0)
    data: list[dict[str, Any]]

    @model_validator(mode="after")
    def _count_matches_data(self) -> SearchPage:
        # SEEK signals the end with totalCount 0 and no data; anything else must have rows.
        if (self.total_count == 0) != (not self.data):
            raise ValueError("totalCount and data disagree")
        return self


def parse_search_page(payload: dict[str, Any]) -> SearchPage:
    try:
        return SearchPage.model_validate(payload)
    except ValidationError as exc:
        raise AppError(ErrorCode.SCRAPE_SOURCE_ERROR, f"Bad SEEK search response: {exc}") from exc


async def fetch_search_page(
    client: httpx.AsyncClient, category: Category, page: int
) -> dict[str, Any]:
    site = COUNTRIES[category.country]
    for attempt in range(MAX_ATTEMPTS):
        try:
            response = await client.get(
                f"https://{site.seek_host}/api/jobsearch/v5/search",
                params={
                    "siteKey": site.seek_site_key,
                    "sourcesystem": "houston",
                    "page": str(page),
                    "pageSize": "22",
                    "classification": category.seek_classification_id,
                    "locale": site.seek_locale,
                },
                follow_redirects=True,
            )
            response.raise_for_status()
            break
        except (httpx.TransportError, httpx.HTTPStatusError) as exc:
            status = exc.response.status_code if isinstance(exc, httpx.HTTPStatusError) else 0
            transient = status == 0 or status == 429 or status >= 500
            if not transient or attempt == MAX_ATTEMPTS - 1:
                raise AppError(
                    ErrorCode.SCRAPE_SOURCE_ERROR, f"SEEK request failed: {exc!r}"
                ) from exc
            await asyncio.sleep(2 * 2**attempt)
    payload = response.json()
    if not isinstance(payload, dict):
        raise AppError(ErrorCode.SCRAPE_SOURCE_ERROR, "SEEK search response is not an object")
    return payload


async def fetch_description(
    http: AsyncSession, external_id: str, country: str = "NZ"
) -> str | None:
    """Plain-text description, or None when SEEK has no content for the job (taken down)."""
    response = await chrome_http.request(
        http,
        "POST",
        f"https://{COUNTRIES[country].seek_host}/graphql",
        json={"query": DETAIL_QUERY, "variables": {"id": external_id}},
        headers={**DETAIL_HEADERS, "seek-request-country": country},
    )
    payload: Any = response.json()
    job = ((payload.get("data") or {}).get("jobDetails") or {}).get("job") or {}
    return build_description({"description": job.get("content")}) or None
