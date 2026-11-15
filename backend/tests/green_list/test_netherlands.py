import pytest

from job_scout.core.errors import AppError
from job_scout.green_list.netherlands import parse_amounts_page

PAGE = (
    "<p>Type of highly skilled migrant/European Blue Card with the right required amount "
    "(gross per month) for 2026</p>"
    "<p>Highly skilled migrants reduced salary criterion€ 3,122.00€ 3,122.00€ 3,122.00</p>"
    "<p>Highly skilled migrants younger than 30 years€ 4,357.00</p>"
    "<p>Highly skilled migrants 30 years or older€ 5,942.00€ 5,942.00€ 5,942.00</p>"
    "<p>​European Blue Card€ 5,942.00€ 5,942.00€ 5,942.00</p>"
    "<p>Reduced salary criterion European Blue Card€ 4,754.00€ 4,754.00€ 4,754.00</p>"
)


def test_each_monthly_amount_becomes_a_salary_threshold_role() -> None:
    roles = {r.record_id: r for r in parse_amounts_page(PAGE)}

    assert {k: v.anzsco_code for k, v in roles.items()} == {
        "hsm-30-and-over": "€5,942 a month",
        "hsm-under-30": "€4,357 a month",
        "hsm-reduced": "€3,122 a month",
        "blue-card-standard": "€5,942 a month",
        "blue-card-reduced": "€4,754 a month",
    }
    assert all(r.industry == "Salary threshold 2026" for r in roles.values())


def test_a_page_missing_an_amount_is_refused_not_read_as_empty() -> None:
    with pytest.raises(AppError):
        parse_amounts_page(PAGE.replace("€ 4,754.00", "").replace("Reduced salary", "Other"))
