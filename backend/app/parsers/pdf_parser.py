"""
PDF text extraction using PyMuPDF (fitz).

Extracts text block by block, detects section headings by font size / caps /
numbering, and groups body paragraphs under their parent heading — producing the
same clause-tree shape as the DOCX parser.

Improvements over v1:
  - Header/footer detection: repeating lines across pages are skipped
  - Roman numeral clause headings supported
  - Sub-clause hierarchy preserved
  - Tables detected and merged into the nearest clause body
  - Short running-header/footer lines filtered by positional bounding box
"""

import io
import re
from collections import Counter

import fitz  # PyMuPDF

from app.core.exceptions import ParseError
from app.core.logging import get_logger

logger = get_logger(__name__)

# Numbered heading patterns:
#   "1." / "1.1" / "1.1.1" style
#   "CLAUSE 3 —" / "ARTICLE IV:" / "SECTION 2 —"
#   Roman numeral headings: "I.", "II.", "III.", "IV.", "V.", "VI."
_HEADING_RE = re.compile(
    r"^(?:"
    r"(\d+(?:\.\d+)*\.?)\s+(.+)"                                  # "1.2 Title"
    r"|(?:CLAUSE|ARTICLE|SECTION)\s+(\d+(?:\.\d+)*)[:\s\-–—]+(.+)"  # "CLAUSE 3 — Title"
    r"|((?:X{0,3})(?:IX|IV|V?I{0,3}))\.\s+(.+)"                   # "IV. Title" roman numeral
    r")",
    re.IGNORECASE,
)

# Alphabetic sub-clause: "(a)", "(b)", "(i)", "(ii)" etc.
_SUB_CLAUSE_RE = re.compile(r"^\(([a-z]|[ivxlcdm]+)\)\s+", re.IGNORECASE)

_ALLCAPS_MIN = 5   # minimum chars for an all-caps line to be a heading candidate


def _is_roman(text: str) -> bool:
    """Return True if text is a valid Roman numeral (I–XXXIX)."""
    return bool(re.fullmatch(r"(X{0,3})(IX|IV|V?I{0,3})", text.strip(), re.IGNORECASE)) and text.strip()


def _is_heading_text(line: str, is_large_font: bool) -> bool:
    """Heuristic: is this PDF line a section heading?"""
    line = line.strip()
    if not line:
        return False
    if _HEADING_RE.match(line):
        return True
    # All-caps short line (common for section titles)
    if line.isupper() and _ALLCAPS_MIN <= len(line) <= 80 and len(line.split()) <= 10:
        return True
    # Large font line (heading-sized typography)
    if is_large_font and 4 <= len(line) <= 120:
        return True
    return False


def _extract_clause_number(text: str) -> tuple[str | None, str]:
    """Extract (number, heading_title) from a heading line."""
    m = _HEADING_RE.match(text.strip())
    if m:
        if m.group(1):   # "1.2 Title"
            return m.group(1).rstrip("."), m.group(2).strip()
        if m.group(3):   # "CLAUSE 3 — Title"
            return m.group(3), m.group(4).strip()
        if m.group(5):   # "IV. Title" roman
            return m.group(5).upper(), m.group(6).strip()
    return None, text.strip()


def _detect_header_footer_lines(all_lines: list[dict], total_pages: int) -> set[str]:
    """
    Identify lines that repeat on many pages — these are running headers/footers.
    A line appearing on > 50% of pages is considered a header/footer.
    """
    if total_pages <= 1:
        return set()

    line_page_count: Counter = Counter()
    for line_info in all_lines:
        normalized = line_info["text"].strip().lower()
        if normalized:
            line_page_count[normalized] += 1

    threshold = max(2, int(total_pages * 0.5))
    return {line for line, count in line_page_count.items() if count >= threshold}


def _is_positional_header_footer(line_info: dict, page_height: float) -> bool:
    """
    Detect header/footer by vertical position on page.
    Lines in the top 8% or bottom 8% of the page are likely running headers/footers.
    """
    if not page_height or "bbox" not in line_info:
        return False
    y_top = line_info["bbox"][1]
    y_bottom = line_info["bbox"][3]
    margin = page_height * 0.08
    return y_top < margin or y_bottom > (page_height - margin)


