import json
from contextlib import asynccontextmanager

import httpx
import pytest
from freezegun import freeze_time
from httpx import AsyncClient

from job_scout.categories.models import Category
from job_scout.chat.router import get_llm_client
from job_scout.config import settings
from job_scout.core.countries import COUNTRIES
from job_scout.core.rate_limit import RateLimiter
from job_scout.database import get_session
from job_scout.jobs.models import Job
from job_scout.main import app

Context = tuple[AsyncClient, Category, list[Job]]


async def _ask(client: AsyncClient, message: str, country: str | None = None) -> dict:
    response = await client.post("/api/chat", json={"message": message, "country": country})
    assert response.status_code == 200
    return response.json()


async def test_search_applies_the_filters_read_from_the_question(api_context: Context) -> None:
    client, category, jobs = api_context

    body = await _ask(client, "junior jobs with visa sponsorship", category.country)

    assert [job["id"] for job in body["jobs"]] == [str(jobs[1].id)]
    assert "Found 1 open jobs" in body["reply"]
    assert body["understood"] == [
        "Country: New Zealand",
        "Level: junior",
        "Visa sponsorship offered",
    ]


async def test_a_country_in_the_question_wins_over_the_default(api_context: Context) -> None:
    client, category, _ = api_context
    other = next(code for code in COUNTRIES if code != category.country)

    body = await _ask(client, f"jobs in {COUNTRIES[category.country].name}", other)

    assert len(body["jobs"]) == 2  # the two open jobs


async def test_search_asks_for_a_country_when_none_is_known(api_context: Context) -> None:
    client, _, _ = api_context

    body = await _ask(client, "python jobs")

    assert body["reply"].startswith("Which country do you mean?")
    assert body["jobs"] == []


async def test_no_matches_says_so(api_context: Context) -> None:
    client, category, _ = api_context

    body = await _ask(client, "kubernetes jobs", category.country)

    assert body["reply"] == "New Zealand: No open jobs match 'kubernetes'."


async def test_a_no_match_names_the_filter_that_removed_every_job(api_context: Context) -> None:
    client, category, _ = api_context

    body = await _ask(client, "junior jobs with visa sponsorship above 900k", category.country)

    assert "no open jobs match all of that" in body["reply"].lower()
    assert "Without Salary from 900,000: 1 open job" in body["reply"]


async def test_a_greeting_gets_the_list_of_example_questions(api_context: Context) -> None:
    client, _, _ = api_context

    body = await _ask(client, "hello")

    assert "For example:" in body["reply"]
    assert body["jobs"] == []


async def test_comparing_a_title_lists_countries_by_visa_sponsorship(api_context: Context) -> None:
    client, category, _ = api_context

    body = await _ask(client, "which country sponsors engineers the most", category.country)

    assert (
        f"- {COUNTRIES[category.country].name}: 2 open, 1 offer visa sponsorship" in body["reply"]
    )
    # The sidebar country is not a filter here, so it must not be reported as one.
    assert not any(part.startswith("Country:") for part in body["understood"])


async def test_visa_by_country_without_a_title(api_context: Context) -> None:
    client, category, _ = api_context

    body = await _ask(client, "how many jobs offer visa sponsorship per country")

    assert f"- {COUNTRIES[category.country].name}: 1 of 2 jobs" in body["reply"]


async def test_regions_lists_where_the_open_jobs_are(api_context: Context) -> None:
    client, category, _ = api_context

    body = await _ask(client, "where are the jobs located", category.country)

    assert "- Wellington: 1" in body["reply"]


@freeze_time("2026-10-21T12:00:00Z")
async def test_trend_summarises_opens_and_closes_in_the_window(api_context: Context) -> None:
    client, category, _ = api_context

    body = await _ask(client, "is hiring growing this month", category.country)

    assert body["reply"].startswith("New Zealand: open jobs went from")
    assert "in the last 30 days." in body["reply"]


async def test_an_empty_message_is_rejected(api_context: Context) -> None:
    client, _, _ = api_context

    response = await client.post("/api/chat", json={"message": "   "})

    assert response.status_code == 422


async def _add_role(title: str, country: str, **fields: object) -> None:
    from job_scout.green_list.models import GreenListRole

    opener = asynccontextmanager(app.dependency_overrides[get_session])
    async with opener() as session:
        session.add(
            GreenListRole(
                country=country,
                record_id=f"{country}-{title}",
                title=title,
                anzsco_code="261313",
                industry="ICT",
                raw={},
                **fields,
            )
        )
        await session.flush()


