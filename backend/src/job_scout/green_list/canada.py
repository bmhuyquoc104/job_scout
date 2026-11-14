"""Canada's Express Entry category-based selection occupations, read from IRCC's page.

Each category (healthcare, STEM, trades...) has a table of occupations with their 2021 NOC code and
TEER level. A role is one NOC code; `lists` holds every category it is in. The NOC code is stored
in the `anzsco_code` column (the column is the country's occupation code, whatever the system).
"""

import re

from job_scout.core.errors import AppError, ErrorCode
from job_scout.green_list.parsing import RoleRecord, html_to_text
from job_scout.scraper import chrome_http

URL = (
    "https://www.canada.ca/en/immigration-refugees-citizenship/services/immigrate-canada/"
    "express-entry/rounds-invitations/category-based-selection.html"
)
MIN_ROLES = 40  # the page lists about 90; far fewer means it changed shape, not that they left
_SECTION = re.compile(r"<h[23][^>]*>(.*?)</h[23]>|<table.*?</table>", re.S)
_ROW = re.compile(r"<tr>\s*<td>(.*?)</td>\s*<td>(.*?)</td>\s*<td>(.*?)</td>", re.S)
_HEADING = re.compile(r"eligible for the (.+?)(?: occupations)? category", re.I)


def parse_categories_page(page: str) -> list[RoleRecord]:
    roles: dict[str, RoleRecord] = {}
    category = ""
    for match in _SECTION.finditer(page):
        if match.group(1) is not None:
            heading = _HEADING.search(html_to_text(match.group(1)))
            category = heading.group(1)[0].upper() + heading.group(1)[1:] if heading else ""
            continue
        for title, code, teer in _ROW.findall(match.group(0)):
            title, code, teer = (html_to_text(cell) for cell in (title, code, teer))
            if not category or not title or not re.fullmatch(r"\d{5}", code):
                raise AppError(ErrorCode.SCRAPE_SOURCE_ERROR, f"Unreadable IRCC row: {title!r}")
            known = roles.get(code)
            lists = (*known.lists, category) if known else (category,)
            roles[code] = RoleRecord(
                record_id=code,
                title=title,
                anzsco_code=code,
                industry=f"TEER {teer}",
                tier=None,
                pathway="Express Entry category-based draws",
                requirements="",
                engineering_degrees="",
                note="",
                raw={"occupation": title, "noc_2021": code, "teer": teer, "categories": lists},
                lists=lists,
            )
    if not roles:
        raise AppError(ErrorCode.SCRAPE_SOURCE_ERROR, "No occupation tables on the IRCC page")
    return list(roles.values())


async def fetch_occupations() -> list[RoleRecord]:
    """Every occupation on the page. Raises rather than return a partial list, because a partial
    list would make the sync look like occupations had been removed."""
    async with chrome_http.client() as http:
        response = await chrome_http.request(http, "GET", URL)
    roles = parse_categories_page(response.text)
    if len(roles) < MIN_ROLES:
        raise AppError(ErrorCode.SCRAPE_SOURCE_ERROR, f"Only {len(roles)} occupations on the page")
    return roles
