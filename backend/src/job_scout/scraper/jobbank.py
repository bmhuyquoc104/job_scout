"""Job Bank (Canada's government job board), searched for IT jobs by NOC code.

Search pages list 25 jobs each (`&page=N`); a job's own page carries the full description. Job
Bank flags jobs whose employer applied for or holds an LMIA (Labour Market Impact Assessment, the
permit to hire a foreign worker), so that is saved with the job. Canada only.
"""

import asyncio
import html
import logging
import re
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any

from curl_cffi.requests import AsyncSession

from job_scout.core.errors import AppError, ErrorCode
from job_scout.green_list.parsing import html_to_text
from job_scout.scraper import chrome_http
from job_scout.scraper.normalization import NormalizedListing, get_pay_period

logger = logging.getLogger(__name__)
BASE = "https://www.jobbank.gc.ca"
# NOC 2021 IT occupations: data scientists, cybersecurity, systems analysts and developers, web
# designers and developers, network, user-support and testing technicians.
IT_NOC_CODES = (
    "21211", "21220", "21221", "21222", "21223", "21230", "21231", "21232",
    "21233", "21234", "22220", "22221", "22222",
)  # fmt: skip
SEARCH_URL = f"{BASE}/jobsearch/jobsearch?sort=D&" + "&".join(f"fn21={c}" for c in IT_NOC_CODES)
MAX_PAGES = 60  # 25 jobs a page; about 45 pages are IT jobs today
DETAIL_DELAY = 0.2  # seconds each request waits before freeing its slot
DETAIL_CONCURRENCY = 5  # job pages fetched at once
_ARTICLE = re.compile(r'<article id="article-(\d+)"(.*?)</article>', re.S)
_DESCRIPTION = re.compile(r'<span class="hidden" property="description">(.*?)</span>', re.S)


def _text(html: str, pattern: str) -> str:
    match = re.search(pattern, html, re.S)
    return html_to_text(match.group(1)).replace("\n", " ").strip() if match else ""


def parse_search_page(page: str) -> list[dict[str, Any]]:
    jobs = []
    for job_id, body in _ARTICLE.findall(page):
        flag = re.search(r'class="jobLMIAflag([^"]*)"', body)
        lmia = "" if not flag else "requested" if "submitted" in flag.group(1) else "approved"
        salary = _text(body, r'<li class="salary">(.*?)</li>').removeprefix("Salary").strip()
        jobs.append(
            {
                "id": job_id,
                "title": _text(body, r'<span class="noctitle">(.*?)</span>'),
                "company": _text(body, r'<li class="business">(.*?)</li>'),
                "location": _text(body, r'<li class="location">(.*?)</li>')
                .removeprefix("Location")
                .strip(),
                "salary": salary if "$" in salary else "",
                "posted": _text(body, r'<li class="date">(.*?)</li>'),
                "lmia": lmia,
                "url": f"{BASE}/jobsearch/jobposting/{job_id}",
            }
        )
    return jobs


def parse_description(page: str) -> str:
    match = _DESCRIPTION.search(page)
    # Some employers' descriptions arrive as escaped HTML.
    return html_to_text(html.unescape(match.group(1))) if match else ""


def client(country: str = "CA") -> AsyncSession:
    if country != "CA":
        raise AppError(ErrorCode.SCRAPE_SOURCE_ERROR, "Job Bank only covers Canada")
    return chrome_http.client()


async def _add_description(
    http: AsyncSession, limit: asyncio.Semaphore, job: dict[str, Any]
) -> None:
    async with limit:
        try:
            detail = await chrome_http.request(http, "GET", job["url"])
            job["description"] = parse_description(detail.text)
        except AppError as exc:  # a missing description never fails a job
            logger.warning("Job Bank %s: no description: %s", job["id"], exc)
            job["description"] = ""
        await asyncio.sleep(DETAIL_DELAY)


async def pages(http: AsyncSession, country: str = "CA") -> AsyncIterator[list[dict[str, Any]]]:
    limit = asyncio.Semaphore(DETAIL_CONCURRENCY)
    for number in range(1, MAX_PAGES + 1):
        response = await chrome_http.request(http, "GET", f"{SEARCH_URL}&page={number}")
        jobs = parse_search_page(response.text)
        if not jobs:
            return
        await asyncio.gather(*(_add_description(http, limit, job) for job in jobs))
        yield jobs
    raise AppError(ErrorCode.SCRAPE_SOURCE_ERROR, f"Exceeded {MAX_PAGES} Job Bank pages")


_PERIODS = {"hourly": "per hour", "daily": "per day", "weekly": "per week", "monthly": "per month",
            "annually": "per year"}  # fmt: skip


def normalize_listing(payload: dict[str, Any]) -> NormalizedListing:
    try:
        listed_at = datetime.strptime(str(payload.get("posted")), "%B %d, %Y").replace(tzinfo=UTC)
    except ValueError:
        listed_at = None
    salary_label = " ".join(_PERIODS.get(w, w) for w in str(payload.get("salary") or "").split())
    return NormalizedListing(
        source="jobbank",
        external_id=str(payload.get("id") or ""),
        company_name=str(payload.get("company") or ""),
        position=str(payload.get("title") or ""),
        listed_at=listed_at,
        location=str(payload.get("location") or ""),
        work_arrangements=[],
        work_types=[],
        salary_label=salary_label,
        pay_period=get_pay_period(salary_label),
        url=str(payload.get("url") or ""),
    )


_LMIA_NOTES = {
    "approved": "The employer has an approved LMIA (can hire foreign workers).",
    "requested": "The employer has applied for an LMIA (to hire foreign workers).",
}


def build_description(payload: dict[str, Any]) -> str:
    parts = [str(payload.get("description") or ""), _LMIA_NOTES.get(str(payload.get("lmia")), "")]
    return "\n\n".join(part for part in parts if part)
