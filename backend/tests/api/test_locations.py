from httpx import AsyncClient

from job_scout.categories.models import Category
from job_scout.jobs.locations import build_location_breakdown
from job_scout.jobs.models import Job


def test_breakdown_groups_suburbs_into_regions_biggest_first_then_by_name() -> None:
    rows = [
        ("Newmarket, Auckland", 3),
        ("Auckland CBD, Auckland", 2),
        ("Auckland", 4),
        ("Wellington Central, Wellington", 5),
        ("Wellington", 4),
        ("Albany, Zealandia", 1),
        ("Albany, Albania", 1),
        ("", 2),
    ]

    breakdown = build_location_breakdown(rows)

    assert [(item.region, item.count) for item in breakdown.regions] == [
        ("Auckland", 9),
        ("Wellington", 9),
        ("Not stated", 2),
        ("Albania", 1),
        ("Zealandia", 1),
    ]
    assert breakdown.total_open == 22


def test_breakdown_of_nothing_is_empty() -> None:
    breakdown = build_location_breakdown([])

    assert breakdown.regions == [] and breakdown.total_open == 0


async def test_location_endpoint_counts_only_open_jobs(
    api_context: tuple[AsyncClient, Category, list[Job]],
) -> None:
    client, category, _ = api_context

    response = await client.get(f"/api/categories/{category.id}/stats/locations")

    # Fixture: Wellington and Auckland are open; the Christchurch job is closed.
    assert response.status_code == 200
    assert response.json() == {
        "regions": [{"region": "Auckland", "count": 1}, {"region": "Wellington", "count": 1}],
        "total_open": 2,
    }


async def test_location_endpoint_rejects_unknown_category(
    api_context: tuple[AsyncClient, Category, list[Job]],
) -> None:
    client, _, _ = api_context

    response = await client.get(
        "/api/categories/00000000-0000-7000-8000-000000000001/stats/locations"
    )

    assert response.status_code == 404
