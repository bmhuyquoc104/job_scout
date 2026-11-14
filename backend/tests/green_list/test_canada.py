import pytest

from job_scout.core.errors import AppError
from job_scout.green_list.canada import parse_categories_page


def table(*rows: tuple[str, str, int]) -> str:
    body = "".join(
        f"<tr><td><p>{name}</p></td><td><p>{noc}</p></td><td><p>{teer}</p></td></tr>"
        for name, noc, teer in rows
    )
    return (
        "<table><thead><tr><th>Occupation</th><th>2021 NOC code</th><th>2021 TEER category</th>"
        f"</tr></thead><tbody>{body}</tbody></table>"
    )


PAGE = (
    "<h2>Who’s eligible for the French-language proficiency category</h2><p>No list.</p>"
    "<h2>Who’s eligible for the healthcare and social services occupations category</h2>"
    + table(("Pharmacists", "31120", 1), ("Nurse aides", "33102", 3))
    + "<h2>Who’s eligible for the Science, Technology, Engineering and Math (STEM) occupations "
    "category</h2>" + table(("Pharmacists", "31120", 1), ("Software engineers", "21231", 1))
)


def test_each_noc_code_becomes_one_role_listing_every_category_it_is_in() -> None:
    roles = {role.record_id: role for role in parse_categories_page(PAGE)}

    assert sorted(roles) == ["21231", "31120", "33102"]
    pharmacist = roles["31120"]
    assert (pharmacist.title, pharmacist.anzsco_code, pharmacist.industry) == (
        "Pharmacists",
        "31120",
        "TEER 1",
    )
    assert pharmacist.lists == (
        "Healthcare and social services",
        "Science, Technology, Engineering and Math (STEM)",
    )
    assert roles["33102"].lists == ("Healthcare and social services",)


def test_a_page_without_occupation_tables_is_refused_not_read_as_empty() -> None:
    with pytest.raises(AppError):
        parse_categories_page("<h2>Who’s eligible for the trade occupations category</h2>")
