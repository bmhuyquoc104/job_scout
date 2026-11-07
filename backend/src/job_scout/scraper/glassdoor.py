"""Glassdoor NZ via the `/graph` endpoint its own site uses (the approach JobSpy takes).

The CSRF token is supplied through settings; Glassdoor can rotate it at any time.
Search results carry no description, so each page's jobs are completed with a details query.
"""

from collections.abc import AsyncIterator
from datetime import UTC, date, datetime, timedelta
from typing import Any

from curl_cffi.requests import AsyncSession

from job_scout.config import settings
from job_scout.core.errors import AppError, ErrorCode
from job_scout.scraper import chrome_http, employmenthero
from job_scout.scraper.normalization import NormalizedListing, get_pay_period

BASE_URL = "https://www.glassdoor.co.nz"
SEARCH_TERM = "IT"
LOCATION = "New Zealand"  # shortcut: resolved through Glassdoor's location lookup (a country).
PAGE_SIZE = 100
DETAILS_PER_REQUEST = 25
MAX_PAGES = 20
_LOCATION_TYPES = {"C": "CITY", "S": "STATE", "N": "COUNTRY"}
_WORK_TYPES = {
    "fulltime": "Full time",
    "parttime": "Part time",
    "contract": "Contract/Temp",
    "temporary": "Contract/Temp",
}
_PERIODS = {"ANNUAL": "year", "MONTHLY": "month", "HOURLY": "hour"}
_SEARCH_QUERY = """
query JobSearchResultsQuery(
    $keyword: String,
    $locationId: Int,
    $locationType: LocationTypeEnum,
    $numJobsToShow: Int!,
    $pageCursor: String,
    $pageNumber: Int,
    $filterParams: [FilterParams],
    $parameterUrlInput: String
) {
    jobListings(
        contextHolder: {
            searchParams: {
                keyword: $keyword,
                locationId: $locationId,
                locationType: $locationType,
                numPerPage: $numJobsToShow,
                pageCursor: $pageCursor,
                pageNumber: $pageNumber,
                filterParams: $filterParams,
                parameterUrlInput: $parameterUrlInput,
                searchType: SR
            }
        }
    ) {
        jobListings {
            jobview {
                header {
                    adOrderSponsorshipLevel
                    ageInDays
                    employer {
                        id
                    }
                    employerNameFromSearch
                    jobTypeKeys
                    locationName
                    locationType
                    payCurrency
                    payPeriod
                    payPeriodAdjustedPay {
                        p10
                        p90
                    }
                    rating
                    remoteWorkTypes
                }
                job {
                    jobTitleText
                    listingId
                }
                map {
                    country
                }
                overview {
                    headquarters
                    overview {
                        description
                    }
                    primaryIndustry {
                        industryName
                    }
                    revenue
                    size
                    squareLogoUrl
                    website
                }
            }
        }
        paginationCursors {
            cursor
            pageNumber
        }
    }
}
"""
_DETAILS_ALIAS = """
    j%s: jobView(listingId: %s, contextHolder: {queryString: "q", pageTypeEnum: SERP}) {
        job {
            description
        }
    }
"""


def client() -> AsyncSession:
    if not settings.glassdoor_csrf_token:
        raise AppError(ErrorCode.SCRAPE_SOURCE_ERROR, "GLASSDOOR_CSRF_TOKEN is not set")
    return chrome_http.client({"gd-csrf-token": settings.glassdoor_csrf_token})


async def _graph(http: AsyncSession, operation: str, query: str, variables: dict[str, Any]) -> Any:
    body = [{"operationName": operation, "variables": variables, "query": query}]
    response = await chrome_http.request(http, "POST", f"{BASE_URL}/graph", json=body)
    return response.json()[0]


async def _search_variables(http: AsyncSession) -> dict[str, Any]:
    response = await chrome_http.request(
        http,
        "GET",
        f"{BASE_URL}/autocomplete/location",
        params={"locationTypeFilters": "CITY,STATE,COUNTRY", "caller": "jobs", "term": LOCATION},
    )
    places = response.json()
    if not places:
        raise AppError(ErrorCode.SCRAPE_SOURCE_ERROR, f"Glassdoor location {LOCATION!r} not found")
    location_type = _LOCATION_TYPES[places[0]["locationType"]]
    location_id = places[0]["locationId"]
    return {
        "keyword": SEARCH_TERM,
        "numJobsToShow": PAGE_SIZE,
        "filterParams": [],
        "locationId": location_id,
        "locationType": location_type,
        "parameterUrlInput": f"IL.0,12_I{location_type}{location_id}",
    }


