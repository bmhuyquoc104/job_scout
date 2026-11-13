from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from job_scout.jobs.sources import JOB_SOURCES
from job_scout.models import Base


class JobDraft(Base):
    __tablename__ = "job_draft"
    __table_args__ = (
        CheckConstraint(
            f"source IN ({', '.join(repr(source) for source in JOB_SOURCES)})", name="valid_source"
        ),
        UniqueConstraint("category_id", "source", "external_id"),
        CheckConstraint(
            "status IN ('pending', 'eligible', 'ineligible', 'failed')",
            name="valid_status",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=text("uuidv7()")
    )
    category_id: Mapped[UUID] = mapped_column(ForeignKey("category.id"), nullable=False)
    source: Mapped[str] = mapped_column(
        String(24), nullable=False, default="seek", server_default="seek"
    )
    external_id: Mapped[str] = mapped_column(String(300), nullable=False)
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    enriched_data: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    immigration_result: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="pending")
    error_code: Mapped[str | None] = mapped_column(String(64))
    error_message: Mapped[str | None] = mapped_column(Text)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
