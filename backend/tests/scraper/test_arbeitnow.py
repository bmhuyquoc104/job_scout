from datetime import UTC, datetime

from job_scout.scraper import arbeitnow


def job(slug: str, title: str, tags: list[str]) -> dict:
    return {
        "slug": slug,
        "company_name": "Acme GmbH",
        "title": title,
        "description": "<p>Build <b>APIs</b></p>",
        "remote": True,
        "url": f"https://www.arbeitnow.com/jobs/companies/acme/{slug}",
        "tags": tags,
        "job_types": ["Full Time"],
        "location": "Berlin",
        "created_at": 1794623437,
    }


def test_only_it_jobs_are_kept_by_tag_or_title() -> None:
    page = [
        job("a", "Backend Developer", ["Engineering"]),
        job("b", "Account Executive", ["Sales"]),
        job("c", "Platform Lead", ["Software Development"]),
        job("d", "Nurse", ["Healthcare"]),
    ]

    assert [j["id"] for j in arbeitnow.it_jobs(page)] == ["a", "c"]


def test_jobs_outside_germany_are_dropped() -> None:
    def at(slug: str, location: str) -> dict:
        return {**job(slug, "Backend Developer", []), "location": location}

    page = [
        at("de1", "Munich, Bavaria, Germany"),
        at("de2", "Oberrot"),
        at("de3", "Bernau bei Berlin"),
        at("de4", "Remote"),
        at("de5", "Germany - Remote"),
        at("uk", "London - Hybrid"),
        at("uk2", "Remote or Hybrid UK"),
        at("nl", "Amsterdam, Noord-Holland, Netherlands"),
        at("ch", "Zürich, Switzerland"),
        at("fr", "Paris, Île-de-France, France"),
        at("multi", "UK, Netherlands, Spain, or Belgium"),
    ]

    kept = [j["id"] for j in arbeitnow.it_jobs(page)]

    assert kept == ["de1", "de2", "de3", "de4", "de5"]


def test_a_listing_is_normalised_from_the_api_job() -> None:
    payload = arbeitnow.it_jobs([job("a", "Backend Developer", [])])[0]

    listing = arbeitnow.normalize_listing(payload)

    assert (listing.source, listing.external_id, listing.position) == (
        "arbeitnow",
        "a",
        "Backend Developer",
    )
    assert (listing.company_name, listing.location, listing.work_arrangements) == (
        "Acme GmbH",
        "Berlin",
        ["Remote"],
    )
    assert listing.listed_at == datetime.fromtimestamp(1794623437, UTC)
    assert listing.url.endswith("/a")
    assert arbeitnow.build_description(payload) == "Build APIs"
