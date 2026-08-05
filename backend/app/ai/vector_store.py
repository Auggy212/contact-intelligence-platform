"""
Vector store implementations behind the VectorStore interface.

  - QdrantVectorStore  (default) — payload-filtered ANN, per-tenant safe
  - PgVectorStore                — "zero extra services" option

Both enforce a MANDATORY scope filter on every search so tenant isolation holds
at the index level (defense-in-depth on top of Postgres RLS). Clients are lazy.
"""

from __future__ import annotations

import uuid
from typing import Any

from app.ai.providers.base import VectorHit, VectorStore
from app.core.config import settings

_COLLECTION = "contract_chunks"


def _to_point_id(raw: Any) -> Any:
    """
    Coerce an arbitrary stable id into something Qdrant accepts as a point ID:
    an unsigned int or a UUID. Our chunk_id ("clauseid:0:hash") is neither, so we
    map it to a DETERMINISTIC uuid5 (same input → same point, keeping upserts
    idempotent). Ints and already-valid UUIDs pass through unchanged.
    """
    if isinstance(raw, int):
        return raw
    s = str(raw)
    try:
        return str(uuid.UUID(s))
    except ValueError:
        return str(uuid.uuid5(uuid.NAMESPACE_URL, s))


class QdrantVectorStore(VectorStore):
    name = "qdrant"

    def __init__(self, collection: str = _COLLECTION) -> None:
        self._collection = collection
        self._client = None

    def _ensure_client(self):
        if self._client is None:
            from qdrant_client import QdrantClient

            self._client = QdrantClient(
                url=settings.QDRANT_URL,
                api_key=settings.QDRANT_API_KEY or None,
            )
        return self._client

    def ensure_collection(self, dimension: int) -> None:
        from qdrant_client.models import Distance, VectorParams

        client = self._ensure_client()
        existing = {c.name for c in client.get_collections().collections}
        if self._collection not in existing:
            client.create_collection(
                collection_name=self._collection,
                vectors_config=VectorParams(size=dimension, distance=Distance.COSINE),
            )

    def upsert(self, points: list[dict[str, Any]]) -> None:
        from qdrant_client.models import PointStruct

        client = self._ensure_client()
        structs = []
        for p in points:
            # Qdrant needs a UUID/int point id; keep the original id in the payload
            # so search results can be mapped back to our chunk_id.
            payload = {**p["payload"], "chunk_id": p["payload"].get("chunk_id", p["id"])}
            structs.append(
                PointStruct(id=_to_point_id(p["id"]), vector=p["vector"], payload=payload)
            )
        client.upsert(collection_name=self._collection, points=structs)

    def search(
        self,
        vector: list[float],
        *,
        scope_filter: dict[str, Any],
        limit: int = 10,
    ) -> list[VectorHit]:
        from qdrant_client.models import FieldCondition, Filter, MatchValue

        if not scope_filter:
            raise ValueError("scope_filter is mandatory — refusing an unscoped vector search")

        client = self._ensure_client()
        must = [
            FieldCondition(key=k, match=MatchValue(value=v))
            for k, v in scope_filter.items()
        ]
        query_filter = Filter(must=must)
        # qdrant-client renamed search() -> query_points() in newer versions.
        # Support both so we work across the pinned range without a hard upgrade.
        if hasattr(client, "query_points"):
            results = client.query_points(
                collection_name=self._collection,
                query=vector,
                query_filter=query_filter,
                limit=limit,
            ).points
        else:  # older clients (<=1.9) expose search()
            results = client.search(
                collection_name=self._collection,
                query_vector=vector,
                query_filter=query_filter,
                limit=limit,
            )
        # Return OUR chunk_id (from payload) as the hit id, not Qdrant's coerced
        # UUID — so vector and lexical results share ids and RRF can fuse them.
        return [
            VectorHit(
                id=str((r.payload or {}).get("chunk_id", r.id)),
                score=r.score,
                payload=r.payload or {},
            )
            for r in results
        ]

    def delete_scope(self, scope_filter: dict[str, Any]) -> None:
        from qdrant_client.models import FieldCondition, Filter, FilterSelector, MatchValue

        if not scope_filter:
            raise ValueError("scope_filter is mandatory — refusing an unscoped delete")
        client = self._ensure_client()
        must = [
            FieldCondition(key=k, match=MatchValue(value=v))
            for k, v in scope_filter.items()
        ]
        client.delete(
            collection_name=self._collection,
            points_selector=FilterSelector(filter=Filter(must=must)),
        )


class PgVectorStore(VectorStore):
    """pgvector-backed store — same interface, vectors live in a Postgres column.

    Full query logic lands in Phase 6.4 with the ClauseEmbedding model/migration;
    this satisfies the interface and the config-selection contract now.
    """

    name = "pgvector"

    def ensure_collection(self, dimension: int) -> None:  # pragma: no cover - 6.4
        raise NotImplementedError("PgVectorStore wired in Phase 6.4")

    def upsert(self, points: list[dict[str, Any]]) -> None:  # pragma: no cover - 6.4
        raise NotImplementedError("PgVectorStore wired in Phase 6.4")

    def search(self, vector, *, scope_filter, limit=10):  # pragma: no cover - 6.4
        raise NotImplementedError("PgVectorStore wired in Phase 6.4")

    def delete_scope(self, scope_filter):  # pragma: no cover - 6.4
        raise NotImplementedError("PgVectorStore wired in Phase 6.4")
