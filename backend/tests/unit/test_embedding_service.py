"""
Unit tests for the embedding service (Phase 6.5) — the embed-on-parse core.

The service turns parsed clauses into chunk embeddings and writes them to BOTH
Postgres (source of truth) and the vector store (derived index). It's built
around a pure, dependency-injected core so it runs offline with:
  - a FAKE embedding provider (deterministic vectors, no API, no credits)
  - a FAKE vector store (records upserts in memory, no Qdrant)
  - plain clause dicts (no DB)

We assert the contract that matters:
  - clauses are chunked, then embedded (one vector per chunk)
  - a ClauseEmbedding-shaped row is produced per chunk with full scope + provenance
  - the vector store gets points whose payload carries the tenant scope
  - the vector dim drives ensure_collection
  - empty input is a no-op (no embed call, no upsert)
"""

from app.ai.providers.base import EmbeddingProvider, VectorStore
from app.services.embedding_service import build_chunk_embeddings


class FakeEmbeddingProvider(EmbeddingProvider):
    name = "fake"

    def __init__(self, dim: int = 4) -> None:
        self._dim = dim
        self.calls: list[list[str]] = []

    def embed(self, texts: list[str]) -> list[list[float]]:
        self.calls.append(texts)
        # deterministic non-zero vector per text
        return [[float(len(t) % 7) + 0.1] * self._dim for t in texts]

    @property
    def dimension(self) -> int:
        return self._dim


class FakeVectorStore(VectorStore):
    name = "fake"

    def __init__(self) -> None:
        self.collection_dim: int | None = None
        self.upserted: list[dict] = []

    def ensure_collection(self, dimension: int) -> None:
        self.collection_dim = dimension

    def upsert(self, points):
        self.upserted.extend(points)

    def search(self, vector, *, scope_filter, limit=10):  # pragma: no cover
        return []

    def delete_scope(self, scope_filter):  # pragma: no cover
        pass


def _clause(cid, body, heading=None, clause_type="general", file_role="B"):
    return {
        "id": cid,
        "heading": heading,
        "body_text": body,
        "char_start": 0,
        "char_end": len(body),
        "clause_type": clause_type,
        "file_role": file_role,
        "document_id": "doc-1",
        "project_id": "proj-1",
        "organization_id": "org-1",
    }


class TestBuildChunkEmbeddings:
    def test_one_chunk_one_vector_and_row(self):
        provider = FakeEmbeddingProvider()
        store = FakeVectorStore()
        clauses = [_clause("c1", "The vendor shall deliver services within thirty days.")]

        rows = build_chunk_embeddings(clauses, provider=provider, store=store)

        assert len(rows) == 1
        row = rows[0]
        # provenance + scope carried onto the row
        assert row["clause_id"] == "c1"
        assert row["document_id"] == "doc-1"
        assert row["project_id"] == "proj-1"
        assert row["organization_id"] == "org-1"
        assert len(row["embedding"]) == provider.dimension
        assert row["embedding_provider"] == "fake"

    def test_vector_store_gets_scoped_points(self):
        provider = FakeEmbeddingProvider()
        store = FakeVectorStore()
        clauses = [_clause("c1", "Confidential information stays confidential forever.")]

        build_chunk_embeddings(clauses, provider=provider, store=store)

        assert store.collection_dim == provider.dimension
        assert len(store.upserted) == 1
        point = store.upserted[0]
        assert "vector" in point and "id" in point
        # scope MUST be in the payload so search can filter server-side
        assert point["payload"]["organization_id"] == "org-1"
        assert point["payload"]["project_id"] == "proj-1"

    def test_point_id_matches_chunk_id(self):
        provider = FakeEmbeddingProvider()
        store = FakeVectorStore()
        clauses = [_clause("c1", "A clause about liability and indemnity obligations.")]

        rows = build_chunk_embeddings(clauses, provider=provider, store=store)

        assert store.upserted[0]["id"] == rows[0]["chunk_id"]

    def test_oversized_clause_makes_multiple_rows(self):
        provider = FakeEmbeddingProvider()
        store = FakeVectorStore()
        big = "This sentence describes obligations and liabilities in detail. " * 200
        clauses = [_clause("big", big)]

        rows = build_chunk_embeddings(
            clauses, provider=provider, store=store, max_tokens=256
        )

        assert len(rows) > 1
        assert all(r["clause_id"] == "big" for r in rows)
        assert len(store.upserted) == len(rows)

    def test_empty_input_is_noop(self):
        provider = FakeEmbeddingProvider()
        store = FakeVectorStore()

        rows = build_chunk_embeddings([], provider=provider, store=store)

        assert rows == []
        assert provider.calls == []          # no embed call → no credits spent
        assert store.upserted == []
