"""Turn a typed question into a plan (what to look up, with which filters) using keywords only.

shortcut: fixed word lists and regexes, so unusual phrasings fall through to a plain title
search; swap `understand` for an embedding-based matcher if that proves too rigid.
"""

import re
from dataclasses import dataclass, field
from difflib import get_close_matches
from typing import Any, Literal

from job_scout.core.countries import COUNTRIES

Intent = Literal["help", "compare", "visa", "trend", "regions", "immigration", "search"]

SENIORITY = {
    "senior": "senior",
    "sr": "senior",
    "junior": "junior",
    "jr": "junior",
    "graduate": "graduate",
    "intern": "graduate",
    "internship": "graduate",
    "lead": "lead",
    "principal": "lead",
    "mid": "mid",
}
VISA_WORDS = {"visa", "visas", "sponsor", "sponsors", "sponsored", "sponsoring", "sponsorship"}
ARRANGEMENTS = {"remote": "Remote", "hybrid": "Hybrid", "onsite": "On-site"}
WORK_TYPES = {
    "fulltime": "Full time",
    "parttime": "Part time",
    "contract": "Contract/Temp",
    "contractor": "Contract/Temp",
    "temp": "Contract/Temp",
}
# Words that carry no part of a job title.
STOPWORDS = set(
    """
    a an the in on at for of to with and or me my i we you it is are was be any there have
    has do does can what which where who how many much most top best all some about show
    find list give get tell jobs job roles role positions position openings vacancies work
    working hiring country countries compare across per by each trend trends growing growth
    grow new offer offers offering this last week month year days day over above below under
    least minimum min salary pay paying than more less from located location locations
    region regions city cities number count total currently open available hi hello hey
    thanks thank please want looking need would like anywhere are s only just also same
    those these instead but ones one them that then ask asking asked listing
    ago not now today well so yeah yep ok okay sure choose pick decide between versus vs
    """.split()
)
# Interjections ("hmm", "ohh", "uhh", "errr", "ahh", "wow"), in any stretched spelling.
INTERJECTION = re.compile(
    r"\b(?:h+m+|h+u+h+|u+h+m*|u+m+|o+h+|a+h+|e+h+|e+r+m*|a+r+g+h+|u+g+h+|w+o+w+|oops|whoa|yay)\b"
)
REWRITES = {
    r"on[- ]site": "onsite",
    r"full[- ]time": "fulltime",
    r"part[- ]time": "parttime",
    r"work from home": "remote",
    r"mid[- ]level": "mid",
    r"\bit (?=jobs?\b|roles?\b|positions?\b|vacanc)": "software ",  # "IT jobs"
    r"\b(for|in) it\b": r"\1 software",  # "it" is a stopword; IT roles are software roles
    # Synonyms, rewritten to the word the rules know. "priority occupation list" is a phrase.
    r"(?<!priority )\boccupations?\b(?! list)|\b(professions?|vocations?|careers?)\b": "job",
    r"\b(wages?|earnings?|remuneration|compensation)\b": "salary",
    r"\b(relocat\w+|emigrat\w+|expat\w*|settle|settling)\b": "immigrate",
}
# Only phrases that cannot be a job title ("data migration", "green energy", "critical care").
IMMIGRATION = re.compile(
    r"\b(immigrat\w*|emigrat\w*|migrate to|migrating to|green list|blue card|critical skills?"
    r"|priority (?:occupation|list)s?|work permits?|residen(?:ce|cy)|permanent resident"
    r"|eligib\w*|routes?|paths?|pathways?|(?:move|moving|relocate) to|easier|easiest|harder|hardest"
    r"|(?:get|apply for) (?:a |an )?(?:work )?visa"
    r"|visa (?:routes?|options?|requirements?|process))\b"
)
# Words that carry no part of the role in an immigration question.
IMMIGRATION_WORDS = set(
    """immigrate immigrating immigration emigrate migrate migrating route routes pathway pathways
    green blue card critical skill skills priority occupation occupations permit permits eligible
    eligibility residence residency permanent resident move moving relocate easiest easy easier
    path paths possible get apply options option requirements requirement process as harder hardest
    between versus vs""".split()
)
JOB_WORD = re.compile(r"\b(jobs?|roles?|positions?|openings?|vacancies)\b")
# "those jobs", "show them": points at an earlier message, which is not remembered.
REFERENCE = re.compile(r"\b(those|them|these|the same|previous|above|earlier|that one)\b")
# A message that builds on the one before: points back, or starts like "how about ...".
FOLLOW_UP = re.compile(
    REFERENCE.pattern + r"|^\s*(?:and|also|what about|how about|only|just|same|but|instead)\b"
)
COUNTRY_SCOPE = re.compile(r"\bcountr(?:y|ies)\b")
TREND = re.compile(
    r"\b(trends?|grow\w*|shrink\w*|declin\w*|increas\w*|decreas\w*|hiring|new jobs)\b"
)
REGIONS = re.compile(r"\b(where|regions?|cit(?:y|ies)|locations?|located)\b")
GREETING = re.compile(
    r"\b(help|hello|hi|hey|thanks|thank you)\b|what can you|what do you do|how do you"
)
WINDOW = re.compile(r"\b(?:last\s+)?(\d+)\s*(day|week|month)s?\b")
SALARY = re.compile(r"(\d[\d,]*(?:\.\d+)?)(\s*k)?\b")
DAYS_PER = {"day": 1, "week": 7, "month": 30}
NAMED_WINDOWS = {
    "yesterday": 1,
    "this week": 7,
    "last week": 7,
    "this month": 30,
    "last month": 30,
    "this year": 365,
}


