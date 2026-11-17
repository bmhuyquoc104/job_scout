import json
from datetime import UTC, datetime

import httpx
import pytest

from job_scout.config import settings
from job_scout.notifications.service import (
    PolicyResult,
    RunResult,
    notify_policy,
    notify_run,
    render_policy_summary,
    render_summary,
    send,
)

START, END = 1_000_000, 1_000_000 + 2 * 3600 + 41 * 60
ISO_END = datetime.fromtimestamp(END, UTC).isoformat()


def test_success_embed_shows_counts_per_source() -> None:
    results = [
        RunResult("job_scout_seek_daily", "success", new=42, closed=10),
        RunResult("job_scout_employmenthero_daily", "success", new=5, closed=1),
    ]
    payload = render_summary(results, START, END, mention_user_id="42")
    embed = payload["embeds"][0]
    assert payload["content"] == ""  # no ping when everything worked
    assert embed["title"] == "✅ Scrape finished: all 2 DAGs succeeded"
    assert embed["color"] == 0xA6E3A1
    assert embed["description"].startswith("**+47 new · −11 closed**")
    assert "employmenthero   +5     −1" in embed["description"]
    assert "seek             +42    −10" in embed["description"]
    assert embed["footer"]["text"] == "2/2 DAGs ok · Duration 2h 41m"
    assert embed["timestamp"] == ISO_END


def test_failure_embed_pings_and_lists_failures() -> None:
    results = [
        RunResult("job_scout_indeed_daily", "failed"),
        RunResult("job_scout_seek_daily", "timeout"),
        RunResult("job_scout_x_daily", "success"),
    ]
    payload = render_summary(results, START, END, mention_user_id="42")
    embed = payload["embeds"][0]
    assert payload["content"] == "<@42>"
    assert embed["title"] == "❌ Scrape: 2 of 3 DAGs failed"
    assert embed["color"] == 0xF38BA8
    assert "• indeed: failed\n• seek: timeout" in embed["description"]
    assert embed["footer"]["text"] == "1/3 DAGs ok · Duration 2h 41m"


def test_failure_without_mention_id_has_no_ping() -> None:
    payload = render_summary([RunResult("a", "failed")], START, END, mention_user_id="")
    assert payload["content"] == ""


def test_failure_list_is_capped() -> None:
    results = [RunResult(f"dag{i}", "failed") for i in range(13)]
    embed = render_summary(results, START, END, mention_user_id="")["embeds"][0]
    assert embed["description"].count("•") == 10
    assert "+3 more" in embed["description"]


def test_policy_embed_lists_each_country() -> None:
    results = [
        PolicyResult("NZ", baseline=False),
        PolicyResult("AU", baseline=False, created=3, removed=1),
        PolicyResult("IE", baseline=True),
        PolicyResult("CA", baseline=False, tier_changed=2, restored=1),
    ]
    embed = render_policy_summary(results, END)["embeds"][0]
    assert embed["title"] == "📋 Immigration policy sync"
    assert embed["description"] == (
        "• **AU**: 3 new · 1 removed\n"
        "• **CA**: 2 tier changes · 1 restored\n"
        "• **IE**: first sync, baseline stored\n"
        "• **NZ**: no changes"
    )
    assert embed["footer"]["text"] == "4 countries checked · 2 with changes"
    assert embed["timestamp"] == ISO_END


def test_policy_embed_with_no_changes() -> None:
    embed = render_policy_summary([PolicyResult("NZ", baseline=False)], END)["embeds"][0]
    assert embed["footer"]["text"] == "1 country checked · no changes"


async def test_send_posts_payload_and_limits_mentions() -> None:
    seen: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(json.loads(request.content))
        return httpx.Response(204)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        assert await send({"content": "hi"}, "https://discord.test/hook", client) is True
    assert seen == [{"content": "hi", "allowed_mentions": {"parse": ["users"]}}]


async def test_send_swallows_http_errors() -> None:
    transport = httpx.MockTransport(lambda request: httpx.Response(500))
    async with httpx.AsyncClient(transport=transport) as client:
        assert await send({"content": "hi"}, "https://discord.test/hook", client) is False


async def test_notify_run_skips_without_webhook(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "discord_webhook_url", "")
    assert await notify_run([RunResult("seek", "success")], START, END) is False


async def test_notify_functions_post_embeds(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "discord_webhook_url", "https://discord.test/hook")
    seen: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(json.loads(request.content))
        return httpx.Response(204)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        assert await notify_run([RunResult("job_scout_seek_daily", "success")], START, END, client)
        assert await notify_policy([PolicyResult("NZ", baseline=False)], END, client)
    assert [p["embeds"][0]["title"][:1] for p in seen] == ["✅", "📋"]
