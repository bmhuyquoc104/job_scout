from typing import Annotated

from fastapi import APIRouter, Depends, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from job_scout.database import get_session
from job_scout.matching import service
from job_scout.matching.schemas import CvSkills, JobMatch, MatchRequest

router = APIRouter(tags=["matching"])


@router.post("/cv", response_model=CvSkills)
async def read_cv(file: UploadFile) -> CvSkills:
    """Read an uploaded PDF CV in memory and return the IT skills it names; the CV is not stored."""
    return CvSkills(skills=await service.parse_cv(await file.read(service.MAX_CV_BYTES + 1)))


@router.post("/matches", response_model=list[JobMatch])
async def match_cv(
    request: MatchRequest, session: Annotated[AsyncSession, Depends(get_session)]
) -> list[JobMatch]:
    """Rank every open job against CV skills, so a saved CV needs no re-upload."""
    return await service.match_jobs(session, request.skills)
