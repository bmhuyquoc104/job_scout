import pytest

from job_scout.chat.understand import understand


def test_a_full_search_sentence_is_split_into_filters() -> None:
    plan = understand("senior python jobs in Ireland with visa sponsorship above 80k, remote")

    assert plan.intent == "search"
    assert plan.country == "IE"
    assert plan.title == "python"
    assert plan.filters == {
        "seniority": ["senior"],
        "visa": "offered",
        "min_salary": 80_000,
        "arrangement": ["Remote"],
    }


@pytest.mark.parametrize(
    ("text", "country"),
    [
        ("jobs in the Netherlands", "NL"),
        ("jobs in new zealand", "NZ"),
        ("jobs in Germeny", "DE"),  # typo
        ("jobs in AU", "AU"),
        ("jobs anywhere", None),
    ],
)
def test_country_is_found_by_name_code_or_close_spelling(text: str, country: str | None) -> None:
    assert understand(text).country == country


@pytest.mark.parametrize(
    ("text", "intent"),
    [
        ("which country sponsors data engineers the most", "compare"),
        ("compare devops roles across countries", "compare"),
        ("is hiring growing in Ireland", "trend"),
        ("how many new jobs this week", "trend"),
        ("where are the jobs located", "regions"),
        ("which cities have the most jobs", "regions"),
        ("how many jobs offer visa sponsorship per country", "visa"),
        ("hello", "help"),
        ("what can you do", "help"),
        ("python developer", "search"),
    ],
)
def test_intent_comes_from_keywords(text: str, intent: str) -> None:
    assert understand(text).intent == intent


def test_time_windows_become_days() -> None:
    assert understand("trend over the last 90 days").days == 90
    assert understand("hiring this week").days == 7
    assert understand("hiring this month").days == 30
    assert understand("hiring in ireland").days == 30


def test_title_keeps_multi_word_roles_and_drops_filler() -> None:
    assert understand("show me data engineer roles in Germany").title == "data engineer"
    assert understand("which country sponsors data engineers the most").title == "data engineers"


def test_numbers_that_are_not_salaries_are_ignored() -> None:
    plan = understand("hiring trend over the last 90 days")

    assert "min_salary" not in plan.filters
    assert plan.title == ""


def test_an_immigration_question_is_not_read_as_a_job_search() -> None:
    plan = understand("how to immigrate to new zealand")

    assert (plan.intent, plan.country, plan.title, plan.filters) == ("immigration", "NZ", "", {})


@pytest.mark.parametrize(
    ("text", "country", "title", "across"),
    [
        ("is data engineer on the green list in new zealand", "NZ", "data engineer", False),
        ("how can I get a visa for Germany", "DE", "", False),
        (
            "what are the routes for a software developer in Ireland",
            "IE",
            "software developer",
            False,
        ),
        (
            "which country is easiest to immigrate to as a data engineer",
            None,
            "data engineer",
            True,
        ),
    ],
)
def test_immigration_questions_keep_the_country_and_role(
    text: str, country: str | None, title: str, across: bool
) -> None:
    plan = understand(text)

    assert (plan.intent, plan.country, plan.title, plan.across) == (
        "immigration",
        country,
        title,
        across,
    )


@pytest.mark.parametrize(
    "text",
    [
        "data migration engineer jobs",  # "migration" alone is a job title word
        "jobs with visa sponsorship",
        "green energy jobs in Germany",
        "critical care nurse",
    ],
)
def test_job_questions_with_immigration_looking_words_stay_job_searches(text: str) -> None:
    assert understand(text).intent == "search"


def test_every_country_named_in_the_question_is_read_in_order() -> None:
    plan = understand("which country is easier between new zealand and canada")

    assert plan.intent == "immigration"
    assert plan.countries == ["NZ", "CA"]
    assert plan.title == ""
    assert understand("canada or ireland jobs").countries == ["CA", "IE"]
    assert understand("jobs in ireland").countries == ["IE"]
    assert understand("jobs anywhere").countries == []


@pytest.mark.parametrize(
    ("text", "countries"),
    [
        ("which countries is easier to migrate to between can and ire", ["CA", "IE"]),
        ("is it easier in ire or can", ["IE", "CA"]),
        ("irish jobs", ["IE"]),
        ("jobs in aus and the dutch market", ["AU", "NL"]),
        ("can you help me", []),  # "can" is only Canada between other countries
        ("what can i do", []),
    ],
)
def test_abbreviations_and_nationalities_name_countries(text: str, countries: list[str]) -> None:
    plan = understand(text)

    assert plan.countries == countries
    assert "ire" not in plan.title.split()


def test_the_pasted_conversation_is_read_as_two_country_questions() -> None:
    first = understand("which countries is easier to migrate to between can and ire")
    second = understand("i ask to choose between ireland and canada")

    assert (first.intent, first.title) == ("immigration", "")
    assert (second.intent, second.countries, second.title) == ("compare", ["IE", "CA"], "")


def test_two_named_countries_are_never_a_one_country_search() -> None:
    assert understand("jobs in canada and ireland").intent == "compare"
    assert understand("senior python jobs in canada vs ireland").intent == "compare"
    assert understand("jobs in canada").intent == "search"


def test_easiest_path_for_it_is_an_immigration_question_about_software() -> None:
    plan = understand("in 2026, and 2027 which country has a easiest path to immigrate for IT")
    assert (plan.intent, plan.title) == ("immigration", "software")
    assert understand("I ask for the easiest one, not asking for listing").title == ""


def test_a_bare_time_window_is_a_hiring_question_and_a_jobs_window_filters_jobs() -> None:
    assert understand("how about last week").intent == "trend"
    plan = understand("i want all jobs last week")
    assert (plan.intent, plan.days, plan.days_given) == ("search", 7, True)


def test_the_see_all_link_carries_the_search_as_jobs_page_filters() -> None:
    from datetime import date
    from uuid import uuid4

    from job_scout.chat.service import _jobs_page
    from job_scout.jobs.schemas import JobQuery

    category = uuid4()
    query = JobQuery(
        position="python",
        visa="offered",
        min_salary=80000,
        arrangement=["Remote"],
        seniority=["senior"],
        listed_from=date(2026, 11, 14),
    )

    url = _jobs_page(category, query)

    assert url.startswith(f"/categories/{category}?status=open")
    for part in ("position=python", "visa=offered", "min_salary=80000", "arrangement=Remote"):
        assert part in url
    assert "listed_from=2026-11-14" in url
    assert "seniority" not in url


def test_yesterday_is_a_one_day_search_not_a_month_trend() -> None:
    plan = understand("are there any new jobs in ireland yesterday")
    assert (plan.intent, plan.days, plan.days_given, plan.country) == ("search", 1, True, "IE")


def test_days_ago_is_a_window_not_a_title() -> None:
    plan = understand("any new jobs in ireland 5 days ago")
    assert (plan.title, plan.days, plan.days_given) == ("", 5, True)
