"""
OOXML change detection for DOCX files.

Handles three distinct markup types in the Word XML:
  - Tracked insertions:  <w:ins>  wraps inserted runs
  - Tracked deletions:   <w:del>  wraps deleted runs, text in <w:delText>
  - Strikethroughs:      <w:strike> inside <w:rPr> (manual formatting, not tracked)
"""

from lxml import etree

# OOXML namespace
_W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def _qn(tag: str) -> str:
    """Returns the Clark-notation qualified name for a w: element."""
    return f"{{{_W}}}{tag}"


def is_strikethrough(run_element: etree._Element) -> bool:
    """True if the run has w:strike in its run properties."""
    rpr = run_element.find(_qn("rPr"))
    if rpr is None:
        return False
    strike = rpr.find(_qn("strike"))
    if strike is None:
        return False
    # w:strike with val="0" explicitly disables it
    val = strike.get(_qn("val"))
    return val != "0"


def extract_tracked_insertions(doc_element: etree._Element) -> list[dict]:
    """
    Returns all tracked insertions found in the document XML.
    Each item: {"author": str, "date": str, "text": str, "paragraph_index": int}
    """
    insertions = []
    paragraphs = doc_element.findall(f".//{_qn('p')}")
    for para_idx, para in enumerate(paragraphs):
        for ins in para.findall(f".//{_qn('ins')}"):
            author = ins.get(_qn("author"), "")
            date = ins.get(_qn("date"), "")
            text_parts = [t.text or "" for t in ins.findall(f".//{_qn('t')}")]
            text = "".join(text_parts)
            if text.strip():
                insertions.append({
                    "author": author,
                    "date": date,
                    "text": text,
                    "paragraph_index": para_idx,
                })
    return insertions


def extract_tracked_deletions(doc_element: etree._Element) -> list[dict]:
    """
    Returns all tracked deletions found in the document XML.
    Deleted text lives in <w:delText>, not <w:t>.
    Each item: {"author": str, "date": str, "text": str, "paragraph_index": int}
    """
    deletions = []
    paragraphs = doc_element.findall(f".//{_qn('p')}")
    for para_idx, para in enumerate(paragraphs):
        for del_elem in para.findall(f".//{_qn('del')}"):
            author = del_elem.get(_qn("author"), "")
            date = del_elem.get(_qn("date"), "")
            text_parts = [t.text or "" for t in del_elem.findall(f".//{_qn('delText')}")]
            text = "".join(text_parts)
            if text.strip():
                deletions.append({
                    "author": author,
                    "date": date,
                    "text": text,
                    "paragraph_index": para_idx,
                })
    return deletions


def has_any_change(paragraph: etree._Element) -> dict[str, bool]:
    """
    Checks a single paragraph element for all change types.
    Returns flags: {"insertion": bool, "deletion": bool, "strikethrough": bool}
    """
    has_insertion = len(paragraph.findall(f".//{_qn('ins')}")) > 0
    has_deletion = len(paragraph.findall(f".//{_qn('del')}")) > 0

    has_strike = False
    for run in paragraph.findall(f".//{_qn('r')}"):
        if is_strikethrough(run):
            has_strike = True
            break

    return {
        "insertion": has_insertion,
        "deletion": has_deletion,
        "strikethrough": has_strike,
    }
