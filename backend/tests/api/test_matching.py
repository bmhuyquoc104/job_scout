from collections.abc import AsyncIterator
from types import SimpleNamespace
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from job_scout.categories.models import Category
from job_scout.database import get_session
from job_scout.jobs.models import Job
from job_scout.main import app
from job_scout.matching.fit import analyze_job, cv_years, required_years
from job_scout.matching.service import rank_jobs


def make_pdf(text: str) -> bytes:
    """A one-page PDF whose only content is `text` (empty text gives a page with no text)."""
    stream = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET" if text else ""
    bodies = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 5 0 R"
        " /Resources << /Font << /F1 4 0 R >> >> >>",
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        f"<< /Length {len(stream)} >>\nstream\n{stream}\nendstream",
    ]
    pdf, offsets = b"%PDF-1.4\n", []
    for number, body in enumerate(bodies, 1):
        offsets.append(len(pdf))
        pdf += f"{number} 0 obj\n{body}\nendobj\n".encode()
    xref = len(pdf)
    pdf += f"xref\n0 {len(bodies) + 1}\n0000000000 65535 f \n".encode()
    pdf += b"".join(f"{offset:010d} 00000 n \n".encode() for offset in offsets)
    pdf += f"trailer\n<< /Size {len(bodies) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF".encode()
    return pdf


@pytest.fixture
async def match_client(async_test_database_url: str) -> AsyncIterator[AsyncClient]:
    engine = create_async_engine(async_test_database_url)
    async with async_sessionmaker(engine, expire_on_commit=False)() as session:
        transaction = await session.begin()
        await session.execute(delete(Job))
        category = await session.scalar(select(Category).where(Category.slug == "ict"))
        assert category is not None
        session.add_all(
            Job(
                category_id=category.id,
                source="indeed" if external_id == "b" else "seek",
                external_id=external_id,
                company_name=f"Company {external_id}",
                location="Auckland",
                position=position,
                job_description=description,
                **analyze_job(position, description),
                url=f"https://www.seek.co.nz/job/{external_id}",
                is_active=active,
            )
            for external_id, position, description, active in (
                ("a", "Python Developer", "FastAPI PostgreSQL Docker", True),
                ("b", "Python Engineer", "FastAPI Terraform Kubernetes", True),
                ("c", "DevOps Engineer", "Terraform Kubernetes Docker", True),
                ("d", "Registered Nurse", "patient care medication", True),
                ("e", "Healthcare Assistant", "patient care medication", True),
                ("z", "Python Developer", "FastAPI PostgreSQL Docker", False),
            )
        )
        au = await session.scalar(select(Category).where(Category.slug == "ict-au"))
        assert au is not None
        session.add(
            Job(
                category_id=au.id,
                external_id="au",
                company_name="Company au",
                location="Sydney NSW",
                position="Python Developer",
                job_description="FastAPI PostgreSQL Docker",
                **analyze_job("Python Developer", "FastAPI PostgreSQL Docker"),
                url="https://www.seek.com.au/job/au",
            )
        )
        await session.flush()

        async def override_session() -> AsyncIterator[AsyncSession]:
            yield session

        app.dependency_overrides[get_session] = override_session
        try:
            async with AsyncClient(
                transport=ASGITransport(app=app, raise_app_exceptions=False),
                base_url="http://test",
            ) as client:
                yield client
        finally:
            app.dependency_overrides.clear()
            await transaction.rollback()
    await engine.dispose()


async def upload(client: AsyncClient, content: bytes, content_type: str = "application/pdf"):
    return await client.post("/api/cv", files={"file": ("cv.pdf", content, content_type)})


