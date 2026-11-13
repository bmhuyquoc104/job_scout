from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from job_scout.categories.models import Category
from job_scout.database import get_session
from job_scout.jobs.models import Job
from job_scout.main import app


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
                external_id=external_id,
                company_name=f"Company {external_id}",
                location="Auckland",
                position=position,
                job_description=description,
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
    assert (matches["Company a"]["score"], matches["Company a"]["missing_skills"]) == (80, [])
    assert matches["Company b"]["score"] == 33
    assert matches["Company b"]["missing_skills"] == ["kubernetes", "terraform"]
    assert matches["Company c"]["score"] == 12
    # Words that are not skills ("engineer", "patient") are never suggested.
    assert (matches["Company d"]["score"], matches["Company d"]["missing_skills"]) == (0, [])


async def test_cv_upload_returns_its_distinct_words(match_client: AsyncClient) -> None:
    response = await upload(match_client, make_pdf("Python developer, python FastAPI"))

    assert response.status_code == 200
    assert response.json() == {"skills": ["fastapi", "python"]}


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
