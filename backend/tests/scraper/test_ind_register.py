import pytest

from job_scout.core.errors import AppError
from job_scout.scraper.ind_register import is_recognised_sponsor, normalize_company, parse_register

PAGE = (
    '<table><thead><tr><th scope="col">Organisation</th>'
    '<th scope="col">KVK (Chamber of Commerce) number</th></tr></thead><tbody>'
    '<tr><th scope="row">bunq B.V.</th><td>54992659</td></tr>'
    '<tr><th scope="row">N.V. Nederlandse Spoorwegen</th><td>30124910</td></tr>'
    '<tr><th scope="row">&quot;AAE&quot; Advanced Automated Equipment B.V.</th>'
    "<td>17037842</td></tr>"
    "</tbody></table>"
)


def test_company_names_match_ignoring_case_punctuation_and_legal_forms() -> None:
    assert normalize_company("N.V. Nederlandse Spoorwegen") == normalize_company(
        "Nederlandse Spoorwegen"
    )
    assert normalize_company("Bunq") == normalize_company("bunq B.V.")
    assert normalize_company("Booking.com B.V.") == "bookingcom"


def test_the_register_page_gives_its_organisations_as_matchable_names() -> None:
    names = parse_register(PAGE)

    assert len(names) == 3
    assert is_recognised_sponsor("Bunq", names)
    assert is_recognised_sponsor("Nederlandse Spoorwegen", names)
    assert is_recognised_sponsor('"AAE" Advanced Automated Equipment', names)
    assert not is_recognised_sponsor("Some Other Company", names)
    assert not is_recognised_sponsor("", names)


def test_a_page_without_the_table_is_refused_not_read_as_empty() -> None:
    with pytest.raises(AppError):
        parse_register("<p>Maintenance</p>")
