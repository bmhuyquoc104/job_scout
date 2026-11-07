"""drop redundant category indexes

Revision ID: a3f1c9d2e7b4
Revises: 5bd815ca442f
Create Date: 2026-11-06 00:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a3f1c9d2e7b4"
down_revision: str | Sequence[str] | None = "5bd815ca442f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # The (category_id, seek_job_id) unique constraints already index category_id.
    op.drop_index("ix_job_category_id_idx", table_name="job")
    op.drop_index("ix_job_draft_category_id_idx", table_name="job_draft")


def downgrade() -> None:
    op.create_index("ix_job_draft_category_id_idx", "job_draft", ["category_id"], unique=False)
    op.create_index("ix_job_category_id_idx", "job", ["category_id"], unique=False)
