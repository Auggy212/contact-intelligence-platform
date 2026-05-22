"""
Extracts inline reviewer comments from a DOCX file.

Comments in DOCX are stored in word/comments.xml, with anchors in the
main document referencing them via <w:commentReference w:id="N"/>.
"""

import zipfile
from lxml import etree

_W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def _qn(tag: str) -> str:
    return f"{{{_W}}}{tag}"


def extract_comments(docx_path: str) -> list[dict]:
    """
    Opens the DOCX zip and parses word/comments.xml.
    Returns list of: {
        "id": str,
        "author": str,
        "date": str,
        "text": str,
        "paragraph_index": int | None  (None if anchor lookup is skipped)
    }
    """
    comments = []
    try:
        with zipfile.ZipFile(docx_path, "r") as zf:
            if "word/comments.xml" not in zf.namelist():
                return []
            comments_xml = zf.read("word/comments.xml")
    except (zipfile.BadZipFile, KeyError):
        return []

    root = etree.fromstring(comments_xml)
    for comment in root.findall(_qn("comment")):
        comment_id = comment.get(_qn("id"), "")
        author = comment.get(_qn("author"), "")
        date = comment.get(_qn("date"), "")
        text_parts = [t.text or "" for t in comment.findall(f".//{_qn('t')}")]
        text = " ".join(text_parts).strip()
        if text:
            comments.append({
                "id": comment_id,
                "author": author,
                "date": date,
                "text": text,
                "paragraph_index": None,
            })
    return comments
