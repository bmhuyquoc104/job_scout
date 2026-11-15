"""allow the iamexpat job source

Revision ID: f4c8e2a6b013
Revises: e1b7d3f5a902
Create Date: 2026-11-15 21:05:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f4c8e2a6b013"
down_revision: str | Sequence[str] | None = "e1b7d3f5a902"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

OLD = "source IN ('seek', 'employmenthero', 'indeed', 'glassdoor', 'jobbank', 'arbeitnow')"
NEW = (
    "source IN ('seek', 'employmenthero', 'indeed', 'glassdoor', 'jobbank', 'arbeitnow', "
    "'iamexpat')"
)


def _swap(condition: str) -> None:
    for table in ("job", "job_draft"):
        op.drop_constraint(f"{table}_valid_source_check", table, type_="check")
        op.create_check_constraint(f"{table}_valid_source_check", table, condition)


def upgrade() -> None:
    _swap(NEW)


def downgrade() -> None:
    # Rows from the new source cannot exist under the narrower check.
    op.execute("DELETE FROM job WHERE source = 'iamexpat'")
    op.execute("DELETE FROM job_draft WHERE source = 'iamexpat'")
    _swap(OLD)
