import hashlib
import json
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import case, func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from job_scout.categories.models import Category
from job_scout.categories.service import require_enabled_category
from job_scout.core.errors import ERROR_CATALOG, ErrorCode
from job_scout.jobs.models import Job, JobEvent, JobEventType
from job_scout.scraper.models import JobDraft
from job_scout.scraper.normalization import NormalizedListing, classify_seniority, parse_salary


def draft_key(payload: dict[str, Any]) -> str:
    source_id = payload.get("id")
    if source_id is not None and str(source_id):
        return str(source_id)
    # shortcut: identical ID-less payloads deduplicate; revisit if SEEK often omits IDs.
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()
    return f"invalid:{digest[:40]}"


async def save_drafts(
    session_factory: async_sessionmaker[AsyncSession],
    category_id: UUID,
    rows: list[tuple[str, dict[str, Any]]],
    source: str = "seek",
) -> None:
    """Upsert one page of drafts in a single transaction. Keys must be unique."""
    if not rows:
        return
    statement = insert(JobDraft).values(
        [
            {
                "category_id": category_id,
                "source": source,
                "external_id": external_id,
                "raw_payload": payload,
            }
            for external_id, payload in rows
        ]
    )
    payload_changed = JobDraft.raw_payload.is_distinct_from(statement.excluded.raw_payload)
    async with session_factory() as session, session.begin():
        await session.execute(
            statement.on_conflict_do_update(
                index_elements=["category_id", "source", "external_id"],
                set_={
                    "raw_payload": statement.excluded.raw_payload,
                    "last_seen_at": func.now(),
                    "status": case((payload_changed, "pending"), else_=JobDraft.status),
                    "attempts": case((payload_changed, 0), else_=JobDraft.attempts),
                    "enriched_data": case((payload_changed, None), else_=JobDraft.enriched_data),
                    "immigration_result": case(
                        (payload_changed, None), else_=JobDraft.immigration_result
                    ),
                    "error_code": case((payload_changed, None), else_=JobDraft.error_code),
                    "error_message": case((payload_changed, None), else_=JobDraft.error_message),
                    "processed_at": case((payload_changed, None), else_=JobDraft.processed_at),
                },
            )
        )


# Content fields whose change counts as an "updated" job event.
TRACKED_JOB_FIELDS = (
    "company_name",
    "location",
    "work_arrangements",
    "work_types",
    "salary_label",
    "pay_period",
    "position",
    "job_description",
    "nzbn",
    "trading_name",
    "listed_at",
)


async def save_outcome(
    session_factory: async_sessionmaker[AsyncSession],
    category_id: UUID,
    external_id: str,
    *,
    status: str,
    enriched_data: dict[str, Any] | None = None,
    immigration_result: dict[str, Any] | None = None,
    error: ErrorCode | None = None,
    source: str = "seek",
) -> None:
    async with session_factory() as session, session.begin():
        await session.execute(
            update(JobDraft)
            .where(
                JobDraft.category_id == category_id,
                JobDraft.source == source,
                JobDraft.external_id == external_id,
            )
            .values(
                status=status,
                enriched_data=enriched_data,
                immigration_result=immigration_result,
                error_code=error.value if error else None,
                error_message=ERROR_CATALOG[error].message if error else None,
                attempts=JobDraft.attempts + 1 if status == "failed" else JobDraft.attempts,
                processed_at=func.now(),
            )
        )
        if status != "accredited" or enriched_data is None:
            return

        listing = NormalizedListing.model_validate(enriched_data)
        salary_min, salary_max = parse_salary(listing.salary_label)
        job_values = {
            "category_id": category_id,
            **listing.model_dump(),
            "annual_salary_min": salary_min,
            "annual_salary_max": salary_max,
            "seniority": classify_seniority(listing.position),
            "job_description": enriched_data["job_description"],
            "nzbn": enriched_data["nzbn"],
            "trading_name": enriched_data["trading_name"],
            "is_active": True,
            "last_seen_at": func.now(),
            "updated_at": func.now(),
        }
        existing = await session.scalar(
            select(Job).where(
                Job.category_id == category_id,
                Job.source == listing.source,
                Job.external_id == listing.external_id,
            )
        )
        statement = insert(Job).values(**job_values)
        update_values = {
            key: getattr(statement.excluded, key)
            for key in (
                *TRACKED_JOB_FIELDS,
                "url",
                "annual_salary_min",
                "annual_salary_max",
                "seniority",
                "is_active",
                "last_seen_at",
                "updated_at",
            )
        }
        job_id = await session.scalar(
            statement.on_conflict_do_update(
                index_elements=["category_id", "source", "external_id"],
                set_=update_values,
            ).returning(Job.id)
        )
        for event_type, details in _promotion_events(existing, job_values):
            session.add(
                JobEvent(
                    job_id=job_id, category_id=category_id, event_type=event_type, details=details
                )
            )


def _promotion_events(
    existing: Job | None, new_values: dict[str, Any]
) -> list[tuple[JobEventType, dict[str, Any] | None]]:
    """What a promotion means for history: a new job, a reopened one, and/or changed fields."""
    if existing is None:
        return [(JobEventType.NEW, None)]
    events: list[tuple[JobEventType, dict[str, Any] | None]] = []
    if not existing.is_active:
        events.append((JobEventType.REOPENED, None))
    changes = {
        field: {"old": _json_value(getattr(existing, field)), "new": _json_value(new_values[field])}
        for field in TRACKED_JOB_FIELDS
        if getattr(existing, field) != new_values[field]
    }
    if changes:
        events.append((JobEventType.UPDATED, changes))
    return events


def _json_value(value: Any) -> Any:
    return value.isoformat() if isinstance(value, datetime) else value


async def get_enabled_category(
    session_factory: async_sessionmaker[AsyncSession], category_id: UUID
) -> Category:
    async with session_factory() as session:
        return await require_enabled_category(session, category_id)