async def test_immigration_without_a_role_lists_the_main_routes(api_context: Context) -> None:
    client, _, _ = api_context

    body = await _ask(client, "how to immigrate to new zealand", "AU")

    assert "Accredited Employer Work Visa" in body["reply"]
    assert "Immigration New Zealand" in body["reply"]
    assert body["understood"] == ["Country: New Zealand"]
    assert body["jobs"] == []


async def test_immigration_with_a_role_shows_the_matching_list_entries(
    api_context: Context,
) -> None:
    client, _, _ = api_context
    await _add_role("Data Engineer", "NZ", tier=1, pathway="Straight to residence")

    body = await _ask(client, "is data engineer on the green list in new zealand", "AU")

    assert "- Data Engineer" in body["reply"]
    assert "Straight to residence" in body["reply"]
    assert "Accredited Employer Work Visa" in body["reply"]  # the other routes still follow


async def test_immigration_says_when_the_role_is_not_on_the_list(api_context: Context) -> None:
    client, _, _ = api_context

    body = await _ask(client, "is astronaut on the green list in new zealand", "AU")

    assert "isn't on the Green List" in body["reply"]
    assert "Accredited Employer Work Visa" in body["reply"]


async def test_immigration_across_countries_ranks_by_matching_roles(api_context: Context) -> None:
    client, _, _ = api_context
    await _add_role("Data Engineer", "NZ")

    body = await _ask(client, "which country is easiest to immigrate to as a data engineer", "AU")

    assert "- New Zealand: 1 match on the Green List" in body["reply"]
    assert body["reply"].index("New Zealand") < body["reply"].index("Ireland")
    assert body["understood"] == ["Title: data engineer"]  # the sidebar country is not a filter


async def test_across_countries_without_a_role_asks_for_one(api_context: Context) -> None:
    client, _, _ = api_context

    body = await _ask(client, "which country is easiest to immigrate to", "AU")

    assert body["reply"].startswith("Which job do you mean?")


async def test_between_two_countries_shows_the_routes_of_each(api_context: Context) -> None:
    client, _, _ = api_context

    body = await _ask(client, "which country is easier between new zealand and canada", "AU")

    assert body["reply"].startswith("I can't say which is easier")
    assert "New Zealand" in body["reply"]
    assert "Canada" in body["reply"]
    assert "Accredited Employer Work Visa" in body["reply"]
    assert "Australia" not in body["reply"]  # the sidebar country is not part of the question
    assert body["understood"] == ["Country: New Zealand", "Country: Canada"]


async def test_between_two_countries_for_a_role_compares_only_those(api_context: Context) -> None:
    client, _, _ = api_context
    await _add_role("Data Engineer", "NZ")

    body = await _ask(client, "is nz or canada easier for a data engineer", "AU")

    assert "- New Zealand: 1 match on the Green List" in body["reply"]
    assert "- Canada: none on" in body["reply"]
    assert "Ireland" not in body["reply"]


async def test_a_question_it_does_not_support_gets_help_instead_of_a_job_search(
    api_context: Context,
) -> None:
    client, _, _ = api_context

    body = await _ask(client, "how do i bake a cake", "NZ")

    assert body["reply"].startswith("I can only help with jobs and immigration")
    assert "You could ask, for example:" in body["reply"]
    assert "how to immigrate to New Zealand" in body["reply"]
    assert body["understood"] == []  # nothing was understood, so no filter chips


async def test_a_plain_job_search_with_no_result_is_not_called_unsupported(
    api_context: Context,
) -> None:
    client, _, _ = api_context

    body = await _ask(client, "kubernetes jobs", "NZ")

    assert body["reply"].startswith("New Zealand: No open jobs match")


async def test_the_pasted_question_with_abbreviations_gets_a_route_comparison(
    api_context: Context,
) -> None:
    client, _, _ = api_context

    body = await _ask(client, "which countries is easier to migrate to between can and ire", "AU")

    assert body["reply"].startswith("I can't say which is easier")
    assert "Ireland" in body["reply"]
    assert "Canada" in body["reply"]
    assert "Australia" not in body["reply"]
    assert body["understood"] == ["Country: Canada", "Country: Ireland"]


async def test_two_countries_without_a_topic_compare_their_job_counts(api_context: Context) -> None:
    client, _, _ = api_context

    body = await _ask(client, "jobs in new zealand and canada", "AU")

    assert "- New Zealand: 2 open jobs, 1 offer visa sponsorship" in body["reply"]
    assert "- Canada: 0 open jobs" in body["reply"]
    assert "Australia" not in body["reply"]


async def test_two_countries_with_filters_compare_the_matching_jobs(api_context: Context) -> None:
    client, _, _ = api_context

    body = await _ask(client, "junior jobs in new zealand or canada", "AU")

    assert "- New Zealand: 1 open job" in body["reply"]
    assert "- Canada: 0 open jobs" in body["reply"]
    assert body["understood"][:2] == ["Country: New Zealand", "Country: Canada"]


