"""rename job_draft status accredited/not_accredited to eligible/ineligible

Revision ID: a7e4c0b93d15
Revises: f1c9d3a58b72
Create Date: 2026-11-14 01:00:00.000000

The status says whether the employer passes the country's rule. Australia has no employer
check, so "accredited" was the wrong word for it.
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a7e4c0b93d15"
down_revision: str | Sequence[str] | None = "f1c9d3a58b72"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CONSTRAINT = op.f("job_draft_valid_status_check")  # op.f: the name is already final


def _swap(constraint: str, rename: dict[str, str]) -> None:
    op.drop_constraint(CONSTRAINT, "job_draft", type_="check")
    for old, new in rename.items():
        op.execute(f"UPDATE job_draft SET status = '{new}' WHERE status = '{old}'")
    op.create_check_constraint(CONSTRAINT, "job_draft", constraint)


def upgrade() -> None:
    _swap(
        "status IN ('pending', 'eligible', 'ineligible', 'failed')",
        {"accredited": "eligible", "not_accredited": "ineligible"},
    )


def downgrade() -> None:
    _swap(
        "status IN ('pending', 'accredited', 'not_accredited', 'failed')",
        {"eligible": "accredited", "ineligible": "not_accredited"},
    )
