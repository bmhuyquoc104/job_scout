from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from job_scout.core.countries import COUNTRIES
from job_scout.core.errors import AppError, ErrorCode
from job_scout.database import get_session
from job_scout.green_list import service
from job_scout.green_list.schemas import (
    GreenListChangesResponse,
    GreenListResponse,
    RoutesResponse,
)

router = APIRouter(prefix="/green-list", tags=["green-list"])
SessionDep = Annotated[AsyncSession, Depends(get_session)]


def known_country(country: str = "NZ") -> str:
    if country not in COUNTRIES:
        raise AppError(ErrorCode.VALIDATION_ERROR, f"unknown country {country!r}")
    return country


CountryDep = Annotated[str, Depends(known_country)]


@router.get("", response_model=GreenListResponse)
async def get_green_list(session: SessionDep, country: CountryDep) -> GreenListResponse:
    return await service.get_green_list(session, country)


@router.get("/changes", response_model=GreenListChangesResponse)
async def get_green_list_changes(
    session: SessionDep, country: CountryDep, days: Annotated[int, Query(ge=7, le=365)] = 90
) -> GreenListChangesResponse:
    return await service.get_changes(session, days, country)


@router.get("/routes", response_model=RoutesResponse)
async def get_routes(
    session: SessionDep, title: Annotated[str, Query(min_length=1, max_length=200)]
) -> RoutesResponse:
    return await service.get_routes(session, title)


@router.get("/titles", response_model=list[str])
async def get_titles(session: SessionDep) -> list[str]:
    return await service.get_titles(session)