@dataclass
class Plan:
    intent: Intent
    country: str | None = None  # the first country named, as a code
    countries: list[str] = field(default_factory=list)  # every country named, in order
    across: bool = False  # asks about "which country", so the sidebar country must not apply
    title: str = ""
    days: int = 30
    days_given: bool = False  # the question named a window, so a follow-up may change it
    filters: dict[str, Any] = field(default_factory=dict)  # keyword args for JobQuery
    location: str = ""  # the place after "in", searched as a job location
    note: str = ""  # said before the answer, when context changed what was asked


def _days(text: str) -> tuple[int, str]:
    if match := WINDOW.search(text):
        days = min(int(match[1]) * DAYS_PER[match[2]], 365)
        return max(days, 1), text.replace(match[0], " ")
    for phrase, days in NAMED_WINDOWS.items():
        if phrase in text:
            return days, text.replace(phrase, " ")
    return 30, text


def _salary(text: str) -> tuple[int | None, str]:
    for match in SALARY.finditer(text):
        value = float(match[1].replace(",", "")) * (1000 if match[2] else 1)
        if value >= 1000:
            return int(value), text.replace(match[0], " ", 1)
    return None, text


# Short forms and nationalities people type instead of a country's name.
ALIASES = {
    "ire": "IE", "irl": "IE", "eire": "IE", "irish": "IE",
    "ger": "DE", "deu": "DE", "german": "DE",
    "nld": "NL", "holland": "NL", "dutch": "NL",
    "aus": "AU", "aussie": "AU", "australian": "AU",
    "canadian": "CA", "kiwi": "NZ",
}  # fmt: skip
# "can" is a verb, so it means Canada only when it sits between other countries ("can and ire").
CAN_BETWEEN = re.compile(r" (?:between|or|and|vs|versus) can | can (?:and|or|vs|versus) ")


def _countries(tokens: list[str]) -> tuple[list[str], set[str]]:
    """Every country named by name or code, in the order they appear; else one close spelling."""
    padded = f" {' '.join(tokens)} "
    found: dict[str, int] = {}
    used: set[str] = set()
    for code, country in COUNTRIES.items():
        aliases = [alias for alias, target in ALIASES.items() if target == code]
        for word in (country.name.lower(), code.lower(), *aliases):
            if (position := padded.find(f" {word} ")) >= 0:
                found[code] = min(position, found.get(code, position))
                used |= set(word.split())
    if found and "CA" in COUNTRIES and "CA" not in found and CAN_BETWEEN.search(padded):
        found["CA"] = padded.find(" can ")
        used.add("can")
    if found:
        return sorted(found, key=found.__getitem__), used
    single = {c.name.lower(): code for code, c in COUNTRIES.items() if " " not in c.name}
    for token in tokens:
        if len(token) >= 5 and token not in STOPWORDS:
            if close := get_close_matches(token, single, n=1, cutoff=0.8):
                return [single[close[0]]], {token}
    return [], set()


