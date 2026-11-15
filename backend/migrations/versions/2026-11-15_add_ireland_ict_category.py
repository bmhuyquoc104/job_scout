"""add an Irish ICT category

Revision ID: d8a4c6e2b917
Revises: c9a3e5d7b182
Create Date: 2026-11-15 20:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d8a4c6e2b917"
down_revision: str | Sequence[str] | None = "c9a3e5d7b182"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Off until someone turns it on, like the other countries. 6281 is only the id the job boards'
    # "IT" search is filed under (no SEEK in Ireland); Glassdoor picks it up, Indeed is skipped.
    op.execute(
        "INSERT INTO category (name, slug, seek_classification_id, country, enabled) "
        "VALUES ('Information & Communication Technology', 'ict-ie', '6281', 'IE', false)"
    )


def downgrade() -> None:
    op.execute("DELETE FROM category WHERE slug = 'ict-ie'")
