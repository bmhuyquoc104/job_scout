import os
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy.engine import make_url

os.environ.setdefault("TESTCONTAINERS_DOCKER_SOCKET_OVERRIDE", "/var/run/docker.sock")

from testcontainers.community.postgres import PostgresContainer

BACKEND_DIR = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def postgres_url() -> str:
    with PostgresContainer(
        "postgres:18-alpine",
        username="job_scout_test",
        password="job_scout_test",
        dbname="job_scout_test",
    ) as postgres:
        database_url = make_url(postgres.get_connection_url()).set(drivername="postgresql+asyncpg")
        env = {**os.environ, "DATABASE_URL": database_url.render_as_string(hide_password=False)}
        result = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            cwd=BACKEND_DIR,
            env=env,
            capture_output=True,
            text=True,
        )
        if result.returncode:
            raise RuntimeError(f"Test database migration failed:\n{result.stderr}")
        yield database_url.render_as_string(hide_password=False)


@pytest.fixture(scope="session")
def async_test_database_url(postgres_url: str) -> str:
    return postgres_url


@pytest.fixture(scope="session")
def sync_test_database_url(postgres_url: str) -> str:
    return make_url(postgres_url).set(drivername="postgresql").render_as_string(hide_password=False)
