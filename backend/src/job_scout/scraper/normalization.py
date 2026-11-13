import re
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel

from job_scout.core.countries import COUNTRIES


class NormalizedListing(BaseModel):
    source: str = "seek"
    external_id: str
    company_name: str
    position: str
    listed_at: datetime | None
    location: str
    work_arrangements: list[str]
    work_types: list[str]
    salary_label: str
    pay_period: str
    url: str


def normalize_text(text: str = "") -> str:
    return re.sub(r"\s+", " ", text).strip()


def build_description(payload: dict[str, Any]) -> str:
    """SEEK's search results carry a teaser and bullet points; job pages are not scraped."""
    teaser = normalize_text(str(payload.get("teaser") or ""))
    raw_bullets = payload.get("bulletPoints")
    bullets = [
        text
        for item in (raw_bullets if isinstance(raw_bullets, list) else [])
        if isinstance(item, str) and (text := normalize_text(item))
    ]
    parts = [teaser] if teaser else []
    if bullets:
        parts.append("\n".join(f"• {bullet}" for bullet in bullets))
    return "\n\n".join(parts)


_AMOUNT = re.compile(r"\$\s*(\d[\d,]*(?:\.\d+)?)\s*(k\b)?", re.IGNORECASE)
# Pay period -> multiplier to a yearly figure (40h x 52 weeks = 2080h; 260 working days).
_PERIODS = (
    (re.compile(r"per\s*(?:hour|hr)|/\s*h(?:ou)?r|hourly", re.IGNORECASE), 2080),
    (re.compile(r"per\s*day|/\s*day|daily", re.IGNORECASE), 260),
    (re.compile(r"per\s*week|/\s*w(?:ee)?k|weekly", re.IGNORECASE), 52),
    (re.compile(r"per\s*month|/\s*mo(?:nth)?|monthly", re.IGNORECASE), 12),
    (re.compile(r"per\s*(?:year|annum)|/\s*y(?:ea)?r|\bp\.?a\b|annum|yearly|annual", re.I), 1),
)
_UP_TO = re.compile(r"\bup\s*to\b|\bmax(?:imum)?\b", re.IGNORECASE)
_FROM = re.compile(r"\b(?:from|starting|min(?:imum)?)\b", re.IGNORECASE)
_MIN_ANNUAL, _MAX_ANNUAL = 10_000, 1_000_000


def parse_salary(label: str) -> tuple[int | None, int | None]:
    """Estimate (min, max) annual NZD from free-text pay; (None, None) if there is no figure.

    shortcut: only `$` amounts are read and hours/days are annualised at 2080h/260d; upgrade if
    SEEK starts sending structured pay data.
    """
    amounts = [
        float(match.group(1).replace(",", "")) * (1000 if match.group(2) else 1)
        for match in _AMOUNT.finditer(label)
    ][:2]
    if not amounts:
        return None, None
    factor = next((factor for pattern, factor in _PERIODS if pattern.search(label)), None)
    if factor is None:  # no pay period written: big numbers are yearly, small ones hourly
        factor = 1 if max(amounts) >= _MIN_ANNUAL else 2080 if max(amounts) <= 500 else None
    if factor is None:
        return None, None
    annual = [round(amount * factor) for amount in amounts]
    if not all(_MIN_ANNUAL <= value <= _MAX_ANNUAL for value in annual):
        return None, None
    if len(annual) == 2:
        return min(annual), max(annual)
    if _UP_TO.search(label):
        return None, annual[0]
    if _FROM.search(label):
        return annual[0], None
    return annual[0], annual[0]


SENIORITY_LEVELS = ("graduate", "junior", "mid", "senior", "lead", "management", "unspecified")

# Manager titles that run people/teams; "Project/Product/Delivery Manager" are normal ICT roles.
_TEAM_MANAGER = (
    r"(?:it|ict|engineering|development|technology|infrastructure|security|technical|platform|"
    r"operations?|operational|service\s*desk|help\s*desk|support|team|department|general|"
    r"country|regional)"
)
# First match wins, so an explicit "junior" beats a later "lead" and "Senior Engineering Manager"
# is management.
_SENIORITY_RULES = (
    (
        "graduate",
        r"\b(?:graduate|grad|intern(?:ship)?|trainee|apprentice(?:ship)?|cadet|entry[- ]level)\b",
    ),
    ("junior", r"\b(?:junior|jr)\b"),
    (
        "management",
        rf"\b(?:head\s+of|director|chief|vice\s+president|vp|cto|cio|ciso|ceo|cfo|coo)\b"
        rf"|\b{_TEAM_MANAGER}\s+manager\b",
    ),
    ("lead", r"\b(?:lead|principal|team\s+leader)\b"),
    ("senior", r"\b(?:senior|snr|sr)\b"),
    ("mid", r"\b(?:intermediate|mid[- ]?level|midweight)\b"),
)
_SENIORITY_PATTERNS = tuple(
    (level, re.compile(pattern, re.IGNORECASE)) for level, pattern in _SENIORITY_RULES
)


def classify_seniority(title: str) -> str:
    """Level words in a job title, or "unspecified" (most titles say nothing about level).

    shortcut: title keywords only, no description or years-of-experience; upgrade if the
    seniority chart needs to be more accurate than that.
    """
    return next(
        (level for level, pattern in _SENIORITY_PATTERNS if pattern.search(title)), "unspecified"
    )


def region_of(location: str) -> str:
    """SEEK labels read "Suburb, Region" or just "Region", so the region is the last part."""
    region = re.sub(r"\s+\d{4}$", "", location.rsplit(",", 1)[-1].strip())  # drop NZ postcode
    return region or "Not stated"


def get_pay_period(salary: str = "") -> str:
    normalized = salary.lower()
    if "week" in normalized:
        return "Week"
    if "month" in normalized:
        return "Month"
    if "year" in normalized or "annum" in normalized or "pa" in normalized:
        return "Year"
    return ""


def normalize_listing(payload: dict[str, Any], country: str = "NZ") -> NormalizedListing:
    external_id = str(payload.get("id") or "")
    advertiser = payload.get("advertiser") or {}
    company_name = payload.get("companyName")
    if company_name is None:
        company_name = advertiser.get("description") or ""

    locations = payload.get("locations") or []
    arrangements = (payload.get("workArrangements") or {}).get("data") or []
    listed_at = payload.get("listingDate")
    try:
        listed_at = datetime.fromisoformat(listed_at.replace("Z", "+00:00"))
        if listed_at.tzinfo is None:
            listed_at = listed_at.replace(tzinfo=UTC)
    except AttributeError, TypeError, ValueError:
        listed_at = None

    salary_label = payload.get("salaryLabel") or ""
    return NormalizedListing(
        external_id=external_id,
        company_name=company_name,
        position=payload.get("title") or "",
        listed_at=listed_at,
        location=(locations[0].get("label") or "") if locations else "",
        work_arrangements=[
            label for item in arrangements if (label := (item.get("label") or {}).get("text"))
        ],
        work_types=payload.get("workTypes") or [],
        salary_label=salary_label,
        pay_period=get_pay_period(salary_label),
        url=f"https://{COUNTRIES[country].seek_host}/job/{external_id}",
    )
