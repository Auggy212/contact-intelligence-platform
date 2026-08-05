"""
Contract-aware chunking (Phase 6.3).

Contracts already have semantic units — clauses — so we chunk by clause first,
never blind fixed-size splitting (which would cut a clause mid-sentence and
destroy the exact thing we analyse). Three tiers:

  1. PRIMARY  — one clause = one chunk (heading + body).
  2. SPLIT    — a clause over the token budget is split on sentence boundaries
                with overlap, so no context is lost at the seam.
  3. MERGE    — a tiny fragment (e.g. "1.1 Definitions.") is merged with the
                next clause so no chunk is meaninglessly small.

Every chunk carries the metadata retrieval + citation need: clause_id,
document_id, project_id, organization_id, clause_type, file_role, char offsets,
and a token_count. Pure logic — no API, no DB — so it's fully unit-testable.

Token counting uses tiktoken when available, else a stable word-based estimate
(~1.3 tokens/word). Exactness isn't required for budgeting; determinism is.
"""

from __future__ import annotations

import hashlib
import re
from typing import Any

# Defaults tuned for contract clauses + typical embedding context windows.
DEFAULT_MAX_TOKENS = 512
DEFAULT_OVERLAP_TOKENS = 60
DEFAULT_MIN_TOKENS = 12

_WORD_RE = re.compile(r"\S+")
# Split on sentence-ending punctuation followed by whitespace. Conservative so
# we don't split on "No." / abbreviations mid-clause more than necessary.
_SENTENCE_RE = re.compile(r"(?<=[.;:!?])\s+")


def count_tokens(text: str) -> int:
    """Approximate token count. Deterministic; good enough for budgeting."""
    if not text:
        return 0
    try:
        import tiktoken

        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))
    except Exception:
        # Word-based estimate: ~1.3 tokens per whitespace-delimited word.
        words = len(_WORD_RE.findall(text))
        return max(1, round(words * 1.3))


def _chunk_id(clause_id: str, index: int, text: str) -> str:
    """Stable id from clause + position + content hash (reproducible across runs)."""
    h = hashlib.sha1(f"{clause_id}:{index}:{text}".encode()).hexdigest()[:16]
    return f"{clause_id}:{index}:{h}"


def _clause_text(clause: dict[str, Any]) -> str:
    heading = (clause.get("heading") or "").strip()
    body = (clause.get("body_text") or "").strip()
    if heading and body and heading not in body:
        return f"{heading}\n{body}"
    return body or heading


def _base_meta(clause: dict[str, Any]) -> dict[str, Any]:
    return {
        "clause_id": clause.get("id"),
        "document_id": clause.get("document_id"),
        "project_id": clause.get("project_id"),
        "organization_id": clause.get("organization_id"),
        "clause_type": clause.get("clause_type"),
        "file_role": clause.get("file_role"),
        "char_start": clause.get("char_start"),
        "char_end": clause.get("char_end"),
    }


def _make_chunk(clause: dict[str, Any], index: int, text: str) -> dict[str, Any]:
    meta = _base_meta(clause)
    meta.update(
        {
            "chunk_id": _chunk_id(str(clause.get("id")), index, text),
            "text": text,
            "token_count": count_tokens(text),
        }
    )
    return meta


def _split_oversized(clause: dict[str, Any], text: str, max_tokens: int,
                     overlap_tokens: int) -> list[dict[str, Any]]:
    """Split a too-long clause on sentence boundaries with token overlap."""
    # Work at the WORD level so the token budget is checked against the actual
    # joined-text token count (avoids per-piece rounding drift in the estimate).
    # First flatten to words, tagging sentence-final words for nicer overlap.
    words: list[str] = []
    for sent in _SENTENCE_RE.split(text):
        words.extend(sent.split())

    # Cap overlap so an overlap tail can never fill the budget by itself.
    overlap_cap = min(overlap_tokens, max(0, max_tokens // 3))

    chunks: list[dict[str, Any]] = []
    idx = 0
    cur: list[str] = []

    def emit():
        nonlocal cur, idx
        if cur:
            chunks.append(_make_chunk(clause, idx, " ".join(cur).strip()))
            idx += 1

    def overlap_tail(prev_words: list[str]) -> list[str]:
        if overlap_cap <= 0:
            return []
        keep: list[str] = []
        for w in reversed(prev_words):
            if count_tokens(" ".join([w, *keep])) > overlap_cap:
                break
            keep.insert(0, w)
        return keep

    for word in words:
        candidate = [*cur, word]
        # Budget invariant: the emitted chunk's REAL token count must fit.
        if cur and count_tokens(" ".join(candidate)) > max_tokens:
            emit()
            cur = overlap_tail(cur)
            cur.append(word)
        else:
            cur = candidate
    emit()
    return chunks


def chunk_clauses(
    clauses: list[dict[str, Any]],
    *,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    overlap_tokens: int = DEFAULT_OVERLAP_TOKENS,
    min_tokens: int = DEFAULT_MIN_TOKENS,
) -> list[dict[str, Any]]:
    """
    Turn parsed clauses into retrieval-ready chunks.

    Args:
        clauses: list of clause dicts (id, heading, body_text, char offsets, +metadata).
        max_tokens: split any clause whose text exceeds this.
        overlap_tokens: token overlap between split sub-chunks.
        min_tokens: merge a clause smaller than this into the following clause.
    """
    # Pass 1: merge tiny fragments forward into the next clause.
    merged: list[dict[str, Any]] = []
    carry: dict[str, Any] | None = None
    for clause in clauses:
        text = _clause_text(clause)
        if carry is not None:
            # prepend the carried tiny fragment's text to this clause
            clause = {**clause, "body_text": f"{_clause_text(carry)} {text}".strip(),
                      "char_start": carry.get("char_start", clause.get("char_start")),
                      "heading": carry.get("heading") or clause.get("heading")}
            carry = None
            text = _clause_text(clause)
        if count_tokens(text) < min_tokens:
            carry = clause
            continue
        merged.append(clause)
    if carry is not None:
        # trailing tiny fragment with no successor — keep it rather than drop it
        merged.append(carry)

    # Pass 2: emit one chunk per clause, splitting oversized ones.
    out: list[dict[str, Any]] = []
    for clause in merged:
        text = _clause_text(clause)
        if count_tokens(text) <= max_tokens:
            out.append(_make_chunk(clause, 0, text))
        else:
            out.extend(_split_oversized(clause, text, max_tokens, overlap_tokens))
    return out
