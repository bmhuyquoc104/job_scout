from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from job_scout.categories.models import Category
from job_scout.jobs.sources import JOB_SOURCES
from job_scout.models import Base


class Job(Base):
    __tablename__ = "job"
    __table_args__ = (
        CheckConstraint(
            f"source IN ({', '.join(repr(source) for source in JOB_SOURCES)})", name="valid_source"
        ),
        UniqueConstraint("category_id", "source", "external_id"),
        Index("ix_job_is_active_idx", "is_active"),
        Index("ix_job_listed_at_idx", "listed_at"),
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=text("uuidv7()")
    )
    category_id: Mapped[UUID] = mapped_column(ForeignKey("category.id"), nullable=False)
    # Where the job came from; external_id and url are that source's own id and link.
    source: Mapped[str] = mapped_column(
        String(24), nullable=False, default="seek", server_default="seek"
    )
    external_id: Mapped[str] = mapped_column(String(300), nullable=False)
    company_name: Mapped[str] = mapped_column(String(300), nullable=False, default="")
    location: Mapped[str] = mapped_column(String(300), nullable=False, default="")
    work_arrangements: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, default=list, server_default="[]"
    )
    work_types: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, default=list, server_default="[]"
    )
    salary_label: Mapped[str] = mapped_column(Text, nullable=False, default="")
    pay_period: Mapped[str] = mapped_column(String(16), nullable=False, default="")
    # Estimated yearly NZD range parsed from salary_label; NULL when it has no figure.
    annual_salary_min: Mapped[int | None] = mapped_column(Integer)
    annual_salary_max: Mapped[int | None] = mapped_column(Integer)
    # Level read from the title (see classify_seniority); "unspecified" if it names none.
    seniority: Mapped[str] = mapped_column(
        String(16), nullable=False, default="unspecified", server_default="unspecified"
    )
    position: Mapped[str] = mapped_column(String(300), nullable=False, default="")
    # The ad offers visa sponsorship or similar (see offers_sponsorship), read from title and text.
    visa_sponsor: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    # Read from the title and description once, when promoted (see analyze_job), so ranking a CV
    # never scans ad text: IT skill keys, and the years of experience the ad asks for.
    skills: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, default=list, server_default="[]"
    )
    required_years: Mapped[int | None] = mapped_column(Integer)
    job_description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    url: Mapped[str] = mapped_column(Text, nullable=False)
    nzbn: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    trading_name: Mapped[str] = mapped_column(String(300), nullable=False, default="")
    listed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    category: Mapped[Category] = relationship(back_populates="jobs")


class JobEventType(StrEnum):
    NEW = "new"
    UPDATED = "updated"
    CLOSED = "closed"
    REOPENED = "reopened"


class JobEvent(Base):
    """Append-only history of a job: charts and audits are built from these rows."""

    __tablename__ = "job_event"
    __table_args__ = (
        CheckConstraint(
            "event_type IN ('new', 'updated', 'closed', 'reopened')",
            name="valid_event_type",
        ),
        Index("ix_job_event_category_id_occurred_at_idx", "category_id", "occurred_at"),
        Index("ix_job_event_job_id_occurred_at_idx", "job_id", "occurred_at"),
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=text("uuidv7()")
    )
    job_id: Mapped[UUID] = mapped_column(ForeignKey("job.id", ondelete="CASCADE"), nullable=False)
    category_id: Mapped[UUID] = mapped_column(ForeignKey("category.id"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(16), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    # For "updated" events: {field: {"old": ..., "new": ...}} for each changed field.
    details: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
