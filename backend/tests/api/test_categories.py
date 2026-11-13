from httpx import AsyncClient

from job_scout.categories.models import Category


async def test_categories_returns_enabled_category_with_active_job_count(
    api_context: tuple[AsyncClient, Category, list],
) -> None:
    client, category, _ = api_context

    response = await client.get("/api/categories")

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": str(category.id),
            "name": "Information & Communication Technology",
            "slug": "ict",
            "country": "NZ",
            "country_name": "New Zealand",
            "seek_classification_id": "6281",
            "active_job_count": 2,
        }
    ]
