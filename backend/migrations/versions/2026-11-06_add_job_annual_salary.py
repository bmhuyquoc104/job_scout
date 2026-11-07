"""add job annual salary range

Revision ID: e9c3a7d15b82
Revises: d4a8e1b7f205
Create Date: 2026-11-06 03:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from job_scout.scraper.normalization import parse_salary

# revision identifiers, used by Alembic.
revision: str = "e9c3a7d15b82"
down_revision: str | Sequence[str] | None = "d4a8e1b7f205"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("job", sa.Column("annual_salary_min", sa.Integer(), nullable=True))
    op.add_column("job", sa.Column("annual_salary_max", sa.Integer(), nullable=True))
    # Fill the new columns for jobs that already exist; new ones are filled when promoted.
    bind = op.get_bind()
    for job_id, label in bind.execute(
        sa.text("SELECT id, salary_label FROM job WHERE salary_label <> ''")
    ).all():
        low, high = parse_salary(label)
        if low is not None or high is not None:
            bind.execute(
                sa.text(
                    "UPDATE job SET annual_salary_min = :low, "
                    "annual_salary_max = :high WHERE id = :id"
                ),
                {"low": low, "high": high, "id": job_id},
            )


def downgrade() -> None:
    op.drop_column("job", "annual_salary_max")
    op.drop_column("job", "annual_salary_min")
