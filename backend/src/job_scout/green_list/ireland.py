"""Ireland's Critical Skills Occupations List and permit salary thresholds, from the DETE site.

The list is a Word file: a table of SOC-3 / employment category / SOC-4 / employments, with the
first two columns merged down across a group's rows and one employment per line in the last cell.
Each employment is a role (its SOC-4 code in the `anzsco_code` column). The salary rules come from
the permit page and are stored as roles too, like Germany's, so the monthly sync records changes.
"""

import io
import re
import zipfile
from xml.etree import ElementTree

from job_scout.core.errors import AppError, ErrorCode
from job_scout.green_list.parsing import RoleRecord, html_to_text
from job_scout.scraper import chrome_http

LIST_URL = "https://enterprise.gov.ie/en/publications/publication-files/critical-skills-occupations-list.docx"
PERMIT_URL = (
    "https://enterprise.gov.ie/en/what-we-do/workplace-and-skills/employment-permits/"
    "permit-types/critical-skills-employment-permit/"
)
LIST_NAME = "Critical Skills Occupations List"
MAX_TITLE = 300  # the role title column's width; a few employments are whole sentences
MIN_ROLES = 80  # the list has about 200 employments; far fewer means the file changed shape
_NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
_W = "{" + _NS["w"] + "}"
_SOC4 = re.compile(r"\d{4}")


def _lines(cell: ElementTree.Element) -> list[str]:
    paragraphs = ("".join(t.text or "" for t in p.iter(_W + "t")) for p in cell.iter(_W + "p"))
    return [" ".join(text.split()) for text in paragraphs if text.strip()]


def _is_continuation(cell: ElementTree.Element) -> bool:
    merge = cell.find("w:tcPr/w:vMerge", _NS)
    return merge is not None and merge.get(_W + "val") != "restart"


def parse_csol_docx(content: bytes) -> list[RoleRecord]:
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            document = ElementTree.fromstring(archive.read("word/document.xml"))
    except (zipfile.BadZipFile, KeyError, ElementTree.ParseError) as exc:
        raise AppError(ErrorCode.SCRAPE_SOURCE_ERROR, "Unreadable Critical Skills list") from exc
    category = ""
    roles: dict[str, RoleRecord] = {}
    for row in document.iterfind(".//w:tbl/w:tr", _NS):
        cells = row.findall("w:tc", _NS)
        if len(cells) != 4:
            continue
        if not _is_continuation(cells[1]):
            category = " ".join(_lines(cells[1]))
        soc4 = " ".join(_lines(cells[2]))
        if not _SOC4.fullmatch(soc4):
            continue  # the header row
        for title in _lines(cells[3]):
            if title.endswith(":"):
                continue  # a heading for the lines below it
            record_id = f"{soc4}-{re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')}"[:32]
            roles[record_id] = RoleRecord(
                record_id=record_id,
                title=title if len(title) <= MAX_TITLE else title[: MAX_TITLE - 1] + "…",
                anzsco_code=soc4,
                industry=category,
                tier=None,
                pathway="Critical Skills Employment Permit",
                requirements="A relevant degree, and the minimum annual salary (see thresholds)",
                engineering_degrees="",
                note="",
                raw={"employment": title, "soc_4": soc4, "category": category},
                lists=(LIST_NAME,),
            )
    if not roles:
        raise AppError(
            ErrorCode.SCRAPE_SOURCE_ERROR, "No occupations table in the Critical Skills list"
        )
    return list(roles.values())


_AMOUNT = r"€\s?(\d{1,3}(?:,\d{3})*)"
_CSOL_SALARY = re.compile(
    r"minimum annual remuneration of " + _AMOUNT + r" for a restricted number of strategically "
    r"important occupations"
)
_GRADUATE_SALARY = re.compile(
    r"within the 12 month period[^.]{0,120}?minimum annual remuneration will be " + _AMOUNT
)
_ANY_SALARY = re.compile(r"All occupations with a minimum annual remuneration of over " + _AMOUNT)


def _threshold(slug: str, title: str, amount: str, pathway: str) -> RoleRecord:
    return RoleRecord(
        record_id=slug,
        title=title,
        anzsco_code=f"€{amount}",
        industry="Salary threshold",
        tier=None,
        pathway=pathway,
        requirements="Minimum annual remuneration; a 2-year job offer",
        engineering_degrees="",
        note="",
        raw={"threshold": amount},
        lists=("Critical Skills Employment Permit",),
    )


def parse_permit_page(page: str) -> list[RoleRecord]:
    text = " ".join(html_to_text(page).split())
    csol, graduate, anyone = (p.search(text) for p in (_CSOL_SALARY, _GRADUATE_SALARY, _ANY_SALARY))
    if csol is None or graduate is None or anyone is None:
        raise AppError(ErrorCode.SCRAPE_SOURCE_ERROR, "No Critical Skills salary thresholds found")
    return [
        _threshold(
            "critical-skills-csol",
            "Critical Skills Employment Permit: roles on the Critical Skills Occupations List",
            csol.group(1),
            "A relevant degree or higher is required",
        ),
        _threshold(
            "critical-skills-graduate",
            "Critical Skills Employment Permit: qualified in the last 12 months",
            graduate.group(1),
            "For a qualification gained within 12 months of applying",
        ),
        _threshold(
            "critical-skills-any-occupation",
            "Critical Skills Employment Permit: any eligible occupation",
            anyone.group(1),
            "Any occupation not on the Ineligible List; experience can replace a degree",
        ),
    ]


async def fetch_occupations() -> list[RoleRecord]:
    """The list's employments and the salary thresholds. Raises rather than return a partial
    list, because a partial list would make the sync look like roles had been removed."""
    async with chrome_http.client() as http:
        listing = await chrome_http.request(http, "GET", LIST_URL)
        permit = await chrome_http.request(http, "GET", PERMIT_URL)
    roles = parse_csol_docx(listing.content)
    if len(roles) < MIN_ROLES:
        raise AppError(ErrorCode.SCRAPE_SOURCE_ERROR, f"Only {len(roles)} occupations in the list")
    return [*parse_permit_page(permit.text), *roles]
