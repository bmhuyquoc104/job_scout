import asyncio
import logging

from job_scout.core.errors import AppError
from job_scout.core.logging import configure_logging
from job_scout.green_list.sync import FETCHERS, sync_green_list

logger = logging.getLogger(__name__)


async def sync_all() -> bool:
    """Sync every country; one failing must not stop the others. True if all succeeded."""
    ok = True
    for country in FETCHERS:
        try:
            await sync_green_list(country=country)
        except AppError as exc:
            logger.error("%s: %s (%s)", country, exc.message, exc.detail)
            ok = False
    return ok


def main() -> None:
    configure_logging()
    if not asyncio.run(sync_all()):
        raise SystemExit(1)


main()
