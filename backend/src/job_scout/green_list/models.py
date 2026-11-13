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
from sqlalchemy.orm import Mapped, mapped_column

from job_scout.models import Base


class GreenListRole(Base):
    """One priority occupation for a country (NZ: Green List; AU: skilled occupation lists)."""

    __tablename__ = "green_list_role"
    __table_args__ = (UniqueConstraint("country", "record_id"),)

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=text("uuidv7()")
    )
    country: Mapped[str] = mapped_column(
        String(2), nullable=False, default="NZ", server_default="NZ"
    )
    record_id: Mapped[str] = mapped_column(String(32), nullable=False)  # the source's own id
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    anzsco_code: Mapped[str] = mapped_column(String(16), nullable=False)
    industry: Mapped[str] = mapped_column(String(120), nullable=False)
    # NZ: 1 = straight to residence, 2 = work to residence. None for countries without tiers.
    tier: Mapped[int | None] = mapped_column(Integer)
    # Australia: the official lists the role is on, e.g. ["CSOL", "MLTSSL"].
    lists: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, default=list, server_default="[]"
    )
    pathway: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    requirements: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    engineering_degrees: Mapped[str] = mapped_column(
        Text, nullable=False, default="", server_default=""
    )
    note: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    raw: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)  # the full record, for audit
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )  # false once the role has dropped off the list
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class GreenListEventType(StrEnum):
    NEW = "new"
    TIER_CHANGED = "tier_changed"
    REMOVED = "removed"
    RESTORED = "restored"


class GreenListEvent(Base):
    """Append-only history of the list: what changed between monthly syncs."""

    __tablename__ = "green_list_event"
    __table_args__ = (
        CheckConstraint(
            "event_type IN ('new', 'tier_changed', 'removed', 'restored')", name="valid_event_type"
        ),
        Index("ix_green_list_event_occurred_at_idx", "occurred_at"),
        Index("ix_green_list_event_role_id_occurred_at_idx", "role_id", "occurred_at"),
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=text("uuidv7()")
    )
    role_id: Mapped[UUID] = mapped_column(
        ForeignKey("green_list_role.id", ondelete="CASCADE"), nullable=False
    )
    event_type: Mapped[str] = mapped_column(String(16), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    # For "tier_changed": {"from_tier": 1, "to_tier": 2}.
    details: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
