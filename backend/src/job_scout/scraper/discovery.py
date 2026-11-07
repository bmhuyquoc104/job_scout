import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime
from functools import partial
from typing import Any
from uuid import UUID

import httpx
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from job_scout.core.errors import AppError, ErrorCode
from job_scout.jobs.models import Job, JobEvent, JobEventType
from job_scout.scraper import employmenthero, glassdoor, indeed, seek_client
from job_scout.scraper.models import JobDraft
from job_scout.scraper.normalization import normalize_text
from job_scout.scraper.persistence import draft_key, get_enabled_category, save_drafts

logger = logging.getLogger(__name__)
MAX_SEEK_PAGES = 1000  # shortcut: cap is 1,000 pages; raise if SEEK categories exceed it.


@dataclass
class DiscoverySummary:
    category_id: UUID
    scan_started_at: datetime
    fetched: int = 0


async def discover(
    session_factory: async_sessionmaker[AsyncSession], category_id: UUID
) -> DiscoverySummary:
    category = await get_enabled_category(session_factory, category_id)
    async with session_factory() as session:
        scan_started_at = await session.scalar(select(func.now()))
    if scan_started_at is None:
        raise AppError(ErrorCode.SCRAPE_SOURCE_ERROR, "Could not read the DB clock")

    logger.info("Starting SEEK discovery for %s (%s)", category.name, category.slug)
    summary = DiscoverySummary(category_id=category_id, scan_started_at=scan_started_at)
    seen_ids: set[str] = set()
    page_number = 1
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            while True:
                if page_number > MAX_SEEK_PAGES:
                    raise AppError(
                        ErrorCode.SCRAPE_SOURCE_ERROR, f"Exceeded {MAX_SEEK_PAGES} SEEK pages"
                    )
                page = seek_client.parse_search_page(
                    await seek_client.fetch_search_page(client, category, page_number)
                )
                if page.total_count == 0:
                    if page_number == 1:
                        logger.info("No SEEK listings found for %s", category.slug)
                    break
                logger.info(
                    "SEEK page %d for %s: %d listing(s) returned",
                    page_number,
                    category.slug,
                    len(page.data),
                )

                new_rows: list[tuple[str, dict[str, Any]]] = []
                for payload in page.data:
                    external_id = draft_key(payload)
                    if external_id in seen_ids:
                        continue
                    seen_ids.add(external_id)
                    new_rows.append((external_id, payload))
                if not new_rows:
                    raise AppError(
                        ErrorCode.SCRAPE_SOURCE_ERROR, f"Page {page_number} repeated known listings"
                    )
                await save_drafts(session_factory, category_id, new_rows)
                for external_id, payload in new_rows:
                    summary.fetched += 1
                    logger.info(
                        "Discovered listing %d (%s): %s",
                        summary.fetched,
                        external_id,
                        normalize_text(str(payload.get("title") or external_id)),
                    )
                page_number += 1
    except AppError as exc:
        logger.error("SEEK discovery failed for %s: %s", category.slug, exc)
        raise
    except Exception as exc:
        logger.exception("SEEK category discovery failed for category %s", category_id)
        raise AppError(ErrorCode.SCRAPE_SOURCE_ERROR) from exc

    logger.info(
        "SEEK discovery complete for %s: %d listing(s) seen",
        category.slug,
        summary.fetched,
    )
    return summary


MAX_EMPLOYMENTHERO_PAGES = 50  # shortcut: a safety cap; the board is a few pages per sector.
EMPLOYMENTHERO_DELAY = 1.0  # seconds between requests to their site


async def discover_employmenthero(
    session_factory: async_sessionmaker[AsyncSession], category_id: UUID
) -> DiscoverySummary:
    """Save every job on Employment Hero's board for the category's sector as a draft.

    Fails (so nothing is reconciled) if a page cannot be read, or the first page has no jobs.
    """
    category = await get_enabled_category(session_factory, category_id)
    if category.employmenthero_sector_id is None:
        raise AppError(ErrorCode.CATEGORY_NOT_FOUND)
    async with session_factory() as session:
        scan_started_at = await session.scalar(select(func.now()))
    if scan_started_at is None:
        raise AppError(ErrorCode.SCRAPE_SOURCE_ERROR, "Could not read the DB clock")

    logger.info("Starting Employment Hero discovery for %s", category.slug)
    summary = DiscoverySummary(category_id=category_id, scan_started_at=scan_started_at)
    seen: set[str] = set()
    try:
        async with employmenthero.client() as http:
            for page_number in range(1, MAX_EMPLOYMENTHERO_PAGES + 1):
                page_html = await employmenthero.fetch_list_page(
                    http, category.employmenthero_sector_id, page_number
                )
                slugs = [
                    slug for slug in employmenthero.parse_job_slugs(page_html) if slug not in seen
                ]
                if not slugs:
                    if page_number == 1:
                        raise AppError(
                            ErrorCode.SCRAPE_SOURCE_ERROR,
                            "Employment Hero's first page had no jobs",
                        )
                    break
                rows: list[tuple[str, dict[str, Any]]] = []
                for slug in slugs:
                    await asyncio.sleep(EMPLOYMENTHERO_DELAY)
                    payload = employmenthero.parse_job_posting(
                        await employmenthero.fetch_job_page(http, slug), slug
                    )
                    rows.append((slug, payload))
                seen.update(slugs)
                await save_drafts(session_factory, category_id, rows, source="employmenthero")
                summary.fetched += len(rows)
                await asyncio.sleep(EMPLOYMENTHERO_DELAY)
            else:
                raise AppError(
                    ErrorCode.SCRAPE_SOURCE_ERROR,
                    f"Exceeded {MAX_EMPLOYMENTHERO_PAGES} Employment Hero pages",
                )
    except AppError as exc:
        logger.error("Employment Hero discovery failed for %s: %s", category.slug, exc)
        raise
    except Exception as exc:
        logger.exception("Employment Hero discovery failed for category %s", category_id)
        raise AppError(ErrorCode.SCRAPE_SOURCE_ERROR) from exc
    logger.info("Employment Hero discovery complete: %d job(s) seen", summary.fetched)
    return summary


