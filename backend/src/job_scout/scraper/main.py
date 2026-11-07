import argparse
import asyncio
import logging

from job_scout.core.errors import AppError, ErrorCode
from job_scout.core.logging import configure_logging
from job_scout.scraper.phases import discover_phase, enrich_phase, reconcile_phase, run_all_phases

logger = logging.getLogger(__name__)


async def run_once(
    category_slug: str,
    phase: str = "all",
    scan_started_at: str | None = None,
    source: str = "seek",
) -> int:
    try:
        if phase == "discover":
            print(await discover_phase(category_slug, source))
            return 0
        if phase == "reconcile":
            if scan_started_at is None:
                raise AppError(ErrorCode.INVALID_SCAN_TIMESTAMP, "--scan-started-at is required")
            await reconcile_phase(category_slug, scan_started_at, source)
            return 0
        # argparse restricts --phase, so anything else here is "all".
        if phase == "enrich":
            summary = await enrich_phase(category_slug, source)
        else:
            summary = await run_all_phases(category_slug, source)
    except AppError as exc:
        logger.error("%s%s", exc.message, f" ({exc.detail})" if exc.detail else "")
        return 1
    except Exception:
        logger.exception("Scraper stopped unexpectedly")
        return 1

    logger.info(
        "Scrape complete: %s fetched, %s accredited, %s not accredited, %s failed",
        summary.fetched,
        summary.accredited,
        summary.not_accredited,
        summary.failed,
    )
    return int(summary.failed > 0)


def main() -> None:
    parser = argparse.ArgumentParser(description="Scrape jobs for one category")
    parser.add_argument("--category", required=True, help="enabled category slug, e.g. ict")
    parser.add_argument("--source", choices=("seek", "employmenthero"), default="seek")
    parser.add_argument(
        "--phase", choices=("all", "discover", "reconcile", "enrich"), default="all"
    )
    parser.add_argument(
        "--scan-started-at", help="discovery timestamp required by the reconcile phase"
    )
    args = parser.parse_args()
    configure_logging()
    try:
        exit_code = asyncio.run(
            run_once(args.category, args.phase, args.scan_started_at, args.source)
        )
    except Exception:
        logger.exception("Scraper command failed")
        exit_code = 1
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
