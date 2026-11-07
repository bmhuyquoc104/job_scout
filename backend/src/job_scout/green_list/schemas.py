from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class GreenListRoleItem(BaseModel):
    id: UUID
    title: str
    anzsco_code: str
    industry: str
    tier: int
    pathway: str
    requirements: str
    engineering_degrees: str
    note: str
    # Set when this role moved between tiers; shows the tier it came from and when.
    tier_changed_from: int | None = None
    tier_changed_at: datetime | None = None


class GreenListResponse(BaseModel):
    synced_at: datetime | None
    tier_1: int
    tier_2: int
    total: int
    roles: list[GreenListRoleItem]


class GreenListChange(BaseModel):
    occurred_at: datetime
    event_type: str
    role_id: UUID
    title: str
    anzsco_code: str
    industry: str
    # Only for tier changes: the tier the role came from.
    from_tier: int | None = None
    # The tier the role has (for a tier change: the tier it moved to).
    tier: int


class GreenListChangesResponse(BaseModel):
    changes: list[GreenListChange]
