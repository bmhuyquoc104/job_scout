import asyncio
import logging
from typing import Any
from uuid import UUID

from curl_cffi.requests import AsyncSession as HttpSession
from playwright.async_api import Page, async_playwright
from pydantic import ValidationError
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from job_scout.core.errors import AppError, ErrorCode
from job_scout.scraper import (
    chrome_http,
    employmenthero,
    glassdoor,
    immigration_client,
    indeed,
    seek_client,
)
from job_scout.scraper.immigration_client import extract_immigration_fields
from job_scout.scraper.models import JobDraft
from job_scout.scraper.normalization import (
    build_description,
    normalize_listing,
    normalize_text,
)
from job_scout.scraper.persistence import get_enabled_category, save_outcome
from job_scout.scraper.summary import ScrapeSummary

logger = logging.getLogger(__name__)
# Per source: how to read a draft payload and how to build its description.
SOURCES = {
    "seek": (normalize_listing, build_description),
    "employmenthero": (employmenthero.normalize_listing, employmenthero.build_description),
    "indeed": (indeed.normalize_listing, indeed.build_description),
    "glassdoor": (glassdoor.normalize_listing, glassdoor.build_description),
}
MAX_ENRICH_ATTEMPTS = 3  # failed drafts are retried this many times, then left for a payload change


async def _full_seek_description(http: HttpSession, external_id: str) -> str | None:
    """The full ad, or None to keep the search teaser (a missing description never fails a job)."""
    try:
        return await seek_client.fetch_description(http, external_id)
    except AppError as exc:
        logger.warning("SEEK %s: full description unavailable, using teaser: %s", external_id, exc)
        return None


async def process_listing(
    session_factory: async_sessionmaker[AsyncSession],
    category_id: UUID,
    external_id: str,
    payload: dict[str, Any],
    immigration_page: Page,
    accreditation_cache: dict[str, dict[str, Any]],
    source: str = "seek",
    seek_http: HttpSession | None = None,
) -> str:
    normalize, describe = SOURCES[source]
    if payload.get("id") is None or str(payload.get("id")) == "":
        await save_outcome(
            session_factory,
            category_id,
            external_id,
            status="failed",
            error=ErrorCode.SCRAPE_SOURCE_ERROR,
            source=source,
        )
        return "failed"

    immigration_result: dict[str, Any] | None = None
    try:
        listing = normalize(payload)
        company_key = normalize_text(listing.company_name).casefold()
        immigration_result = accreditation_cache.get(company_key)
        if immigration_result is None:
            immigration_result = await immigration_client.check_accreditation(
                immigration_page, listing.company_name
            )
            accreditation_cache[company_key] = immigration_result
        accredited = immigration_client.is_accredited(immigration_result)
        description = ""
        fields = {"nzbn": "", "trading_name": ""}
        if accredited:
            fields = extract_immigration_fields(immigration_result)
            description = describe(payload)
            if seek_http is not None:
                description = await _full_seek_description(seek_http, external_id) or description
            if not description:
                raise AppError(ErrorCode.SCRAPE_SOURCE_ERROR, "Listing has no description")
        enriched_data = {
            **listing.model_dump(mode="json"),
            "job_description": description,
            **fields,
        }
    except AppError as exc:
        logger.error("Failed to enrich SEEK listing %s: %s", external_id, exc)
        error = exc.code
    except ValidationError:
        logger.exception("Malformed SEEK listing %s", external_id)
        error = ErrorCode.SCRAPE_SOURCE_ERROR
    except Exception:
        logger.exception("Failed to enrich SEEK listing %s", external_id)
        error = ErrorCode.INTERNAL_ERROR
    else:
        error = None

    if error is not None:
        await save_outcome(
            session_factory,
            category_id,
            external_id,
            status="failed",
            immigration_result=immigration_result,
            error=error,
            source=source,
        )
        return "failed"

    await save_outcome(
        session_factory,
        category_id,
        external_id,
        status="accredited" if accredited else "not_accredited",
        enriched_data=enriched_data,
        immigration_result=immigration_result,
        source=source,
    )
    return "accredited" if accredited else "not_accredited"


async def enrich(
    session_factory: async_sessionmaker[AsyncSession], category_id: UUID, source: str = "seek"
) -> ScrapeSummary:
    category = await get_enabled_category(session_factory, category_id)
    summary = ScrapeSummary(category_id=category_id)
    async with session_factory() as session:
        drafts = (
            await session.execute(
                select(JobDraft.external_id, JobDraft.raw_payload)
                .where(
                    JobDraft.category_id == category_id,
                    JobDraft.source == source,
                    or_(
                        JobDraft.status == "pending",
                        (JobDraft.status == "failed") & (JobDraft.attempts < MAX_ENRICH_ATTEMPTS),
                    ),
                )
                .order_by(JobDraft.first_seen_at)
            )
        ).all()
        exhausted = await session.scalar(
            select(func.count()).where(
                JobDraft.category_id == category_id,
                JobDraft.source == source,
                JobDraft.status == "failed",
                JobDraft.attempts >= MAX_ENRICH_ATTEMPTS,
            )
        )
    if exhausted:
        logger.warning(
            "%d draft(s) for %s failed %d times; not retried until the source changes them",
            exhausted,
            category.slug,
            MAX_ENRICH_ATTEMPTS,
        )
    if not drafts:
        logger.info("No pending drafts to enrich for %s", category.slug)
        return summary

    logger.info("Starting enrichment for %s: %d pending draft(s)", category.slug, len(drafts))
    seek_http = chrome_http.client() if source == "seek" else None
    try:
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=True)
            try:
                # One page, kept on the Immigration NZ site between lookups.
                immigration_page = await browser.new_page()
                accreditation_cache: dict[str, dict[str, Any]] = {}
                for external_id, payload in drafts:
                    summary.fetched += 1
                    logger.info(
                        "Enriching listing %d/%d (%s): %s",
                        summary.fetched,
                        len(drafts),
                        external_id,
                        normalize_text(str(payload.get("title") or external_id)),
                    )
                    outcome = await process_listing(
                        session_factory,
                        category_id,
                        external_id,
                        payload,
                        immigration_page,
                        accreditation_cache,
                        source,
                        seek_http,
                    )
                    if outcome == "accredited":
                        summary.accredited += 1
                    elif outcome == "not_accredited":
                        summary.not_accredited += 1
                    else:
                        summary.failed += 1
                    logger.info(
                        "Finished listing %d/%d (%s): %s",
                        summary.fetched,
                        len(drafts),
                        external_id,
                        outcome.replace("_", " "),
                    )
                    await asyncio.sleep(2)
            finally:
                await browser.close()
                if seek_http is not None:
                    await seek_http.close()
    except AppError:
        raise
    except Exception as exc:
        logger.exception("SEEK listing enrichment failed for category %s", category_id)
        raise AppError(ErrorCode.SCRAPE_SOURCE_ERROR) from exc
    return summary
