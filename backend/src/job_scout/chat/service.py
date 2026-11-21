"""Answer a question by running the existing job services and writing the result from templates."""

import re
import time
from datetime import UTC, datetime, timedelta
from difflib import get_close_matches
from urllib.parse import urlencode
from uuid import UUID

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from job_scout.categories import service as categories
from job_scout.chat.llm import ask_model
from job_scout.chat.schemas import (
    ChatRequest,
    ChatResponse,
)
from job_scout.chat.understand import (
    FOLLOW_UP,
    GREETING,
    JOB_WORD,
    REFERENCE,
    STOPWORDS,
    Plan,
    understand,
)
from job_scout.config import settings
from job_scout.core.countries import COUNTRIES
from job_scout.core.rate_limit import RateLimiter
from job_scout.green_list import service as green_list
from job_scout.green_list.schemas import CountryRoutes
from job_scout.jobs import compare, locations, service, trends
from job_scout.jobs.schemas import JobListItem, JobQuery

EXAMPLES = (
    "- senior python jobs in Ireland with visa sponsorship above 80k\n"
    "- which country sponsors data engineers the most\n"
    "- is hiring growing in the Netherlands this month\n"
    "- where are the jobs located in Germany\n"
    "- how many jobs offer visa sponsorship per country\n"
    "- how to immigrate to New Zealand\n"
    "- is data engineer on the Green List in New Zealand\n"
    "- is New Zealand or Canada easier for a data engineer"
)
HELP = (
    "Hi! I can answer questions about the jobs on this site: searching, salaries, visa "
    "sponsorship, hiring trends and immigration routes. For example:\n" + EXAMPLES
)
QUESTION = re.compile(
    r"^(?:who|what|which|why|how|can|could|should|would|is|are|do|does|did|will)\b|\?$"
)
LEGAL = (
    "This is a summary, not legal advice; check the official immigration sites for current rules."
)
NEEDS_COUNTRY = (
    "Which country do you mean? Name it in your question (for example 'in Ireland') "
    "or pick one in the sidebar."
)
NEEDS_TITLE = (
    "Which job do you mean? For example: 'which country sponsors data engineers the most'."
)
NEEDS_ROLE = "Which job do you mean? For example: 'which country is easiest for a data engineer'."
OFF_TOPIC = (
    "I can only help with jobs and immigration on this site, so I can't answer that one. "
    "You could ask, for example:\n" + EXAMPLES
)
FORGOT = (
    "I don't remember earlier messages, so each question needs its own details. For example: "
    "'visa sponsorship jobs in Australia'."
)
NO_PLACE = "I couldn't find any open jobs in"
NO_MATCH = "No open jobs match"
UNSUPPORTED = "I couldn't find any open jobs for"
MAX_ROLES = 5
LABELS = {"seniority": "Level", "arrangement": "Arrangement", "work_type": "Work type"}


def _understood(plan: Plan) -> list[str]:
    parts = []
    for code in plan.countries or ([plan.country] if plan.country else []):
        parts.append(f"Country: {COUNTRIES[code].name}")
    whole_country = plan.intent in ("trend", "regions")  # these ignore title and filters
    if plan.title and not whole_country:
        parts.append(f"Title: {plan.title}")
    if plan.location and plan.intent == "search":
        parts.append(f"Location: {plan.location}")
    for key, value in {} if whole_country else plan.filters.items():
        if key == "visa":
            parts.append("Visa sponsorship offered")
        elif key == "min_salary":
            parts.append(f"Salary from {value:,}")
        else:
            parts.append(f"{LABELS[key]}: {', '.join(value)}")
    if plan.intent == "trend" or plan.days_given:
        parts.append(f"Last {max(plan.days, 7) if plan.intent == 'trend' else plan.days} days")
    return parts


def _covered() -> str:
    names = [country.name for country in COUNTRIES.values()]
    return ", ".join(names[:-1]) + f" and {names[-1]}"


def _jobs(count: int) -> str:
    return f"{count:,} open job{'s' * (count != 1)}"


