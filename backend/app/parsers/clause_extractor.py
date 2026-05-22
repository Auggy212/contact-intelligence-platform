"""
Extracts clauses from a parsed python-docx Document object.

A "clause" is a logical unit: a numbered heading + its following body paragraphs.
Unnumbered paragraphs between headings are grouped under the previous heading.
"""

import re
from dataclasses import dataclass, field

from docx import Document
from docx.oxml.ns import qn

from app.parsers.change_detector import has_any_change

_CLAUSE_NUMBER_RE = re.compile(
    r"^(\d+(\.\d+)*\.?)\s+",  # Matches "1.", "1.2", "1.2.3." etc.
)


@dataclass
class Clause:
    clause_number: str | None
    heading: str | None
    body_text: str
    paragraph_index: int
    char_start: int
    char_end: int
    has_tracked_insertion: bool = False
    has_tracked_deletion: bool = False
    has_strikethrough: bool = False
    has_comment: bool = False
    change_metadata: dict = field(default_factory=dict)


def _is_heading(paragraph) -> bool:
    return paragraph.style.name.startswith("Heading")


def _extract_clause_number(text: str) -> tuple[str | None, str]:
    """Returns (clause_number, remaining_text) from a heading string."""
    match = _CLAUSE_NUMBER_RE.match(text.strip())
    if match:
        num = match.group(1)
        rest = text[match.end():].strip()
        return num, rest
    return None, text.strip()


def extract_clauses(doc: Document) -> list[Clause]:
    """
    Walks the document's paragraphs and groups them into Clause objects.
    Preserves character offsets from the full joined document text.
    """
    clauses: list[Clause] = []
    current_heading: str | None = None
    current_number: str | None = None
    current_body_parts: list[str] = []
    current_para_idx: int = 0
    char_cursor = 0

    def flush(para_idx: int, change_flags: dict) -> None:
        nonlocal char_cursor
        if not current_body_parts and current_heading is None:
            return
        body = "\n".join(current_body_parts)
        start = char_cursor
        end = start + len(body)
        char_cursor = end + 1  # +1 for the newline separator

        clauses.append(Clause(
            clause_number=current_number,
            heading=current_heading,
            body_text=body,
            paragraph_index=para_idx,
            char_start=start,
            char_end=end,
            has_tracked_insertion=change_flags.get("insertion", False),
            has_tracked_deletion=change_flags.get("deletion", False),
            has_strikethrough=change_flags.get("strikethrough", False),
        ))

    change_flags: dict = {}

    for idx, para in enumerate(doc.paragraphs):
        text = para.text.strip()
        if not text:
            continue

        para_element = para._element
        flags = has_any_change(para_element)

        # Merge flags across all paragraphs in the current clause
        change_flags = {
            "insertion": change_flags.get("insertion", False) or flags["insertion"],
            "deletion": change_flags.get("deletion", False) or flags["deletion"],
            "strikethrough": change_flags.get("strikethrough", False) or flags["strikethrough"],
        }

        if _is_heading(para):
            flush(current_para_idx, change_flags)
            change_flags = flags
            current_number, heading_text = _extract_clause_number(text)
            current_heading = heading_text
            current_body_parts = []
            current_para_idx = idx
        else:
            current_body_parts.append(text)

    flush(current_para_idx, change_flags)
    return clauses
