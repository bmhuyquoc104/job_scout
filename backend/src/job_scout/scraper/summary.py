from dataclasses import dataclass
from uuid import UUID


@dataclass
class ScrapeSummary:
    category_id: UUID
    fetched: int = 0
    accredited: int = 0
    not_accredited: int = 0
    failed: int = 0
