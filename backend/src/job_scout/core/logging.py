import logging

from job_scout.config import settings

LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"


def configure_logging(level: str | None = None) -> None:
    """Set up root logging once; every entry point (API, scraper, Airflow) calls this."""
    logging.basicConfig(level=(level or settings.log_level).upper(), format=LOG_FORMAT)
