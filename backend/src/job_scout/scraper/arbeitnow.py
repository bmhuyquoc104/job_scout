"""Arbeitnow's free public job API (Germany), filtered to IT jobs.

The API returns 300 jobs a page across every field, so IT jobs are picked by tag or title. Its terms
ask clients not to abuse it and to link back: each job links to its Arbeitnow page.
"""

import re
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any

from curl_cffi.requests import AsyncSession

from job_scout.core.errors import AppError, ErrorCode
from job_scout.green_list.parsing import html_to_text
from job_scout.scraper import chrome_http
from job_scout.scraper.normalization import NormalizedListing

API_URL = "https://www.arbeitnow.com/api/job-board-api"
MAX_PAGES = 60  # 300 jobs a page; the whole board is about 32 pages (9,000 jobs) today
IT_TAGS = {
    "software development",
    "technology",
    "infrastructure & devops",
    "it",
    "data & analytics",
}
# shortcut: a keyword guess at "IT"; tighten if non-IT jobs show up.
IT_TITLE = re.compile(
    r"software|entwickler|developer|devops|\bit\b|data (engineer|scientist)|cloud|cyber|"
    r"sysadmin|administrator|qa engineer|frontend|backend|full.?stack|machine learning",
    re.IGNORECASE,
)


def it_jobs(page: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The page's IT jobs, each given our `id` (the job's slug)."""
    return [
        {**job, "id": job["slug"]}
        for job in page
        if IT_TITLE.search(str(job.get("title") or ""))
        or any(str(tag).lower() in IT_TAGS for tag in job.get("tags") or [])
    ]


def client(country: str = "DE") -> AsyncSession:
    if country != "DE":
        raise AppError(ErrorCode.SCRAPE_SOURCE_ERROR, "Arbeitnow only covers Germany")
    return chrome_http.client()


async def pages(http: AsyncSession, country: str = "DE") -> AsyncIterator[list[dict[str, Any]]]:
    for number in range(1, MAX_PAGES + 1):
        body = (await chrome_http.request(http, "GET", API_URL, params={"page": number})).json()
        data = body.get("data")
        if not isinstance(data, list):
            raise AppError(ErrorCode.SCRAPE_SOURCE_ERROR, "Unreadable Arbeitnow response")
        if not data:
            return
        yield it_jobs(data)
        if not (body.get("links") or {}).get("next"):
            return
    raise AppError(ErrorCode.SCRAPE_SOURCE_ERROR, f"Exceeded {MAX_PAGES} Arbeitnow pages")


def _work_types(job_types: list[str]) -> list[str]:
    text = " ".join(job_types).lower()
    found = [
        label
        for label, words in (
            ("Full time", ("full", "vollzeit")),
            ("Part time", ("part", "teilzeit")),
            ("Contract/Temp", ("contract", "temp", "befristet", "freelance")),
        )
        if any(word in text for word in words)
    ]
    return found


def normalize_listing(payload: dict[str, Any]) -> NormalizedListing:
    try:
        listed_at = datetime.fromtimestamp(int(payload["created_at"]), UTC)
    except KeyError, TypeError, ValueError:
        listed_at = None
    return NormalizedListing(
        source="arbeitnow",
        external_id=str(payload.get("id") or ""),
        company_name=str(payload.get("company_name") or ""),
        position=str(payload.get("title") or ""),
        listed_at=listed_at,
        location=str(payload.get("location") or ""),
        work_arrangements=["Remote"] if payload.get("remote") else [],
        work_types=_work_types([str(t) for t in payload.get("job_types") or []]),
        salary_label="",
        pay_period="",
        url=str(payload.get("url") or ""),
    )


def build_description(payload: dict[str, Any]) -> str:
    return html_to_text(str(payload.get("description") or ""))
