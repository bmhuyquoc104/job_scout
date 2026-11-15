"""add a Dutch ICT category

Revision ID: e1b7d3f5a902
Revises: d8a4c6e2b917
Create Date: 2026-11-15 21:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e1b7d3f5a902"
down_revision: str | Sequence[str] | None = "d8a4c6e2b917"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Off until someone turns it on, like the other countries. 6281 is only the id the job boards'
    # "IT" search is filed under (no SEEK in the Netherlands).
    op.execute(
        "INSERT INTO category (name, slug, seek_classification_id, country, enabled) "
        "VALUES ('Information & Communication Technology', 'ict-nl', '6281', 'NL', false)"
    )


def downgrade() -> None:
    op.execute("DELETE FROM category WHERE slug = 'ict-nl'")
