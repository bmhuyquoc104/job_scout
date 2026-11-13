from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Boolean, DateTime, Integer, String, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from job_scout.models import Base

if TYPE_CHECKING:
    from job_scout.jobs.models import Job


class Category(Base):
    __tablename__ = "category"
    __table_args__ = (
        UniqueConstraint("country", "seek_classification_id"),
        UniqueConstraint("country", "employmenthero_sector_id"),
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=text("uuidv7()")
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    seek_classification_id: Mapped[str] = mapped_column(String(20), nullable=False)
    # Two-letter code from core/countries.py; the same SEEK classification id repeats per country.
    country: Mapped[str] = mapped_column(
        String(2), nullable=False, default="NZ", server_default="NZ"
    )
    # Employment Hero's sector id for this category; None = not crawled there.
    employmenthero_sector_id: Mapped[int | None] = mapped_column(Integer)
    enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    jobs: Mapped[list["Job"]] = relationship(back_populates="category")  # noqa: UP037 (SQLAlchemy forward ref)
