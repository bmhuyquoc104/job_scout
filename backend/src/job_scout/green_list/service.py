from collections import Counter

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from job_scout.core.countries import COUNTRIES
from job_scout.green_list.models import GreenListEvent, GreenListEventType, GreenListRole
from job_scout.green_list.routes import matching_roles
from job_scout.green_list.schemas import (
    CountryRoutes,
    GreenListChange,
    GreenListChangesResponse,
    GreenListResponse,
    GreenListRoleItem,
    RouteRole,
    RoutesResponse,
)

_MAX_CHANGES = 500


async def get_green_list(session: AsyncSession, country: str = "NZ") -> GreenListResponse:
    """A country's roles on the list now, with tier or list counts and any recent tier move."""
    roles = (
        await session.scalars(
            select(GreenListRole)
            .where(GreenListRole.is_active.is_(True), GreenListRole.country == country)
            .order_by(GreenListRole.title)
        )
    ).all()
    # Oldest first, so the last tier change per role wins.
    moves = await session.execute(
        select(GreenListEvent.role_id, GreenListEvent.occurred_at, GreenListEvent.details)
        .join(GreenListRole, GreenListRole.id == GreenListEvent.role_id)
        .where(
            GreenListEvent.event_type == GreenListEventType.TIER_CHANGED,
            GreenListRole.country == country,
        )
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
        country=country,
        list_name=COUNTRIES[country].occupation_list_name,
        source_name=COUNTRIES[country].immigration_body,
        list_counts=dict(Counter(name for role in roles for name in role.lists)),
        synced_at=max((role.last_seen_at for role in roles), default=None),
        tier_1=sum(role.tier == 1 for role in roles),
        tier_2=sum(role.tier == 2 for role in roles),
        total=len(roles),
        roles=items,
    )


async def get_changes(
    session: AsyncSession, days: int, country: str = "NZ"
) -> GreenListChangesResponse:
    rows = (
        await session.execute(
            select(GreenListEvent, GreenListRole)
            .join(GreenListRole, GreenListRole.id == GreenListEvent.role_id)
            .where(
                GreenListEvent.occurred_at >= func.now() - func.make_interval(0, 0, 0, days),
                GreenListRole.country == country,
            )
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


async def get_routes(session: AsyncSession, title: str) -> RoutesResponse:
    """For one job title, every country's immigration routes: general ones and matching roles."""
    roles = (
        await session.scalars(select(GreenListRole).where(GreenListRole.is_active.is_(True)))
    ).all()
    countries = []
    for code, country in COUNTRIES.items():
        matches = matching_roles(title, [role for role in roles if role.country == code])
        countries.append(
            CountryRoutes(
                country=code,
                country_name=country.name,
                list_name=country.occupation_list_name,
                general_routes=list(country.general_routes),
                roles=[
                    RouteRole(
                        title=role.title,
                        code=role.anzsco_code,
                        tier=role.tier,
                        lists=role.lists,
                        pathway=role.pathway,
                    )
                    for role in matches
                ],
            )
        )
    return RoutesResponse(title=title, countries=countries)


async def get_titles(session: AsyncSession) -> list[str]:
    """Every role title on any country's list, once (ignoring case), for a picker."""
    titles = await session.scalars(
        select(GreenListRole.title).where(
            GreenListRole.is_active.is_(True),
            GreenListRole.industry.not_like("Salary threshold%"),
        )
    )
    unique: dict[str, str] = {}
    for title in titles:  # of two spellings differing in case, keep the capitalised one
        unique[title.lower()] = min(title, unique.get(title.lower(), title))
    return sorted(unique.values(), key=str.lower)