async def test_every_open_job_is_ranked_with_skills_to_add_for_weak_matches(
    match_client: AsyncClient,
) -> None:
    skills = ["Python", "fastapi", "postgresql", "docker"]  # any case is accepted
    response = await match_client.post("/api/matches", json={"skills": skills})

    assert response.status_code == 200
    matches = {match["company_name"]: match for match in response.json()}
    assert [m["company_name"] for m in response.json()[:3]] == [
        "Company a",
        "Company b",
        "Company c",
    ]
    assert len(matches) == 5  # all open jobs, including ones with nothing in common; not closed "z"
    assert (matches["Company a"]["source"], matches["Company b"]["source"]) == ("seek", "indeed")
    assert (matches["Company a"]["score"], matches["Company a"]["missing_skills"]) == (80, [])
    assert matches["Company b"]["score"] == 33
    assert matches["Company b"]["missing_skills"] == ["kubernetes", "terraform"]
    assert matches["Company c"]["score"] == 12
    # Words that are not skills ("engineer", "patient") are never suggested.
    assert (matches["Company d"]["score"], matches["Company d"]["missing_skills"]) == (0, [])


async def test_matches_only_cover_the_chosen_country(match_client: AsyncClient) -> None:
    skills = ["python", "fastapi"]

    nz = await match_client.post("/api/matches", json={"skills": skills})
    au = await match_client.post("/api/matches", json={"skills": skills, "country": "AU"})

    assert "Company au" not in {match["company_name"] for match in nz.json()}
    assert [match["company_name"] for match in au.json()] == ["Company au"]


async def test_unknown_country_is_rejected(match_client: AsyncClient) -> None:
    response = await match_client.post("/api/matches", json={"skills": ["python"], "country": "XX"})

    assert response.status_code == 422


async def test_cv_upload_returns_its_distinct_words(match_client: AsyncClient) -> None:
    response = await upload(match_client, make_pdf("Python developer, python FastAPI"))

    assert response.status_code == 200
    assert response.json() == {"skills": ["fastapi", "python"], "years": None}


async def test_non_pdf_upload_is_rejected(match_client: AsyncClient) -> None:
    response = await upload(match_client, b"just some text", "text/plain")

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_cv_file"


async def test_cv_without_any_it_skill_is_rejected(match_client: AsyncClient) -> None:
    response = await upload(match_client, make_pdf("Keen gardener and baker"))

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "cv_no_skills"


async def test_pdf_without_text_is_rejected(match_client: AsyncClient) -> None:
    response = await upload(match_client, make_pdf(""))

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "cv_unreadable"


def job(position: str, description: str = "Python FastAPI Docker"):
    return SimpleNamespace(
        id=uuid4(),
        position=position,
        company_name="Co",
        source="seek",
        location="Auckland",
        salary_label="",
        **analyze_job(position, description),
    )


def score_of(position: str, description: str = "Python FastAPI Docker", years=None) -> int:
    return rank_jobs({"python", "fastapi", "docker"}, [job(position, description)], years)[0].score


def test_a_job_asking_for_more_years_than_the_cv_has_scores_lower() -> None:
    ask = "Python FastAPI Docker. 5+ years of experience required"
    assert score_of("Developer", ask, years=1) < score_of("Developer", ask, years=5)
    assert score_of("Developer", ask, years=1) < score_of("Developer", ask, years=3)


def test_a_job_asking_for_fewer_years_scores_a_little_lower() -> None:
    ask = "Python FastAPI Docker. 2 years experience"
    assert score_of("Developer", ask, years=15) < score_of("Developer", ask, years=2)


def test_title_seniority_implies_years_when_the_ad_states_none() -> None:
    assert score_of("Senior Python Developer", years=1) < score_of("Python Developer", years=1)
    assert score_of("Senior Python Developer", years=5) == score_of("Python Developer", years=5)


def test_unknown_years_change_nothing() -> None:
    ask = "Python FastAPI Docker. 8 years experience"
    assert score_of("Senior Developer", ask) == score_of("Developer", "Python FastAPI Docker")


