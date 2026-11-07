"""add job seniority

Revision ID: f2b6d8a43c91
Revises: e9c3a7d15b82
Create Date: 2026-11-06 04:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from job_scout.scraper.normalization import classify_seniority

# revision identifiers, used by Alembic.
revision: str = "f2b6d8a43c91"
down_revision: str | Sequence[str] | None = "e9c3a7d15b82"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "job",
        sa.Column("seniority", sa.String(length=16), server_default="unspecified", nullable=False),
    )
    # Fill the new column for jobs that already exist; new ones are filled when promoted.
    bind = op.get_bind()
    for job_id, title in bind.execute(sa.text("SELECT id, position FROM job")).all():
        level = classify_seniority(title)
        if level != "unspecified":
            bind.execute(
                sa.text("UPDATE job SET seniority = :level WHERE id = :id"),
                {"level": level, "id": job_id},
            )


def downgrade() -> None:
    op.drop_column("job", "seniority")
