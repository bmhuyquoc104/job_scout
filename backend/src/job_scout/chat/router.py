from collections.abc import AsyncIterator
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from job_scout.chat import service
from job_scout.chat.schemas import ChatRequest, ChatResponse
from job_scout.config import settings
from job_scout.database import get_session

router = APIRouter(tags=["chat"])
SessionDep = Annotated[AsyncSession, Depends(get_session)]


async def get_llm_client() -> AsyncIterator[httpx.AsyncClient | None]:
    """The rescue model's client, or None while no model is configured."""
    if not (settings.llm_api_key and settings.llm_model):
        yield None
        return
    async with httpx.AsyncClient(
        base_url=settings.llm_base_url,
        headers={"Authorization": f"Bearer {settings.llm_api_key}"},
        timeout=settings.llm_timeout,
    ) as client:
        yield client


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    session: SessionDep,
    llm: Annotated[httpx.AsyncClient | None, Depends(get_llm_client)],
) -> ChatResponse:
    return await service.answer(session, request, llm)