async def _across(session: AsyncSession, plan: Plan) -> str:
    """Two or more named countries: their job counts side by side, with the question's filters."""
    names = [COUNTRIES[code].name for code in plan.countries]
    if not plan.title and not plan.filters:
        stats = {s.country: s for s in await compare.visa_by_country(session)}
        lines = [
            f"- {stats[code].country_name}: {_jobs(stats[code].open_jobs)}, "
            f"{stats[code].visa_sponsor:,} offer visa sponsorship"
            for code in plan.countries
        ]
    else:
        category_ids: dict[str, UUID] = {}
        for category in await categories.list_categories(session):
            category_ids.setdefault(category.country, category.id)
        lines = []
        for code in plan.countries:
            total = 0
            if code in category_ids:
                query = JobQuery(
                    limit=1, status="open", position=plan.title or None, **plan.filters
                )
                total = (await service.list_category_jobs(session, category_ids[code], query)).total
            lines.append(f"- {COUNTRIES[code].name}: {_jobs(total)}")
    hint = f"To compare immigration routes, ask 'is {names[0]} or {names[1]} easier to migrate to'."
    return f"{' vs '.join(names)}:\n" + "\n".join(lines) + f"\n{hint}"


async def _by_country(session: AsyncSession, plan: Plan) -> tuple[str, list[JobListItem]]:
    if not plan.title:
        if plan.filters.get("visa"):
            stats = sorted(await compare.visa_by_country(session), key=lambda s: -s.visa_sponsor)
            lines = [f"- {s.country_name}: {s.visa_sponsor} of {s.open_jobs} jobs" for s in stats]
            return "Open jobs that offer visa sponsorship, by country:\n" + "\n".join(lines), []
        return NEEDS_TITLE, []
    rows = (await compare.compare_job(session, plan.title)).countries
    if len(plan.countries) >= 2:
        rows = [row for row in rows if row.country in plan.countries]
    by_visa = bool(plan.filters.get("visa"))
    rows = sorted(rows, key=lambda c: (-c.visa_sponsor, -c.open_jobs) if by_visa else -c.open_jobs)
    if not any(row.open_jobs for row in rows):
        return f"No open jobs match '{plan.title}' in any country.", []
    lines = [
        f"- {c.country_name}: {c.open_jobs} open, {c.visa_sponsor} offer visa sponsorship"
        for c in rows
        if c.open_jobs
    ]
    return f"Open '{plan.title}' jobs by country:\n" + "\n".join(lines), []


def _short(text: str) -> str:
    """The first sentence, so a reply never ends mid-word."""
    return re.split(r"(?<=[.!?])\s", " ".join(text.split()), maxsplit=1)[0]


def _match_line(c: CountryRoutes) -> str:
    matches = f"{len(c.roles)} match{'es' * (len(c.roles) != 1)}" if c.roles else "none"
    return f"- {c.country_name}: {matches} on the {c.list_name}"


async def _between(session: AsyncSession, plan: Plan) -> str:
    names = " vs ".join(COUNTRIES[code].name for code in plan.countries)
    if plan.title:
        routes = [
            c
            for c in (await green_list.get_routes(session, plan.title)).countries
            if c.country in plan.countries
        ]
        routes.sort(key=lambda c: (-len(c.roles), c.country_name))
        lines = "\n".join(_match_line(c) for c in routes)
        return (
            f"{names} for '{plan.title}':\n{lines}\n"
            f"Counts show list matches, not how easy a route is. {LEGAL}"
        )
    blocks = [
        f"{COUNTRIES[code].name} ({COUNTRIES[code].occupation_list_name}):\n"
        + "\n".join(f"- {route}" for route in COUNTRIES[code].general_routes)
        for code in plan.countries
    ]
    return (
        "I can't say which is easier: it depends on your job, salary and qualifications. "
        "Here are the main routes:\n\n"
        + "\n\n".join(blocks)
        + "\n\nName a job to compare list matches, for example "
        f"'is {names.lower().replace(' vs ', ' or ')} easier for a data engineer'. {LEGAL}"
    )


