import logging

import pytest

from job_scout.core.logging import LOG_FORMAT, configure_logging
from job_scout.main import app, lifespan


def _capture_basic_config(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, object]]:
    calls: list[dict[str, object]] = []
    monkeypatch.setattr(logging, "basicConfig", lambda **kwargs: calls.append(kwargs))
    return calls


def test_configure_logging_uses_shared_format_and_default_info_level(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = _capture_basic_config(monkeypatch)

    configure_logging()

    assert calls == [{"level": "INFO", "format": LOG_FORMAT}]


def test_configure_logging_accepts_a_level_override(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _capture_basic_config(monkeypatch)

    configure_logging("debug")

    assert calls[0]["level"] == "DEBUG"


async def test_api_startup_configures_logging(monkeypatch: pytest.MonkeyPatch) -> None:
    configured: list[bool] = []
    monkeypatch.setattr("job_scout.main.configure_logging", lambda: configured.append(True))

    async with lifespan(app):
        assert configured == [True]
