"""IamExpat's job board for the Netherlands: the English-language "IT & technology" section.

The list page shows 20 jobs and `?page=N` the rest. A job's own page carries a schema.org
`JobPosting` (title, description, date, employer, city) inside its Next.js flight data, so the list
only supplies the job links. Netherlands only.
"""

import asyncio
import json
import logging
import re
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any

from curl_cffi.requests import AsyncSession

from job_scout.core.errors import AppError, ErrorCode
from job_scout.green_list.parsing import html_to_text
from job_scout.scraper import chrome_http
from job_scout.scraper.normalization import NormalizedListing

logger = logging.getLogger(__name__)
BASE = "https://www.iamexpat.nl"
SECTION = "/career/jobs-netherlands/it-technology-positions"
MAX_PAGES = 20  # about 20 jobs a page; the section has under 30 jobs today
DETAIL_DELAY = 0.5  # seconds between job pages
_LINK = re.compile(re.escape(SECTION) + r'/[^"/]+/[A-Za-z0-9]+(?=")')
_CHUNK = re.compile(r'self\.__next_f\.push\(\[1,("(?:[^"\\]|\\.)*")\]\)')
_POSTING = re.compile(r'"@type"\s*:\s*"JobPosting"')


def parse_list_page(page: str) -> list[str]:
    """The IT job links on a list page, each once, in page order."""
    return list(dict.fromkeys(_LINK.findall(page)))


def _object_around(text: str, position: int) -> dict[str, Any] | None:
    """The smallest JSON object that starts before `position` and holds it."""
    start = position
    while start > 0:
        start -= 1
        if text[start] != "{":
            continue
        depth = 0
        for end in range(start, len(text)):
            depth += (text[end] == "{") - (text[end] == "}")
            if depth == 0:
                try:
                    found = json.loads(text[start : end + 1])
                except ValueError:
                    break
                if isinstance(found, dict) and "description" in found:
                    return found
                break
    return None


def parse_job_page(page: str, href: str) -> dict[str, Any]:
    """The page's JobPosting, plus our `id` (the job's code) and `url`."""
    flight = "".join(json.loads(chunk) for chunk in _CHUNK.findall(page))
    for match in _POSTING.finditer(flight):
        posting = _object_around(flight, match.start())
        if posting is not None:
            return {**posting, "id": href.rsplit("/", 1)[-1], "url": f"{BASE}{href}"}
    raise AppError(ErrorCode.SCRAPE_SOURCE_ERROR, f"No JobPosting on IamExpat page {href}")


def client(country: str = "NL") -> AsyncSession:
    if country != "NL":
        raise AppError(ErrorCode.SCRAPE_SOURCE_ERROR, "IamExpat only covers the Netherlands")
    return chrome_http.client()


async def pages(http: AsyncSession, country: str = "NL") -> AsyncIterator[list[dict[str, Any]]]:
    seen: set[str] = set()
    for number in range(1, MAX_PAGES + 1):
        url = f"{BASE}{SECTION}" + (f"?page={number}" if number > 1 else "")
        hrefs = [
            h
            for h in parse_list_page((await chrome_http.request(http, "GET", url)).text)
            if h not in seen
        ]
        if not hrefs:
            return
        seen.update(hrefs)
        jobs = []
        for href in hrefs:
            detail = await chrome_http.request(http, "GET", f"{BASE}{href}")
            try:
                jobs.append(parse_job_page(detail.text, href))
            except AppError as exc:
                # The list can still link a job that was just taken down; one dead page must
                # not stop the whole scrape.
                logger.warning("Skipping IamExpat job: %s", exc)
            await asyncio.sleep(DETAIL_DELAY)
        yield jobs
    raise AppError(ErrorCode.SCRAPE_SOURCE_ERROR, f"Exceeded {MAX_PAGES} IamExpat pages")


def normalize_listing(payload: dict[str, Any]) -> NormalizedListing:
    try:
        listed_at = datetime.fromisoformat(str(payload["datePosted"])).replace(tzinfo=UTC)
    except KeyError, ValueError:
        listed_at = None
    organisation = payload.get("hiringOrganization") or {}
    address = (payload.get("jobLocation") or {}).get("address") or {}
    return NormalizedListing(
        source="iamexpat",
        external_id=str(payload.get("id") or ""),
        company_name=str(organisation.get("name") or ""),
        position=str(payload.get("title") or ""),
        listed_at=listed_at,
        location=str(address.get("addressLocality") or ""),
        work_arrangements=[],
        work_types=[],
        salary_label="",
        pay_period="",
        url=str(payload.get("url") or ""),
    )


def build_description(payload: dict[str, Any]) -> str:
    return html_to_text(str(payload.get("description") or ""))
