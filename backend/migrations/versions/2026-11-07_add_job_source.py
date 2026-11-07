"""add job source and generic external id/url columns

Revision ID: d6a1f3b8c452
Revises: b3e7c51d9a04
Create Date: 2026-11-07 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d6a1f3b8c452"
down_revision: str | Sequence[str] | None = "b3e7c51d9a04"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SOURCES = "source IN ('seek', 'employmenthero')"


def upgrade() -> None:
    op.alter_column("job", "seek_job_id", new_column_name="external_id")
    op.alter_column("job", "seek_url", new_column_name="url")
    op.alter_column("job_draft", "seek_job_id", new_column_name="external_id")
    for table in ("job", "job_draft"):
        # Employment Hero ids are URL slugs (some over 100 characters).
        op.alter_column(table, "external_id", type_=sa.String(300))
        op.add_column(
            table, sa.Column("source", sa.String(24), nullable=False, server_default="seek")
        )
        op.create_check_constraint(f"{table}_valid_source_check", table, SOURCES)
        # The constraint name is the same as before: the naming convention uses the first column.
        op.drop_constraint(f"{table}_category_id_key", table, type_="unique")
        op.create_unique_constraint(
            f"{table}_category_id_key", table, ["category_id", "source", "external_id"]
        )
    # Employment Hero's own sector id for a category (ICT = 18); NULL = not crawled there.
    op.add_column("category", sa.Column("employmenthero_sector_id", sa.Integer(), nullable=True))
    op.create_unique_constraint(
        "category_employmenthero_sector_id_key", "category", ["employmenthero_sector_id"]
    )
    op.execute("UPDATE category SET employmenthero_sector_id = 18 WHERE slug = 'ict'")


def downgrade() -> None:
    op.drop_constraint("category_employmenthero_sector_id_key", "category", type_="unique")
    op.drop_column("category", "employmenthero_sector_id")
    # Employment Hero rows cannot exist under the SEEK-only schema (ids are per source).
    for table in ("job_draft", "job"):
        if table == "job":
            op.execute("DELETE FROM job WHERE source <> 'seek'")
        else:
            op.execute("DELETE FROM job_draft WHERE source <> 'seek'")
        op.drop_constraint(f"{table}_category_id_key", table, type_="unique")
        op.create_unique_constraint(
            f"{table}_category_id_key", table, ["category_id", "external_id"]
        )
        op.drop_constraint(f"{table}_valid_source_check", table, type_="check")
        op.drop_column(table, "source")
        op.alter_column(table, "external_id", type_=sa.String(50))
    op.alter_column("job_draft", "external_id", new_column_name="seek_job_id")
    op.alter_column("job", "url", new_column_name="seek_url")
    op.alter_column("job", "external_id", new_column_name="seek_job_id")
