import asyncio
from collections import Counter
from collections.abc import Sequence
from io import BytesIO
from math import log
from typing import Any

from pypdf import PdfReader
from pypdf.errors import PyPdfError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from job_scout.categories.models import Category
from job_scout.core.errors import AppError, ErrorCode
from job_scout.jobs.models import Job
from job_scout.matching.fit import (
    SPONSOR_BONUS,
    cv_years,
    experience_factor,
)
from job_scout.matching.schemas import CvSkills, JobMatch
from job_scout.matching.skills import SKILL_KEYS, find_skills

MAX_CV_BYTES = 5 * 1024 * 1024
MAX_PAGES = 10
MAX_SUGGESTIONS = 6
MAX_MATCHED = 8
SUGGEST_BELOW = 80  # jobs scoring under this get "add to your CV" suggestions


def read_cv(content: bytes) -> CvSkills:
    if len(content) > MAX_CV_BYTES or not content.startswith(b"%PDF-"):
        raise AppError(ErrorCode.INVALID_CV_FILE)
    try:
        reader = PdfReader(BytesIO(content))
        text = " ".join(page.extract_text() or "" for page in reader.pages[:MAX_PAGES])
    except (PyPdfError, ValueError, KeyError) as exc:  # corrupt or encrypted PDF
        raise AppError(ErrorCode.INVALID_CV_FILE, repr(exc)) from exc
    if not text.strip():
        raise AppError(ErrorCode.CV_UNREADABLE)
    if not (skills := find_skills(text)):
        raise AppError(ErrorCode.CV_NO_SKILLS)
    return CvSkills(skills=sorted(skills), years=cv_years(text))


def rank_jobs(
    cv_skills: set[str],
    jobs: Sequence[Any],
    years: int | None = None,
    limit: int | None = None,
    visa_only: bool = False,
) -> list[JobMatch]:
    """Score each job by how much of its skill list the CV covers.

    A job's skills are the IT skills named in its title and description, read once when the job
    was stored (`job.skills`). Coverage is the share of them the CV has, weighting rarer skills
    higher. It is then scaled by matched/(matched+1) so a job that names a single skill cannot
    score 100 on one lucky match. Jobs that name no known skill score 0.

    The score is then scaled down when the job's `required_years` exceed the CV's `years`
    (steeply) or fall below them (mildly), and raised when the ad offers visa sponsorship (only
    if the CV matches at least one skill, so sponsorship alone never ranks an unrelated job).

    `visa_only` and `limit` are applied after ranking; weights still use every job.

    shortcut: whole-name skill matching from a hand-kept list (see skills.py), computed per
    request; upgrade to embeddings if the list cannot keep up with the jobs.
    """
    wanted = [frozenset(job.skills) for job in jobs]
    demand = Counter(skill for skills in wanted for skill in skills)
    weight = {skill: log((len(jobs) + 1) / (n + 1)) + 1 for skill, n in demand.items()}
    scored = []
    for job, skills in zip(jobs, wanted, strict=True):
        have = skills & cv_skills
        whole = sum(weight[skill] for skill in skills)
        covered = sum(weight[skill] for skill in have)
        score = 100 * covered / whole * len(have) / (len(have) + 1) if whole else 0
        score *= experience_factor(job.required_years, years)
        score = round(min(100, score + SPONSOR_BONUS) if job.visa_sponsor and score else score)
        scored.append((score, job, skills))
    ranked = sorted(scored, key=lambda item: -item[0])  # ties keep newest first
    if visa_only:
        ranked = [item for item in ranked if item[1].visa_sponsor]
    matches = []
    for score, job, skills in ranked[:limit]:
        missing = sorted(skills - cv_skills, key=lambda skill: (-demand[skill], skill))
        matches.append(
            JobMatch(
                id=job.id,
                position=job.position,
                company_name=job.company_name,
                source=job.source,
                location=job.location,
                salary_label=job.salary_label,
                score=score,
                visa_sponsor=job.visa_sponsor,
                required_years=job.required_years,
                missing_skills=missing[:MAX_SUGGESTIONS] if score < SUGGEST_BELOW else [],
                matched_skills=sorted(skills & cv_skills)[:MAX_MATCHED],
            )
        )
    return matches


async def parse_cv(content: bytes) -> CvSkills:
    return await asyncio.to_thread(read_cv, content)  # PDF parsing is CPU-bound


async def match_jobs(
    session: AsyncSession,
    skills: list[str],
    country: str,
    years: int | None = None,
    limit: int | None = None,
    visa_only: bool = False,
) -> list[JobMatch]:
    cv = {skill.lower() for skill in skills} & SKILL_KEYS
    jobs = (
        await session.execute(
            select(
                Job.id,
                Job.position,
                Job.company_name,
                Job.source,
                Job.location,
                Job.salary_label,
                Job.skills,
                Job.required_years,
                Job.visa_sponsor,
            )
            .join(Category, Category.id == Job.category_id)
            .where(Job.is_active.is_(True), Category.country == country)
            .order_by(Job.listed_at.desc().nulls_last())
        )
    ).all()
    return await asyncio.to_thread(rank_jobs, cv, jobs, years, limit, visa_only)
