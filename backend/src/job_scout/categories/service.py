from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from job_scout.categories.models import Category
from job_scout.categories.schemas import CategoryItem
from job_scout.core.errors import AppError, ErrorCode
from job_scout.jobs.models import Job


async def require_enabled_category(session: AsyncSession, category_id: UUID) -> Category:
    category = await session.scalar(
        select(Category).where(Category.id == category_id, Category.enabled.is_(True))
    )
    if category is None:
        raise AppError(ErrorCode.CATEGORY_NOT_FOUND)
    return category


async def list_categories(session: AsyncSession) -> list[CategoryItem]:
    query = (
        select(Category, func.count(Job.id))
        .outerjoin(Job, (Job.category_id == Category.id) & Job.is_active.is_(True))
        .where(Category.enabled.is_(True))
        .group_by(Category.id)
        .order_by(Category.name)
    )
    rows = (await session.execute(query)).all()
    return [
        CategoryItem(
            id=category.id,
            name=category.name,
            slug=category.slug,
            seek_classification_id=category.seek_classification_id,
            active_job_count=active_job_count,
        )
        for category, active_job_count in rows
    ]
