from httpx import AsyncClient

from job_scout.categories.models import Category
from job_scout.jobs.models import Job


async def test_comparison_counts_open_sponsored_jobs_per_country(
    api_context: tuple[AsyncClient, Category, list[Job]],
) -> None:
    client, _, _ = api_context

    response = await client.get("/api/compare/jobs?title=Engineer")

    stats = {item["country"]: item for item in response.json()["countries"]}
    assert (stats["NZ"]["open_jobs"], stats["NZ"]["visa_sponsor"]) == (2, 1)
    assert (stats["AU"]["open_jobs"], stats["AU"]["visa_sponsor"]) == (0, 0)


async def test_visa_sponsorship_stats_cover_every_country(
    api_context: tuple[AsyncClient, Category, list[Job]],
) -> None:
    client, _, _ = api_context

    response = await client.get("/api/stats/visa-sponsorship")

    assert response.status_code == 200
    stats = {item["country"]: item for item in response.json()}
    assert set(stats) == {"NZ", "AU", "CA", "DE"}
    assert (stats["NZ"]["open_jobs"], stats["NZ"]["visa_sponsor"]) == (2, 1)
    assert stats["NZ"]["country_name"] == "New Zealand"
    assert (stats["DE"]["open_jobs"], stats["DE"]["visa_sponsor"]) == (0, 0)


async def test_category_visa_stats_count_open_jobs_only(
    api_context: tuple[AsyncClient, Category, list[Job]],
) -> None:
    client, category, _ = api_context

    response = await client.get(f"/api/categories/{category.id}/stats/visa-sponsorship")

    assert response.status_code == 200
    assert response.json() == {"total_open": 2, "sponsored": 1}


async def test_category_visa_stats_reject_unknown_and_disabled_categories(
    api_context: tuple[AsyncClient, Category, list[Job]],
) -> None:
    client, _, _ = api_context

    response = await client.get(
        "/api/categories/00000000-0000-7000-8000-000000000001/stats/visa-sponsorship"
    )

    assert response.status_code == 404
