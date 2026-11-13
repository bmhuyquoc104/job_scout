"""add category country and an Australian ICT category

Revision ID: e8b2a47c91d3
Revises: d6a1f3b8c452
Create Date: 2026-11-14 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e8b2a47c91d3"
down_revision: str | Sequence[str] | None = "a4c8e2f61b97"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "category",
        sa.Column("country", sa.String(2), nullable=False, server_default="NZ"),
    )
    # SEEK classification ids repeat across countries (ICT is 6281 in both).
    op.drop_constraint("category_seek_classification_id_key", "category", type_="unique")
    op.create_unique_constraint(
        "category_country_seek_classification_id_key",
        "category",
        ["country", "seek_classification_id"],
    )
    # Disabled until someone turns it on: a full Australian scrape is thousands of listings.
    op.execute(
        "INSERT INTO category (name, slug, seek_classification_id, country, enabled) "
        "VALUES ('Information & Communication Technology', 'ict-au', '6281', 'AU', false)"
    )


def downgrade() -> None:
    op.execute("DELETE FROM category WHERE slug = 'ict-au'")
    op.drop_constraint("category_country_seek_classification_id_key", "category", type_="unique")
    op.create_unique_constraint(
        "category_seek_classification_id_key", "category", ["seek_classification_id"]
    )
    op.drop_column("category", "country")
