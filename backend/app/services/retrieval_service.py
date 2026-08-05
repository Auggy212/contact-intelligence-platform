"""
Hybrid retrieval (Phase 6.6) — the search layer the RAG chatbot (Phase 7) calls.

Two signals, fused:

  - VECTOR (semantic)  — nearest-neighbour on chunk embeddings. Catches meaning
    even when wording differs ("IP stays with us" ~ "supplier retains title").
  - LEXICAL (keyword)  — Postgres full-text (ts_rank). Catches EXACT tokens the
    vector side is weak on: clause numbers ("14.2"), defined terms, section refs.

They live on totally different score scales, so we fuse by RANK, not score, using
Reciprocal Rank Fusion (RRF). RRF needs no normalisation and is robust — a doc
that ranks decently in BOTH lists beats one that ranks highly in only one.

Every search is MANDATORILY scope-filtered (project/org) on both backends, on
top of Postgres RLS — defense in depth. The fusion core is pure + unit-tested;
the backends are injected so the whole thing runs offline with fakes.
"""

from __future__ import annotations

from typing import Any, Protocol

from app.ai.providers.base import EmbeddingProvider, VectorStore

# RRF dampening constant. 60 is the value from the original RRF paper (Cormack
# et al.); large enough that a strong single-list rank can't dominate a doc that
# ranks solidly in both lists.
DEFAULT_RRF_K = 60


def reciprocal_rank_fusion(
    vector_ranking: list[str],
    lexical_ranking: list[str],
    *,
    k: int = DEFAULT_RRF_K,
) -> list[tuple[str, float]]:
    """
    Fuse two ranked id-lists into one, by Reciprocal Rank Fusion.

    score(id) = Σ over each list  1 / (k + rank)   (rank is 0-based here)

    Returns [(id, score), ...] descending by score, each id once. Pure: no DB,
    no API — this is the ranking logic under test.
    """
    scores: dict[str, float] = {}
    for ranking in (vector_ranking, lexical_ranking):
        seen: set[str] = set()
        for rank, item_id in enumerate(ranking):
            if item_id in seen:          # only the best rank per list counts
                continue
            seen.add(item_id)
            scores[item_id] = scores.get(item_id, 0.0) + 1.0 / (k + rank + 1)
    return sorted(scores.items(), key=lambda kv: kv[1], reverse=True)


class LexicalSearcher(Protocol):
    """Keyword search backend. Returns [(chunk_id, payload), ...] best-first."""

    async def search(
        self, query: str, *, scope_filter: dict[str, Any], limit: int
    ) -> list[tuple[str, dict[str, Any]]]:
        ...


class HybridRetriever:
    """Runs vector + lexical search, fuses with RRF, returns scoped chunk hits."""

    def __init__(
        self,
        *,
        provider: EmbeddingProvider,
        store: VectorStore,
        lexical: LexicalSearcher,
        rrf_k: int = DEFAULT_RRF_K,
    ) -> None:
        self._provider = provider
        self._store = store
        self._lexical = lexical
        self._rrf_k = rrf_k

    def _embed_query(self, text: str) -> list[float]:
        # Retrieval models (NVIDIA nv-embedqa) want input_type="query" on the
        # query side; providers that support it expose embed_query.
        embed_query = getattr(self._provider, "embed_query", None)
        if callable(embed_query):
            return embed_query(text)
        return self._provider.embed_one(text)

    async def retrieve(
        self,
        query: str,
        *,
        scope_filter: dict[str, Any],
        limit: int = 10,
        candidate_multiplier: int = 3,
    ) -> list[dict[str, Any]]:
        """
        Retrieve the top-`limit` chunks for a query within a tenant scope.

        Pulls `limit * candidate_multiplier` candidates from EACH backend before
        fusing, so a chunk strong in one list isn't lost before it can be fused.
        """
        if not scope_filter:
            raise ValueError("scope_filter is mandatory — refusing an unscoped retrieval")

        candidates = max(limit * candidate_multiplier, limit)

        query_vec = self._embed_query(query)
        vector_hits = self._store.search(
            query_vec, scope_filter=scope_filter, limit=candidates
        )
        lexical_hits = await self._lexical.search(
            query, scope_filter=scope_filter, limit=candidates
        )

        # Keep payloads so we can return chunk_text without another round-trip.
        payloads: dict[str, dict[str, Any]] = {}
        vector_ids: list[str] = []
        for h in vector_hits:
            vector_ids.append(h.id)
            payloads.setdefault(h.id, h.payload or {})
        lexical_ids: list[str] = []
        for chunk_id, payload in lexical_hits:
            lexical_ids.append(chunk_id)
            payloads.setdefault(chunk_id, payload or {})

        fused = reciprocal_rank_fusion(vector_ids, lexical_ids, k=self._rrf_k)

        results: list[dict[str, Any]] = []
        for chunk_id, score in fused[:limit]:
            payload = payloads.get(chunk_id, {})
            results.append({
                "chunk_id": chunk_id,
                "chunk_text": payload.get("chunk_text", ""),
                "score": score,
                "payload": payload,
            })
        return results


class PostgresLexicalSearcher:
    """
    Lexical backend over clause_embeddings using Postgres full-text (ts_rank).

    Runs inside a tenant-scoped session (RLS already limits rows to the org); the
    explicit scope_filter adds project/document narrowing and defense-in-depth.
    Zero new dependencies — Postgres FTS is built in.
    """

    # Columns we allow to be filtered on (guards against SQL identifier injection
    # since these become raw column names in the WHERE clause).
    _ALLOWED_SCOPE = {"organization_id", "project_id", "document_id", "clause_id"}

    def __init__(self, session: Any) -> None:
        self._session = session

    async def search(
        self, query: str, *, scope_filter: dict[str, Any], limit: int
    ) -> list[tuple[str, dict[str, Any]]]:
        from sqlalchemy import text

        conds = ["to_tsvector('english', chunk_text) @@ plainto_tsquery('english', :q)"]
        params: dict[str, Any] = {"q": query, "limit": limit}
        for key, value in scope_filter.items():
            if key not in self._ALLOWED_SCOPE:
                raise ValueError(f"unsupported scope filter column: {key}")
            conds.append(f"{key} = :{key}")
            params[key] = value

        sql = text(
            "SELECT chunk_id, chunk_text, clause_id, document_id, "
            "       project_id, organization_id, clause_type, "
            "       ts_rank(to_tsvector('english', chunk_text), "
            "               plainto_tsquery('english', :q)) AS rank "
            "FROM clause_embeddings "
            f"WHERE {' AND '.join(conds)} "
            "ORDER BY rank DESC "
            "LIMIT :limit"
        )
        rows = (await self._session.execute(sql, params)).mappings().all()
        return [
            (
                r["chunk_id"],
                {
                    "chunk_text": r["chunk_text"],
                    "clause_id": str(r["clause_id"]),
                    "document_id": str(r["document_id"]),
                    "project_id": str(r["project_id"]),
                    "organization_id": str(r["organization_id"]),
                    "clause_type": r["clause_type"],
                },
            )
            for r in rows
        ]


def get_hybrid_retriever(session: Any) -> HybridRetriever:
    """Build a retriever from config: factory-selected provider + store + PG lexical."""
    from app.ai.providers.factory import get_embedding_provider, get_vector_store
    from app.core.config import settings

    return HybridRetriever(
        provider=get_embedding_provider(settings.EMBEDDING_PROVIDER),
        store=get_vector_store(settings.VECTOR_STORE),
        lexical=PostgresLexicalSearcher(session),
    )
