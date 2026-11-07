import asyncio
import logging

from job_scout.core.errors import AppError
from job_scout.core.logging import configure_logging
from job_scout.green_list.sync import sync_green_list

logger = logging.getLogger(__name__)


def main() -> None:
    configure_logging()
    try:
        asyncio.run(sync_green_list())
    except AppError as exc:
        logger.error("%s (%s)", exc.message, exc.detail)
        raise SystemExit(1) from exc


main()
