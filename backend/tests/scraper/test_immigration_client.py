import pytest
from playwright.async_api import Error as PlaywrightError

from job_scout.core.errors import AppError, ErrorCode
from job_scout.scraper import immigration_client


class StubPage:
    def __init__(self, goto_errors: int = 0, evaluate_results: list[object] | None = None) -> None:
        self.goto_errors = goto_errors
        self.evaluate_results = evaluate_results or []
        self.goto_calls: list[tuple[str, dict[str, object]]] = []
        self.evaluate_calls = 0
        self.waits: list[int] = []
        self.url = "about:blank"

    async def goto(self, url: str, **options: object) -> None:
        self.goto_calls.append((url, options))
        if len(self.goto_calls) <= self.goto_errors:
            raise PlaywrightError("navigation failed")
        self.url = url

    async def evaluate(self, script: str, argument: object = None) -> object:
        self.evaluate_calls += 1
        result = self.evaluate_results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result

    async def wait_for_timeout(self, delay_ms: int) -> None:
        self.waits.append(delay_ms)


async def test_check_accreditation_retries_then_returns_result() -> None:
    check = getattr(immigration_client, "check_accreditation", None)
    assert callable(check), "check_accreditation must exist"
    page = StubPage(goto_errors=2, evaluate_results=[{"Title": "Results", "results": "[]"}])

    result = await check(page, "Daraco IT Services")

    assert result == {"Title": "Results", "results": "[]"}
    assert len(page.goto_calls) == 3
    assert page.waits == [5000, 5000]


async def test_check_accreditation_raises_after_three_failures() -> None:
    check = getattr(immigration_client, "check_accreditation", None)
    assert callable(check), "check_accreditation must exist"
    page = StubPage(goto_errors=3)

    with pytest.raises(AppError) as error:
        await check(page, "Daraco IT Services")

    assert error.value.code is ErrorCode.SCRAPE_SOURCE_ERROR
    assert len(page.goto_calls) == 3
    assert page.waits == [5000, 5000]


def test_accreditation_rule_preserves_current_non_no_results_behavior() -> None:
    is_accredited = getattr(immigration_client, "is_accredited", None)
    assert callable(is_accredited), "is_accredited must exist"

    assert is_accredited({"Title": "No Results"}) is False
    assert is_accredited({"Title": "Possible matches"}) is True
    assert is_accredited({"results": "[]"}) is True


def test_extract_immigration_fields_uses_first_result_values() -> None:
    extract = getattr(immigration_client, "extract_immigration_fields", None)
    assert callable(extract), "extract_immigration_fields must exist"
    result = {
        "results": '[{"field_schema":{"raw":['
        '{"APIColumn":"nzbn","Value":"942903"},'
        '{"APIColumn":"tradingName","Value":"Daraco"}]}}]'
    }

    assert extract(result) == {"nzbn": "942903", "trading_name": "Daraco"}
    assert extract({"Title": "No Results"}) == {"nzbn": "", "trading_name": ""}


def test_extract_immigration_fields_turns_null_values_into_empty_strings() -> None:
    # An accredited employer can have an NZBN but no trading name (a JSON null, not a missing key).
    result = {
        "results": '[{"field_schema":{"raw":['
        '{"APIColumn":"nzbn","Value":"9429047912045"},'
        '{"APIColumn":"tradingName","Value":null}]}}]'
    }

    assert immigration_client.extract_immigration_fields(result) == {
        "nzbn": "9429047912045",
        "trading_name": "",
    }


def test_extract_immigration_fields_accepts_empty_result_list() -> None:
    extract = getattr(immigration_client, "extract_immigration_fields", None)
    assert callable(extract), "extract_immigration_fields must exist"

    assert extract({"results": "[]"}) == {"nzbn": "", "trading_name": ""}


def test_extract_immigration_fields_rejects_malformed_payload_as_source_error() -> None:
    for bad in ({"results": "not-json"}, {"results": '{"not": "a list"}'}):
        with pytest.raises(AppError) as error:
            immigration_client.extract_immigration_fields(bad)
        assert error.value.code is ErrorCode.SCRAPE_SOURCE_ERROR


async def test_check_accreditation_reuses_an_already_loaded_page() -> None:
    page = StubPage(evaluate_results=[{"Title": "Results"}, {"Title": "No Results"}])

    first = await immigration_client.check_accreditation(page, "A Ltd")
    second = await immigration_client.check_accreditation(page, "B Ltd")

    assert (first["Title"], second["Title"]) == ("Results", "No Results")
    assert len(page.goto_calls) == 1


async def test_check_accreditation_reloads_the_page_when_a_lookup_fails() -> None:
    page = StubPage(
        evaluate_results=[{"Title": "Results"}, PlaywrightError("stale"), {"Title": "Results"}]
    )

    await immigration_client.check_accreditation(page, "A Ltd")
    await immigration_client.check_accreditation(page, "B Ltd")

    assert len(page.goto_calls) == 2
    assert page.waits == [5000]