# Words the rules react to; a typed word close to one of these is corrected before reading.
KNOWN_WORDS = (
    set(SENIORITY)
    | VISA_WORDS
    | set(ARRANGEMENTS)
    | set(WORK_TYPES)
    | IMMIGRATION_WORDS
    | {w for c in COUNTRIES.values() for w in c.name.lower().split()}
    | set(
        """immigrate immigration migrate salary hiring growing growth declining decreasing
        increasing trend trends compare countries country located location regions cities
        available vacancies sponsorship graduate""".split()
    )
)


def _correct(text: str) -> str:
    """Fix typos by snapping a long unknown word to a close known one (see KNOWN_WORDS)."""

    def fix(match: re.Match[str]) -> str:
        word = match[0]
        if len(word) < 5 or word in KNOWN_WORDS or word in STOPWORDS:
            return word
        close = get_close_matches(word, KNOWN_WORDS, n=1, cutoff=0.8)
        # A typo changes at most a letter or two; "migration" is a word, not "immigration" misspelt.
        return close[0] if close and abs(len(close[0]) - len(word)) <= 1 else word

    return re.sub(r"[a-z]+", fix, text)


def understand(text: str) -> Plan:
    text = text.lower().replace("€", " ").replace("$", " ").replace("£", " ")
    for pattern, replacement in REWRITES.items():
        text = re.sub(pattern, replacement, text)
    text = _correct(INTERJECTION.sub(" ", text))
    days, rest = _days(text)
    days_given, text = rest != text, rest
    min_salary, text = _salary(text)
    tokens = [t.rstrip(".") for t in re.findall(r"[a-z0-9+#.]+", text)]
    countries, used = _countries(tokens)
    country = countries[0] if countries else None

    filters: dict[str, Any] = {}
    if seniority := [SENIORITY[t] for t in dict.fromkeys(tokens) if t in SENIORITY]:
        filters["seniority"] = list(dict.fromkeys(seniority))
    if VISA_WORDS & set(tokens):
        filters["visa"] = "offered"
    if min_salary:
        filters["min_salary"] = min_salary
    if arrangement := [ARRANGEMENTS[t] for t in tokens if t in ARRANGEMENTS]:
        filters["arrangement"] = arrangement
    if work_type := [WORK_TYPES[t] for t in tokens if t in WORK_TYPES]:
        filters["work_type"] = list(dict.fromkeys(work_type))

    immigration = bool(IMMIGRATION.search(text))
    if immigration:
        filters = {}  # "get a visa" is not the filter "jobs that offer sponsorship"
    known = set(SENIORITY) | VISA_WORDS | set(ARRANGEMENTS) | set(WORK_TYPES) | used | STOPWORDS
    if immigration:
        known |= IMMIGRATION_WORDS
    location = ""
    if "in" in tokens[:-1]:
        for word in tokens[tokens.index("in") + 1 :][:2]:
            if word in known or word.isdigit():
                break
            location = f"{location} {word}".strip()
    title = " ".join(
        t for t in tokens if t not in known and not t.isdigit() and t not in location.split()
    )

    intent: Intent = "search"
    if GREETING.search(text) and not title and not filters and not country:
        intent = "help"
    elif immigration:
        intent = "immigration"
    elif COUNTRY_SCOPE.search(text) or re.search(r"\bcompare\b", text):
        intent = "compare" if title or not VISA_WORDS & set(tokens) else "visa"
    elif len(countries) >= 2 and not (TREND.search(text) or REGIONS.search(text)):
        intent = "compare"  # two countries named: never a search of just the first
    elif TREND.search(text):
        intent = "trend"
    elif REGIONS.search(text):
        intent = "regions"
    elif days_given and not (title or filters or JOB_WORD.search(text)):
        intent = "trend"  # "how about last week": the same hiring question for another window
    elif not (title or filters or country or days_given or location):
        intent = "help"
    if intent == "trend" and days_given and days < 7:
        intent = "search"  # a trend needs a week of history; a day or two is "what was listed"
    return Plan(
        intent,
        country=country,
        countries=countries,
        across=bool(COUNTRY_SCOPE.search(text)),
        title=title,
        days=days,
        days_given=days_given,
        filters=filters,
        location=location,
    )
