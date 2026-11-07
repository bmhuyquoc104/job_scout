import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from job_scout.core.errors import AppError, ErrorCode
from job_scout.green_list.models import GreenListEvent, GreenListRole
from job_scout.green_list.parsing import parse_record
from job_scout.green_list.sync import apply_sync
from tests.green_list.conftest import TIER_1, TIER_2, inz_record

Factory = async_sessionmaker[AsyncSession]


def roles(*specs: tuple[str, str, str]):
    return [parse_record(inz_record(record_id, title, tier)) for record_id, title, tier in specs]


BASE = (("1", "Software Engineer", TIER_1), ("2", "Nurse", TIER_1), ("3", "Welder", TIER_2))


async def events(factory: Factory) -> list[tuple[str, str, dict | None]]:
    async with factory() as session:
        rows = await session.execute(
            select(GreenListRole.title, GreenListEvent.event_type, GreenListEvent.details)
            .join(GreenListRole, GreenListRole.id == GreenListEvent.role_id)
            .order_by(GreenListEvent.occurred_at, GreenListRole.title)
        )
        return [(title, kind, details) for title, kind, details in rows]


async def test_the_first_sync_is_a_baseline_without_events(green_db: Factory) -> None:
    summary = await apply_sync(green_db, roles(*BASE))

    assert (summary.baseline, summary.created) == (True, 3)
    async with green_db() as session:
        stored = (await session.scalars(select(GreenListRole))).all()
    assert len(stored) == 3 and all(role.is_active and role.raw for role in stored)
    assert await events(green_db) == []


async def test_syncing_unchanged_data_records_nothing(green_db: Factory) -> None:
    await apply_sync(green_db, roles(*BASE))

    summary = await apply_sync(green_db, roles(*BASE))

    assert (summary.baseline, summary.created, summary.tier_changed, summary.removed) == (
        False,
        0,
        0,
        0,
    )
    assert await events(green_db) == []


async def test_a_tier_change_is_recorded_with_old_and_new_tier(green_db: Factory) -> None:
    await apply_sync(green_db, roles(*BASE))

    summary = await apply_sync(
        green_db,
        roles(("1", "Software Engineer", TIER_2), ("2", "Nurse", TIER_1), ("3", "Welder", TIER_2)),
    )

    assert summary.tier_changed == 1
    assert await events(green_db) == [
        ("Software Engineer", "tier_changed", {"from_tier": 1, "to_tier": 2})
    ]
    async with green_db() as session:
        engineer = await session.scalar(select(GreenListRole).where(GreenListRole.record_id == "1"))
    assert engineer is not None and engineer.tier == 2


async def test_new_removed_and_restored_roles_are_recorded(green_db: Factory) -> None:
    await apply_sync(green_db, roles(*BASE))

    await apply_sync(
        green_db,
        roles(("1", "Software Engineer", TIER_1), ("2", "Nurse", TIER_1), ("4", "Plumber", TIER_2)),
    )
    await apply_sync(green_db, roles(*BASE, ("4", "Plumber", TIER_2)))

    assert await events(green_db) == [
        ("Plumber", "new", None),
        ("Welder", "removed", None),
        ("Welder", "restored", None),
    ]
    async with green_db() as session:
        active = {
            r.title: r.is_active for r in (await session.scalars(select(GreenListRole))).all()
        }
    assert active == {"Software Engineer": True, "Nurse": True, "Welder": True, "Plumber": True}


async def test_a_removed_role_stays_in_the_table_as_inactive(green_db: Factory) -> None:
    await apply_sync(green_db, roles(*BASE))

    await apply_sync(green_db, roles(("1", "Software Engineer", TIER_1), ("2", "Nurse", TIER_1)))

    async with green_db() as session:
        welder = await session.scalar(select(GreenListRole).where(GreenListRole.record_id == "3"))
    assert welder is not None and welder.is_active is False


async def test_an_empty_or_collapsed_list_never_removes_anything(green_db: Factory) -> None:
    await apply_sync(green_db, roles(*BASE))

    for bad in ([], roles(("1", "Software Engineer", TIER_1))):  # nothing / far fewer than before
        with pytest.raises(AppError) as error:
            await apply_sync(green_db, bad)
        assert error.value.code is ErrorCode.SCRAPE_SOURCE_ERROR

    assert await events(green_db) == []
    async with green_db() as session:
        assert all(r.is_active for r in (await session.scalars(select(GreenListRole))).all())


async def test_the_same_record_twice_in_one_response_is_refused(green_db: Factory) -> None:
    with pytest.raises(AppError):
        await apply_sync(green_db, roles(("1", "A", TIER_1), ("1", "B", TIER_1)))
