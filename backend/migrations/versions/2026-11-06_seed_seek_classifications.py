"""seed the other SEEK classifications (disabled)

Revision ID: a8d41f6e92c7
Revises: f2b6d8a43c91
Create Date: 2026-11-06 05:00:00.000000

"""

import re
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a8d41f6e92c7"
down_revision: str | Sequence[str] | None = "f2b6d8a43c91"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# SEEK NZ classifications (id, name), found from the search API's listings. ICT (6281) is already
# seeded and enabled; the rest are added disabled, so a category is switched on deliberately with
# `UPDATE category SET enabled = true WHERE slug = '...'`.
CLASSIFICATIONS = [
    ("1200", "Accounting"),
    ("1203", "Banking & Financial Services"),
    ("1204", "Call Centre & Customer Service"),
    ("1206", "Construction"),
    ("1209", "Engineering"),
    ("1210", "Government & Defence"),
    ("1211", "Healthcare & Medical"),
    ("1212", "Hospitality & Tourism"),
    ("1216", "Legal"),
    ("1220", "Real Estate & Property"),
    ("1223", "Science & Technology"),
    ("1225", "Trades & Services"),
    ("6008", "Marketing & Communications"),
    ("6043", "Retail & Consumer Products"),
    ("6058", "Mining, Resources & Energy"),
    ("6092", "Manufacturing, Transport & Logistics"),
    ("6123", "Education & Training"),
    ("6163", "Community Services & Development"),
    ("6205", "Farming, Animals & Conservation"),
    ("6246", "Sport & Recreation"),
    ("6251", "Administration & Office Support"),
    ("6263", "Design & Architecture"),
    ("6304", "Advertising, Arts & Media"),
    ("6317", "Human Resources & Recruitment"),
    ("6362", "Sales"),
    ("7019", "CEO & General Management"),
]


def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def upgrade() -> None:
    bind = op.get_bind()
    for classification_id, name in CLASSIFICATIONS:
        bind.execute(
            sa.text(
                "INSERT INTO category (name, slug, seek_classification_id, enabled) "
                "VALUES (:name, :slug, :id, false) ON CONFLICT DO NOTHING"
            ),
            {"name": name, "slug": slugify(name), "id": classification_id},
        )


def downgrade() -> None:
    # Only remove categories nothing was ever scraped into.
    bind = op.get_bind()
    bind.execute(
        sa.text(
            "DELETE FROM category WHERE seek_classification_id = ANY(:ids) "
            "AND id NOT IN (SELECT category_id FROM job) "
            "AND id NOT IN (SELECT category_id FROM job_draft)"
        ),
        {"ids": [classification_id for classification_id, _ in CLASSIFICATIONS]},
    )
