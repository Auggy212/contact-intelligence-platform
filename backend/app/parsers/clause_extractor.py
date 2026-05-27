"""
Extracts clauses from a parsed python-docx Document object.

A "clause" is a logical unit: a heading + its following body paragraphs.

Detection priority:
  1. Word Heading styles ("Heading 1", "Heading 2", …)
  2. Numbered paragraphs detected by regex ("1.", "2.1", "CLAUSE 3 —")
  3. Roman numeral headings: "I.", "II.", "III.", "IV.", etc.
  4. ALL CAPS short lines (likely informal headings)
  5. Bold-only short lines (likely informal headings)
  6. Fallback: every paragraph becomes its own "Section N" clause

Sub-clause support:
  - "(a)", "(b)", "(i)", "(ii)" lines are treated as body content of the parent clause
  - Nested numbering "1.1.1" is recognized
  - Empty body clauses (heading only) are preserved
"""

import re
from dataclasses import dataclass, field

from docx import Document

from app.parsers.change_detector import has_any_change

# Primary numbered heading: "1.", "2.1", "3.2.1"
_CLAUSE_NUMBER_RE = re.compile(r"^(\d+(?:\.\d+)*\.?)\s+")

# Full heading detection: numbered, CLAUSE/ARTICLE/SECTION prefix, or Roman numeral
_NUMBERED_HEADING_RE = re.compile(
    r"^(?:"
    r"(\d+(?:\.\d+)*\.?)\s+(.+)"                                    # "1.2 Title"
    r"|(?:CLAUSE|ARTICLE|SECTION)\s+(\d+(?:\.\d+)*)[:\s\-–—]+(.+)"  # "CLAUSE 3 — Title"
    r"|((?:X{0,3})(?:IX|IV|V?I{0,3}))\.\s+(.+)"                     # "IV. Title" roman numeral
    r")",
    re.IGNORECASE,
)

# Sub-clause pattern: "(a)", "(b)", "(i)", "(ii)", "(iii)" etc.
_SUB_CLAUSE_RE = re.compile(r"^\([a-z]|(?:iv|ix|v?i{1,3}|x{1,3})\)\s+", re.IGNORECASE)

_ALLCAPS_MIN = 5
_BOLD_HEADING_MAX_WORDS = 12


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


def _para_is_entirely_bold(para) -> bool:
    runs = [r for r in para.runs if r.text.strip()]
    return bool(runs) and all(r.bold for r in runs)


def _is_word_heading(para) -> bool:
    return para.style.name.startswith("Heading")


def _is_roman_numeral(text: str) -> bool:
    """Return True if text matches a Roman numeral heading like 'IV. Title'."""
    return bool(re.match(
        r"^((?:X{0,3})(?:IX|IV|V?I{0,3}))\.\s+\S",
        text.strip(),
        re.IGNORECASE,
    ))


def _is_numbered_heading(text: str) -> bool:
    stripped = text.strip()
    return bool(_NUMBERED_HEADING_RE.match(stripped))


def _is_allcaps_heading(text: str) -> bool:
    stripped = text.strip()
    return (
        stripped.isupper()
        and len(stripped) >= _ALLCAPS_MIN
        and len(stripped.split()) <= 10
        and len(stripped) <= 100
    )


def _is_bold_heading(para, text: str) -> bool:
    if len(text.split()) > _BOLD_HEADING_MAX_WORDS:
        return False
    return _para_is_entirely_bold(para)


def _is_sub_clause(text: str) -> bool:
    """Return True for alphabetic/roman sub-clauses like (a), (b), (i), (ii)."""
    return bool(_SUB_CLAUSE_RE.match(text.strip()))


def _classify_as_heading(para, text: str) -> bool:
    """
    Returns True if this paragraph should be treated as a clause heading.
    Sub-clauses are explicitly NOT headings — they belong to the parent body.
    """
    if _is_sub_clause(text):
        return False
    return (
        _is_word_heading(para)
        or _is_numbered_heading(text)
        or _is_allcaps_heading(text)
        or _is_bold_heading(para, text)
    )


