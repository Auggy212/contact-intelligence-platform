"""
Main DOCX parsing pipeline.

Input:  raw bytes of a .docx file
Output: normalized dict with clauses, tracked changes, comments
"""

import io
import os
import tempfile
import zipfile

from docx import Document

from app.core.exceptions import ParseError
from app.core.logging import get_logger
from app.parsers.clause_extractor import Clause, extract_clauses
from app.parsers.comment_extractor import extract_comments
from app.parsers.change_detector import extract_tracked_deletions, extract_tracked_insertions

logger = get_logger(__name__)


def parse_docx(file_bytes: bytes, filename: str = "document.docx") -> dict:
    """
    Parses a DOCX file from bytes into a normalized clause-tree dict.

    Returns:
    {
        "filename": str,
        "clauses": [
            {
                "clause_number": str | None,
                "heading": str | None,
                "body_text": str,
                "paragraph_index": int,
                "char_start": int,
                "char_end": int,
                "has_tracked_insertion": bool,
                "has_tracked_deletion": bool,
                "has_strikethrough": bool,
                "has_comment": bool,
                "change_metadata": dict,
            },
            ...
        ],
        "tracked_insertions": [...],
        "tracked_deletions": [...],
        "comments": [...],
        "full_text": str,
        "total_clauses": int,
    }
    """
    try:
        doc = Document(io.BytesIO(file_bytes))
    except Exception as exc:
        raise ParseError(f"Cannot open DOCX '{filename}': {exc}") from exc

    # Write to temp file for comment extraction (needs the zip path)
    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name

    try:
        comments = extract_comments(tmp_path)
    finally:
        os.unlink(tmp_path)

    # Build set of paragraph indices that have comments anchored to them
    comment_para_indices: set[int] = set()
    try:
        with zipfile.ZipFile(io.BytesIO(file_bytes)) as zf:
            if "word/document.xml" in zf.namelist():
                import re as _re
                doc_xml = zf.read("word/document.xml").decode("utf-8", errors="ignore")
                # Find all comment reference IDs in the document body
                ref_ids = set(_re.findall(r'w:commentReference[^>]+w:id="(\d+)"', doc_xml))
                for c in comments:
                    if c["id"] in ref_ids and c.get("paragraph_index") is not None:
                        comment_para_indices.add(c["paragraph_index"])
    except Exception:
        pass  # comment annotation is best-effort

    clauses = extract_clauses(doc)

    # Extract doc-level tracked change summaries
    doc_element = doc.element.body
    insertions = extract_tracked_insertions(doc_element)
    deletions = extract_tracked_deletions(doc_element)

    # Serialize clauses to dicts, annotating has_comment from comment anchors
    clause_dicts = []
    for clause in clauses:
        clause_dicts.append({
            "clause_number": clause.clause_number,
            "heading": clause.heading,
            "body_text": clause.body_text,
            "paragraph_index": clause.paragraph_index,
            "char_start": clause.char_start,
            "char_end": clause.char_end,
            "has_tracked_insertion": clause.has_tracked_insertion,
            "has_tracked_deletion": clause.has_tracked_deletion,
            "has_strikethrough": clause.has_strikethrough,
            "has_comment": bool(comments) and clause.paragraph_index in comment_para_indices,
            "change_metadata": clause.change_metadata,
        })

    full_text = "\n\n".join(
        f"{c['clause_number'] or ''} {c['heading'] or ''}\n{c['body_text']}".strip()
        for c in clause_dicts
    )

    logger.info(
        "docx_parsed",
        filename=filename,
        total_clauses=len(clause_dicts),
        insertions=len(insertions),
        deletions=len(deletions),
        comments=len(comments),
    )

    return {
        "filename": filename,
        "clauses": clause_dicts,
        "tracked_insertions": insertions,
        "tracked_deletions": deletions,
        "comments": comments,
        "full_text": full_text,
        "total_clauses": len(clause_dicts),
    }
