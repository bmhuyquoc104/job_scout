from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from job_scout.green_list.models import GreenListEvent, GreenListEventType, GreenListRole
from job_scout.green_list.schemas import (
    GreenListChange,
    GreenListChangesResponse,
    GreenListResponse,
    GreenListRoleItem,
)

_MAX_CHANGES = 500


async def get_green_list(session: AsyncSession) -> GreenListResponse:
    """The roles on the list now, with the tier counts and any recent tier move."""
    roles = (
        await session.scalars(
            select(GreenListRole)
            .where(GreenListRole.is_active.is_(True))
            .order_by(GreenListRole.title)
        )
    ).all()
    # Oldest first, so the last tier change per role wins.
    moves = await session.execute(
        select(GreenListEvent.role_id, GreenListEvent.occurred_at, GreenListEvent.details)
        .where(GreenListEvent.event_type == GreenListEventType.TIER_CHANGED)
        .order_by(GreenListEvent.occurred_at)
    )
    latest_move = {role_id: (at, details["from_tier"]) for role_id, at, details in moves}
    items = [
        GreenListRoleItem.model_validate(role, from_attributes=True).model_copy(
            update={
                "tier_changed_from": latest_move[role.id][1] if role.id in latest_move else None,
                "tier_changed_at": latest_move[role.id][0] if role.id in latest_move else None,
            }
        )
        for role in roles
    ]
    return GreenListResponse(
        synced_at=max((role.last_seen_at for role in roles), default=None),
        tier_1=sum(role.tier == 1 for role in roles),
        tier_2=sum(role.tier == 2 for role in roles),
        total=len(roles),
        roles=items,
    )


async def get_changes(session: AsyncSession, days: int) -> GreenListChangesResponse:
    rows = (
        await session.execute(
            select(GreenListEvent, GreenListRole)
            .join(GreenListRole, GreenListRole.id == GreenListEvent.role_id)
            .where(GreenListEvent.occurred_at >= func.now() - func.make_interval(0, 0, 0, days))
            .order_by(GreenListEvent.occurred_at.desc(), GreenListRole.title)
            .limit(_MAX_CHANGES)
        )
    ).all()
    return GreenListChangesResponse(
        changes=[
            GreenListChange(
                occurred_at=event.occurred_at,
                event_type=event.event_type,
                role_id=role.id,
                title=role.title,
                anzsco_code=role.anzsco_code,
                industry=role.industry,
                from_tier=(event.details or {}).get("from_tier"),
                tier=(event.details or {}).get("to_tier", role.tier),
            )
            for event, role in rows
        ]
    )
