from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field, StringConstraints, field_validator

from job_scout.core.countries import COUNTRIES


class JobMatch(BaseModel):
    id: UUID
    position: str
    company_name: str
    source: str
    location: str
    salary_label: str
    # 0-100: how much of the job's skill list the CV covers (see rank_jobs).
    score: int
    # Skills this job asks for that the CV lacks, most in-demand first; only for weak matches.
    missing_skills: list[str]


class CvSkills(BaseModel):
    """The IT skills found in an uploaded CV; the page keeps them in the browser."""

    skills: list[str]


class MatchRequest(BaseModel):
    skills: list[Annotated[str, StringConstraints(min_length=1, max_length=30)]] = Field(
        min_length=1, max_length=5000
    )
    country: str = "NZ"  # only this country's open jobs are ranked

    @field_validator("country")
    @classmethod
    def _known_country(cls, value: str) -> str:
        if value not in COUNTRIES:
            raise ValueError("unknown country")
        return value