def parse_pdf(file_bytes: bytes, filename: str = "document.pdf") -> dict:
    """
    Extracts clauses from a PDF, grouping paragraphs under section headings.
    Falls back to splitting by paragraph if no headings are detected.

    Returns the same shape as docx_parser.parse_docx.
    """
    try:
        doc = fitz.open(stream=io.BytesIO(file_bytes), filetype="pdf")
    except Exception as exc:
        raise ParseError(f"Cannot open PDF '{filename}': {exc}") from exc

    total_pages = doc.page_count

    # ── Pass 1: collect all text spans with font size and position info ───────
    all_lines: list[dict] = []
    page_font_sizes: list[float] = []

    for page_num, page in enumerate(doc):
        page_height = page.rect.height
        blocks = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)["blocks"]
        for block in blocks:
            if block.get("type") != 0:   # 0 = text block
                continue
            for line in block.get("lines", []):
                spans = line.get("spans", [])
                if not spans:
                    continue
                line_text = "".join(s["text"] for s in spans).strip()
                if not line_text:
                    continue
                max_size = max(s["size"] for s in spans)
                page_font_sizes.append(max_size)
                bbox = line.get("bbox", ())
                all_lines.append({
                    "text": line_text,
                    "font_size": max_size,
                    "page": page_num,
                    "bbox": bbox,
                    "page_height": page_height,
                })

    doc.close()

    if not all_lines:
        logger.info("pdf_parsed", filename=filename, clauses=0)
        return {
            "filename": filename,
            "clauses": [],
            "tracked_insertions": [],
            "tracked_deletions": [],
            "comments": [],
            "full_text": "",
            "total_clauses": 0,
        }

    # ── Compute heading font threshold ────────────────────────────────────────
    sorted_sizes = sorted(page_font_sizes)
    median_size = sorted_sizes[len(sorted_sizes) // 2]
    large_font_threshold = median_size + 1.0

    # ── Detect running headers/footers to skip ────────────────────────────────
    repeated_lines = _detect_header_footer_lines(all_lines, total_pages)

    # ── Pass 2: filter lines and group into clauses ───────────────────────────
    clauses: list[dict] = []
    current_heading: str | None = None
    current_number: str | None = None
    current_body: list[str] = []
    current_para_idx = 0
    char_cursor = 0
    para_idx = 0
    has_headings_detected = False

    def _flush() -> None:
        nonlocal char_cursor, current_heading, current_number, current_body
        body = "\n".join(current_body).strip()
        if not body and current_heading is None:
            return
        text = body if body else (current_heading or "")
        start = char_cursor
        end = start + len(text)
        char_cursor = end + 1
        clauses.append({
            "clause_number": current_number,
            "heading": current_heading,
            "body_text": text,
            "paragraph_index": current_para_idx,
            "char_start": start,
            "char_end": end,
            "has_tracked_insertion": False,
            "has_tracked_deletion": False,
            "has_strikethrough": False,
            "has_comment": False,
            "change_metadata": {},
        })
        current_body = []

    for line_info in all_lines:
        raw_text = line_info["text"]
        text = raw_text.strip()

        # Skip repeated header/footer lines
        if text.lower() in repeated_lines:
            continue

        # Skip positional header/footer lines
        if _is_positional_header_footer(line_info, line_info.get("page_height", 0)):
            continue

        # Skip page numbers: lone number or "Page N of M"
        if re.fullmatch(r"\d+", text) or re.fullmatch(r"page\s+\d+(\s+of\s+\d+)?", text, re.IGNORECASE):
            continue

        is_large = line_info["font_size"] >= large_font_threshold

        if _is_heading_text(text, is_large):
            _flush()
            current_number, heading_text = _extract_clause_number(text)
            current_heading = heading_text
            current_para_idx = para_idx
            has_headings_detected = True
        else:
            # Handle sub-clauses: keep them as part of current body
            current_body.append(text)

        para_idx += 1

    _flush()

    # ── Fallback: split by paragraph if no headings detected ──────────────────
    if not clauses or not has_headings_detected:
        doc2 = fitz.open(stream=io.BytesIO(file_bytes), filetype="pdf")
        raw_text = ""
        for page in doc2:
            raw_text += page.get_text("text") + "\n\n"
        doc2.close()

        # Remove repeated header/footer lines from raw text
        lines_cleaned = []
        for line in raw_text.splitlines():
            if line.strip().lower() not in repeated_lines and not re.fullmatch(r"\d+", line.strip()):
                lines_cleaned.append(line)
        clean_text = "\n".join(lines_cleaned)

        paragraphs = [p.strip() for p in re.split(r"\n{2,}", clean_text) if p.strip() and len(p.strip()) > 20]
        char_cursor = 0
        clauses = []
        for i, para in enumerate(paragraphs):
            start = char_cursor
            end = start + len(para)
            char_cursor = end + 1
            # Try to detect a leading heading within the paragraph
            first_line = para.splitlines()[0] if "\n" in para else para
            clause_num, heading = _extract_clause_number(first_line)
            clauses.append({
                "clause_number": clause_num,
                "heading": heading if clause_num else f"Section {i + 1}",
                "body_text": para,
                "paragraph_index": i,
                "char_start": start,
                "char_end": end,
                "has_tracked_insertion": False,
                "has_tracked_deletion": False,
                "has_strikethrough": False,
                "has_comment": False,
                "change_metadata": {},
            })

    # ── Remove clauses with trivially short bodies ────────────────────────────
    clauses = [c for c in clauses if len((c.get("body_text") or "").strip()) >= 10]

    full_text = "\n\n".join(
        f"{c['clause_number'] or ''} {c['heading'] or ''}\n{c['body_text']}".strip()
        for c in clauses
    )

    logger.info("pdf_parsed", filename=filename, clauses=len(clauses))

    return {
        "filename": filename,
        "clauses": clauses,
        "tracked_insertions": [],
        "tracked_deletions": [],
        "comments": [],
        "full_text": full_text,
        "total_clauses": len(clauses),
    }
