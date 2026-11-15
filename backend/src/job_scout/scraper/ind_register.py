"""The IND's public register of recognised sponsors (employers who may hire highly skilled
migrants), read from its "Work" page: one table of about 13,000 organisations and KvK numbers,
updated monthly. A job from an organisation on it is noted as such; nothing is filtered by it.

shortcut: names are matched whole, after dropping case, punctuation and legal forms (B.V., N.V.),
so a brand that differs from the registered name ("ING" for "ING Bank N.V.") is not recognised.
Upgrade to the KvK number if ads ever carry it.
"""

import html
import re

from job_scout.core.errors import AppError, ErrorCode
from job_scout.scraper import chrome_http

URL = "https://ind.nl/en/public-register-recognised-sponsors/public-register-work"
MIN_NAMES = 1000  # the register lists about 13,000; far fewer means the page changed shape
NOTE = (
    "The employer is an IND-recognised sponsor: it can hire highly skilled migrants from "
    "outside the EU."
)
_ROW = re.compile(r'<th scope="row">(.*?)</th>\s*<td>\s*\d+\s*</td>', re.S)
_LEGAL_FORM = {"bv", "nv", "vof", "cv", "holding", "ltd", "limited", "gmbh", "inc", "llc"}


def normalize_company(name: str) -> str:
    text = html.unescape(name).casefold()
    words = re.sub(
        r"[^a-z0-9 ]", "", re.sub(r"[.\-/&]", lambda m: "" if m.group() == "." else " ", text)
    ).split()
    return "".join(word for word in words if word not in _LEGAL_FORM)


def parse_register(page: str) -> set[str]:
    names = {normalize_company(re.sub(r"<[^>]+>", "", row)) for row in _ROW.findall(page)}
    names.discard("")
    if not names:
        raise AppError(ErrorCode.SCRAPE_SOURCE_ERROR, "No organisations on the IND register page")
    return names


def is_recognised_sponsor(company: str, names: set[str]) -> bool:
    key = normalize_company(company)
    return bool(key) and key in names


async def fetch_register() -> set[str]:
    async with chrome_http.client() as http:
        response = await chrome_http.request(http, "GET", URL)
    names = parse_register(response.text)
    if len(names) < MIN_NAMES:
        raise AppError(ErrorCode.SCRAPE_SOURCE_ERROR, f"Only {len(names)} sponsors on the page")
    return names
