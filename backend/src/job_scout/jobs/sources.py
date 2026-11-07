"""The one list of job sources: id -> display name, in display order.

Adding a source = add it here, write its scraper (scraper/discovery.py JOB_BOARDS and
scraper/enrichment.py SOURCES), and add an Alembic migration for the `source` check constraint.
tests/test_job_sources.py fails if any of those is missed. The API, the check constraint in the
models and the frontend (labels, filters, colours) are all derived from this.
"""

JOB_SOURCES: dict[str, str] = {
    "seek": "SEEK",
    "employmenthero": "Employment Hero",
    "indeed": "Indeed",
    "glassdoor": "Glassdoor",
}
