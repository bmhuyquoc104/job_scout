"""make the Green List a per-country priority-occupation list

Revision ID: b9d2f6a14c83
Revises: a7e4c0b93d15
Create Date: 2026-11-14 02:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "b9d2f6a14c83"
down_revision: str | Sequence[str] | None = "a7e4c0b93d15"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "green_list_role",
        sa.Column("country", sa.String(2), nullable=False, server_default="NZ"),
    )
    op.add_column(
        "green_list_role",
        sa.Column("lists", postgresql.JSONB(), nullable=False, server_default="[]"),
    )
    op.alter_column("green_list_role", "tier", nullable=True)
    op.drop_constraint(op.f("green_list_role_record_id_key"), "green_list_role", type_="unique")
    op.create_unique_constraint(
        op.f("green_list_role_country_record_id_key"), "green_list_role", ["country", "record_id"]
    )


def downgrade() -> None:
    op.execute("DELETE FROM green_list_role WHERE country <> 'NZ'")
    op.drop_constraint(
        op.f("green_list_role_country_record_id_key"), "green_list_role", type_="unique"
    )
    op.create_unique_constraint(
        op.f("green_list_role_record_id_key"), "green_list_role", ["record_id"]
    )
    op.alter_column("green_list_role", "tier", nullable=False)
    op.drop_column("green_list_role", "lists")
    op.drop_column("green_list_role", "country")
