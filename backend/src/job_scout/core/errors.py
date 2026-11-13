from dataclasses import dataclass
from enum import StrEnum


class ErrorCode(StrEnum):
    CATEGORY_NOT_FOUND = "category_not_found"
    JOB_NOT_FOUND = "job_not_found"
    NOT_FOUND = "not_found"
    HTTP_ERROR = "http_error"
    VALIDATION_ERROR = "validation_error"
    INVALID_CV_FILE = "invalid_cv_file"
    CV_UNREADABLE = "cv_unreadable"
    CV_NO_SKILLS = "cv_no_skills"
    SCRAPE_SOURCE_ERROR = "scrape_source_error"
    INVALID_SCAN_TIMESTAMP = "invalid_scan_timestamp"
    INTERNAL_ERROR = "internal_error"


@dataclass(frozen=True)
class ErrorDefinition:
    status_code: int
    message: str


ERROR_CATALOG = {
    ErrorCode.CATEGORY_NOT_FOUND: ErrorDefinition(404, "Category not found."),
    ErrorCode.JOB_NOT_FOUND: ErrorDefinition(404, "Job not found."),
    ErrorCode.NOT_FOUND: ErrorDefinition(404, "Resource not found."),
    ErrorCode.HTTP_ERROR: ErrorDefinition(400, "Request could not be completed."),
    ErrorCode.VALIDATION_ERROR: ErrorDefinition(422, "Request validation failed."),
    ErrorCode.INVALID_CV_FILE: ErrorDefinition(422, "Upload a PDF file of 5 MB or less."),
    ErrorCode.CV_UNREADABLE: ErrorDefinition(
        422, "No text could be read from this PDF. Scanned images are not supported."
    ),
    ErrorCode.CV_NO_SKILLS: ErrorDefinition(
        422, "No IT skills were recognised in this CV. List tools and technologies by name."
    ),
    ErrorCode.SCRAPE_SOURCE_ERROR: ErrorDefinition(502, "A job source could not be processed."),
    ErrorCode.INVALID_SCAN_TIMESTAMP: ErrorDefinition(422, "Scan timestamp is missing or invalid."),
    ErrorCode.INTERNAL_ERROR: ErrorDefinition(500, "An unexpected error occurred."),
}


class AppError(Exception):
    """Typed application error. `detail` is for server logs only and never sent to clients."""

    def __init__(self, code: ErrorCode, detail: str | None = None) -> None:
        self.code = code
        self.detail = detail
        super().__init__(f"{code.value}: {detail}" if detail else code.value)

    @property
    def message(self) -> str:
        return ERROR_CATALOG[self.code].message
