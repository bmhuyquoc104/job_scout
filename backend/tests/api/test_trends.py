from datetime import date

import pytest
from freezegun import freeze_time
from httpx import AsyncClient

from job_scout.categories.models import Category
from job_scout.jobs.models import Job
from job_scout.jobs.trends import build_trend

D = date


def test_trend_is_a_running_total_of_opens_minus_closes_per_seniority() -> None:
    rows = [
        (D(2026, 11, 1), "senior", "new", 3),
        (D(2026, 11, 1), "junior", "new", 1),
        (D(2026, 11, 3), "senior", "closed", 1),
        (D(2026, 11, 3), "junior", "updated", 5),  # changes nothing
        (D(2026, 11, 4), "senior", "reopened", 1),
    ]

    trend = build_trend(rows, today=D(2026, 11, 4), days=30)

    assert [point.date for point in trend.points] == [D(2026, 11, d) for d in (1, 2, 3, 4)]
    assert [point.total_open for point in trend.points] == [4, 4, 3, 4]
    assert [(p.new, p.closed) for p in trend.points] == [(4, 0), (0, 0), (0, 1), (0, 0)]
    assert trend.points[2].by_seniority == {
        "graduate": 0,
        "junior": 1,
        "mid": 0,
        "senior": 2,
        "lead": 0,
        "management": 0,
        "unspecified": 0,
    }
    assert trend.history_starts == D(2026, 11, 1)


def test_events_before_the_window_still_count_towards_the_starting_total() -> None:
    rows = [(D(2026, 10, 1), "senior", "new", 5), (D(2026, 11, 3), "senior", "new", 1)]

    trend = build_trend(rows, today=D(2026, 11, 4), days=3)

    assert [point.date for point in trend.points] == [D(2026, 11, d) for d in (2, 3, 4)]
    assert [point.total_open for point in trend.points] == [5, 6, 6]
    assert trend.history_starts == D(2026, 10, 1)


def test_no_events_means_an_empty_trend() -> None:
    trend = build_trend([], today=D(2026, 11, 4), days=30)

    assert trend.points == [] and trend.history_starts is None


# real_asyncio keeps the event loop on the real clock; only the app's "today" is frozen.
@freeze_time("2026-11-08 00:00:00", real_asyncio=True)
async def test_trend_endpoint_rebuilds_the_fixture_history(
    api_context: tuple[AsyncClient, Category, list[Job]],
) -> None:
    client, category, _ = api_context

    response = await client.get(f"/api/categories/{category.id}/stats/trends?days=365")

    assert response.status_code == 200
    body = response.json()
    by_day = {point["date"]: point for point in body["points"]}
    assert body["history_starts"] == "2026-10-01"
    assert (
        body["seniority_levels"][0] == "graduate" and body["seniority_levels"][-1] == "unspecified"
    )
    assert (by_day["2026-10-01"]["total_open"], by_day["2026-10-01"]["new"]) == (1, 1)
    assert by_day["2026-10-03"]["total_open"] == 3
    assert by_day["2026-10-03"]["by_seniority"]["senior"] == 2  # jobs 0 and 2
    assert (by_day["2026-10-05"]["total_open"], by_day["2026-10-05"]["closed"]) == (2, 1)
    assert by_day["2026-10-06"]["total_open"] == 3  # job 1 reopened
    assert by_day["2026-10-20"]["total_open"] == 2  # job 2 closed
    assert body["points"][-1]["total_open"] == 2  # matches the two open jobs now


@pytest.mark.parametrize("query", ["days=3", "days=0", "days=9999", "days=abc"])
async def test_trend_endpoint_validates_days(
    api_context: tuple[AsyncClient, Category, list[Job]], query: str
) -> None:
    client, category, _ = api_context

    response = await client.get(f"/api/categories/{category.id}/stats/trends?{query}")

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


async def test_trend_endpoint_rejects_unknown_category(
    api_context: tuple[AsyncClient, Category, list[Job]],
) -> None:
    client, _, _ = api_context

    response = await client.get("/api/categories/00000000-0000-7000-8000-000000000001/stats/trends")

    assert response.status_code == 404
