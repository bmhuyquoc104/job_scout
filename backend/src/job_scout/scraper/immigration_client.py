import json
from typing import Any

from playwright.async_api import Error as PlaywrightError
from playwright.async_api import Page

from job_scout.core.errors import AppError, ErrorCode

IMMIGRATION_URL = (
    "https://www.immigration.govt.nz/work/requirements-for-work-visas/"
    "approved-employers/accredited-employer-list/"
)


async def check_accreditation(page: Page, company: str) -> dict[str, Any]:
    for attempt in range(3):
        try:
            # The loaded page is reused across lookups; retries always reload it.
            if attempt or page.url != IMMIGRATION_URL:
                await page.goto(IMMIGRATION_URL, wait_until="networkidle")
            return await page.evaluate(
                """async (company) => {
                  const formData = new FormData();
                  formData.append("query", company);
                  formData.append("collection", "2");
                  formData.append("page", "1");
                  const response = await fetch("/list-api/getAPIResults/", {
                    method: "POST",
                    body: formData,
                    headers: { Accept: "application/json" },
                  });
                  return await response.json();
                }""",
                company,
            )
        except PlaywrightError:
            if attempt < 2:
                await page.wait_for_timeout(5000)
    raise AppError(ErrorCode.SCRAPE_SOURCE_ERROR, "Immigration NZ site unreachable")


def is_accredited(result: dict[str, Any]) -> bool:
    return result.get("Title") != "No Results"


def extract_immigration_fields(result: dict[str, Any]) -> dict[str, str]:
    if not result.get("results"):
        return {"nzbn": "", "trading_name": ""}

    try:
        parsed = json.loads(result["results"])
        fields = (parsed[0].get("field_schema", {}).get("raw") if parsed else None) or []
        return {
            "nzbn": next(
                (
                    (field.get("Value") or "")
                    for field in fields
                    if field.get("APIColumn") == "nzbn"
                ),
                "",
            ),
            "trading_name": next(
                (
                    (field.get("Value") or "")
                    for field in fields
                    if field.get("APIColumn") == "tradingName"
                ),
                "",
            ),
        }
    except (ValueError, TypeError, AttributeError, KeyError) as exc:
        raise AppError(
            ErrorCode.SCRAPE_SOURCE_ERROR, "Immigration NZ result has an unexpected shape"
        ) from exc
