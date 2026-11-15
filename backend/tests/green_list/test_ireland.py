import io
import zipfile

import pytest

from job_scout.core.errors import AppError
from job_scout.green_list.ireland import parse_csol_docx, parse_permit_page

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def cell(*lines: str, merge: str | None = None) -> str:
    props = f"<w:tcPr><w:vMerge{merge}/></w:tcPr>" if merge is not None else ""
    paragraphs = "".join(f"<w:p><w:r><w:t>{line}</w:t></w:r></w:p>" for line in lines)
    return f"<w:tc>{props}{paragraphs}</w:tc>"


def row(*cells: str) -> str:
    return f"<w:tr>{''.join(cells)}</w:tr>"


def docx(*rows: str) -> bytes:
    xml = (
        f'<w:document xmlns:w="{W}"><w:body><w:p><w:r><w:t>Critical Skills Occupations List'
        f"</w:t></w:r></w:p><w:tbl>{''.join(rows)}</w:tbl>"
        "<w:p><w:r><w:t>A note after the table.</w:t></w:r></w:p></w:body></w:document>"
    )
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("word/document.xml", xml)
    return buffer.getvalue()


HEADER = row(cell("SOC-3", merge=None), cell("Employment category", merge=None),
             cell("SOC-4", merge=None), cell("Employments", merge=None))  # fmt: skip
CSOL = docx(
    HEADER,
    row(
        cell("113", merge=' w:val="restart"'),
        cell("ICT Professionals", merge=' w:val="restart"'),
        cell("1136", merge=None),
        cell("IT project and programme managers", "Programmers and software development "
             "professionals", merge=None),
    ),
    row(cell("", merge=""), cell("", merge=""), cell("1137", merge=None),
        cell("Web design and development professionals", merge=None)),
)  # fmt: skip


def test_each_listed_employment_becomes_a_role_under_its_soc_code_and_category() -> None:
    roles = parse_csol_docx(CSOL)

    assert [(r.anzsco_code, r.title, r.industry) for r in roles] == [
        ("1136", "IT project and programme managers", "ICT Professionals"),
        ("1136", "Programmers and software development professionals", "ICT Professionals"),
        ("1137", "Web design and development professionals", "ICT Professionals"),
    ]
    assert len({r.record_id for r in roles}) == 3
    assert roles[0].lists == ("Critical Skills Occupations List",)


def test_a_very_long_employment_is_kept_with_a_shortened_title() -> None:
    long_text = "Academics who hold a qualification " + "with relevant teaching experience " * 12
    roles = parse_csol_docx(
        docx(
            HEADER,
            row(
                cell("231", merge=' w:val="restart"'),
                cell("Teaching", merge=' w:val="restart"'),
                cell("2311", merge=None),
                cell(long_text, merge=None),
            ),
        )  # fmt: skip
    )

    assert len(roles[0].title) <= 300
    assert roles[0].title.endswith("…")
    assert roles[0].raw["employment"] == long_text.strip()


def test_a_document_without_the_table_is_refused_not_read_as_empty() -> None:
    with pytest.raises(AppError):
        parse_csol_docx(docx())


PERMIT_PAGE = (
    "<p>The following are eligible: Occupations with a minimum annual remuneration of €40,904 "
    "for a restricted number of strategically important occupations contained in the Critical "
    "Skills Occupations List a relevant degree qualification or higher is required. Where the "
    "applicant has received their qualification within the 12 month period prior to the date of "
    "application, the minimum annual remuneration will be €36,848.</p>"
    "<p>All occupations with a minimum annual remuneration of over €68,911, other than those on "
    "the Ineligible List of Occupations.</p>"
)


def test_the_permit_page_gives_three_salary_thresholds() -> None:
    thresholds = {r.record_id: r for r in parse_permit_page(PERMIT_PAGE)}

    assert {k: v.anzsco_code for k, v in thresholds.items()} == {
        "critical-skills-csol": "€40,904",
        "critical-skills-graduate": "€36,848",
        "critical-skills-any-occupation": "€68,911",
    }
    assert all(r.industry.startswith("Salary threshold") for r in thresholds.values())


def test_a_page_without_the_thresholds_is_refused_not_read_as_empty() -> None:
    with pytest.raises(AppError):
        parse_permit_page("<p>Page not found</p>")