JOB_BOARDS = {"indeed": indeed, "glassdoor": glassdoor}
JOB_BOARD_DELAY = 1.0  # seconds between pages


async def discover_job_board(
    session_factory: async_sessionmaker[AsyncSession], category_id: UUID, source: str
) -> DiscoverySummary:
    """Save every job the board returns for the search as a draft.

    Fails (so nothing is reconciled) if a page cannot be read, or the first page has no jobs.
    """
    board = JOB_BOARDS[source]
    category = await get_enabled_category(session_factory, category_id)
    async with session_factory() as session:
        scan_started_at = await session.scalar(select(func.now()))
    if scan_started_at is None:
        raise AppError(ErrorCode.SCRAPE_SOURCE_ERROR, "Could not read the DB clock")

    logger.info("Starting %s discovery for %s", source, category.slug)
    summary = DiscoverySummary(category_id=category_id, scan_started_at=scan_started_at)
    seen: set[str] = set()
    first_page = True
    try:
        async with board.client() as http:
            async for page in board.pages(http):
                rows: list[tuple[str, dict[str, Any]]] = []
                for payload in page:
                    if payload["id"] not in seen:
                        seen.add(payload["id"])
                        rows.append((payload["id"], payload))
                if first_page and not rows:
                    raise AppError(
                        ErrorCode.SCRAPE_SOURCE_ERROR, f"{source}'s first page had no jobs"
                    )
                first_page = False
                await save_drafts(session_factory, category_id, rows, source=source)
                summary.fetched += len(rows)
                await asyncio.sleep(JOB_BOARD_DELAY)
    except AppError as exc:
        logger.error("%s discovery failed for %s: %s", source, category.slug, exc)
        raise
    except Exception as exc:
        logger.exception("%s discovery failed for category %s", source, category_id)
        raise AppError(ErrorCode.SCRAPE_SOURCE_ERROR) from exc
    logger.info("%s discovery complete: %d job(s) seen", source, summary.fetched)
    return summary


def discoverer(source: str) -> Callable[..., Awaitable[DiscoverySummary]]:
    if source == "seek":
        return discover
    if source == "employmenthero":
        return discover_employmenthero
    if source not in JOB_BOARDS:
        raise KeyError(source)
    return partial(discover_job_board, source=source)


async def reconcile_active_jobs(
    session_factory: async_sessionmaker[AsyncSession],
    category_id: UUID,
    scan_started_at: datetime,
    source: str = "seek",
) -> None:
    """Open/close this source's jobs by whether the scan saw them; other sources are untouched."""
    seen_ids = select(JobDraft.external_id).where(
        JobDraft.category_id == category_id,
        JobDraft.source == source,
        JobDraft.last_seen_at >= scan_started_at,
    )
    async with session_factory() as session, session.begin():
        reopened = await session.scalars(
            update(Job)
            .where(
                Job.category_id == category_id,
                Job.source == source,
                Job.external_id.in_(seen_ids),
                Job.is_active.is_(False),
            )
            .values(is_active=True, last_seen_at=func.now(), updated_at=func.now())
            .returning(Job.id)
        )
        reopened_ids = list(reopened)
        await session.execute(
            update(Job)
            .where(
                Job.category_id == category_id,
                Job.source == source,
                Job.external_id.in_(seen_ids),
                Job.is_active.is_(True),
            )
            .values(last_seen_at=func.now(), updated_at=func.now())
        )
        closed = await session.scalars(
            update(Job)
            .where(
                Job.category_id == category_id,
                Job.source == source,
                Job.external_id.not_in(seen_ids),
                Job.is_active.is_(True),
            )
            .values(is_active=False, updated_at=func.now())
            .returning(Job.id)
        )
        closed_ids = list(closed)
        session.add_all(
            [
                JobEvent(job_id=job_id, category_id=category_id, event_type=event_type)
                for event_type, job_ids in (
                    (JobEventType.REOPENED, reopened_ids),
                    (JobEventType.CLOSED, closed_ids),
                )
                for job_id in job_ids
            ]
        )
