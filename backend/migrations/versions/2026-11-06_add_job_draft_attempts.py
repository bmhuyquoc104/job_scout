"""add job_draft attempts

Revision ID: c7e2b94a1d36
Revises: a3f1c9d2e7b4
Create Date: 2026-11-06 01:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c7e2b94a1d36"
down_revision: str | Sequence[str] | None = "a3f1c9d2e7b4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "job_draft",
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("job_draft", "attempts")
