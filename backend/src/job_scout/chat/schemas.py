from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints

from job_scout.jobs.schemas import JobListItem


class ChatRequest(BaseModel):
    message: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]
    # Country the person is browsing, used when the question names none.
    country: str | None = Field(None, max_length=2)
    # The last five questions of this chat (oldest first), kept by the browser, never stored.
    earlier: list[Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)]] = Field(
        default_factory=list, max_length=5
    )


class ChatResponse(BaseModel):
    reply: str
    # What was read from the question, so a misread filter is visible.
    understood: list[str]
    jobs: list[JobListItem]
    # The jobs page with the same search prefilled, when there are more jobs than are shown.
    more_url: str | None = None
