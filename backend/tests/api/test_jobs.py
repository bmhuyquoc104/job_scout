import pytest
from httpx import AsyncClient
from pydantic import TypeAdapter

from job_scout.categories.models import Category
from job_scout.jobs.models import Job
from job_scout.jobs.schemas import JobSource


async def test_job_list_defaults_to_all_jobs_newest_first_and_paginates(
    api_context: tuple[AsyncClient, Category, list[Job]],
) -> None:
    client, category, jobs = api_context

    response = await client.get(f"/api/categories/{category.id}/jobs?limit=1&offset=0")

    assert response.status_code == 200
    assert response.json() == {
        "items": [
            {
                "id": str(jobs[2].id),
                "source": "seek",
                "position": "Engineer 2",
                "company_name": "Company 2",
                "location": "Christchurch",
                "work_arrangements": ["On-site"],
                "work_types": ["Part time"],
                "salary_label": "Competitive salary",
                "pay_period": "Year",
                "annual_salary_min": None,
                "annual_salary_max": None,
                "listed_at": "2026-10-03T00:00:00Z",
                "is_active": False,
                "visa_sponsor": False,
                "closed_at": "2026-10-20T00:00:00Z",
            }
        ],
        "total": 3,
        "limit": 1,
        "offset": 0,
        "category_name": category.name,
        "category_slug": "ict",
    }

    second_page = await client.get(f"/api/categories/{category.id}/jobs?limit=1&offset=1")
    assert second_page.json()["items"][0]["position"] == "Engineer 1"
    assert second_page.json()["offset"] == 1


async def test_job_detail_returns_all_csv_fields(
    api_context: tuple[AsyncClient, Category, list[Job]],
) -> None:
    client, _, jobs = api_context
    job = jobs[1]

    response = await client.get(f"/api/jobs/{job.id}")

    assert response.status_code == 200
    assert response.json() == {
        "id": str(job.id),
        "category_id": str(job.category_id),
        "source": "employmenthero",
        "external_id": "seek-1",
        "company_name": "Company 1",
        "location": "Auckland",
        "work_arrangements": ["Remote"],
        "work_types": ["Contract/Temp"],
        "salary_label": "$50 per hour",
        "pay_period": "Year",
        "annual_salary_min": 104000,
        "annual_salary_max": 104000,
        "position": "Engineer 1",
        "job_description": "Description 1",
        "url": "https://www.seek.co.nz/job/1",
        "nzbn": "nzbn-1",
        "trading_name": "Trading 1",
        "listed_at": "2026-10-02T00:00:00Z",
        "is_active": True,
        "visa_sponsor": True,
        "required_years": None,
        "closed_at": None,
    }


async def test_closed_job_detail_is_available_with_its_closing_date(
    api_context: tuple[AsyncClient, Category, list[Job]],
) -> None:
    client, _, jobs = api_context

    response = await client.get(f"/api/jobs/{jobs[2].id}")

    assert response.status_code == 200
    assert response.json()["is_active"] is False
    assert response.json()["closed_at"] == "2026-10-20T00:00:00Z"


async def test_missing_job_uses_central_not_found_error(
    api_context: tuple[AsyncClient, Category, list[Job]],
) -> None:
    client, _, _ = api_context

    response = await client.get("/api/jobs/00000000-0000-7000-8000-000000000001")

    assert response.status_code == 404
    assert response.json() == {"error": {"code": "job_not_found", "message": "Job not found."}}


async def test_job_list_status_filter_shows_open_closed_or_all_jobs(
    api_context: tuple[AsyncClient, Category, list[Job]],
) -> None:
    client, category, jobs = api_context
    base = f"/api/categories/{category.id}/jobs"

    closed = (await client.get(f"{base}?status=closed")).json()
    everything = (await client.get(f"{base}?status=all")).json()
    default = (await client.get(base)).json()

    assert [(i["id"], i["is_active"], i["closed_at"]) for i in closed["items"]] == [
        (str(jobs[2].id), False, "2026-10-20T00:00:00Z")
    ]
    assert closed["total"] == 1
    assert [i["id"] for i in everything["items"]] == [
        str(j.id) for j in (jobs[2], jobs[1], jobs[0])
    ]
    assert everything["total"] == 3
    assert default["total"] == 3
    assert (await client.get(f"{base}?status=open")).json()["total"] == 2


