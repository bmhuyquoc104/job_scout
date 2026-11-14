"""add job skills and required_years

Revision ID: b4e8d1a62c57
Revises: a7d2f4c91b36
Create Date: 2026-11-15 18:00:00.000000

"""

import json
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from job_scout.matching.fit import analyze_job

# revision identifiers, used by Alembic.
revision: str = "b4e8d1a62c57"
down_revision: str | Sequence[str] | None = "a7d2f4c91b36"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "job",
        sa.Column(
            "skills",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="[]",
            nullable=False,
        ),
    )
    op.add_column("job", sa.Column("required_years", sa.Integer(), nullable=True))
    # Fill both for jobs that already exist; new ones are filled when promoted.
    bind = op.get_bind()
    rows = bind.execute(sa.text("SELECT id, position, job_description FROM job")).all()
    update = sa.text(
        "UPDATE job SET skills = CAST(:skills AS jsonb), required_years = :years WHERE id = :id"
    )
    for job_id, position, description in rows:
        found = analyze_job(position, description)
        bind.execute(
            update,
            {
                "id": job_id,
                "skills": json.dumps(found["skills"]),
                "years": found["required_years"],
            },
        )


def downgrade() -> None:
    op.drop_column("job", "required_years")
    op.drop_column("job", "skills")
