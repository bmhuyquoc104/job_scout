"""The Netherlands' highly skilled migrant and EU Blue Card salary amounts, from the IND's page.

The Netherlands has no priority-occupation list for IT: the rule is a minimum gross monthly
salary, indexed each January and July. Each amount is stored as a role (its amount in the
`anzsco_code` column), like Germany's thresholds, so the monthly sync records when they change.
"""

import re

from job_scout.core.errors import AppError, ErrorCode
from job_scout.green_list.parsing import RoleRecord, html_to_text
from job_scout.scraper import chrome_http

URL = "https://ind.nl/en/required-amounts-income-requirements"
_YEAR = re.compile(r"required amount \(gross per month\) for (\d{4})")
_AMOUNT = r"€\s?(\d{1,3}(?:,\d{3})*)\.\d\d"
# (slug, title, pattern, pathway)
_AMOUNTS = (
    (
        "hsm-30-and-over",
        "Highly skilled migrant: aged 30 or older",
        r"Highly skilled migrants 30 years or older" + _AMOUNT,
        "Highly skilled migrant permit; the employer must be a recognised sponsor",
    ),
    (
        "hsm-under-30",
        "Highly skilled migrant: under 30",
        r"Highly skilled migrants younger than 30 years" + _AMOUNT,
        "Highly skilled migrant permit; the employer must be a recognised sponsor",
    ),
    (
        "hsm-reduced",
        "Highly skilled migrant: reduced criterion (recent graduates)",
        r"Highly skilled migrants reduced salary criterion" + _AMOUNT,
        "For an orientation-year permit holder or a recent graduate",
    ),
    (
        "blue-card-standard",
        "EU Blue Card: standard salary",
        r"(?<!criterion )European Blue Card" + _AMOUNT,
        "EU Blue Card; the employer need not be a recognised sponsor",
    ),
    (
        "blue-card-reduced",
        "EU Blue Card: reduced criterion (graduates)",
        r"Reduced salary criterion European Blue Card" + _AMOUNT,
        "For graduates of a higher education programme",
    ),
)


def parse_amounts_page(page: str) -> list[RoleRecord]:
    text = html_to_text(page).replace("​", "")
    year = _YEAR.search(text)
    roles = []
    for slug, title, pattern, pathway in _AMOUNTS:
        found = re.search(pattern, text)
        if found is None or year is None:
            raise AppError(
                ErrorCode.SCRAPE_SOURCE_ERROR, f"IND amount missing from the page: {slug}"
            )
        amount = found.group(1)
        roles.append(
            RoleRecord(
                record_id=slug,
                title=title,
                anzsco_code=f"€{amount} a month",
                industry=f"Salary threshold {year.group(1)}",
                tier=None,
                pathway=pathway,
                requirements="Minimum gross salary per month, without holiday allowance",
                engineering_degrees="",
                note="",
                raw={"threshold": amount, "year": year.group(1)},
                lists=("Highly skilled migrant",),
            )
        )
    return roles


async def fetch_thresholds() -> list[RoleRecord]:
    async with chrome_http.client() as http:
        response = await chrome_http.request(http, "GET", URL)
    return parse_amounts_page(response.text)
