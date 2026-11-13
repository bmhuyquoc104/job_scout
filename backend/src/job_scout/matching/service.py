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

from job_scout.core.errors import AppError, ErrorCode
from job_scout.jobs.models import Job
from job_scout.matching.schemas import JobMatch
from job_scout.matching.skills import SKILL_KEYS, find_skills

MAX_CV_BYTES = 5 * 1024 * 1024
MAX_PAGES = 10
MAX_SUGGESTIONS = 6
SUGGEST_BELOW = 80  # jobs scoring under this get "add to your CV" suggestions


def read_cv_skills(content: bytes) -> list[str]:
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
    return sorted(skills)


def rank_jobs(cv_skills: set[str], jobs: Sequence[Any]) -> list[JobMatch]:
    """Score each job by how much of its skill list the CV covers.

    A job's skills are the IT skills named in its title and description. Coverage is the share
    of them the CV has, weighting rarer skills higher. It is then scaled by matched/(matched+1)
    so a job that names a single skill cannot score 100 on one lucky match. Jobs that name no
    known skill score 0.

    shortcut: whole-name skill matching from a hand-kept list (see skills.py), computed per
    request; upgrade to embeddings if the list cannot keep up with the jobs.
    """
    wanted = [find_skills(f"{job.position} {job.job_description}") for job in jobs]
    demand = Counter(skill for skills in wanted for skill in skills)
    weight = {skill: log((len(jobs) + 1) / (n + 1)) + 1 for skill, n in demand.items()}
    matches = []
    for job, skills in zip(jobs, wanted, strict=True):
        have = skills & cv_skills
        whole = sum(weight[skill] for skill in skills)
        covered = sum(weight[skill] for skill in have)
        score = round(100 * covered / whole * len(have) / (len(have) + 1)) if whole else 0
        missing = sorted(skills - cv_skills, key=lambda skill: (-demand[skill], skill))
        matches.append(
            JobMatch(
                id=job.id,
                position=job.position,
                company_name=job.company_name,
                location=job.location,
                salary_label=job.salary_label,
                score=score,
                missing_skills=missing[:MAX_SUGGESTIONS] if score < SUGGEST_BELOW else [],
            )
        )
    return sorted(matches, key=lambda match: -match.score)  # ties keep newest first


async def parse_cv(content: bytes) -> list[str]:
    return await asyncio.to_thread(read_cv_skills, content)  # PDF parsing is CPU-bound


async def match_jobs(session: AsyncSession, skills: list[str]) -> list[JobMatch]:
    cv = {skill.lower() for skill in skills} & SKILL_KEYS
    jobs = (
        await session.execute(
            select(
                Job.id,
                Job.position,
                Job.company_name,
                Job.location,
                Job.salary_label,
                Job.job_description,
            )
            .where(Job.is_active.is_(True))
            .order_by(Job.listed_at.desc().nulls_last())
        )
    ).all()
    return await asyncio.to_thread(rank_jobs, cv, jobs)
