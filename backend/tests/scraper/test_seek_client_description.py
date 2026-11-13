from typing import Any

from job_scout.scraper import seek_client as backfill


class _Response:
    def __init__(self, body: dict[str, Any]) -> None:
        self._body = body
        self.status_code = 200

    def json(self) -> dict[str, Any]:
        return self._body


class _Http:
    def __init__(self, body: dict[str, Any]) -> None:
        self.body = body

    async def request(self, *args: Any, **kwargs: Any) -> _Response:
        return _Response(self.body)


async def test_fetch_description_turns_html_into_text() -> None:
    body = {
        "data": {"jobDetails": {"job": {"content": "<p>Hello&nbsp;there</p><ul><li>One</li></ul>"}}}
    }
    text = await backfill.fetch_description(_Http(body), "1")  # type: ignore[arg-type]
    assert text == "Hello there\n• One"


async def test_fetch_description_is_none_when_seek_has_no_job() -> None:
    body = {"data": {"jobDetails": {"job": None}}}
    assert await backfill.fetch_description(_Http(body), "1") is None  # type: ignore[arg-type]
