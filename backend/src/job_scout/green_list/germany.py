"""Germany's EU Blue Card salary thresholds, read from the Federal Employment Agency's page.

Germany has no priority-occupation list for IT: the rule is a minimum gross salary, with a lower
one for shortage occupations, IT specialists and new graduates. Each threshold is stored as a role
(its amount in the `anzsco_code` column) so the monthly sync records when the figures change.
"""

import re

from job_scout.core.errors import AppError, ErrorCode
from job_scout.green_list.parsing import RoleRecord, html_to_text
from job_scout.scraper import chrome_http

URL = (
    "https://www.arbeitsagentur.de/vor-ort/zav/working-and-living-in-germany/"
    "iss-en/issue-03-2026/blue-card"
)
# shortcut: the page is one issue of a newsletter; when a new year's issue appears, update URL.
_STANDARD = re.compile(r'"regular" EU Blue Card[^€]{0,200}€\s?([\d,]+(?:\.\d+)?) in (\d{4})')
_REDUCED = re.compile(
    r"lower minimum gross annual salary, which is €\s?([\d,]+(?:\.\d+)?) in (\d{4})"
)


def _role(slug: str, title: str, amount: str, year: str, pathway: str) -> RoleRecord:
    return RoleRecord(
        record_id=slug,
        title=title,
        anzsco_code=f"€{amount}",
        industry=f"Salary threshold {year}",
        tier=None,
        pathway=pathway,
        requirements="Minimum gross annual salary",
        engineering_degrees="",
        note="",
        raw={"threshold": amount, "year": year},
        lists=("EU Blue Card",),
    )


def parse_blue_card_page(page: str) -> list[RoleRecord]:
    text = html_to_text(page.replace("&quot;", '"'))
    standard, reduced = _STANDARD.search(text), _REDUCED.search(text)
    if standard is None or reduced is None:
        raise AppError(ErrorCode.SCRAPE_SOURCE_ERROR, "No Blue Card salary thresholds on the page")
    return [
        _role(
            "blue-card-standard",
            "EU Blue Card: standard salary",
            *standard.groups(),
            pathway="Regular Blue Card; no Federal Employment Agency approval needed",
        ),
        _role(
            "blue-card-reduced",
            "EU Blue Card: shortage occupations, IT specialists and new graduates",
            *reduced.groups(),
            pathway="Needs Federal Employment Agency approval of the employment terms",
        ),
    ]


async def fetch_thresholds() -> list[RoleRecord]:
    async with chrome_http.client() as http:
        response = await chrome_http.request(http, "GET", URL)
    return parse_blue_card_page(response.text)
