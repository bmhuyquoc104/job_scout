from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from job_scout.green_list.models import GreenListRole
from job_scout.green_list.routes import matching_roles

Factory = async_sessionmaker[AsyncSession]


def role(title: str, country: str = "NZ", **fields: object) -> GreenListRole:
    return GreenListRole(
        country=country,
        record_id=f"{country}-{title}",
        title=title,
        anzsco_code="1",
        industry=str(fields.pop("industry", "ICT")),
        raw={},
        **fields,
    )


def titles(query: str, *roles: GreenListRole) -> list[str]:
    return [r.title for r in matching_roles(query, list(roles))]


def test_a_job_title_matches_roles_that_share_its_distinctive_words() -> None:
    roles = (role("Software Engineer"), role("Mechanical Engineers"), role("Web Developer"))

    # "Senior" is noise, and "engineer" alone is too generic to make Mechanical Engineers match.
    assert titles("Senior Software Engineer", *roles) == ["Software Engineer"]
    assert titles("backend developer", *roles) == ["Web Developer"]
    assert titles("Chef", *roles) == []


def test_roles_apply_to_the_whole_query_in_either_direction() -> None:
    roles = (role("Registered Nurse"), role("Nurse Practitioner"))

    assert sorted(titles("nurse", *roles)) == ["Nurse Practitioner", "Registered Nurse"]


def test_salary_threshold_roles_apply_to_every_job() -> None:
    threshold = role("EU Blue Card: standard salary", "DE", industry="Salary threshold 2026")

    assert titles("Chef", threshold) == ["EU Blue Card: standard salary"]


async def test_the_api_compares_every_country_for_a_job_title(
    green_api: AsyncClient, green_db: Factory
) -> None:
    async with green_db() as session, session.begin():
        session.add_all(
            [
                role("Software Engineer", "NZ", tier=1, pathway="Straight to residence"),
                role("Software Engineer", "AU", lists=["CSOL", "MLTSSL"]),
                role("Software Engineer", "CA"),
            ]
        )

    body = (
        await green_api.get("/api/green-list/routes", params={"title": "Software Engineer"})
    ).json()

    by_country = {c["country"]: c for c in body["countries"]}
    assert sorted(by_country) == ["AU", "CA", "DE", "NZ"]
    assert by_country["NZ"]["roles"][0]["tier"] == 1
    assert by_country["AU"]["roles"][0]["lists"] == ["CSOL", "MLTSSL"]
    assert by_country["DE"]["roles"] == []  # no list in Germany
    assert all(c["general_routes"] for c in body["countries"])
    assert (await green_api.get("/api/green-list/routes")).status_code == 422


async def test_the_titles_endpoint_lists_each_role_once_across_countries(
    green_api: AsyncClient, green_db: Factory
) -> None:
    async with green_db() as session, session.begin():
        session.add_all(
            [
                role("Software Engineer", "NZ"),
                role("software engineer", "AU"),
                role("Chef", "AU"),
                role("EU Blue Card: standard salary", "DE", industry="Salary threshold 2026"),
            ]
        )

    body = (await green_api.get("/api/green-list/titles")).json()

    assert body == ["Chef", "Software Engineer"]  # case-insensitive duplicates and rules dropped
