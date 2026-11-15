from httpx import AsyncClient

from job_scout.categories.models import Category
from job_scout.jobs.models import Job


async def test_comparison_breaks_each_country_down_by_seniority_arrangement_and_experience(
    api_context: tuple[AsyncClient, Category, list[Job]],
) -> None:
    client, _, _ = api_context

    response = await client.get("/api/compare/jobs?title=Engineer")

    stats = {item["country"]: item for item in response.json()["countries"]}
    nz = stats["NZ"]  # two open jobs: senior/Hybrid/5 years and junior/Remote/0 years
    assert nz["by_seniority"] == {"junior": 1, "senior": 1}
    assert nz["by_arrangement"] == {"Hybrid": 1, "Remote": 1}
    assert nz["median_required_years"] == 2.5
    assert (stats["AU"]["by_seniority"], stats["AU"]["median_required_years"]) == ({}, None)


async def test_comparison_without_a_title_covers_every_open_job(
    api_context: tuple[AsyncClient, Category, list[Job]],
) -> None:
    client, _, _ = api_context

    response = await client.get("/api/compare/jobs")

    assert response.status_code == 200
    assert response.json()["title"] == ""
    assert response.json()["countries"][0]["open_jobs"] == 2