async def test_unknown_status_filter_is_a_validation_error(
    api_context: tuple[AsyncClient, Category, list[Job]],
) -> None:
    client, category, _ = api_context

    response = await client.get(f"/api/categories/{category.id}/jobs?status=bogus")

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


async def test_unknown_category_and_bad_pagination_use_central_errors(
    api_context: tuple[AsyncClient, Category, list[Job]],
) -> None:
    client, category, _ = api_context

    missing = await client.get("/api/categories/00000000-0000-7000-8000-000000000001/jobs")
    invalid = await client.get(f"/api/categories/{category.id}/jobs?limit=0")

    assert missing.status_code == 404
    assert missing.json() == {
        "error": {"code": "category_not_found", "message": "Category not found."}
    }
    assert invalid.status_code == 422
    assert invalid.json() == {
        "error": {"code": "validation_error", "message": "Request validation failed."}
    }


def _positions(response_json: dict) -> list[str]:
    return [item["position"] for item in response_json["items"]]


async def _list(client: AsyncClient, category: Category, query: str) -> dict:
    response = await client.get(f"/api/categories/{category.id}/jobs?{query}")
    assert response.status_code == 200, response.text
    return response.json()


async def test_every_column_can_be_sorted_both_ways(
    api_context: tuple[AsyncClient, Category, list[Job]],
) -> None:
    client, category, _ = api_context
    expected = {
        "position": ["Engineer 0", "Engineer 1", "Engineer 2"],
        "company": ["Engineer 0", "Engineer 1", "Engineer 2"],
        "location": [
            "Engineer 1",
            "Engineer 2",
            "Engineer 0",
        ],  # Auckland, Christchurch, Wellington
        "arrangement": ["Engineer 0", "Engineer 2", "Engineer 1"],  # Hybrid, On-site, Remote
        "work_type": ["Engineer 1", "Engineer 0", "Engineer 2"],  # Contract, Full, Part
        "listed": ["Engineer 0", "Engineer 1", "Engineer 2"],
        "status": ["Engineer 2", "Engineer 1", "Engineer 0"],  # closed first, then by newest
    }
    for column, ascending in expected.items():
        up = await _list(client, category, f"sort={column}&order=asc")
        down = await _list(client, category, f"sort={column}&order=desc")
        assert _positions(up) == ascending, column
        if column != "status":
            assert _positions(down) == ascending[::-1], column


async def test_salary_sort_puts_jobs_without_a_figure_last_in_both_directions(
    api_context: tuple[AsyncClient, Category, list[Job]],
) -> None:
    client, category, _ = api_context

    low_first = await _list(client, category, "sort=salary&order=asc")
    high_first = await _list(client, category, "sort=salary&order=desc")

    assert _positions(low_first) == ["Engineer 0", "Engineer 1", "Engineer 2"]
    assert _positions(high_first) == ["Engineer 1", "Engineer 0", "Engineer 2"]


async def test_text_columns_filter_by_case_insensitive_contains(
    api_context: tuple[AsyncClient, Category, list[Job]],
) -> None:
    client, category, _ = api_context

    assert _positions(await _list(client, category, "position=ENGINEER%201")) == ["Engineer 1"]
    assert _positions(await _list(client, category, "company=pany%202")) == ["Engineer 2"]
    assert _positions(await _list(client, category, "location=auck")) == ["Engineer 1"]
    # A literal % must not act as a wildcard.
    assert (await _list(client, category, "position=%25"))["total"] == 0


async def test_arrangement_and_work_type_filters_match_any_selected_value(
    api_context: tuple[AsyncClient, Category, list[Job]],
) -> None:
    client, category, _ = api_context

    hybrid = await _list(client, category, "arrangement=Hybrid")
    hybrid_or_remote = await _list(
        client, category, "arrangement=Hybrid&arrangement=Remote&sort=position&order=asc"
    )
    part_time = await _list(client, category, "work_type=Part%20time")

    assert _positions(hybrid) == ["Engineer 0"]
    assert _positions(hybrid_or_remote) == ["Engineer 0", "Engineer 1"]
    assert _positions(part_time) == ["Engineer 2"]


