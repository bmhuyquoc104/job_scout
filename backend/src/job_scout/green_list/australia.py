"""Australia's skilled occupation lists, read from the data Home Affairs embeds in its page.

The page carries every occupation with the lists it is on (CSOL, MLTSSL, STSOL, ROL), its ANZSCO
code and the visas it can be used for, as HTML-escaped JSON.
"""

import html
import json
import re
from typing import Any

from job_scout.core.errors import AppError, ErrorCode
from job_scout.green_list.parsing import RoleRecord, html_to_text
from job_scout.scraper import chrome_http

URL = "https://immi.homeaffairs.gov.au/visas/working-in-australia/skill-occupation-list"
MIN_ROLES = 300  # the page lists about 700; far fewer means it changed shape, not that they left
_ARRAY = re.compile(r'\[\s*\{"occupation"')
_CODE = re.compile(r"ANZSCO (2022|2013)[^<']*?(\d{6})")
_LIST_ORDER = ("CSOL", "MLTSSL", "STSOL", "ROL", "RSMS ROL")  # CSOL is the employer-sponsored one
# ANZSCO's first digit is its major group.
_GROUPS = {
    "1": "Managers",
    "2": "Professionals",
    "3": "Technicians and Trades Workers",
    "4": "Community and Personal Service Workers",
    "5": "Clerical and Administrative Workers",
    "6": "Sales Workers",
    "7": "Machinery Operators and Drivers",
    "8": "Labourers",
}


def _role(record: dict[str, Any]) -> RoleRecord:
    try:
        title = str(record["occupation"]).strip()
        codes: dict[str, str] = {}
        for year, code in _CODE.findall(str(record["anzscocode"])):
            codes.setdefault(year, code)
        names = [name.strip() for name in str(record["list"]).split(";") if name.strip()]
    except (KeyError, TypeError) as exc:
        raise AppError(ErrorCode.SCRAPE_SOURCE_ERROR, f"Unreadable occupation: {exc!r}") from exc
    # 2022 is the current classification; every role has at least the 2013 code.
    year = "2022" if "2022" in codes else "2013"
    if not title or year not in codes or not names:
        raise AppError(ErrorCode.SCRAPE_SOURCE_ERROR, f"Occupation {title or '?'} has no code/list")
    code = codes[year]
    authorities = [
        line.lstrip("• ").strip()
        for line in html_to_text(str(record.get("assessauth", ""))).split("\n")
    ]
    authorities = [line for line in authorities if line]
    visas = (re.sub(r"\s+", " ", visa).strip() for visa in str(record.get("visas", "")).split(";"))
    return RoleRecord(
        record_id=f"{year}-{code}",
        title=title,
        anzsco_code=code,
        industry=_GROUPS.get(code[0], ""),
        tier=None,
        pathway="; ".join(visa for visa in visas if visa),
        requirements=f"Assessing authority: {', '.join(authorities)}" if authorities else "",
        engineering_degrees="",
        note="",
        raw=record,
        lists=tuple(
            sorted(names, key=lambda n: (_LIST_ORDER.index(n) if n in _LIST_ORDER else 99, n))
        ),
    )


def parse_occupations_page(page: str) -> list[RoleRecord]:
    text = html.unescape(page)
    start = _ARRAY.search(text)
    if start is None:
        raise AppError(ErrorCode.SCRAPE_SOURCE_ERROR, "No occupation data on the Home Affairs page")
    try:
        records, _ = json.JSONDecoder().raw_decode(text[start.start() :])
    except ValueError as exc:
        raise AppError(ErrorCode.SCRAPE_SOURCE_ERROR, f"Unreadable occupation data: {exc}") from exc
    return [_role(record) for record in records]


async def fetch_occupations() -> list[RoleRecord]:
    """Every occupation on the page. Raises rather than return a partial list, because a partial
    list would make the sync look like occupations had been removed."""
    async with chrome_http.client() as http:
        response = await chrome_http.request(http, "GET", URL)
    roles = parse_occupations_page(response.text)
    if len(roles) < MIN_ROLES:
        raise AppError(ErrorCode.SCRAPE_SOURCE_ERROR, f"Only {len(roles)} occupations on the page")
    return roles
