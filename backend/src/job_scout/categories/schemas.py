from uuid import UUID

from pydantic import BaseModel


class CategoryItem(BaseModel):
    id: UUID
    name: str
    slug: str
    seek_classification_id: str
    active_job_count: int
