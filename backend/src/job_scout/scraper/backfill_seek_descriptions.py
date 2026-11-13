"""One-off: replace the teaser stored for each active SEEK job with its full description.

Run from backend/: uv run python -m job_scout.scraper.backfill_seek_descriptions [--limit N]
Safe to re-run. Updates job_description directly, so no job events are written.

The daily SEEK enrichment fetches the full description itself, so this is only for jobs saved
before that existed.
"""

import argparse
import asyncio
import logging
import sys

from sqlalchemy import select, update

from job_scout.categories.models import Category
from job_scout.core.errors import AppError
from job_scout.core.logging import configure_logging
from job_scout.database import engine, session_factory
from job_scout.jobs.models import Job
from job_scout.scraper import chrome_http
from job_scout.scraper.seek_client import fetch_description

logger = logging.getLogger(__name__)

MAX_CONSECUTIVE_FAILURES = 5  # SEEK is probably blocking us; stop instead of hammering it


async def backfill(limit: int | None, delay: float) -> tuple[int, int, int]:
    async with session_factory() as session:  # closed before any network call
        query = (
            select(Job.id, Job.external_id, Category.country)
            .join(Category, Category.id == Job.category_id)
            .where(Job.source == "seek", Job.is_active.is_(True))
            .order_by(Job.first_seen_at)
        )
        jobs = (await session.execute(query.limit(limit))).all()

    logger.info("Backfilling %d active SEEK jobs", len(jobs))
    updated = skipped = failed = streak = 0
    async with chrome_http.client() as http:
        for done, (job_id, external_id, country) in enumerate(jobs, 1):
            if done % 25 == 0:
                logger.info("%d/%d (updated=%d failed=%d)", done, len(jobs), updated, failed)
            try:
                text = await fetch_description(http, external_id, country)
            except AppError as exc:
                failed, streak = failed + 1, streak + 1
                logger.warning("seek %s: %s", external_id, exc.message)
                if streak >= MAX_CONSECUTIVE_FAILURES:
                    logger.error("Stopping: %d failures in a row", streak)
                    break
            else:
                streak = 0
                if text is None:
                    skipped += 1
                else:
                    async with session_factory() as session, session.begin():
                        await session.execute(
                            update(Job).where(Job.id == job_id).values(job_description=text)
                        )
                    updated += 1
            await asyncio.sleep(delay)
    return updated, skipped, failed


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--limit", type=int, help="only the first N active jobs (try 20 first)")
    parser.add_argument("--delay", type=float, default=1.0, help="seconds between requests")
    args = parser.parse_args()
    configure_logging()
    try:
        updated, skipped, failed = await backfill(args.limit, args.delay)
    finally:
        await engine.dispose()
    logger.info("updated=%d skipped(no content)=%d failed=%d", updated, skipped, failed)
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    asyncio.run(main())
