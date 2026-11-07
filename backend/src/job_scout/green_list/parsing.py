import json
import re
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Any

from job_scout.core.errors import AppError, ErrorCode

_BLOCKS = {"p", "div", "br", "ul", "ol", "tr", "h1", "h2", "h3", "h4", "h5", "h6"}
_TIER = re.compile(r"\s*Tier (\d)\b")


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._skipping = 0

    def handle_starttag(self, tag: str, attrs: Any) -> None:
        if tag in ("script", "style"):
            self._skipping += 1
        elif tag == "li":
            self.parts.append("\n• ")
        elif tag in _BLOCKS:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in ("script", "style"):
            self._skipping = max(0, self._skipping - 1)
        elif tag == "li" or tag in _BLOCKS:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self._skipping:
            self.parts.append(data)


def html_to_text(html: str) -> str:
    """Plain text for display: no tags or scripts, list items as bullets, a line per block."""
    extractor = _TextExtractor()
    extractor.feed(html)
    extractor.close()
    lines = (
        re.sub(r"[ \t\r\f\v]+", " ", line).strip() for line in "".join(extractor.parts).split("\n")
    )
    return "\n".join(line for line in lines if line)


@dataclass(frozen=True)
class RoleRecord:
    record_id: str
    title: str
    anzsco_code: str
    industry: str
    tier: int
    pathway: str
    requirements: str
    engineering_degrees: str
    note: str
    raw: dict[str, Any]


def _raw(value: Any) -> Any:
    return value.get("raw") if isinstance(value, dict) else value


def parse_record(record: dict[str, Any]) -> RoleRecord:
    """Read one Immigration NZ search result; anything unexpected is refused, never guessed."""
    try:
        record_id = str(_raw(record["record_id"])).strip()
        fields = json.loads(_raw(record["field_schema"]))
        by_title = {field.get("Title"): str(field.get("Value") or "") for field in fields}
        title = str(_raw(record["title"])).strip() or by_title.get("Role", "").strip()
    except (KeyError, TypeError, ValueError) as exc:
        raise AppError(
            ErrorCode.SCRAPE_SOURCE_ERROR, f"Unreadable Green List record: {exc!r}"
        ) from exc
    # The tier sits in a column whose title is the ANZSCO code, so find it by its value.
    tier = next(
        (
            int(match.group(1))
            for field in fields
            if (match := _TIER.match(str(field.get("Value") or "")))
        ),
        None,
    )
    if not record_id or not title or tier is None:
        raise AppError(
            ErrorCode.SCRAPE_SOURCE_ERROR,
            f"Green List record {record_id or '?'} has no id, title or tier",
        )
    note = html_to_text(by_title.get("Note", ""))
    return RoleRecord(
        record_id=record_id,
        title=title,
        anzsco_code=re.sub(r"(?i)^\s*ANZSCO\s*", "", by_title.get("ANZSCO number", "")).strip(),
        industry=by_title.get("Industry", "").strip(),
        tier=tier,
        pathway=html_to_text(by_title.get("Pathway to residence", "")),
        requirements=html_to_text(by_title.get("Green List requirements", "")),
        engineering_degrees=html_to_text(
            by_title.get("Washington and Sydney Accord engineering degrees", "")
        ),
        note="" if note.lower() == "none" else note,
        raw=record,
    )