async def _immigration(session: AsyncSession, plan: Plan) -> str:
    if len(plan.countries) >= 2:
        return await _between(session, plan)
    if plan.country is None:  # "which country ...": rank every country for the role
        if not plan.title:
            return NEEDS_ROLE
        routes = (await green_list.get_routes(session, plan.title)).countries
        routes.sort(key=lambda c: (-len(c.roles), c.country_name))
        lines = [_match_line(c) for c in routes]
        return (
            f"Immigration routes for '{plan.title}':\n"
            + "\n".join(lines)
            + "\nCounts show list matches, not how easy a route is. This is a summary, not legal "
            "advice. Ask about one country for its routes."
        )
    country = COUNTRIES[plan.country]
    general = [f"- {route}" for route in country.general_routes]
    advice = (
        f"This is a summary, not legal advice; check {country.immigration_body} for current rules."
    )
    if not plan.title:
        return (
            f"{country.name}: the main routes are\n"
            + "\n".join(general)
            + f"\nPriority list: {country.occupation_list_name}. To check a job, ask for example "
            f"'what are the routes for a data engineer in {country.name}'.\n{advice}"
        )
    match = next(
        c
        for c in (await green_list.get_routes(session, plan.title)).countries
        if c.country == plan.country
    )
    if not match.roles:
        head = f"{country.name}: '{plan.title}' isn't on the {country.occupation_list_name}."
        return head + "\nOther routes:\n" + "\n".join(general) + f"\n{advice}"
    shown = match.roles[:MAX_ROLES]
    roles = [f"- {role.title} ({role.code})" for role in shown]
    # Roles on one list usually share the same pathway text, so each distinct one is said once.
    pathways = list(dict.fromkeys(_short(role.pathway) for role in shown if role.pathway))
    head = (
        f"{country.name}: '{plan.title}' matches {len(match.roles)} "
        f"on the {country.occupation_list_name}:"
    )
    return (
        head
        + "\n"
        + "\n".join(roles)
        + "".join(f"\n{pathway}" for pathway in pathways)
        + "\nOther routes:\n"
        + "\n".join(general)
        + f"\n{advice}"
    )


def _jobs_page(category_id: UUID, query: JobQuery) -> str:
    """The jobs page with this search prefilled. The page has no level filter, so it is left out."""
    fields = query.model_dump(
        include={
            "position",
            "location",
            "arrangement",
            "work_type",
            "visa",
            "min_salary",
            "listed_from",
        },
        exclude_defaults=True,
        mode="json",
    )
    return f"/categories/{category_id}?" + urlencode({"status": "open", **fields}, doseq=True)


def _condition(plan: Plan, key: str) -> str:
    if key == "window":
        return f"listed in the last {plan.days} day{'s' * (plan.days != 1)}"
    value = plan.filters[key]
    if key == "visa":
        return "Visa sponsorship offered"
    if key == "min_salary":
        return f"Salary from {value:,}"
    return f"{LABELS[key]}: {', '.join(value)}"


async def _explain_no_match(session, plan: Plan, category_id: UUID, name: str, query) -> str:
    """Say which condition removed every job, by counting the jobs left when each is dropped."""
    conditions = [*plan.filters, *(["window"] if plan.days_given else [])]
    freed = []
    for key in conditions:
        total = (
            await service.list_category_jobs(
                session, category_id, query(plan.title, plan.location, skip=key)
            )
        ).total
        if total:
            freed.append(f"- Without {_condition(plan, key)}: {_jobs(total)}")
    what = f"'{plan.title}'" if plan.title else "that"
    if not freed:
        return f"{name}: {NO_MATCH} {what}."
    return (
        f"{name}: no open jobs match all of {what}. Dropping one condition would find:\n"
        + "\n".join(freed)
    )


async def _search(
    session: AsyncSession, plan: Plan, category_id: UUID, name: str, vague: bool
) -> tuple[str | None, list[JobListItem], str | None]:
    """Reply, jobs and a link to all of them; a None reply means a likely non-search question."""

    def query(title: str, location: str = "", skip: str | None = None) -> JobQuery:
        windowed = plan.days_given and skip != "window"
        since = (datetime.now(UTC) - timedelta(days=plan.days)).date() if windowed else None
        return JobQuery(
            limit=5,
            status="open",
            position=title[:100] or None,
            location=location or None,
            listed_from=since,
            **{k: v for k, v in plan.filters.items() if k != skip},
        )

    used = query(plan.title, plan.location)
    result = await service.list_category_jobs(session, category_id, used)
    if not result.total and plan.location:
        # "in tech" is not a place after all, so read those words as part of the title.
        used = query(f"{plan.title} {plan.location}".strip())
        result = await service.list_category_jobs(session, category_id, used)
        if not result.total:
            reply = (
                f"{NO_PLACE} '{plan.location}'. I only cover jobs in {_covered()}. "
                "If it is a city, check the spelling."
            )
            return reply, [], None
    words = plan.title.split()
    if not result.total and len(words) > 1:
        # The title is matched as one phrase; fall back to its longest word.
        used = query(max(words, key=len))
        result = await service.list_category_jobs(session, category_id, used)
    window = (
        f" listed in the last {plan.days} day{'s' * (plan.days != 1)}" if plan.days_given else ""
    )
    if not result.total:
        if vague:
            return None, [], None
        return await _explain_no_match(session, plan, category_id, name, query), [], None
    more = _jobs_page(category_id, used) if result.total > len(result.items) else None
    return (
        f"{name}: Found {result.total} open jobs{window}. The newest {len(result.items)}:",
        result.items,
        more,
    )


