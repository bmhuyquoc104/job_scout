from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from job_scout.database import get_session
from job_scout.green_list import service
from job_scout.green_list.schemas import GreenListChangesResponse, GreenListResponse

router = APIRouter(prefix="/green-list", tags=["green-list"])
SessionDep = Annotated[AsyncSession, Depends(get_session)]


@router.get("", response_model=GreenListResponse)
async def get_green_list(session: SessionDep) -> GreenListResponse:
    return await service.get_green_list(session)


@router.get("/changes", response_model=GreenListChangesResponse)
async def get_green_list_changes(
    session: SessionDep, days: Annotated[int, Query(ge=7, le=365)] = 90
) -> GreenListChangesResponse:
    return await service.get_changes(session, days)
