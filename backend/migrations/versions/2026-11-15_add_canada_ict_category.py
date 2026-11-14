"""add a Canadian ICT category

Revision ID: c3f7a19d52e8
Revises: b9d2f6a14c83
Create Date: 2026-11-15 00:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c3f7a19d52e8"
down_revision: str | Sequence[str] | None = "b9d2f6a14c83"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Off until someone turns it on, like Australia: a full Canadian scrape is thousands of
    # listings. 6281 is only the id the job boards' "IT" search is filed under (no SEEK there).
    op.execute(
        "INSERT INTO category (name, slug, seek_classification_id, country, enabled) "
        "VALUES ('Information & Communication Technology', 'ict-ca', '6281', 'CA', false)"
    )


def downgrade() -> None:
    op.execute("DELETE FROM category WHERE slug = 'ict-ca'")
