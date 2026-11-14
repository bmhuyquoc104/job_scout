"""add job visa_sponsor

Revision ID: a7d2f4c91b36
Revises: f2d6a83b19c7
Create Date: 2026-11-15 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from job_scout.matching.fit import offers_sponsorship

# revision identifiers, used by Alembic.
revision: str = "a7d2f4c91b36"
down_revision: str | Sequence[str] | None = "f2d6a83b19c7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "job",
        sa.Column("visa_sponsor", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    # Fill the new column for jobs that already exist; new ones are filled when promoted.
    bind = op.get_bind()
    flagged = [
        job_id
        for job_id, position, description in bind.execute(
            sa.text("SELECT id, position, job_description FROM job")
        ).all()
        if offers_sponsorship(f"{position} {description}")
    ]
    if flagged:
        bind.execute(
            sa.text("UPDATE job SET visa_sponsor = true WHERE id = ANY(:ids)"), {"ids": flagged}
        )


def downgrade() -> None:
    op.drop_column("job", "visa_sponsor")
