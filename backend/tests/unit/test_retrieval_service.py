"""
Unit tests for hybrid retrieval (Phase 6.6).

Hybrid = vector similarity (semantic) + lexical keyword (exact terms like clause
numbers / defined terms), fused with Reciprocal Rank Fusion (RRF). RRF is rank-
based, so it needs no score normalisation between the two very different scales.

Two things under test:
  1. The PURE fusion core (`reciprocal_rank_fusion`) — all the ranking logic,
     no DB / no API. This is where correctness lives.
  2. The retrieval surface (`HybridRetriever.retrieve`) driven with a fake
     embedding provider + fake vector store + fake lexical searcher, so it runs
     offline with zero credits and still proves: query is embedded query-side,
     scope filter is passed through, results are fused + deduped + scoped.
"""

import pytest

from app.services.retrieval_service import (
    HybridRetriever,
    reciprocal_rank_fusion,
)


# ─────────────────────────────────────────────────────────────────────────────
# Pure fusion core
# ─────────────────────────────────────────────────────────────────────────────

class TestReciprocalRankFusion:
    def test_item_in_both_lists_beats_item_in_one(self):
        vector = ["a", "b", "c"]
        lexical = ["b", "d", "e"]
        fused = reciprocal_rank_fusion(vector, lexical)
        # "b" appears in both, so it should rank first
        assert fused[0][0] == "b"

    def test_returns_id_score_pairs_descending(self):
        fused = reciprocal_rank_fusion(["a", "b"], ["a", "c"])
        scores = [s for _, s in fused]
        assert scores == sorted(scores, reverse=True)

    def test_dedupes_ids(self):
        fused = reciprocal_rank_fusion(["a", "b", "a"], ["a"])
        ids = [i for i, _ in fused]
        assert ids.count("a") == 1

    def test_empty_lists_give_empty_result(self):
        assert reciprocal_rank_fusion([], []) == []

    def test_one_empty_list_still_ranks_the_other(self):
        fused = reciprocal_rank_fusion(["a", "b"], [])
        assert [i for i, _ in fused] == ["a", "b"]

    def test_higher_rank_contributes_more(self):
        # same single list; earlier position must score higher
        fused = reciprocal_rank_fusion(["first", "second", "third"], [])
        d = dict(fused)
        assert d["first"] > d["second"] > d["third"]

    def test_k_constant_dampens_top_rank_dominance(self):
        # with a large k, rank-1-in-both should still beat rank-1-in-one
        v = ["x", "y"]
        lx = ["y", "z"]
        fused = dict(reciprocal_rank_fusion(v, lx, k=60))
        assert fused["y"] > fused["x"]


# ─────────────────────────────────────────────────────────────────────────────
# Retrieval surface (fakes — offline)
# ─────────────────────────────────────────────────────────────────────────────

from app.ai.providers.base import EmbeddingProvider, VectorHit, VectorStore


class FakeProvider(EmbeddingProvider):
    name = "fake"

    def __init__(self):
        self.query_calls: list[str] = []

    def embed(self, texts):
        return [[0.1, 0.2, 0.3] for _ in texts]

    def embed_query(self, text):
        self.query_calls.append(text)
        return [0.9, 0.8, 0.7]

    @property
    def dimension(self):
        return 3


class FakeStore(VectorStore):
    name = "fake"

    def __init__(self, hits):
        self._hits = hits
        self.last_scope = None

    def ensure_collection(self, dimension):  # pragma: no cover
        pass

    def upsert(self, points):  # pragma: no cover
        pass

    def search(self, vector, *, scope_filter, limit=10):
        self.last_scope = scope_filter
        return self._hits

    def delete_scope(self, scope_filter):  # pragma: no cover
        pass


class FakeLexical:
    """Stand-in for the Postgres full-text searcher."""

    def __init__(self, results):
        self._results = results
        self.last_scope = None

    async def search(self, query, *, scope_filter, limit):
        self.last_scope = scope_filter
        return self._results  # list of (chunk_id, payload)


class TestHybridRetriever:
    @pytest.mark.asyncio
    async def test_query_is_embedded_query_side(self):
        provider = FakeProvider()
        store = FakeStore([VectorHit(id="a", score=0.9, payload={"chunk_text": "A"})])
        lexical = FakeLexical([("b", {"chunk_text": "B"})])
        r = HybridRetriever(provider=provider, store=store, lexical=lexical)

        await r.retrieve("what is the termination notice period",
                         scope_filter={"project_id": "p1"}, limit=5)

        assert provider.query_calls == ["what is the termination notice period"]

    @pytest.mark.asyncio
    async def test_scope_filter_reaches_both_backends(self):
        provider = FakeProvider()
        store = FakeStore([VectorHit(id="a", score=0.9, payload={"chunk_text": "A"})])
        lexical = FakeLexical([("b", {"chunk_text": "B"})])
        r = HybridRetriever(provider=provider, store=store, lexical=lexical)

        scope = {"project_id": "p1", "organization_id": "o1"}
        await r.retrieve("q", scope_filter=scope, limit=5)

        assert store.last_scope == scope
        assert lexical.last_scope == scope

    @pytest.mark.asyncio
    async def test_empty_scope_is_rejected(self):
        r = HybridRetriever(provider=FakeProvider(),
                            store=FakeStore([]), lexical=FakeLexical([]))
        with pytest.raises(ValueError, match="scope"):
            await r.retrieve("q", scope_filter={}, limit=5)

    @pytest.mark.asyncio
    async def test_fuses_and_returns_chunk_text(self):
        provider = FakeProvider()
        store = FakeStore([VectorHit(id="a", score=0.9, payload={"chunk_text": "vector hit"})])
        lexical = FakeLexical([("a", {"chunk_text": "vector hit"}),
                               ("b", {"chunk_text": "lexical hit"})])
        r = HybridRetriever(provider=provider, store=store, lexical=lexical)

        out = await r.retrieve("q", scope_filter={"project_id": "p1"}, limit=5)

        # "a" is in both → ranked first; result carries text + score + id
        assert out[0]["chunk_id"] == "a"
        assert out[0]["chunk_text"] == "vector hit"
        assert "score" in out[0]
        ids = {h["chunk_id"] for h in out}
        assert ids == {"a", "b"}

    @pytest.mark.asyncio
    async def test_limit_is_respected(self):
        provider = FakeProvider()
        store = FakeStore([VectorHit(id=str(i), score=0.5, payload={"chunk_text": str(i)})
                           for i in range(10)])
        lexical = FakeLexical([(str(i), {"chunk_text": str(i)}) for i in range(10, 20)])
        r = HybridRetriever(provider=provider, store=store, lexical=lexical)

        out = await r.retrieve("q", scope_filter={"project_id": "p1"}, limit=5)
        assert len(out) == 5
