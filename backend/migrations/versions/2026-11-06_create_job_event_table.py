"""create job_event table

Revision ID: d4a8e1b7f205
Revises: c7e2b94a1d36
Create Date: 2026-11-06 02:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "d4a8e1b7f205"
down_revision: str | Sequence[str] | None = "c7e2b94a1d36"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "job_event",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), server_default=sa.text("uuidv7()"), nullable=False
        ),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("category_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(length=16), nullable=False),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.CheckConstraint(
            "event_type IN ('new', 'updated', 'closed', 'reopened')",
            name=op.f("job_event_valid_event_type_check"),
        ),
        sa.ForeignKeyConstraint(
            ["category_id"], ["category.id"], name=op.f("job_event_category_id_fkey")
        ),
        sa.ForeignKeyConstraint(
            ["job_id"], ["job.id"], name=op.f("job_event_job_id_fkey"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("job_event_pkey")),
    )
    op.create_index(
        "ix_job_event_category_id_occurred_at_idx",
        "job_event",
        ["category_id", "occurred_at"],
        unique=False,
    )
    op.create_index(
        "ix_job_event_job_id_occurred_at_idx", "job_event", ["job_id", "occurred_at"], unique=False
    )
    # Jobs that already exist get a "new" event so their history starts somewhere.
    op.execute(
        """
        INSERT INTO job_event (job_id, category_id, event_type, occurred_at)
        SELECT id, category_id, 'new', first_seen_at FROM job
        """
    )


def downgrade() -> None:
    op.drop_index("ix_job_event_job_id_occurred_at_idx", table_name="job_event")
    op.drop_index("ix_job_event_category_id_occurred_at_idx", table_name="job_event")
    op.drop_table("job_event")
