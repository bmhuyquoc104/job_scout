from datetime import UTC, datetime

import pytest

from job_scout.scraper import normalization


def test_normalize_listing_uses_source_fallbacks_and_nested_fields() -> None:
    normalize = getattr(normalization, "normalize_listing", None)
    assert callable(normalize), "normalize_listing must exist"
    payload = {
        "id": 95307525,
        "companyName": None,
        "advertiser": {"description": "Daraco IT Services"},
        "title": "IT Support Engineer",
        "locations": [{"label": "Newtown, Wellington"}],
        "workArrangements": {
            "data": [
                {"label": {"text": "Hybrid"}},
                {"label": {"text": "On-site"}},
                {"label": {}},
            ]
        },
        "workTypes": ["Full time"],
        "salaryLabel": "$80,000 per annum",
        "listingDate": "2026-10-16T03:26:35Z",
    }

    result = normalize(payload)

    assert result.model_dump() == {
        "source": "seek",
        "external_id": "95307525",
        "company_name": "Daraco IT Services",
        "position": "IT Support Engineer",
        "listed_at": datetime(2026, 10, 16, 3, 26, 35, tzinfo=UTC),
        "location": "Newtown, Wellington",
        "work_arrangements": ["Hybrid", "On-site"],
        "work_types": ["Full time"],
        "salary_label": "$80,000 per annum",
        "pay_period": "Year",
        "url": "https://www.seek.co.nz/job/95307525",
    }


def test_normalize_listing_handles_missing_optional_fields() -> None:
    normalize = getattr(normalization, "normalize_listing", None)
    assert callable(normalize), "normalize_listing must exist"

    result = normalize({"id": "job-2"})

    assert result.company_name == ""
    assert result.location == ""
    assert result.work_arrangements == []
    assert result.work_types == []
    assert result.listed_at is None
    assert result.url == "https://www.seek.co.nz/job/job-2"


@pytest.mark.parametrize(
    ("salary", "expected"),
    [
        ("$1,000 per week", "Week"),
        ("$4,000 a month", "Month"),
        ("$90,000 per year", "Year"),
        ("$90,000 per annum", "Year"),
        ("$90,000 pa", "Year"),
        ("Competitive", ""),
    ],
)
def test_get_pay_period_preserves_current_salary_rules(salary: str, expected: str) -> None:
    get_pay_period = getattr(normalization, "get_pay_period", None)
    assert callable(get_pay_period), "get_pay_period must exist"
    assert get_pay_period(salary) == expected


def test_normalize_text_collapses_whitespace() -> None:
    normalize = getattr(normalization, "normalize_text", None)
    assert callable(normalize), "normalize_text must exist"
    assert normalize("  Job\n\t description  ") == "Job description"


def test_build_description_combines_teaser_and_bullet_points() -> None:
    payload = {
        "teaser": "  Join   our team ",
        "bulletPoints": ["Great pay | Perks", "  Remote   friendly "],
    }

    assert normalization.build_description(payload) == (
        "Join our team\n\n• Great pay | Perks\n• Remote friendly"
    )


def test_build_description_tolerates_missing_or_odd_fields() -> None:
    assert normalization.build_description({}) == ""
    assert normalization.build_description({"teaser": "Only teaser"}) == "Only teaser"
    assert normalization.build_description({"bulletPoints": ["Only bullet"]}) == "• Only bullet"
    assert normalization.build_description({"bulletPoints": [None, 3, "", "ok"]}) == "• ok"
    assert normalization.build_description({"bulletPoints": "not a list"}) == ""


@pytest.mark.parametrize(
    ("label", "expected"),
    [
        ("$110,000 – $135,000 per year", (110_000, 135_000)),
        ("$112000.00 - $130000.00 p.a. +  + benefits", (112_000, 130_000)),
        ("$83818 - $117788 p.a.", (83_818, 117_788)),
        ("$100,000 - $120,000", (100_000, 120_000)),
        ("$100k - $120k", (100_000, 120_000)),
        ("$28 per hour", (58_240, 58_240)),
        ("$45 - $55 per hour", (93_600, 114_400)),
        ("Up to $120/hr plus GST", (None, 249_600)),
        ("From $90,000 per year", (90_000, None)),
        ("$3,000 per week", (156_000, 156_000)),
        ("$8,000 per month", (96_000, 96_000)),
        ("$150 per day", (39_000, 39_000)),
        ("Competitive salary + paid medical insurance", (None, None)),
        ("Be Part of a Global Growth Organisation", (None, None)),
        (".", (None, None)),
        ("", (None, None)),
        ("$2", (None, None)),
        ("$2,500,000", (None, None)),
    ],
)
def test_parse_salary_estimates_an_annual_range_or_nothing(
    label: str, expected: tuple[int | None, int | None]
) -> None:
    assert normalization.parse_salary(label) == expected


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        ("Graduate Software Engineer", "graduate"),
        ("Entry Level Support Engineer", "graduate"),
        ("Internship - Data Analyst", "graduate"),
        ("Junior Developer", "junior"),
        ("Jr. Network Engineer", "junior"),
        ("Software Engineer - Junior & Intermediate", "junior"),
        ("Intermediate Business Analyst", "mid"),
        ("Mid-level Data Engineer", "mid"),
        ("Senior Data Engineer", "senior"),
        ("Sr. Systems Administrator", "senior"),
        ("Senior Project Manager", "senior"),
        ("Lead Network & Security Architect", "lead"),
        ("Principal Business Analyst", "lead"),
        ("Tech Lead", "lead"),
        ("Team Lead - Support", "lead"),
        ("Engineering Manager", "management"),
        ("Service Desk Manager", "management"),
        ("Senior Engineering Manager", "management"),
        ("Head of Data", "management"),
        ("Director of Engineering", "management"),
        ("Chief Technology Officer", "management"),
        ("Project Manager", "unspecified"),
        ("Product Manager", "unspecified"),
        ("Business Analyst", "unspecified"),
        ("International Sales Executive", "unspecified"),
        ("", "unspecified"),
    ],
)
def test_classify_seniority_reads_level_words_from_the_title(title: str, expected: str) -> None:
    assert normalization.classify_seniority(title) == expected


@pytest.mark.parametrize(
    ("location", "expected"),
    [
        ("Newmarket, Auckland", "Auckland"),
        ("Auckland CBD, Auckland", "Auckland"),
        ("Rodney & North Shore, Auckland", "Auckland"),
        ("Auckland", "Auckland"),
        ("Christchurch Central, Canterbury", "Canterbury"),
        ("Tauranga Central, Bay of Plenty", "Bay of Plenty"),
        ("  Wellington Central ,  Wellington  ", "Wellington"),
        ("", "Not stated"),
        ("   ", "Not stated"),
        ("Somewhere,", "Not stated"),
    ],
)
def test_region_of_is_the_last_part_of_a_seek_location(location: str, expected: str) -> None:
    assert normalization.region_of(location) == expected
