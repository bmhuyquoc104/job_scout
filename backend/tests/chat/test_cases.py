"""Questions people actually asked, with how they must be read. Add a row for every misread."""

import pytest

from job_scout.chat.understand import understand

# message, intent, countries, title, location
CASES = [
    ("hello", "help", [], "", ""),
    (
        "senior python jobs in ireland with visa sponsorship above 80k",
        "search",
        ["IE"],
        "python",
        "",
    ),
    ("which country sponsors data engineers the most", "compare", [], "data engineers", ""),
    ("is hiring growing this month", "trend", [], "", ""),
    ("where are the jobs located in germany", "regions", ["DE"], "", ""),
    ("how many jobs offer visa sponsorship per country", "visa", [], "", ""),
    ("how to immigrate to new zealand", "immigration", ["NZ"], "", ""),
    (
        "is data engineer on the green list in new zealand",
        "immigration",
        ["NZ"],
        "data engineer",
        "",
    ),
    (
        "is new zealand or canada easier for a data engineer",
        "immigration",
        ["NZ", "CA"],
        "data engineer",
        "",
    ),
    (
        "which countries is easier to migrate to between can and ire",
        "immigration",
        ["CA", "IE"],
        "",
        "",
    ),
    ("i ask to choose between ireland and canada", "compare", ["IE", "CA"], "", ""),
    ("jobs in canada and ireland", "compare", ["CA", "IE"], "", ""),
    (
        "in 2026, and 2027 which country has a easiest path to immigrate for IT",
        "immigration",
        [],
        "software",
        "",
    ),
    ("I ask for the easiest one, not asking for listing", "immigration", [], "", ""),
    ("how about last week", "trend", [], "", ""),
    ("i want all jobs last week", "search", [], "", ""),
    ("are there any visa sponsor jobs now in australia", "search", ["AU"], "", ""),
    ("hmm, any jobs that in the last 3 days", "search", [], "", ""),
    ("any visa sponsorship it jobs in aus and can", "compare", ["AU", "CA"], "software", ""),
    ("job in vn", "search", [], "", "vn"),
    ("jobs in auckland", "search", [], "", "auckland"),
    ("python jobs in auckland", "search", [], "python", "auckland"),
    ("how to get a job in vietnam", "search", [], "", "vietnam"),
    ("what is the weather today in sai gon", "search", [], "weather", "sai gon"),
    ("jobs in irelnd", "search", ["IE"], "", ""),
    ("jobs in new zeland", "search", ["NZ"], "", ""),
    ("how to imigrate to canada", "immigration", ["CA"], "", ""),
    ("which occupation is easiest to relocate to germany", "immigration", ["DE"], "", ""),
    ("what is the priority occupation list in ireland", "immigration", ["IE"], "", ""),
    ("is hiring growin in ireland", "trend", ["IE"], "", ""),
]


@pytest.mark.parametrize(("message", "intent", "countries", "title", "location"), CASES)
def test_a_real_question_is_read_the_same_way(
    message: str, intent: str, countries: list[str], title: str, location: str
) -> None:
    plan = understand(message)

    assert (plan.intent, plan.countries, plan.title, plan.location) == (
        intent,
        countries,
        title,
        location,
    )


def test_misspelt_level_and_visa_words_are_still_read() -> None:
    assert understand("senoir python jobs in ireland").filters == {"seniority": ["senior"]}
    assert understand("jobs with visa sponsorhip in ireland").filters == {"visa": "offered"}


def test_a_short_window_is_kept_for_a_job_search() -> None:
    assert understand("any jobs in the last 3 days").days == 3


@pytest.mark.parametrize("word", ["hmm", "hmmmm", "oh", "ohhh", "uh", "umm", "errr", "ahh", "wow"])
def test_an_interjection_is_never_a_job_title(word: str) -> None:
    assert understand(f"{word}, any jobs in ireland").title == ""


@pytest.mark.parametrize("word", ["well", "so", "yeah", "yep", "ok", "okay", "sure"])
def test_filler_words_are_ignored(word: str) -> None:
    assert understand(f"{word} any jobs in ireland").title == ""


def test_a_window_follow_up_keeps_the_country_and_changes_the_question() -> None:
    from job_scout.chat.service import _read_with_context

    plan, used = _read_with_context(
        ["is hiring growing in ireland this month"], "how about last week"
    )

    assert used
    assert (plan.intent, plan.countries, plan.days) == ("trend", ["IE"], 7)


def test_naming_another_job_repeats_the_same_question_for_it() -> None:
    from job_scout.chat.service import _read_with_context

    plan, used = _read_with_context(
        ["which country sponsors data engineers the most"], "how about software engineer"
    )

    assert used
    assert (plan.intent, plan.title) == ("compare", "software engineer")
