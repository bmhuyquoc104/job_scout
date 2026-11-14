"""Experience and visa-sponsorship signals used to adjust a job's skill score.

shortcut: regex rules on English ads; the CV's years are the largest "N years" it states, so a
line like "10 years in business" would inflate it. Upgrade if ads in other languages (e.g.
German) need the same signals.
"""

import re

from job_scout.matching.skills import find_skills

UNDER_PENALTY = 0.8  # per missing year of experience
UNDER_FLOOR = 0.3
OVER_PENALTY = 0.88  # per year the CV exceeds what the job asks
OVER_FLOOR = 0.4
SPONSOR_BONUS = 15
# A title word implies at least these years, whatever the ad body says ("architect, 3 years").
TITLE_YEARS = (
    (8, re.compile(r"\b(lead|principal|staff|head of|director|architect|manager)\b")),
    (5, re.compile(r"\b(senior|sr\.?)\b")),
    (0, re.compile(r"\b(junior|jr\.?|graduate|grad|intern|internship|entry[- ]level|trainee)\b")),
)
_YEARS = r"(\d{1,2})\s*\+?(?:\s*(?:-|to)\s*\d{1,2})?\s*\+?\s*(?:years?|yrs?)"
_CV_YEARS = re.compile(_YEARS)
# "5+ years of experience" and "experience: minimum 3 years"
_REQUIRED = re.compile(_YEARS + r"[^.\n]{0,40}experience|experience[^.\n]{0,25}?" + _YEARS)
_SPONSOR = re.compile(
    r"visa sponsor|sponsorship|sponsor(?:s|ed|ing)? (?:a |your |the )?(?:work )?visa"
    r"|work visa support|relocation (?:support|assistance|package)|aewv|accredited employer"
    r"|blue card|skilled worker visa|subclass 482|subclass 186"
)
_NO_SPONSOR = re.compile(
    r"(?:no|not|without|unable to|cannot|can't|won't|do not|does not) (?:\w+ ){0,3}sponsor"
    r"|sponsorship (?:is )?not (?:available|offered|provided)"
)


def cv_years(text: str) -> int | None:
    """Years of experience a CV states (its largest "N years"); None when it states none."""
    return max((int(n) for n in _CV_YEARS.findall(text.lower())), default=None)


_FRESHER = re.compile(
    r"\bfreshers?\b|entry[- ]level|no (?:prior |previous )?experience (?:is )?(?:needed|required)"
)


def required_years(position: str, description: str) -> int | None:
    """Years an ad asks for: the larger of its stated years (lower end of "3-5") and the title's."""
    text = description.lower()
    found = [int(n) for pair in _REQUIRED.findall(text) for n in pair if n]
    title = position.lower()
    implied = next((years for years, pattern in TITLE_YEARS if pattern.search(title)), None)
    if found or implied:
        return min(max([*found, implied or 0]), 30)  # largest ask when an ad names several
    return 0 if implied == 0 or _FRESHER.search(text) else None


def experience_factor(required: int | None, have: int | None) -> float:
    """1.0 when unknown or equal; steeply lower when short of the ask, mildly when over it."""
    if required is None or have is None:
        return 1.0
    gap = required - have
    if gap > 0:
        return max(UNDER_FLOOR, UNDER_PENALTY**gap)
    return max(OVER_FLOOR, OVER_PENALTY**-gap)


def offers_sponsorship(text: str) -> bool:
    text = text.lower()
    return bool(_SPONSOR.search(text)) and not _NO_SPONSOR.search(text)


def analyze_job(position: str, description: str) -> dict[str, object]:
    """Everything matching reads from an ad's text, so it is scanned once and stored on the job."""
    text = f"{position} {description}"
    return {
        "skills": sorted(find_skills(text)),
        "required_years": required_years(position, description),
        "visa_sponsor": offers_sponsorship(text),
    }
