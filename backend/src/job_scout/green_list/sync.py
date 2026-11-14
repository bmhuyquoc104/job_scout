import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

import httpx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from job_scout.core.errors import AppError, ErrorCode
from job_scout.green_list.australia import fetch_occupations
from job_scout.green_list.canada import fetch_occupations as fetch_canada
from job_scout.green_list.client import fetch_green_list
from job_scout.green_list.germany import fetch_thresholds
from job_scout.green_list.models import GreenListEvent, GreenListEventType, GreenListRole
from job_scout.green_list.parsing import RoleRecord

logger = logging.getLogger(__name__)
# A response with far fewer roles than before is treated as broken, not as "they were all removed".
MIN_KEEP_RATIO = 0.5


@dataclass
class SyncSummary:
    baseline: bool
    created: int = 0
    tier_changed: int = 0
    removed: int = 0
    restored: int = 0


async def apply_sync(
    session_factory: async_sessionmaker[AsyncSession],
    records: list[RoleRecord],
    country: str = "NZ",
) -> SyncSummary:
    """Bring one country's roles in line with the fetched list and record what changed.

    The first ever sync for a country is a baseline: it stores the roles but writes no events,
    so the change history starts from "nothing changed yet" instead of hundreds of "new" roles.
    """
    ids = [record.record_id for record in records]
    if not records or len(set(ids)) != len(ids):
        raise AppError(ErrorCode.SCRAPE_SOURCE_ERROR, "Green List is empty or repeats a record id")

    async with session_factory() as session, session.begin():
        existing = {
            role.record_id: role
            for role in await session.scalars(
                select(GreenListRole).where(GreenListRole.country == country)
            )
        }
        active_before = sum(role.is_active for role in existing.values())
        if active_before and len(records) < active_before * MIN_KEEP_RATIO:
            raise AppError(
                ErrorCode.SCRAPE_SOURCE_ERROR,
                f"Green List shrank from {active_before} to {len(records)} roles; not applying it",
            )
        summary = SyncSummary(baseline=not existing)
        pending: list[tuple[GreenListRole, GreenListEventType, dict[str, Any] | None]] = []

        for record in records:
            role = existing.get(record.record_id)
            if role is None:
                role = GreenListRole(
                    country=country, record_id=record.record_id, raw=record.raw, **_content(record)
                )
                session.add(role)
                summary.created += 1
                if not summary.baseline:
                    pending.append((role, GreenListEventType.NEW, None))
                continue
            if not role.is_active:
                role.is_active = True
                summary.restored += 1
                pending.append((role, GreenListEventType.RESTORED, None))
            if role.tier != record.tier:
                summary.tier_changed += 1
                details = {"from_tier": role.tier, "to_tier": record.tier}
                pending.append((role, GreenListEventType.TIER_CHANGED, details))
            for field, value in _content(record).items():
                if getattr(role, field) != value:
                    setattr(role, field, value)
            role.raw = record.raw
            role.last_seen_at = func.now()

        seen = set(ids)
        for role in existing.values():
            if role.is_active and role.record_id not in seen:
                role.is_active = False
                summary.removed += 1
                pending.append((role, GreenListEventType.REMOVED, None))

        await session.flush()  # new roles need their ids before events can point at them
        session.add_all(
            GreenListEvent(role_id=role.id, event_type=kind, details=details)
            for role, kind, details in pending
        )
    return summary


def _content(record: RoleRecord) -> dict[str, Any]:
    return {
        "title": record.title,
        "anzsco_code": record.anzsco_code,
        "industry": record.industry,
        "tier": record.tier,
        "pathway": record.pathway,
        "requirements": record.requirements,
        "engineering_degrees": record.engineering_degrees,
        "note": record.note,
        "lists": list(record.lists),
    }


async def _fetch_nz() -> list[RoleRecord]:
    async with httpx.AsyncClient(timeout=60) as http:
        return await fetch_green_list(http)


# One fetcher per country that has a priority-occupation list.
FETCHERS: dict[str, Callable[[], Awaitable[list[RoleRecord]]]] = {
    "NZ": _fetch_nz,
    "AU": fetch_occupations,
    "CA": fetch_canada,
    "DE": fetch_thresholds,
}


async def sync_green_list(
    session_factory: async_sessionmaker[AsyncSession] | None = None, country: str = "NZ"
) -> SyncSummary:
    """Fetch a country's occupation list and apply it. This is what the monthly task runs."""
    from job_scout.database import session_factory as default_session_factory

    records = await FETCHERS[country]()
    summary = await apply_sync(session_factory or default_session_factory, records, country)
    logger.info(
        "%s occupation list synced: %d roles (%s), %d tier change(s), %d removed, %d restored",
        country,
        len(records),
        "baseline" if summary.baseline else f"{summary.created} new",
        summary.tier_changed,
        summary.removed,
        summary.restored,
    )
    return summary
