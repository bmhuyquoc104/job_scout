from dataclasses import dataclass
from uuid import UUID


@dataclass
class ScrapeSummary:
    category_id: UUID
    fetched: int = 0
    eligible: int = 0
    ineligible: int = 0
    failed: int = 0
