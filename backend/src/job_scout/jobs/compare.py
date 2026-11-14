"""One job title compared across the countries: how many open jobs, what they pay, where from."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from job_scout.categories.models import Category
from job_scout.core.countries import COUNTRIES
from job_scout.green_list.routes import distinctive_words
from job_scout.jobs.models import Job
from job_scout.jobs.schemas import CountryJobStats, JobComparison


async def compare_job(session: AsyncSession, title: str) -> JobComparison:
    """Open jobs whose title contains all the distinctive words of `title`, per country."""
    # shortcut: every distinctive word must appear (so a long title finds few jobs); loosen to
    # "most words" if people search with full ad titles.
    words = sorted(distinctive_words(title))
    matches = [Job.position.ilike(f"%{word}%") for word in words]
    base = (
        select(Category.country, Job.source, func.count(), func.count(Job.annual_salary_min))
        .join(Category, Category.id == Job.category_id)
        .where(Job.is_active.is_(True), *matches)
        .group_by(Category.country, Job.source)
    )
    salaries = (
        select(
            Category.country,
            func.percentile_cont(0.5).within_group(Job.annual_salary_min),
            func.percentile_cont(0.5).within_group(Job.annual_salary_max),
        )
        .join(Category, Category.id == Job.category_id)
        .where(Job.is_active.is_(True), Job.annual_salary_min.is_not(None), *matches)
        .group_by(Category.country)
    )
    by_source: dict[str, dict[str, int]] = {}
    totals: dict[str, list[int]] = {}
    for country, source, count, with_salary in (await session.execute(base)).all():
        by_source.setdefault(country, {})[source] = count
        total = totals.setdefault(country, [0, 0])
        total[0] += count
        total[1] += with_salary
    medians = {
        country: (round(low), round(high))
        for country, low, high in (await session.execute(salaries)).all()
    }
    return JobComparison(
        title=title,
        countries=[
            CountryJobStats(
                country=code,
                country_name=country.name,
                currency=country.currency,
                open_jobs=totals.get(code, [0, 0])[0],
                with_salary=totals.get(code, [0, 0])[1],
                median_salary_min=medians[code][0] if code in medians else None,
                median_salary_max=medians[code][1] if code in medians else None,
                by_source=dict(sorted(by_source.get(code, {}).items())),
            )
            for code, country in COUNTRIES.items()
        ],
    )