async def _respond(
    session: AsyncSession, plan: Plan, message: str, default_country: str | None
) -> ChatResponse:
    named = plan.country is not None
    vague = bool(plan.title) and not plan.filters and not named
    vague = vague and bool(QUESTION.search(message.strip().lower()) or len(plan.title.split()) >= 4)
    uses_default = plan.intent in ("trend", "regions", "search") or (
        plan.intent == "immigration" and not plan.across
    )
    if uses_default and default_country in COUNTRIES:
        plan.country = plan.country or default_country
    understood = _understood(plan)
    if plan.intent == "help":
        return ChatResponse(reply=HELP, understood=[], jobs=[])
    if plan.intent == "immigration" and plan.location and not plan.countries:
        reply = f"I don't have immigration information for '{plan.location}'. I cover {_covered()}."
        return ChatResponse(reply=reply, understood=[], jobs=[])
    if plan.intent == "immigration":
        if plan.country is None and not plan.across:
            return ChatResponse(reply=NEEDS_COUNTRY, understood=understood, jobs=[])
        reply = await _immigration(session, plan)
        return ChatResponse(reply=reply, understood=understood, jobs=[])
    if (
        plan.intent == "compare"
        and len(plan.countries) >= 2
        and not (plan.title and not plan.filters)
    ):
        return ChatResponse(reply=await _across(session, plan), understood=understood, jobs=[])
    if plan.intent in ("compare", "visa"):
        reply, jobs = await _by_country(session, plan)
        return ChatResponse(reply=reply, understood=understood, jobs=jobs)

    category = next(
        (c for c in await categories.list_categories(session) if c.country == plan.country), None
    )
    if category is None:
        return ChatResponse(reply=NEEDS_COUNTRY, understood=understood, jobs=[])
    name = COUNTRIES[plan.country].name
    jobs: list[JobListItem] = []
    more: str | None = None
    if plan.intent == "trend":
        days = max(plan.days, 7)  # a trend needs at least a week of history
        points = (await trends.get_trends(session, category.id, days)).points
        if not points:
            reply = f"No job history for {name} in the last {days} days yet."
        else:
            reply = (
                f"{name}: open jobs went from {points[0].total_open} to {points[-1].total_open} "
                f"({points[-1].total_open - points[0].total_open:+,}) in the last {days} days."
            )
    elif plan.intent == "regions":
        regions = (await locations.get_location_breakdown(session, category.id)).regions[:5]
        lines = [f"- {r.region}: {r.count}" for r in regions]
        reply = f"Where the open jobs in {name} are:\n" + "\n".join(lines)
    else:
        reply, jobs, more = await _search(session, plan, category.id, name, vague)
        if reply is None:
            reply = (
                f"{UNSUPPORTED} '{plan.title}', and I'm not sure I understood the question. "
                f"I cover jobs in {_covered()}. You could try:\n{EXAMPLES}"
            )
            return ChatResponse(reply=reply, understood=[], jobs=[])
    return ChatResponse(reply=reply, understood=understood, jobs=jobs, more_url=more)


# Without a signal there is nothing to interpret, and a model call would only cost a request.
SIGNAL = re.compile(
    r"\b(jobs?|roles?|work\w*|hir\w+|salar\w+|pay\w*|visas?|sponsor\w*|career\w*|vacanc\w+"
    r"|positions?|employ\w+|openings?|immigrat\w*|migrat\w*|green list|routes?)\b"
)
_title_words: tuple[float, set[str]] = (float("-inf"), set())


async def _known_title_words(session: AsyncSession) -> set[str]:
    """Every word used in a job title on the site, cached briefly; real data, not a typed list."""
    global _title_words
    if time.monotonic() - _title_words[0] > settings.chat_vocab_ttl:
        rows = await session.scalars(
            text(
                "select distinct w from job, regexp_split_to_table(lower(position), "
                "'[^a-z0-9+#.]+') as w where length(w) > 2"
            )
        )
        _title_words = (time.monotonic(), set(rows))
    return _title_words[1]


async def _fix_title(session: AsyncSession, title: str) -> str:
    """Snap a misspelt title word ("pythn") to a close word used in real job titles."""
    if not title:
        return title
    known = await _known_title_words(session)
    words = []
    for word in title.split():
        close = [] if len(word) < 5 or word in known else get_close_matches(word, known, 1, 0.8)
        words.append(close[0] if close else word)
    return " ".join(words)


