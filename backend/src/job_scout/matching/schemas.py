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
    # The ad mentions visa sponsorship or similar; such jobs get a score bonus.
    visa_sponsor: bool
    # Years of experience the ad asks for (stated, or implied by "senior" etc.); None if unknown.
    required_years: int | None
    # Skills this job asks for that the CV lacks, most in-demand first; only for weak matches.
    missing_skills: list[str]
    # Skills this job asks for that the CV has, by name (at most MAX_MATCHED).
    matched_skills: list[str]


class CvSkills(BaseModel):
    """The IT skills found in an uploaded CV; the page keeps them in the browser."""

    skills: list[str]
    # Years of experience the CV states; None if it states none.
    years: int | None = None


class MatchRequest(BaseModel):
    years: int | None = Field(default=None, ge=0, le=60)
    limit: int | None = Field(default=None, ge=1, le=500)  # keep only the best N
    visa_only: bool = False  # keep only jobs that offer visa sponsorship
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
