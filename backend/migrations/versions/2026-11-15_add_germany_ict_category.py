"""add a German ICT category

Revision ID: e5b9c28a61f4
Revises: d8a1e54c07b3
Create Date: 2026-11-15 01:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e5b9c28a61f4"
down_revision: str | Sequence[str] | None = "d8a1e54c07b3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Off until someone turns it on, like Australia and Canada. 6281 is only the id the job
    # boards' "IT" search is filed under (no SEEK in Germany).
    op.execute(
        "INSERT INTO category (name, slug, seek_classification_id, country, enabled) "
        "VALUES ('Information & Communication Technology', 'ict-de', '6281', 'DE', false)"
    )


def downgrade() -> None:
    op.execute("DELETE FROM category WHERE slug = 'ict-de'")
