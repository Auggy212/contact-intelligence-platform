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
    Dispatches to the correct parser based on MIME type or file extension.
    Extension takes precedence so browsers that lie about MIME types still work.
    """
    name_lower = (filename or "").lower()
    if name_lower.endswith(".docx") or mime_type == _DOCX_MIME:
        return parse_docx(file_bytes, filename)
    elif name_lower.endswith(".pdf") or mime_type == _PDF_MIME:
        return parse_pdf(file_bytes, filename)
    else:
        raise ParseError(
            f"Unsupported file type '{mime_type}' / filename '{filename}'. "
            "Only .docx and .pdf files are accepted."
        )
