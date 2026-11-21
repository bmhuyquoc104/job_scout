"""Rescue a question the keyword rules cannot read: ask a model to fill in the same plan.

The model only turns the question into a plan; the answer is still written from your own data,
so it cannot invent jobs or rules. Its output is validated and any failure returns None.
"""

import logging
from typing import Literal

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from job_scout.chat.understand import Plan
from job_scout.config import settings
from job_scout.core.countries import COUNTRIES

logger = logging.getLogger(__name__)


class LlmFilters(BaseModel):
    model_config = ConfigDict(extra="forbid")  # strict JSON schemas need every field required

    seniority: list[Literal["graduate", "junior", "mid", "senior", "lead"]]
    arrangement: list[Literal["Remote", "Hybrid", "On-site"]]
    work_type: list[Literal["Full time", "Part time", "Contract/Temp"]]
    visa_sponsorship: bool
    min_salary: int | None


class LlmPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    intent: Literal["search", "compare", "trend", "regions", "immigration", "help"]
    countries: list[Literal[*COUNTRIES]]
    title: str = Field(max_length=80)
    days: int | None
    filters: LlmFilters


SYSTEM = (
    "You turn one question about jobs and immigration into JSON. You never answer it.\n"
    "intent: search (find jobs), compare (compare countries for jobs), trend (is hiring growing "
    "or shrinking), regions (where jobs are located), immigration (visa routes, migrating, "
    "priority occupation lists), help (anything else).\n"
    "countries: codes of the countries named, in order, from "
    + ", ".join(f"{code}={country.name}" for code, country in COUNTRIES.items())
    + ". A nationality or short form such as 'ire' or 'kiwi' means its country. Use [] if none.\n"
    "title: only the job role words, lowercase, such as 'data engineer'; empty if none.\n"
    "days: the time window in days if the question gives one, else null.\n"
    "filters: seniority, arrangement and work_type lists (empty if not asked), visa_sponsorship "
    "true only when asking for jobs that sponsor visas, min_salary a yearly integer or null."
)


def to_plan(plan: LlmPlan) -> Plan:
    countries = list(dict.fromkeys(plan.countries))
    title = plan.title.strip().lower()
    filters: dict[str, object] = {}
    if plan.filters.seniority:
        filters["seniority"] = plan.filters.seniority
    if plan.filters.visa_sponsorship:
        filters["visa"] = "offered"
    if plan.filters.min_salary is not None and 1000 <= plan.filters.min_salary <= 10_000_000:
        filters["min_salary"] = plan.filters.min_salary
    if plan.filters.arrangement:
        filters["arrangement"] = plan.filters.arrangement
    if plan.filters.work_type:
        filters["work_type"] = plan.filters.work_type
    intent = plan.intent
    if intent == "compare" and not title and filters.get("visa") and len(countries) < 2:
        intent = "visa"  # "how many jobs sponsor visas per country"
    return Plan(
        intent,
        country=countries[0] if countries else None,
        countries=countries,
        across=intent in ("compare", "immigration") and not countries,
        title=title,
        days=min(max(plan.days, 7), 365) if plan.days is not None else 30,
        days_given=plan.days is not None,
        filters=filters,
    )


async def ask_model(client: httpx.AsyncClient, message: str) -> Plan | None:
    body = {
        "model": settings.llm_model,
        "temperature": 0,
        "max_tokens": 400,
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": message},
        ],
        "response_format": {
            "type": "json_schema",
            "json_schema": {"name": "plan", "strict": True, "schema": LlmPlan.model_json_schema()},
        },
        # OpenRouter: only route to hosts that honour the schema.
        "provider": {"require_parameters": True},
    }
    try:
        response = await client.post("/chat/completions", json=body)
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        return to_plan(LlmPlan.model_validate_json(content))
    except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError, ValidationError) as exc:
        logger.warning("Model rescue failed: %r", exc)  # never the body: it holds the question
        return None
