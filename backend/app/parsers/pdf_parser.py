"""
PDF text extraction using PyMuPDF (fitz).
Used as fallback when uploaded file is PDF instead of DOCX.
PDF does not support tracked changes — all text is treated as final.
"""

import io

import fitz  # PyMuPDF

from app.core.exceptions import ParseError
from app.core.logging import get_logger

logger = get_logger(__name__)


def parse_pdf(file_bytes: bytes, filename: str = "document.pdf") -> dict:
    """
    Extracts text from a PDF page by page.
    Returns same shape as docx_parser.parse_docx for uniform downstream processing,
    but with empty tracked changes and comments fields.
    """
    try:
        doc = fitz.open(stream=io.BytesIO(file_bytes), filetype="pdf")
    except Exception as exc:
        raise ParseError(f"Cannot open PDF '{filename}': {exc}") from exc

    clauses = []
    char_cursor = 0

    for page_num, page in enumerate(doc):
        text = page.get_text("text").strip()
        if not text:
            continue

        start = char_cursor
        end = start + len(text)
        char_cursor = end + 1

        clauses.append({
            "clause_number": None,
            "heading": f"Page {page_num + 1}",
            "body_text": text,
            "paragraph_index": page_num,
            "char_start": start,
            "char_end": end,
            "has_tracked_insertion": False,
            "has_tracked_deletion": False,
            "has_strikethrough": False,
            "has_comment": False,
            "change_metadata": {},
        })

    doc.close()
    full_text = "\n\n".join(c["body_text"] for c in clauses)

    logger.info("pdf_parsed", filename=filename, pages=len(clauses))

    return {
        "filename": filename,
        "clauses": clauses,
        "tracked_insertions": [],
        "tracked_deletions": [],
        "comments": [],
        "full_text": full_text,
        "total_clauses": len(clauses),
    }
