import sys
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest

from job_scout.core.errors import AppError, ErrorCode
from job_scout.scraper import main as scraper_main
from job_scout.scraper import phases

SCAN_STARTED_AT = datetime(2026, 10, 18, 2, 0, tzinfo=UTC)


def test_command_exits_nonzero_when_scrape_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fail(*_: object, **__: object) -> None:
        raise AppError(ErrorCode.SCRAPE_SOURCE_ERROR)

    monkeypatch.setattr(sys, "argv", ["job-scout", "--category", "ict"])
    monkeypatch.setattr(scraper_main, "run_once", fail)
    with pytest.raises(SystemExit) as error:
        scraper_main.main()

    assert error.value.code == 1


def test_command_configures_shared_logging(monkeypatch: pytest.MonkeyPatch) -> None:
    configured: list[bool] = []

    async def complete(*_: object) -> int:
        return 0

    monkeypatch.setattr(sys, "argv", ["job_scout_scrape", "--category", "ict"])
    monkeypatch.setattr(scraper_main, "run_once", complete)
    monkeypatch.setattr(scraper_main, "configure_logging", lambda: configured.append(True))

    with pytest.raises(SystemExit) as result:
        scraper_main.main()

    assert result.value.code == 0
    assert configured == [True]


async def test_discover_phase_prints_scan_timestamp(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    async def discover(_: str, __: str) -> str:
        return SCAN_STARTED_AT.isoformat()

    monkeypatch.setattr(scraper_main, "discover_phase", discover)

    assert await scraper_main.run_once("ict", "discover") == 0
    assert capsys.readouterr().out.strip() == SCAN_STARTED_AT.isoformat()


async def test_reconcile_phase_without_timestamp_logs_catalog_message(
    caplog: pytest.LogCaptureFixture,
) -> None:
    assert await scraper_main.run_once("ict", "reconcile") == 1
    assert "Scan timestamp is missing or invalid." in caplog.text


async def test_value_error_from_a_phase_is_not_reported_as_a_timestamp_problem(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    async def enrich(_: str, __: str) -> None:
        raise ValueError("unrelated bug")

    monkeypatch.setattr(scraper_main, "enrich_phase", enrich)

    assert await scraper_main.run_once("ict", "enrich") == 1
    assert "Scraper stopped unexpectedly" in caplog.text
    assert "timestamp" not in caplog.text


async def test_enrich_phase_returns_failure_when_drafts_remain_failed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def enrich(_: str, __: str) -> SimpleNamespace:
        return SimpleNamespace(fetched=2, accredited=1, not_accredited=0, failed=1)

    monkeypatch.setattr(scraper_main, "enrich_phase", enrich)

    assert await scraper_main.run_once("ict", "enrich") == 1


@pytest.mark.parametrize(("failed", "expected"), [(0, 0), (2, 1)])
async def test_full_run_exits_nonzero_when_listings_failed(
    monkeypatch: pytest.MonkeyPatch, failed: int, expected: int
) -> None:
    async def run_all(_: str, __: str) -> SimpleNamespace:
        return SimpleNamespace(fetched=2, accredited=0, not_accredited=0, failed=failed)

    monkeypatch.setattr(scraper_main, "run_all_phases", run_all)

    assert await scraper_main.run_once("ict", "all") == expected


class _Session:
    def __init__(self, category: SimpleNamespace | None) -> None:
        self.category = category

    async def __aenter__(self) -> _Session:
        return self

    async def __aexit__(self, *_: object) -> None:
        return None

    async def scalar(self, *_: object) -> SimpleNamespace | None:
        return self.category


async def test_phases_reject_unknown_category(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(phases, "session_factory", lambda: _Session(None))

    with pytest.raises(AppError) as error:
        await phases.discover_phase("missing")

    assert error.value.code is ErrorCode.CATEGORY_NOT_FOUND


async def test_reconcile_phase_passes_parsed_timestamp(monkeypatch: pytest.MonkeyPatch) -> None:
    category_id = uuid4()
    seen: list[tuple[object, datetime]] = []

    async def reconcile(
        _: object, found_id: object, scan_started_at: datetime, source: str
    ) -> None:
        seen.append((found_id, scan_started_at, source))

    monkeypatch.setattr(
        phases, "session_factory", lambda: _Session(SimpleNamespace(id=category_id))
    )
    monkeypatch.setattr(phases, "reconcile_active_jobs", reconcile)

    await phases.reconcile_phase("ict", SCAN_STARTED_AT.isoformat())

    assert seen == [(category_id, SCAN_STARTED_AT, "seek")]


async def test_reconcile_phase_rejects_an_invalid_timestamp(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(phases, "session_factory", lambda: _Session(SimpleNamespace(id=uuid4())))

    with pytest.raises(AppError) as error:
        await phases.reconcile_phase("ict", "not-a-date")

    assert error.value.code is ErrorCode.INVALID_SCAN_TIMESTAMP


async def test_the_source_option_reaches_the_phase(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[tuple[str, str]] = []

    async def run_all(slug: str, source: str) -> SimpleNamespace:
        seen.append((slug, source))
        return SimpleNamespace(fetched=1, accredited=1, not_accredited=0, failed=0)

    monkeypatch.setattr(scraper_main, "run_all_phases", run_all)

    assert await scraper_main.run_once("ict", "all", source="employmenthero") == 0
    assert seen == [("ict", "employmenthero")]
