import html
import json
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from job_scout.core.errors import AppError
from job_scout.green_list.australia import parse_occupations_page
from job_scout.green_list.models import GreenListRole
from job_scout.green_list.parsing import parse_record
from job_scout.green_list.sync import apply_sync
from tests.green_list.conftest import TIER_1, inz_record

Factory = async_sessionmaker[AsyncSession]


def label(year: str, note: str, code: str) -> str:
    text = f"ANZSCO {year} - {note} - {code}"
    return (
        f"<p><a class='external' target='_blank' aria-label='{text} - external link' "
        f"href='https://www.abs.gov.au/x'>{text}</a></p>"
    )


def home_affairs_record(
    title: str = "Software Engineer",
    lists: str = "MLTSSL;CSOL",
    codes: str | None = None,
) -> dict[str, Any]:
    """A record shaped like the occupation data embedded in the Home Affairs page."""
    return {
        "occupation": title,
        "anzscocode": codes
        if codes is not None
        else label("2022", "Subclass 186 and 482 visas", "261313")
        + label("2013", "all other visas", "261313"),
        "list": lists,
        "visas": "190 - Skilled Nominated (subclass 190);482 - Skills in Demand (subclass 482)",
        "visacaveats": "<div><ul class='table-search-skill'><li>482 - Core Skills</li></ul></div>",
        "assessauth": "<div><ul class='table-search-skill'><li>ACS</li></ul></div>",
    }


def page(*records: dict[str, Any]) -> str:
    # The real page carries the data as HTML-escaped JSON.
    return f'<html><div data-occupations="{html.escape(json.dumps(list(records)))}"></div></html>'


def au_roles(*records: dict[str, Any]):
    return parse_occupations_page(page(*records))


def test_a_record_becomes_a_role_with_its_lists_and_visas() -> None:
    [role] = au_roles(home_affairs_record())

    assert (role.record_id, role.title, role.anzsco_code) == (
        "2022-261313",
        "Software Engineer",
        "261313",
    )
    assert role.tier is None
    assert role.lists == ("CSOL", "MLTSSL")  # the one that matters for employers comes first
    assert role.industry == "Professionals"  # ANZSCO major group 2
    assert "482 - Skills in Demand" in role.pathway
    assert "ACS" in role.requirements


def test_a_role_without_a_2022_code_falls_back_to_the_2013_one() -> None:
    [role] = au_roles(
        home_affairs_record("Welder", "ROL", label("2013", "all other visas", "322313"))
    )

    assert (role.record_id, role.anzsco_code, role.industry) == (
        "2013-322313",
        "322313",
        "Technicians and Trades Workers",
    )


def test_a_page_without_occupation_data_is_refused_not_read_as_empty() -> None:
    with pytest.raises(AppError):
        parse_occupations_page("<html>maintenance</html>")


async def test_each_country_keeps_its_own_roles_and_baseline(green_db: Factory) -> None:
    await apply_sync(green_db, [parse_record(inz_record("1", "Nurse", TIER_1))])

    summary = await apply_sync(green_db, au_roles(home_affairs_record()), "AU")

    assert (summary.baseline, summary.created, summary.removed) == (True, 1, 0)
    async with green_db() as session:
        rows = (await session.execute(select(GreenListRole.country, GreenListRole.title))).all()
    assert sorted(rows) == [("AU", "Software Engineer"), ("NZ", "Nurse")]  # NZ's was not removed


async def test_the_api_returns_only_the_chosen_countrys_list(
    green_api: AsyncClient, green_db: Factory
) -> None:
    await apply_sync(green_db, [parse_record(inz_record("1", "Nurse", TIER_1))])
    await apply_sync(
        green_db,
        au_roles(
            home_affairs_record(),
            home_affairs_record("Welder", "ROL", label("2013", "all other visas", "322313")),
        ),
        "AU",
    )

    au = (await green_api.get("/api/green-list", params={"country": "AU"})).json()
    nz = (await green_api.get("/api/green-list")).json()

    assert [role["title"] for role in au["roles"]] == ["Software Engineer", "Welder"]
    assert au["roles"][0]["lists"] == ["CSOL", "MLTSSL"] and au["roles"][0]["tier"] is None
    assert au["list_counts"] == {"CSOL": 1, "MLTSSL": 1, "ROL": 1}
    assert (au["country"], au["source_name"]) == ("AU", "Department of Home Affairs")
    assert [role["title"] for role in nz["roles"]] == ["Nurse"] and nz["country"] == "NZ"
    assert (await green_api.get("/api/green-list", params={"country": "XX"})).status_code == 422
