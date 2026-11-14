import pytest

from job_scout.core.errors import AppError
from job_scout.green_list.germany import parse_blue_card_page

PAGE = (
    "<p>To qualify for the &quot;regular&quot; EU Blue Card, applicants must earn a minimum gross "
    "annual salary, which is €50,700 in 2026. This amount is adjusted annually.</p>"
    "<p>Those just starting their careers can apply with a lower minimum gross annual salary, "
    "which is €45,934.20 in 2026.</p>"
)


def test_the_blue_card_thresholds_become_two_roles_with_their_year() -> None:
    standard, reduced = parse_blue_card_page(PAGE)

    assert (standard.record_id, standard.anzsco_code, standard.industry) == (
        "blue-card-standard",
        "€50,700",
        "Salary threshold 2026",
    )
    assert (reduced.record_id, reduced.anzsco_code) == ("blue-card-reduced", "€45,934.20")
    assert reduced.lists == ("EU Blue Card",)
    assert "IT specialists" in reduced.title


def test_a_page_without_the_thresholds_is_refused_not_read_as_empty() -> None:
    with pytest.raises(AppError):
        parse_blue_card_page("<p>Page not found</p>")