async def test_salary_filters_use_the_estimated_annual_range(
    api_context: tuple[AsyncClient, Category, list[Job]],
) -> None:
    client, category, _ = api_context

    listed = await _list(client, category, "salary=listed&sort=position&order=asc")
    unlisted = await _list(client, category, "salary=unlisted")
    at_least_102k = await _list(client, category, "min_salary=102000")
    at_least_100k = await _list(client, category, "min_salary=100000&sort=position&order=asc")

    assert _positions(listed) == ["Engineer 0", "Engineer 1"]
    assert _positions(unlisted) == ["Engineer 2"]
    assert _positions(at_least_102k) == ["Engineer 1"]
    assert _positions(at_least_100k) == ["Engineer 0", "Engineer 1"]


async def test_listed_date_range_is_inclusive_and_filters_combine(
    api_context: tuple[AsyncClient, Category, list[Job]],
) -> None:
    client, category, _ = api_context

    one_day = await _list(client, category, "listed_from=2026-10-02&listed_to=2026-10-02")
    until = await _list(client, category, "listed_to=2026-10-02&sort=listed&order=asc")
    combined = await _list(
        client, category, "status=open&location=wellington&listed_from=2026-10-01"
    )
    nothing = await _list(client, category, "status=closed&location=wellington")

    assert _positions(one_day) == ["Engineer 1"]
    assert _positions(until) == ["Engineer 0", "Engineer 1"]
    assert _positions(combined) == ["Engineer 0"]
    assert nothing["total"] == 0 and nothing["items"] == []


async def test_filtered_totals_drive_pagination(
    api_context: tuple[AsyncClient, Category, list[Job]],
) -> None:
    client, category, _ = api_context

    page = await _list(client, category, "status=open&limit=1&offset=1&sort=position&order=asc")

    assert page["total"] == 2
    assert _positions(page) == ["Engineer 1"]


async def test_bad_sort_and_filter_values_are_validation_errors(
    api_context: tuple[AsyncClient, Category, list[Job]],
) -> None:
    client, category, _ = api_context

    for query in (
        "sort=bogus",
        "order=sideways",
        "min_salary=-1",
        "listed_from=yesterday",
        "salary=maybe",
        "visa=maybe",
        "source=monster",
    ):
        response = await client.get(f"/api/categories/{category.id}/jobs?{query}")
        assert response.status_code == 422, query
        assert response.json()["error"]["code"] == "validation_error"


async def test_facets_list_the_values_that_exist_for_the_filters(
    api_context: tuple[AsyncClient, Category, list[Job]],
) -> None:
    client, category, _ = api_context

    response = await client.get(f"/api/categories/{category.id}/jobs/facets")

    assert response.status_code == 200
    assert response.json() == {
        "arrangements": ["Hybrid", "On-site", "Remote"],
        "work_types": ["Contract/Temp", "Full time", "Part time"],
    }
    missing = await client.get("/api/categories/00000000-0000-7000-8000-000000000001/jobs/facets")
    assert missing.status_code == 404


async def test_jobs_can_be_filtered_and_sorted_by_source(
    api_context: tuple[AsyncClient, Category, list[Job]],
) -> None:
    client, category, jobs = api_context

    assert _positions(await _list(client, category, "source=employmenthero")) == ["Engineer 1"]
    assert (await _list(client, category, "source=seek"))["total"] == 2
    ordered = await _list(client, category, "sort=source&order=asc")
    assert [item["source"] for item in ordered["items"]] == ["employmenthero", "seek", "seek"]
    detail = await client.get(f"/api/jobs/{jobs[1].id}")
    assert detail.json()["source"] == "employmenthero"


@pytest.mark.parametrize("source", ["seek", "employmenthero", "indeed", "glassdoor"])
def test_every_stored_job_source_is_a_valid_api_source(source: str) -> None:
    # The job table allows these sources; a source the API type rejects breaks the response.
    assert TypeAdapter(JobSource).validate_python(source) == source


async def test_visa_sponsorship_filters_and_sorts(
    api_context: tuple[AsyncClient, Category, list[Job]],
) -> None:
    client, category, _ = api_context

    offered = await _list(client, category, "visa=offered")
    not_mentioned = await _list(client, category, "visa=not_mentioned&sort=position&order=asc")
    offered_first = await _list(client, category, "sort=visa&order=desc")

    assert _positions(offered) == ["Engineer 1"]
    assert _positions(not_mentioned) == ["Engineer 0", "Engineer 2"]
    assert _positions(offered_first)[0] == "Engineer 1"
