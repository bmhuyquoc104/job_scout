import pytest

from job_scout.chat.llm import LlmPlan, to_plan


def _plan(**overrides: object) -> LlmPlan:
    base = {
        "intent": "search",
        "countries": ["IE"],
        "title": " Data Engineer ",
        "days": None,
        "filters": {
            "seniority": [],
            "arrangement": [],
            "work_type": [],
            "visa_sponsorship": False,
            "min_salary": None,
        },
    }
    return LlmPlan.model_validate({**base, **overrides})


def test_a_model_plan_becomes_the_same_plan_the_keyword_rules_build() -> None:
    plan = to_plan(
        _plan(
            filters={
                "seniority": ["senior"],
                "arrangement": ["Remote"],
                "work_type": [],
                "visa_sponsorship": True,
                "min_salary": 80_000,
            },
            days=90,
        )
    )

    assert (plan.intent, plan.country, plan.countries, plan.title) == (
        "search",
        "IE",
        ["IE"],
        "data engineer",
    )
    assert plan.filters == {
        "seniority": ["senior"],
        "arrangement": ["Remote"],
        "visa": "offered",
        "min_salary": 80_000,
    }
    assert (plan.days, plan.days_given) == (90, True)


def test_odd_numbers_from_a_model_are_dropped_or_clamped() -> None:
    plan = to_plan(_plan(days=5000, filters={**_plan().filters.model_dump(), "min_salary": 12}))

    assert plan.days == 365
    assert "min_salary" not in plan.filters


def test_repeated_countries_are_listed_once_in_order() -> None:
    assert to_plan(_plan(countries=["CA", "IE", "CA"])).countries == ["CA", "IE"]


def test_visa_stats_by_country_are_a_visa_question_not_a_comparison() -> None:
    plan = to_plan(
        _plan(
            intent="compare",
            countries=[],
            title="",
            filters={**_plan().filters.model_dump(), "visa_sponsorship": True},
        )
    )

    assert plan.intent == "visa"


@pytest.mark.parametrize("code", ["XX", "uk"])
def test_an_unknown_country_code_is_rejected(code: str) -> None:
    with pytest.raises(ValueError):
        _plan(countries=[code])
