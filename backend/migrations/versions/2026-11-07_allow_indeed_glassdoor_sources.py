"""allow the indeed and glassdoor job sources

Revision ID: a4c8e2f61b97
Revises: d6a1f3b8c452
Create Date: 2026-11-07 12:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a4c8e2f61b97"
down_revision: str | Sequence[str] | None = "d6a1f3b8c452"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

OLD = "source IN ('seek', 'employmenthero')"
NEW = "source IN ('seek', 'employmenthero', 'indeed', 'glassdoor')"


def _swap(condition: str) -> None:
    for table in ("job", "job_draft"):
        op.drop_constraint(f"{table}_valid_source_check", table, type_="check")
        op.create_check_constraint(f"{table}_valid_source_check", table, condition)


def upgrade() -> None:
    _swap(NEW)


def downgrade() -> None:
    # Rows from the new sources cannot exist under the narrower check.
    op.execute("DELETE FROM job WHERE source IN ('indeed', 'glassdoor')")
    op.execute("DELETE FROM job_draft WHERE source IN ('indeed', 'glassdoor')")
    _swap(OLD)
