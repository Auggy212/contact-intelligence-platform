"""
Normalizes raw parsed output to a consistent shape regardless of source format.
Routes to docx_parser or pdf_parser based on MIME type.
"""

from app.core.exceptions import ParseError
from app.parsers.docx_parser import parse_docx
from app.parsers.pdf_parser import parse_pdf

_DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
_PDF_MIME = "application/pdf"

SUPPORTED_MIME_TYPES = {_DOCX_MIME, _PDF_MIME}


def parse_document(file_bytes: bytes, filename: str, mime_type: str) -> dict:
    """
    Entry point for all document parsing.
    Dispatches to the correct parser and returns a normalized clause-tree dict.
    """
    if mime_type == _DOCX_MIME or filename.lower().endswith(".docx"):
        return parse_docx(file_bytes, filename)
    elif mime_type == _PDF_MIME or filename.lower().endswith(".pdf"):
        return parse_pdf(file_bytes, filename)
    else:
        raise ParseError(
            f"Unsupported file type '{mime_type}'. Only DOCX and PDF are accepted."
        )