def test_required_years_reads_ranges_and_both_phrasings() -> None:
    assert required_years("Dev", "3-5 years of experience in Python") == 3
    assert required_years("Dev", "Experience: minimum 4 years") == 4
    assert required_years("Dev", "We are 10 years old") is None
    assert required_years("Lead Dev", "no numbers") == 8
    assert required_years("Dev", "no numbers") is None


def test_cv_years_is_the_largest_stated() -> None:
    assert [cv_years(t) for t in ("3 months", "1 year of Python", "5+ years, 2 yrs Go")] == [
        None,
        1,
        5,
    ]


def test_visa_sponsorship_boosts_and_flags_the_job() -> None:
    plain = rank_jobs({"python"}, [job("Python Developer", "Python")])[0]
    offer = rank_jobs({"python"}, [job("Python Developer", "Python. Visa sponsorship offered")])[0]
    assert (plain.visa_sponsor, offer.visa_sponsor) == (False, True)
    assert offer.score > plain.score


def test_no_sponsorship_is_not_a_boost() -> None:
    for text in ("No visa sponsorship", "We cannot sponsor visas", "Must have the right to work"):
        assert not rank_jobs({"python"}, [job("Python Developer", f"Python. {text}")])[
            0
        ].visa_sponsor


def test_sponsorship_does_not_lift_a_job_with_no_skill_in_common() -> None:
    match = rank_jobs({"python"}, [job("Nurse", "patient care. visa sponsorship")])[0]
    assert (match.score, match.visa_sponsor) == (0, True)


def test_an_architect_title_asks_for_more_years_than_the_ad_states() -> None:
    assert required_years("Solution Architect", "Python. 3 years experience") == 8
    assert required_years("Developer", "Python. 3 years experience") == 3


def test_fresher_ads_ask_for_no_experience() -> None:
    for text in ("Freshers welcome", "No experience required", "Entry level role"):
        assert required_years("Developer", text) == 0


def test_an_experienced_cv_ranks_a_fresher_job_well_below_a_matching_one() -> None:
    fresher = score_of("Python Developer", "Python FastAPI Docker. Freshers welcome", years=8)
    matching = score_of("Python Developer", "Python FastAPI Docker. 6+ years experience", years=8)
    assert fresher < matching * 0.6


def test_analyze_job_reads_skills_years_and_visa_once() -> None:
    result = analyze_job(
        "Senior Python Developer", "FastAPI. 6+ years experience. Visa sponsorship"
    )
    assert result == {
        "skills": ["fastapi", "python"],
        "required_years": 6,
        "visa_sponsor": True,
    }


def test_limit_and_visa_only_keep_the_best_matching_jobs() -> None:
    jobs = [
        job("Python Developer", "Python FastAPI"),
        job("Python Engineer", "Python. Visa sponsorship"),
        job("Python Analyst", "Python. Relocation support"),
    ]
    cv = {"python", "fastapi"}

    assert len(rank_jobs(cv, jobs, None, limit=2)) == 2
    sponsored = rank_jobs(cv, jobs, None, visa_only=True)
    assert [m.position for m in sponsored] == ["Python Engineer", "Python Analyst"]
    assert [m.position for m in rank_jobs(cv, jobs, None, limit=1, visa_only=True)] == [
        "Python Engineer"
    ]


async def test_matches_api_accepts_limit_and_visa_only(match_client: AsyncClient) -> None:
    response = await match_client.post(
        "/api/matches", json={"skills": ["python", "fastapi"], "limit": 2}
    )
    none = await match_client.post(
        "/api/matches", json={"skills": ["python", "fastapi"], "visa_only": True}
    )

    assert len(response.json()) == 2
    assert none.json() == []  # no fixture job offers sponsorship


def test_a_match_lists_the_cv_skills_the_job_asks_for() -> None:
    match = rank_jobs({"python", "docker", "react"}, [job("Dev", "Python FastAPI Docker")])[0]

    assert match.matched_skills == ["docker", "python"]
    assert match.missing_skills == ["fastapi"]