async def _has_signal(session: AsyncSession, plan: Plan, message: str) -> bool:
    if (
        plan.countries
        or plan.filters
        or plan.days_given
        or plan.intent not in ("search", "help")
        or SIGNAL.search(message.lower())
    ):
        return True
    words = set(re.findall(r"[a-z0-9+#.]+", message.lower())) - STOPWORDS  # "the" is in titles too
    return bool(words & await _known_title_words(session))


def _unclear(plan: Plan, reply: ChatResponse, message: str) -> bool:
    """The keyword rules did not get a real answer, so a model may read the question better."""
    text = reply.reply
    if plan.intent == "help":
        return not GREETING.search(message.lower())
    if text.startswith((NEEDS_COUNTRY, NEEDS_TITLE, NEEDS_ROLE, UNSUPPORTED)) or NO_MATCH in text:
        return True
    # An immigration role that is on no country's list is usually a misread, not a real role.
    return (
        plan.intent == "immigration"
        and bool(plan.title)
        and (
            "isn't on the" in text
            or (": none on the" in text and not re.search(r": \d+ match", text))
        )
    )


model_limiter = RateLimiter()  # one model call per `llm_min_interval`, for the whole app


def _merge(base: Plan, new: Plan, message: str) -> Plan:
    """A follow-up fills what it leaves out from the question before it; what it says wins."""
    countries = new.countries or base.countries
    note = ""
    if not new.countries and len(countries) > 1 and new.intent in ("help", "search"):
        names = " and ".join(COUNTRIES[code].name for code in countries)
        note = f"You named {names}, so I'm showing {COUNTRIES[countries[0]].name}.\n"
        countries = countries[:1]
    if new.intent not in ("help", "search"):
        intent = new.intent
    else:
        # "how about software engineer" swaps the job in the same question; "show me jobs" lists.
        # A trend or location answer has no title, so naming one asks for a search instead.
        intent = base.intent
        if JOB_WORD.search(message.lower()) or (new.title and intent in ("trend", "regions")):
            intent = "search"
    return Plan(
        intent,
        country=countries[0] if countries else None,
        countries=countries,
        across=new.across or base.across,
        title=new.title or base.title,
        days=new.days if new.days_given else base.days,
        days_given=new.days_given or base.days_given,
        filters={**base.filters, **new.filters},
        location=new.location or base.location,
        note=note,
    )


def _read_with_context(earlier: list[str], message: str) -> tuple[Plan, bool]:
    """Read the message, folding in the earlier ones it builds on; also whether any was used."""
    plan, used = understand(earlier[0]) if earlier else None, False
    for said in [*earlier[1:], message]:
        new = understand(said)
        if plan is not None and FOLLOW_UP.search(said.lower()):
            plan, used = _merge(plan, new, said), True
        else:
            plan, used = new, False
    return plan or understand(message), used


async def answer(
    session: AsyncSession, request: ChatRequest, llm: httpx.AsyncClient | None = None
) -> ChatResponse:
    plan, used_context = _read_with_context(request.earlier, request.message)
    plan.title = await _fix_title(session, plan.title)
    if not plan.countries and not plan.across:
        # The country last talked about beats the sidebar's: "i ask for remote jobs" stays put.
        for said in reversed(request.earlier):
            if named := understand(said).countries:
                plan.country, plan.countries = named[0], named[:1]
                break
    if plan.intent == "help" and GREETING.search(request.message.lower()):
        return ChatResponse(reply=HELP, understood=[], jobs=[])
    if (
        not used_context
        and REFERENCE.search(request.message.lower())
        and not (plan.countries or plan.title or plan.filters or plan.location or plan.days_given)
    ):
        return ChatResponse(reply=FORGOT, understood=[], jobs=[])
    if not await _has_signal(session, plan, request.message):  # nothing to do with the app
        return ChatResponse(reply=OFF_TOPIC, understood=[], jobs=[])
    reply = await _respond(session, plan, request.message, request.country)
    if (
        llm
        and settings.llm_model
        and _unclear(plan, reply, request.message)
        and model_limiter.allow(interval=settings.llm_min_interval)
    ):
        rescued = await ask_model(llm, request.message)
        if rescued is not None and rescued.intent == "help":
            reply = ChatResponse(reply=OFF_TOPIC, understood=[], jobs=[])
        elif rescued is not None:
            reply = await _respond(session, rescued, request.message, request.country)
    if plan.note:
        reply = reply.model_copy(update={"reply": plan.note + reply.reply})
    return reply
