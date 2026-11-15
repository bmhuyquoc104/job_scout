"""recompute job visa_sponsor with the stricter visa-only rule

Revision ID: c9a3e5d7b182
Revises: b4e8d1a62c57
Create Date: 2026-11-15 18:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from job_scout.matching.fit import offers_sponsorship

# revision identifiers, used by Alembic.
revision: str = "c9a3e5d7b182"
down_revision: str | Sequence[str] | None = "b4e8d1a62c57"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Conference/event "sponsorship" no longer counts, so re-read every job's flag.
    bind = op.get_bind()
    flagged = [
        job_id
        for job_id, position, description in bind.execute(
            sa.text("SELECT id, position, job_description FROM job")
        ).all()
        if offers_sponsorship(f"{position} {description}")
    ]
    bind.execute(sa.text("UPDATE job SET visa_sponsor = (id = ANY(:ids))"), {"ids": flagged})


def downgrade() -> None:
    """Data-only change; the previous flags cannot be restored."""
