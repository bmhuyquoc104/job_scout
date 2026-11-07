from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from job_scout.green_list.parsing import parse_record
from job_scout.green_list.sync import apply_sync
from tests.green_list.conftest import TIER_1, TIER_2, inz_record

Factory = async_sessionmaker[AsyncSession]


def roles(*specs: tuple[str, str, str]):
    return [parse_record(inz_record(record_id, title, tier)) for record_id, title, tier in specs]


async def test_an_empty_table_returns_zeros(green_api: AsyncClient) -> None:
    body = (await green_api.get("/api/green-list")).json()

    assert body == {"synced_at": None, "tier_1": 0, "tier_2": 0, "total": 0, "roles": []}
    assert (await green_api.get("/api/green-list/changes")).json() == {"changes": []}


async def test_roles_come_with_tier_counts_sorted_by_title(
    green_api: AsyncClient, green_db: Factory
) -> None:
    await apply_sync(
        green_db, roles(("1", "Welder", TIER_2), ("2", "Nurse", TIER_1), ("3", "Architect", TIER_1))
    )

    body = (await green_api.get("/api/green-list")).json()

    assert (body["tier_1"], body["tier_2"], body["total"]) == (2, 1, 3)
    assert body["synced_at"] is not None
    assert [role["title"] for role in body["roles"]] == ["Architect", "Nurse", "Welder"]
    nurse = body["roles"][1]
    assert nurse["tier"] == 1 and nurse["anzsco_code"] == "261313"
    assert nurse["tier_changed_from"] is None and nurse["tier_changed_at"] is None
    assert "requirements" in nurse and "pathway" in nurse


async def test_a_role_that_changed_tier_says_so_and_a_removed_one_is_hidden(
    green_api: AsyncClient, green_db: Factory
) -> None:
    await apply_sync(
        green_db, roles(("1", "Welder", TIER_2), ("2", "Nurse", TIER_1), ("3", "Chef", TIER_1))
    )
    await apply_sync(green_db, roles(("1", "Welder", TIER_1), ("2", "Nurse", TIER_1)))

    body = (await green_api.get("/api/green-list")).json()

    assert [role["title"] for role in body["roles"]] == ["Nurse", "Welder"]  # Chef was removed
    assert (body["tier_1"], body["tier_2"]) == (2, 0)
    welder = next(role for role in body["roles"] if role["title"] == "Welder")
    assert (welder["tier"], welder["tier_changed_from"]) == (1, 2)
    assert welder["tier_changed_at"] is not None


async def test_changes_list_newest_first_with_what_changed(
    green_api: AsyncClient, green_db: Factory
) -> None:
    await apply_sync(
        green_db, roles(("1", "Welder", TIER_2), ("2", "Nurse", TIER_1), ("3", "Chef", TIER_1))
    )
    await apply_sync(
        green_db, roles(("1", "Welder", TIER_1), ("2", "Nurse", TIER_1), ("4", "Plumber", TIER_2))
    )

    changes = (await green_api.get("/api/green-list/changes?days=90")).json()["changes"]

    seen = {(c["title"], c["event_type"], c["from_tier"], c["tier"]) for c in changes}
    assert seen == {
        ("Welder", "tier_changed", 2, 1),
        ("Plumber", "new", None, 2),
        ("Chef", "removed", None, 1),
    }
    assert all(c["anzsco_code"] and c["occurred_at"] for c in changes)
    times = [c["occurred_at"] for c in changes]
    assert times == sorted(times, reverse=True)


async def test_changes_validate_the_period(green_api: AsyncClient) -> None:
    for query in ("days=3", "days=0", "days=9999", "days=abc"):
        response = await green_api.get(f"/api/green-list/changes?{query}")
        assert response.status_code == 422, query
        assert response.json()["error"]["code"] == "validation_error"
