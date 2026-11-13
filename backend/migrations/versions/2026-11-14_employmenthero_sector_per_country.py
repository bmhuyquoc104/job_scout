"""make the Employment Hero sector id unique per country and set Australian ICT's

Revision ID: f1c9d3a58b72
Revises: e8b2a47c91d3
Create Date: 2026-11-14 00:30:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f1c9d3a58b72"
down_revision: str | Sequence[str] | None = "e8b2a47c91d3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Sector ids repeat across countries (ICT is 18 on both of Employment Hero's boards).
    op.drop_constraint("category_employmenthero_sector_id_key", "category", type_="unique")
    op.create_unique_constraint(
        "category_country_employmenthero_sector_id_key",
        "category",
        ["country", "employmenthero_sector_id"],
    )
    op.execute("UPDATE category SET employmenthero_sector_id = 18 WHERE slug = 'ict-au'")


def downgrade() -> None:
    op.execute("UPDATE category SET employmenthero_sector_id = NULL WHERE slug = 'ict-au'")
    op.drop_constraint("category_country_employmenthero_sector_id_key", "category", type_="unique")
    op.create_unique_constraint(
        "category_employmenthero_sector_id_key", "category", ["employmenthero_sector_id"]
    )
