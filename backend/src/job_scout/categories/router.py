from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from job_scout.categories import service
from job_scout.categories.schemas import CategoryItem
from job_scout.database import get_session

router = APIRouter(prefix="/categories", tags=["categories"])
SessionDep = Annotated[AsyncSession, Depends(get_session)]


@router.get("", response_model=list[CategoryItem])
async def get_categories(session: SessionDep) -> list[CategoryItem]:
    return await service.list_categories(session)
