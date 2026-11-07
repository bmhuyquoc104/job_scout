"""create green list tables

Revision ID: b3e7c51d9a04
Revises: a8d41f6e92c7
Create Date: 2026-11-06 06:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "b3e7c51d9a04"
down_revision: str | Sequence[str] | None = "a8d41f6e92c7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    now = sa.text("now()")
    op.create_table(
        "green_list_role",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), server_default=sa.text("uuidv7()"), nullable=False
        ),
        sa.Column("record_id", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("anzsco_code", sa.String(length=16), nullable=False),
        sa.Column("industry", sa.String(length=120), nullable=False),
        sa.Column("tier", sa.Integer(), nullable=False),
        sa.Column("pathway", sa.Text(), server_default="", nullable=False),
        sa.Column("requirements", sa.Text(), server_default="", nullable=False),
        sa.Column("engineering_degrees", sa.Text(), server_default="", nullable=False),
        sa.Column("note", sa.Text(), server_default="", nullable=False),
        sa.Column("raw", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("green_list_role_pkey")),
        sa.UniqueConstraint("record_id", name=op.f("green_list_role_record_id_key")),
    )
    op.create_table(
        "green_list_event",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), server_default=sa.text("uuidv7()"), nullable=False
        ),
        sa.Column("role_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(length=16), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.CheckConstraint(
            "event_type IN ('new', 'tier_changed', 'removed', 'restored')",
            name=op.f("green_list_event_valid_event_type_check"),
        ),
        sa.ForeignKeyConstraint(
            ["role_id"],
            ["green_list_role.id"],
            name=op.f("green_list_event_role_id_fkey"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("green_list_event_pkey")),
    )
    op.create_index("ix_green_list_event_occurred_at_idx", "green_list_event", ["occurred_at"])
    op.create_index(
        "ix_green_list_event_role_id_occurred_at_idx",
        "green_list_event",
        ["role_id", "occurred_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_green_list_event_role_id_occurred_at_idx", table_name="green_list_event")
    op.drop_index("ix_green_list_event_occurred_at_idx", table_name="green_list_event")
    op.drop_table("green_list_event")
    op.drop_table("green_list_role")
