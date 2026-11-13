from types import SimpleNamespace

import httpx
import pytest

from job_scout.core.errors import AppError, ErrorCode
from job_scout.scraper import seek_client


async def test_fetch_search_page_sends_category_and_pagination_parameters() -> None:
    requests: list[httpx.Request] = []

    async def respond(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"data": [{"id": "job-1"}], "totalCount": 1})

    fetch = getattr(seek_client, "fetch_search_page", None)
    assert callable(fetch), "fetch_search_page must exist"
    category = SimpleNamespace(seek_classification_id="6281", country="NZ")
    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        response = await fetch(client, category, 3)

    assert response == {"data": [{"id": "job-1"}], "totalCount": 1}
    assert requests[0].url.path == "/api/jobsearch/v5/search"
    assert dict(requests[0].url.params) == {
        "siteKey": "NZ-Main",
        "sourcesystem": "houston",
        "page": "3",
        "pageSize": "22",
        "classification": "6281",
        "locale": "en-NZ",
    }


async def test_fetch_search_page_rejects_non_object_payload_with_central_error() -> None:
    async def respond(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[{"id": "unexpected"}])

    category = SimpleNamespace(seek_classification_id="6281", country="NZ")
    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        with pytest.raises(AppError) as error:
            await seek_client.fetch_search_page(client, category, 1)

    assert error.value.code is ErrorCode.SCRAPE_SOURCE_ERROR


async def test_fetch_search_page_follows_seek_market_redirect() -> None:
    requests: list[httpx.Request] = []

    async def respond(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.host == "www.seek.co.nz":
            return httpx.Response(
                308,
                headers={"Location": "https://nz.seek.com/api/jobsearch/v5/search"},
            )
        return httpx.Response(200, json={"data": [{"id": "job-1"}]})

    category = SimpleNamespace(seek_classification_id="6281", country="NZ")
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(respond), follow_redirects=False
    ) as client:
        response = await seek_client.fetch_search_page(client, category, 1)

    assert response == {"data": [{"id": "job-1"}]}
    assert [request.url.host for request in requests] == ["www.seek.co.nz", "nz.seek.com"]


async def _fetch_with_responses(
    monkeypatch: pytest.MonkeyPatch, statuses: list[int]
) -> tuple[dict[str, object], int, list[float]]:
    calls = 0
    sleeps: list[float] = []

    async def respond(_: httpx.Request) -> httpx.Response:
        nonlocal calls
        status = statuses[min(calls, len(statuses) - 1)]
        calls += 1
        return httpx.Response(status, json={"data": [], "totalCount": 0})

    async def fake_sleep(delay: float) -> None:
        sleeps.append(delay)

    monkeypatch.setattr(seek_client.asyncio, "sleep", fake_sleep)
    category = SimpleNamespace(seek_classification_id="6281", country="NZ")
    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        result = await seek_client.fetch_search_page(client, category, 1)
    return result, calls, sleeps


async def test_fetch_search_page_retries_transient_server_errors_with_backoff(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result, calls, sleeps = await _fetch_with_responses(monkeypatch, [503, 429, 200])

    assert result == {"data": [], "totalCount": 0}
    assert calls == 3
    assert sleeps == [2, 4]


async def test_fetch_search_page_gives_up_after_three_attempts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(AppError) as error:
        await _fetch_with_responses(monkeypatch, [500])
    assert error.value.code is ErrorCode.SCRAPE_SOURCE_ERROR
    assert isinstance(error.value.__cause__, httpx.HTTPStatusError)


async def test_fetch_search_page_does_not_retry_client_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sleeps: list[float] = []

    async def fake_sleep(delay: float) -> None:
        sleeps.append(delay)

    monkeypatch.setattr(seek_client.asyncio, "sleep", fake_sleep)
    with pytest.raises(AppError):
        await _fetch_with_responses(monkeypatch, [404])
    assert sleeps == []


def test_parse_search_page_accepts_a_valid_response() -> None:
    page = seek_client.parse_search_page({"totalCount": 1, "data": [{"id": "1"}]})

    assert page.total_count == 1
    assert page.data == [{"id": "1"}]
    assert seek_client.parse_search_page({"totalCount": 0, "data": []}).data == []


@pytest.mark.parametrize(
    "bad",
    [
        {"data": []},
        {"totalCount": True, "data": []},
        {"totalCount": -1, "data": []},
        {"totalCount": "many", "data": []},
        {"totalCount": 1, "data": "nope"},
        {"totalCount": 1, "data": ["not-an-object"]},
        {"totalCount": 0, "data": [{"id": "1"}]},
        {"totalCount": 5, "data": []},
    ],
)
def test_parse_search_page_rejects_bad_responses_as_source_errors(bad: dict[str, object]) -> None:
    with pytest.raises(AppError) as error:
        seek_client.parse_search_page(bad)

    assert error.value.code is ErrorCode.SCRAPE_SOURCE_ERROR


async def test_fetch_search_page_uses_the_categorys_country_site() -> None:
    requests: list[httpx.Request] = []

    async def respond(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"data": [], "totalCount": 0})

    category = SimpleNamespace(seek_classification_id="6281", country="AU")
    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        await seek_client.fetch_search_page(client, category, 1)

    assert requests[0].url.host == "www.seek.com.au"
    assert requests[0].url.params["siteKey"] == "AU-Main"
    assert requests[0].url.params["locale"] == "en-AU"
