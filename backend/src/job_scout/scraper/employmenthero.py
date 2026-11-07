"""Employment Hero's public NZ job board: plain HTML pages with schema.org `JobPosting` data.

Only the job pages are read (never the site's /wp-json API, which robots.txt disallows).
"""

import asyncio
import html
import json
import re
from datetime import UTC, datetime
from typing import Any

import httpx

from job_scout.core.errors import AppError, ErrorCode
from job_scout.scraper.normalization import NormalizedListing, get_pay_period

BASE_URL = "https://employmenthero.com"
USER_AGENT = "job-scout-personal/0.1"
MAX_ATTEMPTS = 3
_SLUG = re.compile(r'href="(?:https://employmenthero\.com)?/nz/jobs/position/([^"#?/]+)')
_JSON_LD = re.compile(r"application/ld\+json[^>]*>(.*?)</script>", re.DOTALL)
_WORK_TYPES = {
    "FULL_TIME": "Full time",
    "PART_TIME": "Part time",
    "CONTRACTOR": "Contract/Temp",
    "TEMPORARY": "Contract/Temp",
    "CASUAL": "Casual/Vacation",
}
_PERIODS = {"YEAR": "year", "MONTH": "month", "WEEK": "week", "DAY": "day", "HOUR": "hour"}


def client() -> httpx.AsyncClient:
    return httpx.AsyncClient(timeout=30, headers={"User-Agent": USER_AGENT}, follow_redirects=True)


async def _get(http: httpx.AsyncClient, url: str, params: dict[str, str] | None = None) -> str:
    for attempt in range(MAX_ATTEMPTS):
        try:
            response = await http.get(url, params=params)
            response.raise_for_status()
            return response.text
        except (httpx.TransportError, httpx.HTTPStatusError) as exc:
            status = exc.response.status_code if isinstance(exc, httpx.HTTPStatusError) else 0
            transient = status == 0 or status == 429 or status >= 500
            if not transient or attempt == MAX_ATTEMPTS - 1:
                raise AppError(
                    ErrorCode.SCRAPE_SOURCE_ERROR, f"Employment Hero request failed: {exc!r}"
                ) from exc
            await asyncio.sleep(2 * 2**attempt)
    raise AssertionError("unreachable")


async def fetch_list_page(http: httpx.AsyncClient, sector_id: int, page: int) -> str:
    params = {"country_code": "NZ", "job_sector_ids": str(sector_id), "page": str(page)}
    return await _get(http, f"{BASE_URL}/nz/jobs/", params)


async def fetch_job_page(http: httpx.AsyncClient, slug: str) -> str:
    return await _get(http, job_url(slug))


def job_url(slug: str) -> str:
    return f"{BASE_URL}/nz/jobs/position/{slug}/"


def parse_job_slugs(page_html: str) -> list[str]:
    return list(dict.fromkeys(_SLUG.findall(page_html)))


def parse_job_posting(page_html: str, slug: str) -> dict[str, Any]:
    """The page's JobPosting, plus our `id` (the URL slug) and `url`."""
    for block in _JSON_LD.findall(page_html):
        try:
            data = json.loads(block)
        except ValueError:
            continue
        for item in data if isinstance(data, list) else [data]:
            if isinstance(item, dict) and item.get("@type") == "JobPosting":
                return {**item, "id": slug, "url": job_url(slug)}
    raise AppError(ErrorCode.SCRAPE_SOURCE_ERROR, f"No JobPosting on Employment Hero page {slug}")


def build_description(payload: dict[str, Any]) -> str:
    text = html.unescape(str(payload.get("description") or ""))
    text = re.sub(r"(?i)<li[^>]*>", "• ", text)
    text = re.sub(r"(?i)<br\s*/?>|</(?:p|li|h\d|div|ul|ol)>", "\n", text)
    text = html.unescape(re.sub(r"<[^>]+>", "", text))
    lines = (re.sub(r"[ \t ]+", " ", line).strip() for line in text.splitlines())
    return "\n".join(line for line in lines if line)


def _salary_label(payload: dict[str, Any]) -> str:
    value = (payload.get("baseSalary") or {}).get("value") or {}
    low, high = value.get("minValue"), value.get("maxValue")
    amounts = [f"${amount:,.0f}" for amount in (low, high) if isinstance(amount, int | float)]
    if not amounts:
        return ""
    period = _PERIODS.get(str(value.get("unitText") or "").upper(), "year")
    return f"{' - '.join(dict.fromkeys(amounts))} per {period}"


def normalize_listing(payload: dict[str, Any]) -> NormalizedListing:
    address = ((payload.get("jobLocation") or {}).get("address")) or {}
    place = ", ".join(
        part for part in (address.get("addressLocality"), address.get("addressRegion")) if part
    )
    employment = payload.get("employmentType") or []
    employment = [employment] if isinstance(employment, str) else employment
    try:
        listed_at = datetime.fromisoformat(str(payload.get("datePosted"))).replace(tzinfo=UTC)
    except ValueError:
        listed_at = None
    salary_label = _salary_label(payload)
    return NormalizedListing(
        source="employmenthero",
        external_id=str(payload.get("id") or ""),
        company_name=str((payload.get("hiringOrganization") or {}).get("name") or ""),
        position=str(payload.get("title") or ""),
        listed_at=listed_at,
        location=place,
        work_arrangements=["Remote"] if payload.get("jobLocationType") == "TELECOMMUTE" else [],
        work_types=[_WORK_TYPES[kind] for kind in employment if kind in _WORK_TYPES],
        salary_label=salary_label,
        pay_period=get_pay_period(salary_label),
        url=str(payload.get("url") or ""),
    )
