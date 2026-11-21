import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import httpx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from job_scout.config import settings
from job_scout.jobs.models import Job, JobEvent, JobEventType

logger = logging.getLogger(__name__)

MAX_LISTED_FAILURES = 10
# Catppuccin Mocha green, red and blue, to match the app's theme.
GREEN, RED, BLUE = 0xA6E3A1, 0xF38BA8, 0x89B4FA


@dataclass(frozen=True)
class RunResult:
    dag: str
    state: str
    new: int = 0
    closed: int = 0
    visa: int = 0  # of the new jobs, those offering visa sponsorship


@dataclass(frozen=True)
class PolicyResult:
    country: str
    baseline: bool
    created: int = 0
    tier_changed: int = 0
    removed: int = 0
    restored: int = 0


def _source(dag: str) -> str:
    return dag.removeprefix("job_scout_").removesuffix("_daily")


def _duration(seconds: int) -> str:
    hours, minutes = divmod(max(seconds, 0) // 60, 60)
    return f"{hours}h {minutes:02d}m" if hours else f"{minutes}m"


def _iso(epoch: int) -> str:
    return datetime.fromtimestamp(epoch, UTC).isoformat()


def render_summary(
    results: list[RunResult], started: int, finished: int, mention_user_id: str
) -> dict[str, Any]:
    failed = sorted((r for r in results if r.state != "success"), key=lambda r: r.dag)
    ok = len(results) - len(failed)
    footer = f"{ok}/{len(results)} DAGs ok · Duration {_duration(finished - started)}"
    if failed:
        lines = [f"• {_source(r.dag)}: {r.state}" for r in failed[:MAX_LISTED_FAILURES]]
        if len(failed) > MAX_LISTED_FAILURES:
            lines.append(f"+{len(failed) - MAX_LISTED_FAILURES} more")
        embed = {
            "title": f"❌ Scrape: {len(failed)} of {len(results)} DAGs failed",
            "description": "\n".join(lines),
            "color": RED,
        }
        content = f"<@{mention_user_id}>" if mention_user_id else ""
    else:
        table = "\n".join(
            f"{_source(r.dag):<16} {'+' + str(r.new):<6} {'🛂' + str(r.visa):<5} −{r.closed}"
            for r in sorted(results, key=lambda r: r.dag)
        )
        total_new, total_closed = sum(r.new for r in results), sum(r.closed for r in results)
        total_visa = sum(r.visa for r in results)
        embed = {
            "title": f"✅ Scrape finished: all {len(results)} DAGs succeeded",
            "description": (
                f"**+{total_new} new · {total_visa} with visa · −{total_closed} closed**"
                f"\n```\n{table}\n```"
            ),
            "color": GREEN,
        }
        content = ""
    embed |= {"footer": {"text": footer}, "timestamp": _iso(finished)}
    return {"content": content, "embeds": [embed]}


def _policy_line(result: PolicyResult) -> str:
    if result.baseline:
        return f"• **{result.country}**: first sync, baseline stored"
    changes = [
        f"{result.created} new" if result.created else "",
        f"{result.tier_changed} tier change{'s' * (result.tier_changed != 1)}"
        if result.tier_changed
        else "",
        f"{result.removed} removed" if result.removed else "",
        f"{result.restored} restored" if result.restored else "",
    ]
    return f"• **{result.country}**: {' · '.join(c for c in changes if c) or 'no changes'}"


def render_policy_summary(results: list[PolicyResult], finished: int) -> dict[str, Any]:
    ordered = sorted(results, key=lambda r: r.country)
    changed = sum(
        1
        for r in ordered
        if not r.baseline and (r.created or r.tier_changed or r.removed or r.restored)
    )
    countries = f"{len(ordered)} {'country' if len(ordered) == 1 else 'countries'} checked"
    embed = {
        "title": "📋 Immigration policy sync",
        "description": "\n".join(_policy_line(r) for r in ordered),
        "color": BLUE,
        "footer": {
            "text": f"{countries} · {f'{changed} with changes' if changed else 'no changes'}"
        },
        "timestamp": _iso(finished),
    }
    return {"content": "", "embeds": [embed]}


async def event_counts(
    since: datetime, session_factory: async_sessionmaker[AsyncSession] | None = None
) -> dict[str, tuple[int, int, int]]:
    """Per source: (new, closed, new with visa sponsorship) job events since `since`."""
    from job_scout.database import session_factory as default_session_factory

    statement = (
        select(
            Job.source,
            JobEvent.event_type,
            func.count(),
            func.count().filter(Job.visa_sponsor.is_(True)),
        )
        .join(Job, Job.id == JobEvent.job_id)
        .where(
            JobEvent.occurred_at >= since,
            JobEvent.event_type.in_([JobEventType.NEW, JobEventType.CLOSED]),
        )
        .group_by(Job.source, JobEvent.event_type)
    )
    async with (session_factory or default_session_factory)() as session:
        rows = (await session.execute(statement)).all()
    counts: dict[str, list[int]] = {}
    for source, event_type, count, visa in rows:
        entry = counts.setdefault(source, [0, 0, 0])
        if event_type == JobEventType.CLOSED:
            entry[1] = count
        else:
            entry[0], entry[2] = count, visa
    return {source: (new, closed, visa) for source, (new, closed, visa) in counts.items()}


async def run_results(
    dags: list[str], started: int, session_factory: async_sessionmaker[AsyncSession] | None = None
) -> list[RunResult]:
    """A success result for each DAG, with the jobs it added and closed since the run began."""
    counts = await event_counts(datetime.fromtimestamp(started, UTC), session_factory)
    return [RunResult(dag, "success", *counts.get(_source(dag), (0, 0, 0))) for dag in dags]


async def send(payload: dict[str, Any], webhook_url: str, client: httpx.AsyncClient) -> bool:
    """Post to Discord. Never raises: a failed alert must not fail the scrape."""
    try:
        # Only user mentions may ping, so a DAG name can never trigger @everyone.
        response = await client.post(
            webhook_url, json={**payload, "allowed_mentions": {"parse": ["users"]}}
        )
        response.raise_for_status()
    except httpx.HTTPError as error:
        logger.warning("Discord notification failed: %s", type(error).__name__)
        return False
    return True


async def _post(payload: dict[str, Any], client: httpx.AsyncClient | None) -> bool:
    if not settings.discord_webhook_url:
        logger.info("DISCORD_WEBHOOK_URL is not set; skipping notification")
        return False
    if client is not None:
        return await send(payload, settings.discord_webhook_url, client)
    async with httpx.AsyncClient(timeout=10) as own_client:
        return await send(payload, settings.discord_webhook_url, own_client)


async def notify_run(
    results: list[RunResult], started: int, finished: int, client: httpx.AsyncClient | None = None
) -> bool:
    """Send the run summary to Discord; skipped when no webhook is configured."""
    payload = render_summary(results, started, finished, settings.discord_mention_user_id)
    return await _post(payload, client)


async def notify_policy(
    results: list[PolicyResult], finished: int, client: httpx.AsyncClient | None = None
) -> bool:
    return await _post(render_policy_summary(results, finished), client)