def _extract_clause_number(text: str) -> tuple[str | None, str]:
    """
    Extract (clause_number, heading_title) from a heading string.
    Returns (None, original_text) if no number is found.
    """
    m = _NUMBERED_HEADING_RE.match(text.strip())
    if m:
        if m.group(1):   # "1.2 Title"
            return m.group(1).rstrip("."), m.group(2).strip()
        if m.group(3):   # "CLAUSE 3 — Title"
            return m.group(3), m.group(4).strip()
        if m.group(5):   # "IV. Title" roman numeral
            return m.group(5).upper(), m.group(6).strip()

    # Plain numbered prefix "1. " without the keyword CLAUSE/ARTICLE
    m2 = _CLAUSE_NUMBER_RE.match(text.strip())
    if m2:
        num = m2.group(1).rstrip(".")
        rest = text.strip()[m2.end():].strip()
        return num, rest or text.strip()

    return None, text.strip()


def _merge_flags(a: dict, b: dict) -> dict:
    return {
        "insertion": a.get("insertion", False) or b.get("insertion", False),
        "deletion": a.get("deletion", False) or b.get("deletion", False),
        "strikethrough": a.get("strikethrough", False) or b.get("strikethrough", False),
    }


def extract_clauses(doc: Document) -> list[Clause]:
    """
    Walk paragraphs and group them into Clause objects.
    Automatically falls back when no formal headings are present.
    """
    paragraphs = []
    for idx, para in enumerate(doc.paragraphs):
        text = para.text.strip()
        if not text:
            continue
        flags = has_any_change(para._element)
        paragraphs.append({"idx": idx, "para": para, "text": text, "flags": flags})

    if not paragraphs:
        return []

    # Detect whether any heading-style markers exist
    has_headings = any(
        _classify_as_heading(p["para"], p["text"]) for p in paragraphs
    )

    clauses: list[Clause] = []
    char_cursor = 0

    if has_headings:
        current_heading: str | None = None
        current_number: str | None = None
        current_body: list[str] = []
        current_para_idx = paragraphs[0]["idx"]
        current_flags: dict = {}

        def flush(para_idx: int, flags: dict) -> None:
            nonlocal char_cursor
            body = "\n".join(current_body).strip()
            if not body and current_heading is None:
                return
            text = body if body else (current_heading or "")
            start = char_cursor
            end = start + len(text)
            char_cursor = end + 1
            clauses.append(Clause(
                clause_number=current_number,
                heading=current_heading,
                body_text=text,
                paragraph_index=para_idx,
                char_start=start,
                char_end=end,
                has_tracked_insertion=flags.get("insertion", False),
                has_tracked_deletion=flags.get("deletion", False),
                has_strikethrough=flags.get("strikethrough", False),
            ))

        for p in paragraphs:
            text = p["text"]
            flags = p["flags"]

            if _classify_as_heading(p["para"], text):
                flush(current_para_idx, current_flags)
                current_flags = flags
                current_number, heading_text = _extract_clause_number(text)
                current_heading = heading_text
                current_body = []
                current_para_idx = p["idx"]
            else:
                # Sub-clause and body paragraphs go into the current clause body
                current_body.append(text)
                current_flags = _merge_flags(current_flags, flags)

        flush(current_para_idx, current_flags)

    else:
        # No headings found — each paragraph becomes its own clause
        # Try to detect inline numbering like "1. Intro text here" as the heading
        for i, p in enumerate(paragraphs):
            text = p["text"]
            flags = p["flags"]

            # Attempt to split first sentence as heading
            clause_num, heading_text = _extract_clause_number(text)
            if not clause_num:
                heading_text = f"Section {i + 1}"

            start = char_cursor
            end = start + len(text)
            char_cursor = end + 1
            clauses.append(Clause(
                clause_number=clause_num,
                heading=heading_text,
                body_text=text,
                paragraph_index=p["idx"],
                char_start=start,
                char_end=end,
                has_tracked_insertion=flags["insertion"],
                has_tracked_deletion=flags["deletion"],
                has_strikethrough=flags["strikethrough"],
            ))

    # Filter out clauses with empty bodies that are just whitespace
    return [c for c in clauses if (c.body_text or "").strip()]
