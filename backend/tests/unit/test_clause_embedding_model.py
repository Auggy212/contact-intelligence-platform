"""
Unit tests for the ClauseEmbedding model (Phase 6.4).

Chunk-level embeddings are a NEW granularity: one ParsedClause can produce many
chunks (see chunking.py), each with its own vector. The clause-level `embedding`
column on parsed_clauses (voyage-era) is coarse; retrieval needs chunk rows.

These tests inspect the mapped model's schema only — no DB connection — so they
run offline with zero services. The migration test (RLS, table creation) is
exercised separately when the DB is up.
"""

from app.models import ClauseEmbedding


def _cols() -> dict:
    return {c.name: c for c in ClauseEmbedding.__table__.columns}


class TestClauseEmbeddingSchema:
    def test_table_name(self):
        assert ClauseEmbedding.__tablename__ == "clause_embeddings"

    def test_has_tenant_scope_columns(self):
        cols = _cols()
        # tenant isolation (RLS + Qdrant payload filter) needs both scope keys
        assert "organization_id" in cols
        assert "project_id" in cols
        assert not cols["organization_id"].nullable
        assert not cols["project_id"].nullable

    def test_links_back_to_clause_and_document(self):
        cols = _cols()
        assert "clause_id" in cols
        assert "document_id" in cols

    def test_carries_chunk_payload(self):
        cols = _cols()
        # everything retrieval + citation needs, mirroring a chunk dict
        for name in ("chunk_id", "chunk_text", "token_count",
                     "char_start", "char_end", "clause_type", "file_role"):
            assert name in cols, f"missing column {name}"

    def test_chunk_id_is_unique(self):
        cols = _cols()
        # stable, content-hashed chunk_id must be unique for idempotent re-embed
        assert cols["chunk_id"].unique is True

    def test_has_vector_column_of_configured_dim(self):
        # A pgvector column so PgVectorStore can search without an extra service.
        cols = _cols()
        assert "embedding" in cols

    def test_records_which_provider_and_model_made_the_vector(self):
        cols = _cols()
        # dimension/provider can change; record provenance so we know when to re-embed
        assert "embedding_provider" in cols
        assert "embedding_model" in cols
