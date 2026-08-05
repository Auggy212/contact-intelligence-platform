"""
Unit tests for contract-aware chunking (Phase 6.3).

Pure logic — no API calls, no DB. Verifies:
  - one clause → one chunk (the common case)
  - an oversized clause splits on sentence boundaries with overlap
  - tiny fragments merge with a neighbour
  - every chunk carries the metadata needed for retrieval + citation
  - no chunk exceeds the token budget
  - deterministic, stable chunk ordering
"""

from app.ai.chunking import chunk_clauses, count_tokens


def _clause(cid, body, heading=None, char_start=0, clause_type="general", file_role="B"):
    return {
        "id": cid,
        "heading": heading,
        "body_text": body,
        "char_start": char_start,
        "char_end": char_start + len(body),
        "clause_type": clause_type,
        "file_role": file_role,
        "document_id": "doc-1",
        "project_id": "proj-1",
        "organization_id": "org-1",
    }


class TestBasicChunking:
    def test_one_normal_clause_one_chunk(self):
        clauses = [_clause("c1", "The vendor shall deliver the services within thirty days.")]
        chunks = chunk_clauses(clauses)
        assert len(chunks) == 1
        assert chunks[0]["clause_id"] == "c1"
        assert "vendor shall deliver" in chunks[0]["text"]

    def test_heading_included_in_chunk_text(self):
        clauses = [_clause("c1", "Body text here.", heading="1. INDEMNITY")]
        chunks = chunk_clauses(clauses)
        assert "INDEMNITY" in chunks[0]["text"]

    def test_metadata_preserved(self):
        clauses = [_clause("c1", "Some clause body.", clause_type="indemnity", file_role="C")]
        chunk = chunk_clauses(clauses)[0]
        for key in ("chunk_id", "clause_id", "document_id", "project_id",
                    "organization_id", "clause_type", "file_role",
                    "char_start", "char_end", "token_count"):
            assert key in chunk
        assert chunk["clause_type"] == "indemnity"
        assert chunk["organization_id"] == "org-1"

    def test_chunk_ids_are_unique_and_stable(self):
        clauses = [_clause("c1", "First."), _clause("c2", "Second.")]
        a = chunk_clauses(clauses)
        b = chunk_clauses(clauses)
        ids = [c["chunk_id"] for c in a]
        assert len(set(ids)) == len(ids)          # unique
        assert ids == [c["chunk_id"] for c in b]   # stable across runs


class TestOversizedClause:
    def test_long_clause_splits_into_multiple_chunks(self):
        # Build a clause well over the token budget from many sentences.
        sentence = "This is a materially long sentence about obligations and liability. "
        body = sentence * 120  # far exceeds a 512-token budget
        clauses = [_clause("big", body)]
        chunks = chunk_clauses(clauses, max_tokens=512, overlap_tokens=60)
        assert len(chunks) > 1
        # all sub-chunks trace back to the same clause
        assert all(c["clause_id"] == "big" for c in chunks)

    def test_no_chunk_exceeds_token_budget(self):
        sentence = "Obligations and liability provisions apply here in detail. "
        clauses = [_clause("big", sentence * 200)]
        chunks = chunk_clauses(clauses, max_tokens=256, overlap_tokens=30)
        assert all(c["token_count"] <= 256 for c in chunks)

    def test_consecutive_chunks_overlap(self):
        sentence = "Alpha bravo charlie delta echo foxtrot golf hotel india. "
        clauses = [_clause("big", sentence * 100)]
        chunks = chunk_clauses(clauses, max_tokens=128, overlap_tokens=30)
        # The end of chunk k should share some words with the start of chunk k+1.
        first_tail = set(chunks[0]["text"].split()[-15:])
        second_head = set(chunks[1]["text"].split()[:15])
        assert first_tail & second_head


class TestTinyFragmentMerge:
    def test_tiny_clause_merges_with_neighbour(self):
        clauses = [
            _clause("c1", "1.1 Definitions.", char_start=0),               # tiny
            _clause("c2", "Confidential Information means all non-public data "
                          "disclosed by either party under this Agreement.", char_start=20),
        ]
        chunks = chunk_clauses(clauses, min_tokens=8)
        # The tiny fragment should not survive as its own chunk.
        assert len(chunks) == 1
        assert "Definitions" in chunks[0]["text"]
        assert "Confidential Information" in chunks[0]["text"]


class TestTokenCounter:
    def test_count_tokens_positive(self):
        assert count_tokens("hello world this is a test") > 0

    def test_empty_is_zero(self):
        assert count_tokens("") == 0
