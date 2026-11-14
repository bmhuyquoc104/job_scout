"""allow the jobbank job source

Revision ID: d8a1e54c07b3
Revises: c3f7a19d52e8
Create Date: 2026-11-15 00:10:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d8a1e54c07b3"
down_revision: str | Sequence[str] | None = "c3f7a19d52e8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

OLD = "source IN ('seek', 'employmenthero', 'indeed', 'glassdoor')"
NEW = "source IN ('seek', 'employmenthero', 'indeed', 'glassdoor', 'jobbank')"


def _swap(condition: str) -> None:
    for table in ("job", "job_draft"):
        op.drop_constraint(f"{table}_valid_source_check", table, type_="check")
        op.create_check_constraint(f"{table}_valid_source_check", table, condition)


def upgrade() -> None:
    _swap(NEW)


def downgrade() -> None:
    # Rows from the new source cannot exist under the narrower check.
    op.execute("DELETE FROM job WHERE source = 'jobbank'")
    op.execute("DELETE FROM job_draft WHERE source = 'jobbank'")
    _swap(OLD)