PLAN = {
    "intent": "search",
    "countries": ["NZ"],
    "title": "",
    "days": None,
    "filters": {
        "seniority": ["junior", "graduate"],
        "arrangement": [],
        "work_type": [],
        "visa_sponsorship": False,
        "min_salary": None,
    },
}
HELP_PLAN = {**PLAN, "intent": "help", "countries": []}
ROUGH_QUESTION = "any entry-level stuff in kiwi land"  # the keyword rules find no jobs for this


def _use_fake_model(*replies: object) -> list[dict]:
    """Serve `replies` in order: dict = the model's JSON, str = raw text, int = HTTP error."""
    received: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        received.append(json.loads(request.content))
        reply = replies[min(len(received), len(replies)) - 1]
        if isinstance(reply, int):
            return httpx.Response(reply, json={"error": "nope"})
        content = reply if isinstance(reply, str) else json.dumps(reply)
        return httpx.Response(200, json={"choices": [{"message": {"content": content}}]})

    async def client():
        async with httpx.AsyncClient(
            base_url="https://llm.test/v1", transport=httpx.MockTransport(handler)
        ) as fake:
            yield fake

    app.dependency_overrides[get_llm_client] = client
    return received


@pytest.fixture
def model_on(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "llm_model", "test-model")


async def test_without_a_model_nothing_changes(api_context: Context) -> None:
    client, _, _ = api_context

    body = await _ask(client, ROUGH_QUESTION, "AU")

    assert body["jobs"] == []  # no model configured: the keyword answer stands


async def test_the_model_rescues_a_question_the_keyword_rules_could_not_read(
    api_context: Context, model_on: None
) -> None:
    client, _, jobs = api_context
    received = _use_fake_model(PLAN)

    body = await _ask(client, ROUGH_QUESTION, "AU")

    assert [job["id"] for job in body["jobs"]] == [str(jobs[1].id)]
    assert body["understood"] == ["Country: New Zealand", "Level: junior, graduate"]
    request = received[0]
    assert request["model"] == "test-model"
    assert request["temperature"] == 0
    assert request["response_format"]["type"] == "json_schema"
    assert request["response_format"]["json_schema"]["strict"] is True
    assert request["provider"] == {"require_parameters": True}
    assert request["messages"][1] == {"role": "user", "content": ROUGH_QUESTION}


async def test_the_model_is_not_asked_when_the_keyword_rules_already_answered(
    api_context: Context, model_on: None
) -> None:
    client, category, _ = api_context
    received = _use_fake_model(PLAN)

    await _ask(client, "senior jobs", category.country)
    await _ask(client, "hello")
    await _ask(client, "kubernetes jobs", category.country)  # zero hits, but a plain search

    assert len(received) == 1  # only the zero-hit search with a title was worth a call


async def test_when_the_model_says_it_is_not_a_jobs_question_the_reply_says_so(
    api_context: Context, model_on: None
) -> None:
    client, _, _ = api_context
    received = _use_fake_model(HELP_PLAN)

    body = await _ask(client, "how do i work a coffee machine", "NZ")

    assert body["reply"].startswith("I can only help with jobs and immigration")
    assert body["understood"] == []
    assert len(received) == 1


@pytest.mark.parametrize("failure", [429, 500, "not json at all", {**PLAN, "countries": ["XX"]}])
async def test_a_failing_or_nonsense_model_falls_back_to_the_keyword_answer(
    api_context: Context, model_on: None, failure: object
) -> None:
    client, _, _ = api_context
    _use_fake_model(failure)

    response = await client.post("/api/chat", json={"message": ROUGH_QUESTION, "country": "AU"})

    assert response.status_code == 200
    assert response.json()["jobs"] == []
    assert "No open jobs match" in response.json()["reply"]


async def test_an_immigration_role_on_no_list_is_sent_to_the_model(
    api_context: Context, model_on: None
) -> None:
    client, _, _ = api_context
    received = _use_fake_model({**PLAN, "intent": "immigration", "countries": [], "title": "x"})

    await _ask(client, "which country has the easiest zzqq to immigrate to", "NZ")

    assert len(received) == 1


async def test_a_question_with_nothing_to_interpret_never_reaches_the_model(
    api_context: Context, model_on: None
) -> None:
    client, _, _ = api_context
    received = _use_fake_model(PLAN)

    body = await _ask(client, "what is the weather today in sai gon", "NZ")

    assert body["reply"].startswith("I can only help with jobs and immigration")
    assert received == []


