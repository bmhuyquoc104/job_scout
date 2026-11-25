import json
from types import SimpleNamespace
from typing import Any

import pytest

from job_scout.core.errors import AppError
from job_scout.scraper import iamexpat

SECTION = "/career/jobs-netherlands/it-technology-positions"


def card(slug: str, job_id: str) -> str:
    return (
        f'<a href="{SECTION}/{slug}/{job_id}" class="JobBoardItemCard_cardWrapper__x" '
        f'target="_blank"><span>{slug}</span></a>'
    )


def posting(title: str = "Security Engineer", **fields: Any) -> dict[str, Any]:
    return {
        "@context": "https://schema.org",
        "@type": "JobPosting",
        "title": title,
        "description": "<p>Keep <b>bank</b> data safe.</p>",
        "datePosted": "2026-11-13T12:00:36",
        "hiringOrganization": {"@type": "Organization", "name": "Bunq"},
        "jobLocation": {
            "@type": "Place",
            "address": {"addressLocality": "Amsterdam", "addressCountry": "Netherlands"},
        },
        **fields,
    }


def job_page(data: dict[str, Any] | None) -> str:
    """A job page: the JobPosting sits inside Next.js flight chunks, split mid-stream."""
    stream = '5:["$","div",null,{}]\n' + (f"6:{json.dumps(data)}\n" if data else "")
    half = len(stream) // 2
    chunks = "".join(
        f"<script>self.__next_f.push([1,{json.dumps(part)}])</script>"
        for part in (stream[:half], stream[half:])
    )
    return f"<html><body>{chunks}</body></html>"


def test_the_list_page_gives_each_it_job_once_and_ignores_other_links() -> None:
    page = (
        card("security-engineer", "1eRjkMubdcVeEhEpKAdp7L")
        + card("data-engineer", "7PvMMswxNJRaG1y719q1Ba")
        + card("security-engineer", "1eRjkMubdcVeEhEpKAdp7L")
        + '<a href="/career/jobs-netherlands/marketing-positions/pr/abc123">other</a>'
    )

    assert iamexpat.parse_list_page(page) == [
        f"{SECTION}/security-engineer/1eRjkMubdcVeEhEpKAdp7L",
        f"{SECTION}/data-engineer/7PvMMswxNJRaG1y719q1Ba",
    ]


def test_a_job_page_gives_its_posting_with_our_id_and_url() -> None:
    href = f"{SECTION}/security-engineer/1eRjkMubdcVeEhEpKAdp7L"

    payload = iamexpat.parse_job_page(job_page(posting()), href)

    assert payload["id"] == "1eRjkMubdcVeEhEpKAdp7L"
    assert payload["url"] == f"https://www.iamexpat.nl{href}"
    assert payload["title"] == "Security Engineer"


def test_a_page_without_a_posting_is_refused() -> None:
    with pytest.raises(AppError):
        iamexpat.parse_job_page(job_page(None), f"{SECTION}/x/abc123")


def test_a_listing_is_normalised_from_the_posting() -> None:
    href = f"{SECTION}/security-engineer/1eRjkMubdcVeEhEpKAdp7L"
    payload = iamexpat.parse_job_page(job_page(posting()), href)

    listing = iamexpat.normalize_listing(payload)

    assert (listing.source, listing.external_id, listing.position) == (
        "iamexpat",
        "1eRjkMubdcVeEhEpKAdp7L",
        "Security Engineer",
    )
    assert (listing.company_name, listing.location) == ("Bunq", "Amsterdam")
    assert listing.listed_at is not None and listing.listed_at.year == 2026
    assert listing.url == payload["url"]
    assert iamexpat.build_description(payload) == "Keep bank data safe."


async def test_pages_read_every_list_page_then_each_new_job(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lists = {
        "": card("a", "idA00000001") + card("b", "idB00000002"),
        "?page=2": card("b", "idB00000002") + card("c", "idC00000003"),
        "?page=3": card("c", "idC00000003"),  # nothing new: the end
    }
    jobs = {f"{SECTION}/{s}/{i}": job_page(posting(s)) for s, i in
            [("a", "idA00000001"), ("b", "idB00000002"), ("c", "idC00000003")]}  # fmt: skip
    asked: list[str] = []

    async def fake_request(_: object, __: str, url: str, **___: object) -> SimpleNamespace:
        asked.append(url)
        path = url.removeprefix("https://www.iamexpat.nl")
        if path.startswith(SECTION + "?page=") or path == SECTION:
            return SimpleNamespace(text=lists[path.removeprefix(SECTION)])
        return SimpleNamespace(text=jobs[path])

    async def no_sleep(_: float) -> None:
        return None

    monkeypatch.setattr(iamexpat.chrome_http, "request", fake_request)
    monkeypatch.setattr(iamexpat.asyncio, "sleep", no_sleep)

    collected = [p["id"] async for page in iamexpat.pages(object(), "NL") for p in page]  # type: ignore[arg-type]

    assert collected == ["idA00000001", "idB00000002", "idC00000003"]
    assert sum("?page=" in url or url.endswith("positions") for url in asked) == 3


def test_it_only_covers_the_netherlands() -> None:
    with pytest.raises(AppError):
        iamexpat.client("DE")


async def test_a_listed_job_whose_page_has_no_posting_is_skipped(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lists = {"": card("a", "idA00000001") + card("gone", "idG00000002"), "?page=2": ""}
    jobs = {
        f"{SECTION}/a/idA00000001": job_page(posting("a")),
        f"{SECTION}/gone/idG00000002": job_page(None),  # taken down, the list still links it
    }

    async def fake_request(_: object, __: str, url: str, **___: object) -> SimpleNamespace:
        path = url.removeprefix("https://www.iamexpat.nl")
        if path.startswith(SECTION + "?page=") or path == SECTION:
            return SimpleNamespace(text=lists[path.removeprefix(SECTION)])
        return SimpleNamespace(text=jobs[path])

    async def no_sleep(_: float) -> None:
        return None

    monkeypatch.setattr(iamexpat.chrome_http, "request", fake_request)
    monkeypatch.setattr(iamexpat.asyncio, "sleep", no_sleep)

    collected = [p["id"] async for page in iamexpat.pages(object(), "NL") for p in page]  # type: ignore[arg-type]

    assert collected == ["idA00000001"]