async def _descriptions(http: AsyncSession, ids: list[str]) -> dict[str, str]:
    found: dict[str, str] = {}
    for start in range(0, len(ids), DETAILS_PER_REQUEST):
        aliases = "".join(
            _DETAILS_ALIAS % (job_id, job_id) for job_id in ids[start : start + DETAILS_PER_REQUEST]
        )
        answer = await _graph(http, "JobDetails", f"query JobDetails {{{aliases}}}", {})
        for alias, view in (answer.get("data") or {}).items():
            if view:
                found[alias[1:]] = view["job"]["description"]
    return found


async def pages(http: AsyncSession) -> AsyncIterator[list[dict[str, Any]]]:
    variables = await _search_variables(http)
    cursor: str | None = None
    today = datetime.now(UTC).date()
    for page in range(1, MAX_PAGES + 1):
        answer = await _graph(
            http,
            "JobSearchResultsQuery",
            _SEARCH_QUERY,
            {**variables, "pageNumber": page, "pageCursor": cursor},
        )
        result = (answer.get("data") or {}).get("jobListings")
        if not result:
            raise AppError(
                ErrorCode.SCRAPE_SOURCE_ERROR, f"Glassdoor API error: {answer.get('errors')}"
            )
        payloads = [parse_listing(item, today) for item in result.get("jobListings") or []]
        descriptions = await _descriptions(http, [p["id"] for p in payloads])
        for payload in payloads:
            payload["description"] = descriptions.get(payload["id"], "")
        yield payloads
        cursor = {c["pageNumber"]: c["cursor"] for c in result.get("paginationCursors") or []}.get(
            page + 1
        )
        if not payloads or not cursor:
            return
    raise AppError(ErrorCode.SCRAPE_SOURCE_ERROR, f"Exceeded {MAX_PAGES} Glassdoor pages")


def parse_listing(listing: dict[str, Any], today: date) -> dict[str, Any]:
    """A search result flattened into our payload (with `id`, `url` and a posted date)."""
    view = listing["jobview"]
    header, job = view["header"], view["job"]
    pay = header.get("payPeriodAdjustedPay") or {}
    job_id = str(job["listingId"])
    return {
        "id": job_id,
        "title": job.get("jobTitleText") or "",
        "company": header.get("employerNameFromSearch") or "",
        "location": header.get("locationName") or "",
        "datePosted": (today - timedelta(days=header.get("ageInDays") or 0)).isoformat(),
        "payPeriod": header.get("payPeriod"),
        "payMin": pay.get("p10"),
        "payMax": pay.get("p90"),
        "jobTypes": header.get("jobTypeKeys") or [],
        "url": f"{BASE_URL}/job-listing/j?jl={job_id}",
    }


def normalize_listing(payload: dict[str, Any]) -> NormalizedListing:
    amounts = [
        f"${amount:,.0f}"
        for amount in (payload.get("payMin"), payload.get("payMax"))
        if isinstance(amount, int | float)
    ]
    salary_label = ""
    if amounts:
        period = _PERIODS.get(str(payload.get("payPeriod") or "").upper(), "year")
        salary_label = f"{' - '.join(dict.fromkeys(amounts))} per {period}"
    try:
        listed_at = datetime.fromisoformat(str(payload.get("datePosted"))).replace(tzinfo=UTC)
    except ValueError:
        listed_at = None
    work_types = [_WORK_TYPES[k] for k in payload.get("jobTypes") or [] if k in _WORK_TYPES]
    return NormalizedListing(
        source="glassdoor",
        external_id=str(payload.get("id") or ""),
        company_name=str(payload.get("company") or ""),
        position=str(payload.get("title") or ""),
        listed_at=listed_at,
        location=str(payload.get("location") or ""),
        work_arrangements=[],
        work_types=list(dict.fromkeys(work_types)),
        salary_label=salary_label,
        pay_period=get_pay_period(salary_label),
        url=str(payload.get("url") or ""),
    )


def build_description(payload: dict[str, Any]) -> str:
    return employmenthero.build_description(payload)
