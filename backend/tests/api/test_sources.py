from httpx import AsyncClient

from job_scout.categories.models import Category
from job_scout.jobs.models import Job
from job_scout.jobs.sources import JOB_SOURCES


async def test_source_endpoint_counts_open_jobs_per_source(
    api_context: tuple[AsyncClient, Category, list[Job]],
) -> None:
    client, category, _ = api_context

    response = await client.get(f"/api/categories/{category.id}/stats/sources")

    # Fixture: job 0 (SEEK) and job 1 (Employment Hero) are open; job 2 (SEEK) is closed.
    assert response.status_code == 200
    assert response.json() == {
        "sources": [{"source": "employmenthero", "count": 1}, {"source": "seek", "count": 1}],
        "total_open": 2,
    }


async def test_source_endpoint_rejects_unknown_category(
    api_context: tuple[AsyncClient, Category, list[Job]],
) -> None:
    client, _, _ = api_context

    response = await client.get(
        "/api/categories/00000000-0000-7000-8000-000000000001/stats/sources"
    )

    assert response.status_code == 404


async def test_sources_endpoint_lists_the_declared_sources_in_order(
    api_context: tuple[AsyncClient, Category, list[Job]],
) -> None:
    client, _, _ = api_context

    response = await client.get("/api/sources")

    assert response.status_code == 200
    assert response.json() == [
        {"source": source, "label": label} for source, label in JOB_SOURCES.items()
    ]
