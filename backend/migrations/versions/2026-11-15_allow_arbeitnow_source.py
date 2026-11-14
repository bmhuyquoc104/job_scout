"""allow the arbeitnow job source

Revision ID: f2d6a83b19c7
Revises: e5b9c28a61f4
Create Date: 2026-11-15 01:10:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f2d6a83b19c7"
down_revision: str | Sequence[str] | None = "e5b9c28a61f4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

OLD = "source IN ('seek', 'employmenthero', 'indeed', 'glassdoor', 'jobbank')"
NEW = "source IN ('seek', 'employmenthero', 'indeed', 'glassdoor', 'jobbank', 'arbeitnow')"


def _swap(condition: str) -> None:
    for table in ("job", "job_draft"):
        op.drop_constraint(f"{table}_valid_source_check", table, type_="check")
        op.create_check_constraint(f"{table}_valid_source_check", table, condition)


def upgrade() -> None:
    _swap(NEW)


def downgrade() -> None:
    # Rows from the new source cannot exist under the narrower check.
    op.execute("DELETE FROM job WHERE source = 'arbeitnow'")
    op.execute("DELETE FROM job_draft WHERE source = 'arbeitnow'")
    _swap(OLD)