async def test_a_very_long_question_does_not_crash_the_search(api_context: Context) -> None:
    client, category, _ = api_context

    body = await _ask(client, "work as " + "a very long role name " * 12, category.country)

    assert (
        "Found" in body["reply"]
        or "No open jobs" in body["reply"]
        or "couldn't find" in body["reply"]
    )


async def test_the_model_is_called_at_most_once_per_interval(
    api_context: Context, model_on: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "llm_min_interval", 60)
    monkeypatch.setattr("job_scout.chat.service.model_limiter", RateLimiter())
    client, _, _ = api_context
    received = _use_fake_model(PLAN)

    first = await _ask(client, ROUGH_QUESTION, "AU")
    second = await _ask(client, ROUGH_QUESTION, "AU")
    plain = await _ask(client, "senior jobs", "NZ")

    assert len(received) == 1  # the second unclear question got the keyword answer
    assert first["jobs"] and not second["jobs"]
    assert plain["jobs"]  # quick keyword answers are never limited


async def test_a_country_the_site_does_not_cover_is_said_so_without_the_model(
    api_context: Context, model_on: None
) -> None:
    client, _, _ = api_context
    received = _use_fake_model(PLAN)

    body = await _ask(client, "how to get a job in Vietnam", "NZ")

    assert body["reply"].startswith(
        "I couldn't find any open jobs in 'vietnam'. I only cover jobs in"
    )
    assert received == []


async def test_a_place_after_in_is_a_location_and_an_unknown_place_says_so(
    api_context: Context, model_on: None
) -> None:
    client, category, jobs = api_context
    received = _use_fake_model(PLAN)

    body = await _ask(client, "jobs in vn", category.country)

    assert body["reply"].startswith("I couldn't find any open jobs in 'vn'. I only cover jobs in")
    assert body["jobs"] == []
    assert received == []  # a missing place is not worth a model call
    assert (await _ask(client, f"jobs in {jobs[0].location}", category.country))["jobs"]


async def test_a_word_from_real_job_titles_counts_as_a_signal_for_the_model(
    api_context: Context, model_on: None
) -> None:
    client, _, _ = api_context
    received = _use_fake_model(PLAN)

    await _ask(
        client, "engineer qwertyuiopasdf", "NZ"
    )  # no work word; 'engineer' is a real title word
    assert len(received) == 1


async def test_immigration_in_a_country_the_site_does_not_cover_says_so(
    api_context: Context, model_on: None
) -> None:
    client, _, _ = api_context
    received = _use_fake_model(PLAN)

    body = await _ask(client, "immigration policy in vietnam", "NZ")

    assert body["reply"].startswith("I don't have immigration information for 'vietnam'")
    assert received == []


async def test_a_misspelt_title_word_is_matched_to_a_real_one(api_context: Context) -> None:
    client, category, _ = api_context

    body = await _ask(client, "enginer jobs", category.country)  # titles hold "Engineer"

    assert len(body["jobs"]) == 2


async def test_a_follow_up_that_points_at_an_earlier_message_says_it_cannot_remember(
    api_context: Context,
) -> None:
    client, category, _ = api_context

    body = await _ask(client, "can you show me those jobs ?", category.country)

    assert body["reply"].startswith("I don't remember earlier messages")
    assert body["jobs"] == []


async def test_a_follow_up_fills_what_it_leaves_out_from_the_earlier_question(
    api_context: Context,
) -> None:
    client, category, jobs = api_context

    async def ask(message: str, earlier: list[str]) -> dict:
        response = await client.post(
            "/api/chat", json={"message": message, "country": "AU", "earlier": earlier}
        )
        assert response.status_code == 200
        return response.json()

    first = "junior jobs with visa sponsorship in new zealand and canada"
    body = await ask("can you show me those jobs ?", [first])

    assert body["reply"].startswith("You named New Zealand and Canada, so I'm showing New Zealand.")
    assert [job["id"] for job in body["jobs"]] == [str(jobs[1].id)]  # junior + visa kept
    assert "Level: junior" in body["understood"]

    # What the follow-up says itself wins; a new complete question ignores the earlier one.
    other = await ask("senior jobs", [first])
    assert "Level: senior" in other["understood"] and "Level: junior" not in other["understood"]


async def test_a_question_naming_no_country_keeps_the_one_from_the_chat(
    api_context: Context,
) -> None:
    client, category, _ = api_context
    other = next(code for code in COUNTRIES if code != category.country)
    earlier = [f"jobs in {COUNTRIES[category.country].name}"]

    response = await client.post(
        "/api/chat", json={"message": "i ask for remote jobs", "country": other, "earlier": earlier}
    )

    assert f"Country: {COUNTRIES[category.country].name}" in response.json()["understood"]
