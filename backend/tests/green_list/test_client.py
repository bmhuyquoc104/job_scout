import json

import httpx
import pytest

from job_scout.core.errors import AppError, ErrorCode
from job_scout.green_list import client
from tests.green_list.conftest import inz_record


def response(records: list, *, pages: int = 1, total: int | None = None) -> dict:
    return {
        "meta": {
            "page": {
                "current": 1,
                "total_pages": pages,
                "total_results": total or len(records),
                "size": 300,
            }
        },
        "results": records,
    }


async def fetch(handler, monkeypatch: pytest.MonkeyPatch | None = None):
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        return await client.fetch_green_list(http)


async def test_fetch_sends_the_green_list_query_and_parses_every_role() -> None:
    sent: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        sent.append(request)
        return httpx.Response(200, json=response([inz_record("1"), inz_record("2", title="Nurse")]))

    roles = await fetch(handler)

    assert [role.record_id for role in roles] == ["1", "2"]
    assert sent[0].method == "POST" and sent[0].url.path.endswith("/engines/--engine--/search.json")
    assert json.loads(sent[0].content) == {
        "query": "",
        "filters": {"all": [{"identifier": "list-4ded06ebc2"}], "none": [], "any": []},
        "page": {"size": 300, "current": 1},
        "sort": [{"title": "asc"}],
    }


@pytest.mark.parametrize(
    "body",
    [
        response([inz_record()], pages=2),  # more pages than the one we read
        response([inz_record()], total=5),  # we got fewer than the site says exist
        response([]),
        {"meta": {}, "results": []},
        {"unexpected": True},
    ],
)
async def test_an_incomplete_or_odd_response_is_refused(body: dict) -> None:
    async def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=body)

    with pytest.raises(AppError) as error:
        await fetch(handler)

    assert error.value.code is ErrorCode.SCRAPE_SOURCE_ERROR


async def test_a_non_json_answer_is_refused() -> None:
    async def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="<html>blocked</html>")

    with pytest.raises(AppError):
        await fetch(handler)


async def test_transient_server_errors_are_retried_then_given_up(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sleeps: list[float] = []

    async def no_wait(delay: float) -> None:
        sleeps.append(delay)

    monkeypatch.setattr(client.asyncio, "sleep", no_wait)
    attempts = 0

    async def flaky(_: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return (
            httpx.Response(503)
            if attempts < 3
            else httpx.Response(200, json=response([inz_record()]))
        )

    assert len(await fetch(flaky)) == 1
    assert (attempts, sleeps) == (3, [2, 4])

    async def down(_: httpx.Request) -> httpx.Response:
        return httpx.Response(500)

    with pytest.raises(AppError) as error:
        await fetch(down)
    assert isinstance(error.value.__cause__, httpx.HTTPStatusError)
