from uuid import UUID

import asyncpg


async def test_models_use_jsonb_and_timezone_aware_listing_date(
    connection: asyncpg.Connection,
) -> None:
    rows = await connection.fetch(
        """
        SELECT table_name, column_name, data_type
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name IN ('job_draft', 'job')
        """
    )
    types = {(row["table_name"], row["column_name"]): row["data_type"] for row in rows}

    assert types[("job_draft", "raw_payload")] == "jsonb"
    assert types[("job_draft", "immigration_result")] == "jsonb"
    assert types[("job", "work_arrangements")] == "jsonb"
    assert types[("job", "work_types")] == "jsonb"
    assert types[("job", "listed_at")] == "timestamp with time zone"


async def test_job_tables_enforce_category_seek_id_uniqueness_and_foreign_keys(
    connection: asyncpg.Connection,
) -> None:
    constraints = await connection.fetch(
        """
        SELECT conrelid::regclass::text AS table_name,
               contype::text AS contype,
               pg_get_constraintdef(oid) AS definition
        FROM pg_constraint
        WHERE conrelid IN (SELECT oid FROM pg_class WHERE relname IN ('job_draft', 'job'))
        """
    )
    definitions = {(row["table_name"], row["contype"], row["definition"]) for row in constraints}

    for table in ("job_draft", "job"):
        assert (
            table,
            "u",
            "UNIQUE (category_id, source, external_id)",
        ) in definitions
        assert (
            table,
            "f",
            "FOREIGN KEY (category_id) REFERENCES category(id)",
        ) in definitions


async def test_identity_columns_are_database_generated_uuid_v7(
    connection: asyncpg.Connection,
) -> None:
    columns = await connection.fetch(
        """
        SELECT table_name, column_name, data_type, column_default
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND (column_name = 'id' OR column_name = 'category_id')
          AND table_name IN ('category', 'job_draft', 'job')
        """
    )
    column_types = {(row["table_name"], row["column_name"]): row["data_type"] for row in columns}
    assert column_types == {
        (table, column): "uuid"
        for table, column in (
            ("category", "id"),
            ("job_draft", "id"),
            ("job_draft", "category_id"),
            ("job", "id"),
            ("job", "category_id"),
        )
    }
    assert all("uuidv7" in row["column_default"] for row in columns if row["column_name"] == "id")

    category_id = await connection.fetchval("SELECT id FROM category WHERE slug = 'ict'")
    assert isinstance(category_id, UUID) and category_id.version == 7
    job_id = await connection.fetchval(
        """
        INSERT INTO job (
            category_id, external_id, company_name, location, salary_label, pay_period,
            position, job_description, url, nzbn, trading_name
        ) VALUES ($1, 'uuidv7-test', 'Test Co', 'Wellington', '', '', 'Test role',
                  '', 'https://www.seek.co.nz/job/test', '', '')
        RETURNING id
        """,
        category_id,
    )
    draft_id = await connection.fetchval(
        """
        INSERT INTO job_draft (category_id, external_id, raw_payload, status)
        VALUES ($1, 'uuidv7-test', '{}', 'pending')
        RETURNING id
        """,
        category_id,
    )
    assert isinstance(job_id, UUID) and job_id.version == 7
    assert isinstance(draft_id, UUID) and draft_id.version == 7
