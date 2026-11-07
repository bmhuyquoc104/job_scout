"""Indeed NZ via the GraphQL API that Indeed's own mobile app uses (the approach JobSpy takes).

The API key is the app's, supplied through settings; it can be rotated by Indeed at any time.
"""

import json
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any

from curl_cffi.requests import AsyncSession

from job_scout.config import settings
from job_scout.core.errors import AppError, ErrorCode
from job_scout.scraper import chrome_http, employmenthero
from job_scout.scraper.normalization import NormalizedListing, get_pay_period

BASE_URL = "https://nz.indeed.com"
API_URL = "https://apis.indeed.com/graphql"
SEARCH_TERM = "IT"
LOCATION = (
    "New Zealand"  # shortcut: untested as a nationwide `where`; use cities if it under-returns.
)
PAGE_SIZE = 100
MAX_PAGES = 20
_HEADERS = {
    "content-type": "application/json",
    "accept": "application/json",
    "accept-language": "en-NZ,en;q=0.9",
    "user-agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6_1 like Mac OS X) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Mobile/15E148 Indeed App 193.1",
    "indeed-app-info": "appv=193.1; appid=com.indeed.jobsearch; osv=16.6.1; os=ios; dtype=phone",
    "indeed-co": "NZ",
    "indeed-locale": "en-NZ",
}
_WORK_TYPES = {
    "CF3CP": "Full time",
    "75GKK": "Part time",
    "NJXCK": "Contract/Temp",
    "T9BXE": "Contract/Temp",
    "T65DZ": "Contract/Temp",
    "4HKF7": "Contract/Temp",
    "CJWTS": "Contract/Temp",
}
_PERIODS = {"HOUR": "hour", "DAY": "day", "WEEK": "week", "MONTH": "month", "YEAR": "year"}
_QUERY = """
    query GetJobData {{
        jobSearch(
            {what}
            {location}
            limit: {limit}
            {cursor}
            sort: RELEVANCE
            {filters}
        ) {{
            pageInfo {{
                nextCursor
            }}
            results {{
                job {{
                    key
                    title
                    sourceEmployerName
                    dateOnIndeed
                    description {{
                        html
                    }}
                    location {{
                        countryCode
                        admin1Code
                        city
                    }}
                    compensation {{
                        estimated {{
                            currencyCode
                            baseSalary {{
                                unitOfWork
                                range {{
                                    ... on Range {{ min max }}
                                    ... on AtLeast {{ min }}
                                    ... on AtMost {{ max }}
                                    ... on Exactly {{ value }}
                                }}
                            }}
                        }}
                        baseSalary {{
                            unitOfWork
                            range {{
                                ... on Range {{ min max }}
                                ... on AtLeast {{ min }}
                                ... on AtMost {{ max }}
                                ... on Exactly {{ value }}
                            }}
                        }}
                        currencyCode
                    }}
                    attributes {{
                        key
                    }}
                    employer {{
                        relativeCompanyPageUrl
                        name
                        ugcStats {{
                            ratings {{
                                overallRating {{
                                    value
                                    count
                                }}
                            }}
                        }}
                        dossier {{
                            employerDetails {{
                                addresses
                                industry
                                employeesLocalizedLabel
                                revenueLocalizedLabel
                                briefDescription
                            }}
                            images {{
                                squareLogoUrl
                            }}
                            links {{
                                corporateWebsite
                            }}
                        }}
                    }}
                    recruit {{
                        viewJobUrl
                    }}
                }}
            }}
        }}
    }}
"""


def client() -> AsyncSession:
    if not settings.indeed_api_key:
        raise AppError(ErrorCode.SCRAPE_SOURCE_ERROR, "INDEED_API_KEY is not set")
    return chrome_http.client({**_HEADERS, "indeed-api-key": settings.indeed_api_key})


def build_query(cursor: str | None) -> str:
    return _QUERY.format(
        what=f"what: {json.dumps(SEARCH_TERM)}",
        location=f"location: {{where: {json.dumps(LOCATION)}, radius: 50, radiusUnit: MILES}}",
        limit=PAGE_SIZE,
        cursor=f"cursor: {json.dumps(cursor)}" if cursor else "",
        filters="",
    )


def parse_search(data: dict[str, Any]) -> tuple[list[dict[str, Any]], str | None]:
    """The page's jobs (each given our `id` and `url`) and the next-page cursor, if any."""
    search = (data.get("data") or {}).get("jobSearch")
    if not search:
        raise AppError(ErrorCode.SCRAPE_SOURCE_ERROR, f"Indeed API error: {data.get('errors')}")
    payloads = [
        {**job, "id": job["key"], "url": f"{BASE_URL}/viewjob?jk={job['key']}"}
        for result in search.get("results") or []
        if (job := result.get("job"))
    ]
    return payloads, (search.get("pageInfo") or {}).get("nextCursor")


async def pages(http: AsyncSession) -> AsyncIterator[list[dict[str, Any]]]:
    cursor: str | None = None
    for _ in range(MAX_PAGES):
        response = await chrome_http.request(
            http, "POST", API_URL, json={"query": build_query(cursor)}
        )
        payloads, cursor = parse_search(response.json())
        yield payloads
        if not payloads or not cursor:
            return
    raise AppError(ErrorCode.SCRAPE_SOURCE_ERROR, f"Exceeded {MAX_PAGES} Indeed pages")


def _salary_label(payload: dict[str, Any]) -> str:
    salary = (payload.get("compensation") or {}).get("baseSalary") or {}
    pay_range = salary.get("range") or {}
    amounts = [
        f"${amount:,.0f}"
        for amount in (pay_range.get("min"), pay_range.get("max"), pay_range.get("value"))
        if isinstance(amount, int | float)
    ]
    if not amounts:
        return ""
    period = _PERIODS.get(str(salary.get("unitOfWork") or "").upper(), "year")
    return f"{' - '.join(dict.fromkeys(amounts))} per {period}"


def normalize_listing(payload: dict[str, Any]) -> NormalizedListing:
    place = payload.get("location") or {}
    posted = payload.get("dateOnIndeed")
    salary_label = _salary_label(payload)
    work_types = [
        _WORK_TYPES[a["key"]]
        for a in payload.get("attributes") or []
        if a.get("key") in _WORK_TYPES
    ]
    return NormalizedListing(
        source="indeed",
        external_id=str(payload.get("id") or ""),
        company_name=str(
            payload.get("sourceEmployerName") or (payload.get("employer") or {}).get("name") or ""
        ),
        position=str(payload.get("title") or ""),
        listed_at=datetime.fromtimestamp(posted / 1000, UTC) if posted else None,
        location=", ".join(p for p in (place.get("city"), place.get("admin1Code")) if p),
        work_arrangements=[],
        work_types=list(dict.fromkeys(work_types)),
        salary_label=salary_label,
        pay_period=get_pay_period(salary_label),
        url=str(payload.get("url") or ""),
    )


def build_description(payload: dict[str, Any]) -> str:
    html = (payload.get("description") or {}).get("html")
    return employmenthero.build_description({"description": html})
