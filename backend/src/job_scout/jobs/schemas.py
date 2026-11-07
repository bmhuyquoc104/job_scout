from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from job_scout.jobs.sources import JOB_SOURCES

JobStatusFilter = Literal["open", "closed", "all"]
JobSource = Literal[*JOB_SOURCES]
JobSort = Literal[
    "position",
    "company",
    "location",
    "arrangement",
    "work_type",
    "status",
    "salary",
    "listed",
    "source",
]


class JobQuery(BaseModel):
    """List parameters: paging, one sort column, and an AND of the per-column filters."""

    model_config = ConfigDict(extra="forbid")

    limit: int = Field(50, ge=1, le=100)
    offset: int = Field(0, ge=0)
    status: JobStatusFilter = "all"
    source: JobSource | None = None
    sort: JobSort = "listed"
    order: Literal["asc", "desc"] = "desc"
    # Case-insensitive "contains" search on each text column.
    position: str | None = Field(None, max_length=100)
    company: str | None = Field(None, max_length=100)
    location: str | None = Field(None, max_length=100)
    # A job matches if it has ANY of the selected values.
    arrangement: list[str] = Field(default_factory=list, max_length=10)
    work_type: list[str] = Field(default_factory=list, max_length=10)
    salary: Literal["any", "listed", "unlisted"] = "any"
    # Minimum estimated annual NZD: the top of the job's range must reach it.
    min_salary: int | None = Field(None, ge=0, le=10_000_000)
    # Inclusive listing dates (UTC).
    listed_from: date | None = None
    listed_to: date | None = None

    @field_validator(
        "position", "company", "location", "min_salary", "listed_from", "listed_to", mode="before"
    )
    @classmethod
    def blank_means_unset(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip() or None
        return value


class JobListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source: JobSource
    position: str
    company_name: str
    location: str
    work_arrangements: list[str]
    work_types: list[str]
    salary_label: str
    pay_period: str
    annual_salary_min: int | None
    annual_salary_max: int | None
    listed_at: datetime | None
    is_active: bool
    # When the listing was last seen closing; only set while the job is closed.
    closed_at: datetime | None = None


class PaginatedJobs(BaseModel):
    items: list[JobListItem]
    total: int
    limit: int
    offset: int
    category_name: str
    category_slug: str


class JobDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    category_id: UUID
    source: JobSource
    external_id: str
    company_name: str
    location: str
    work_arrangements: list[str]
    work_types: list[str]
    salary_label: str
    pay_period: str
    position: str
    job_description: str
    url: str
    nzbn: str
    trading_name: str
    annual_salary_min: int | None
    annual_salary_max: int | None
    listed_at: datetime | None
    is_active: bool
    closed_at: datetime | None = None


class JobFacets(BaseModel):
    """The values that exist in the data, to fill the multi-select filters."""

    arrangements: list[str]
    work_types: list[str]


class TrendPoint(BaseModel):
    date: date
    total_open: int
    new: int
    closed: int
    by_seniority: dict[str, int]


class TrendSeries(BaseModel):
    """Daily history rebuilt from job events (days in Pacific/Auckland time)."""

    points: list[TrendPoint]
    seniority_levels: list[str]
    # First day any event exists; the history cannot go back further than this.
    history_starts: date | None


class LocationCount(BaseModel):
    region: str
    count: int


class SourceOption(BaseModel):
    source: JobSource
    label: str


class SourceCount(BaseModel):
    source: JobSource
    count: int


class SourceBreakdown(BaseModel):
    """Open jobs per source, biggest first."""

    sources: list[SourceCount]
    total_open: int


class LocationBreakdown(BaseModel):
    """Open jobs per region, biggest first."""

    regions: list[LocationCount]
    total_open: int
