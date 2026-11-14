"""Which of a country's priority roles a job title falls under.

A job title ("Senior Software Engineer") rarely equals an official role name ("Software Engineer"),
so roles are matched on their distinctive words: seniority and very common words are ignored.
"""

import re

from job_scout.green_list.models import GreenListRole

MAX_PER_COUNTRY = 8
# Words too common to show that two titles are the same job.
_GENERIC = {
    "senior", "junior", "lead", "principal", "staff", "head", "chief", "associate", "assistant",
    "intern", "graduate", "trainee", "and", "of", "the", "for", "in", "nec", "ii", "iii", "sr",
    "jr", "engineer", "manager", "specialist", "analyst", "officer", "technician", "consultant",
    "worker", "professional", "m", "w", "d", "f",
}  # fmt: skip


def distinctive_words(text: str) -> set[str]:
    words = {
        w[:-1] if len(w) > 3 and w.endswith("s") else w
        for w in re.findall(r"[a-z0-9]+", text.lower())
    }
    return (words - _GENERIC) or words


def matching_roles(title: str, roles: list[GreenListRole]) -> list[GreenListRole]:
    """Roles sharing at least half their distinctive words with the title, best first.

    Salary-threshold roles (Germany) are rules for every job, so they always match.
    """
    wanted = distinctive_words(title)
    scored: list[tuple[float, GreenListRole]] = []
    for role in roles:
        if role.industry.startswith("Salary threshold"):
            scored.append((2.0, role))
            continue
        own = distinctive_words(role.title)
        score = len(own & wanted) / len(own) if own else 0
        if score >= 0.5:
            scored.append((score, role))
    scored.sort(key=lambda pair: (-pair[0], pair[1].title))
    return [role for _, role in scored[:MAX_PER_COUNTRY]]
