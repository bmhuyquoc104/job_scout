import json
import os
import re
import subprocess
from pathlib import Path

import asyncpg
import pytest


async def test_migration_creates_tables_and_seeds_ict(connection: asyncpg.Connection) -> None:
    tables = await connection.fetch(
        """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name IN ('category', 'job_draft', 'job')
        """
    )
    assert {row["table_name"] for row in tables} == {"category", "job_draft", "job"}

    category = await connection.fetchrow(
        """
        SELECT name, slug, seek_classification_id
        FROM category
        WHERE seek_classification_id = '6281'
        """
    )
    assert dict(category) == {
        "name": "Information & Communication Technology",
        "slug": "ict",
        "seek_classification_id": "6281",
    }


async def test_migration_downgrade_succeeds_with_job_data(
    connection: asyncpg.Connection, async_test_database_url: str
) -> None:
    category_id = await connection.fetchval("SELECT id FROM category WHERE slug = 'ict'")
    await connection.execute("DELETE FROM job WHERE external_id = 'migration-test'")
    await connection.execute(
        """
        INSERT INTO job (
            category_id, external_id, company_name, location, salary_label, pay_period,
            position, job_description, url, nzbn, trading_name
        ) VALUES ($1, 'migration-test', 'Test Co', 'Wellington', '', '', 'Test role',
                  '', 'https://www.seek.co.nz/job/test', '', '')
        """,
        category_id,
    )
    backend_dir = Path(__file__).resolve().parents[2]
    env = {**os.environ, "DATABASE_URL": async_test_database_url}
    command = ["uv", "run", "alembic", "downgrade", "base"]
    result = subprocess.run(command, cwd=backend_dir, env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr

    result = subprocess.run(
        ["uv", "run", "alembic", "upgrade", "head"],
        cwd=backend_dir,
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


async def test_redundant_category_indexes_are_dropped(connection: asyncpg.Connection) -> None:
    names = {
        row["indexname"]
        for row in await connection.fetch(
            "SELECT indexname FROM pg_indexes WHERE tablename IN ('job', 'job_draft')"
        )
    }
    assert "ix_job_category_id_idx" not in names
    assert "ix_job_draft_category_id_idx" not in names
    assert "job_category_id_key" in names


async def test_job_event_table_records_job_history_and_follows_its_job(
    connection: asyncpg.Connection,
) -> None:
    columns = {
        row["column_name"]: row["is_nullable"]
        for row in await connection.fetch(
            "SELECT column_name, is_nullable FROM information_schema.columns "
            "WHERE table_name = 'job_event'"
        )
    }
    assert columns == {
        "id": "NO",
        "job_id": "NO",
        "category_id": "NO",
        "event_type": "NO",
        "occurred_at": "NO",
        "details": "YES",
    }

    category_id = await connection.fetchval("SELECT id FROM category WHERE slug = 'ict'")
    job_id = await connection.fetchval(
        """
        INSERT INTO job (category_id, external_id, company_name, location, salary_label,
                         pay_period, position, job_description, url, nzbn, trading_name)
        VALUES ($1, 'event-table-test', 'Co', '', '', '', 'Role', '', 'https://x', '', '')
        RETURNING id
        """,
        category_id,
    )
    await connection.execute(
        "INSERT INTO job_event (job_id, category_id, event_type) VALUES ($1, $2, 'new')",
        job_id,
        category_id,
    )
    with pytest.raises(asyncpg.CheckViolationError):
        await connection.execute(
            "INSERT INTO job_event (job_id, category_id, event_type) VALUES ($1, $2, 'bogus')",
            job_id,
            category_id,
        )

    await connection.execute("DELETE FROM job WHERE id = $1", job_id)
    assert (
        await connection.fetchval("SELECT count(*) FROM job_event WHERE job_id = $1", job_id) == 0
    )


async def test_salary_columns_are_backfilled_from_existing_labels(
    connection: asyncpg.Connection, async_test_database_url: str
) -> None:
    backend_dir = Path(__file__).resolve().parents[2]
    env = {**os.environ, "DATABASE_URL": async_test_database_url}

    def alembic(*args: str) -> None:
        result = subprocess.run(
            ["uv", "run", "alembic", *args],
            cwd=backend_dir,
            env=env,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr

    alembic("downgrade", "d4a8e1b7f205")  # the revision before the salary columns
    category_id = await connection.fetchval("SELECT id FROM category WHERE slug = 'ict'")
    for external_id, label in (("salary-hourly", "$28 per hour"), ("salary-none", "Competitive")):
        await connection.execute(
            """
            INSERT INTO job (category_id, seek_job_id, company_name, location, salary_label,
                             pay_period, position, job_description, seek_url, nzbn, trading_name)
            VALUES ($1, $2, 'Co', '', $3, '', 'Role', '', 'https://x', '', '')
            """,
            category_id,
            external_id,
            label,
        )

    alembic("upgrade", "head")

    rows = {
        row["external_id"]: (row["annual_salary_min"], row["annual_salary_max"])
        for row in await connection.fetch(
            "SELECT external_id, annual_salary_min, annual_salary_max FROM job "
            "WHERE external_id IN ('salary-hourly', 'salary-none')"
        )
    }
    assert rows == {"salary-hourly": (58_240, 58_240), "salary-none": (None, None)}


async def test_seniority_column_is_backfilled_from_existing_titles(
    connection: asyncpg.Connection, async_test_database_url: str
) -> None:
    backend_dir = Path(__file__).resolve().parents[2]
    env = {**os.environ, "DATABASE_URL": async_test_database_url}

    def alembic(*args: str) -> None:
        result = subprocess.run(
            ["uv", "run", "alembic", *args],
            cwd=backend_dir,
            env=env,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr

    alembic("downgrade", "e9c3a7d15b82")  # the revision before the seniority column
    category_id = await connection.fetchval("SELECT id FROM category WHERE slug = 'ict'")
    for external_id, title in (("lvl-senior", "Senior Data Engineer"), ("lvl-plain", "Analyst")):
        await connection.execute(
            """
            INSERT INTO job (category_id, seek_job_id, company_name, location, salary_label,
                             pay_period, position, job_description, seek_url, nzbn, trading_name)
            VALUES ($1, $2, 'Co', '', '', '', $3, '', 'https://x', '', '')
            """,
            category_id,
            external_id,
            title,
        )

    alembic("upgrade", "head")

    rows = {
        row["external_id"]: row["seniority"]
        for row in await connection.fetch(
            "SELECT external_id, seniority FROM job "
            "WHERE external_id IN ('lvl-senior', 'lvl-plain')"
        )
    }
    assert rows == {"lvl-senior": "senior", "lvl-plain": "unspecified"}


async def test_every_seek_classification_is_seeded_and_only_ict_is_enabled(
    connection: asyncpg.Connection,
) -> None:
    rows = await connection.fetch(
        "SELECT slug, name, seek_classification_id, enabled FROM category "
        "WHERE country = 'NZ' ORDER BY slug"
    )

    assert len(rows) == 27
    assert [row["slug"] for row in rows if row["enabled"]] == ["ict"]
    assert {row["seek_classification_id"] for row in rows} >= {"6281", "1225", "7019", "6304"}
    for row in rows:  # slugs are used on the command line and in the Airflow parameter
        assert re.fullmatch(r"[a-z0-9-]+", row["slug"]) and len(row["slug"]) <= 40
    by_slug = {row["slug"]: row for row in rows}
    assert by_slug["trades-services"]["name"] == "Trades & Services"
    assert by_slug["mining-resources-energy"]["seek_classification_id"] == "6058"


async def test_canadian_ict_category_exists_but_is_off_until_enabled(
    connection: asyncpg.Connection,
) -> None:
    row = await connection.fetchrow(
        "SELECT seek_classification_id, employmenthero_sector_id, enabled FROM category "
        "WHERE slug = 'ict-ca' AND country = 'CA'"
    )

    # The job boards find it by the same ICT id; no SEEK or Employment Hero there.
    assert dict(row) == {
        "seek_classification_id": "6281",
        "employmenthero_sector_id": None,
        "enabled": False,
    }


async def test_australian_ict_category_exists_but_is_off_until_enabled(
    connection: asyncpg.Connection,
) -> None:
    row = await connection.fetchrow(
        "SELECT seek_classification_id, employmenthero_sector_id, enabled FROM category "
        "WHERE slug = 'ict-au' AND country = 'AU'"
    )

    # Same ids as the NZ ICT category; off so no scheduled run scrapes it.
    assert dict(row) == {
        "seek_classification_id": "6281",
        "employmenthero_sector_id": 18,
        "enabled": False,
    }


async def test_green_list_tables_exist_and_events_follow_their_role(
    connection: asyncpg.Connection,
) -> None:
    role_id = await connection.fetchval(
        """
        INSERT INTO green_list_role (record_id, title, anzsco_code, industry, tier, raw)
        VALUES ('migration-test', 'Role', '111111', 'Trades', 1, '{}'::jsonb) RETURNING id
        """
    )
    await connection.execute(
        "INSERT INTO green_list_event (role_id, event_type) VALUES ($1, 'tier_changed')", role_id
    )
    with pytest.raises(asyncpg.CheckViolationError):
        await connection.execute(
            "INSERT INTO green_list_event (role_id, event_type) VALUES ($1, 'bogus')", role_id
        )
    with pytest.raises(asyncpg.UniqueViolationError):
        await connection.execute(
            "INSERT INTO green_list_role (record_id, title, anzsco_code, industry, tier, raw) "
            "VALUES ('migration-test', 'Again', '1', 'x', 2, '{}'::jsonb)"
        )

    await connection.execute("DELETE FROM green_list_role WHERE id = $1", role_id)
    assert (
        await connection.fetchval(
            "SELECT count(*) FROM green_list_event WHERE role_id = $1", role_id
        )
        == 0
    )


async def test_jobs_carry_a_source_and_ids_are_unique_per_source(
    connection: asyncpg.Connection,
) -> None:
    category = await connection.fetchrow(
        "SELECT id, employmenthero_sector_id FROM category WHERE slug = 'ict'"
    )
    assert category["employmenthero_sector_id"] == 18
    insert = """
        INSERT INTO job (category_id, source, external_id, company_name, location, salary_label,
                         pay_period, position, job_description, url, nzbn, trading_name)
        VALUES ($1, $2, 'same-id', 'Co', '', '', '', 'Role', '', 'https://x', '', '')
    """
    await connection.execute("DELETE FROM job WHERE external_id = 'same-id'")
    await connection.execute(insert, category["id"], "seek")
    await connection.execute(insert, category["id"], "employmenthero")  # same id, other source
    long_id = "x" * 250  # Employment Hero slugs can be long
    await connection.execute(
        insert.replace("'same-id'", "$3"), category["id"], "employmenthero", long_id
    )
    with pytest.raises(asyncpg.UniqueViolationError):
        await connection.execute(insert, category["id"], "seek")
    with pytest.raises(asyncpg.CheckViolationError):
        await connection.execute(insert, category["id"], "bogus")
    await connection.execute("DELETE FROM job WHERE external_id = 'same-id'")


async def test_visa_sponsor_column_is_backfilled_from_existing_descriptions(
    connection: asyncpg.Connection, async_test_database_url: str
) -> None:
    backend_dir = Path(__file__).resolve().parents[2]
    env = {**os.environ, "DATABASE_URL": async_test_database_url}

    def alembic(*args: str) -> None:
        result = subprocess.run(
            ["uv", "run", "alembic", *args],
            cwd=backend_dir,
            env=env,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr

    alembic("downgrade", "f2d6a83b19c7")  # the revision before the visa_sponsor column
    category_id = await connection.fetchval("SELECT id FROM category WHERE slug = 'ict'")
    for external_id, description in (
        ("visa-yes", "Great role. Visa sponsorship available."),
        ("visa-no", "Must already have the right to work. No sponsorship."),
    ):
        await connection.execute(
            """
            INSERT INTO job (category_id, external_id, company_name, location, salary_label,
                             pay_period, position, job_description, url, nzbn, trading_name)
            VALUES ($1, $2, 'Co', '', '', '', 'Dev', $3, 'https://x', '', '')
            """,
            category_id,
            external_id,
            description,
        )

    alembic("upgrade", "head")

    rows = {
        row["external_id"]: row["visa_sponsor"]
        for row in await connection.fetch(
            "SELECT external_id, visa_sponsor FROM job WHERE external_id IN ('visa-yes', 'visa-no')"
        )
    }
    assert rows == {"visa-yes": True, "visa-no": False}


async def test_job_analysis_columns_are_backfilled(
    connection: asyncpg.Connection, async_test_database_url: str
) -> None:
    backend_dir = Path(__file__).resolve().parents[2]
    env = {**os.environ, "DATABASE_URL": async_test_database_url}

    def alembic(*args: str) -> None:
        result = subprocess.run(
            ["uv", "run", "alembic", *args],
            cwd=backend_dir,
            env=env,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr

    alembic("downgrade", "a7d2f4c91b36")  # the revision before skills and required_years
    category_id = await connection.fetchval("SELECT id FROM category WHERE slug = 'ict'")
    await connection.execute(
        """
        INSERT INTO job (category_id, external_id, company_name, location, salary_label,
                         pay_period, position, job_description, url, nzbn, trading_name)
        VALUES ($1, 'analysis-1', 'Co', '', '', '', 'Senior Python Developer',
                'FastAPI and Docker. 6+ years experience', 'https://x', '', '')
        """,
        category_id,
    )

    alembic("upgrade", "head")

    row = await connection.fetchrow(
        "SELECT skills, required_years FROM job WHERE external_id = 'analysis-1'"
    )
    assert row is not None
    assert (json.loads(row["skills"]), row["required_years"]) == (
        ["docker", "fastapi", "python"],
        6,
    )
