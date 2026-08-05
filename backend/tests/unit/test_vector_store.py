"""
Unit tests for the Qdrant vector store (Phase 6.4).

The Qdrant client is mocked, so these run offline with zero services and make no
network/API calls. We assert the *contract* that matters for correctness and
tenant safety:

  - ensure_collection is idempotent (won't recreate an existing collection)
  - upsert forwards id/vector/payload correctly
  - search ALWAYS applies the scope filter server-side, and refuses an empty one
  - delete_scope refuses an empty filter (never a full-collection wipe)
  - hits are mapped into VectorHit(id, score, payload)
"""

from unittest.mock import MagicMock, patch

import pytest

from app.ai.providers.base import VectorHit
from app.ai.vector_store import QdrantVectorStore


def _store_with_mock_client(client: MagicMock) -> QdrantVectorStore:
    store = QdrantVectorStore(collection="test_chunks")
    store._client = client  # inject mock, bypass lazy real client
    return store


class TestEnsureCollection:
    def test_creates_when_absent(self):
        client = MagicMock()
        client.get_collections.return_value.collections = []
        store = _store_with_mock_client(client)
        store.ensure_collection(dimension=1024)
        client.create_collection.assert_called_once()
        _, kwargs = client.create_collection.call_args
        assert kwargs["collection_name"] == "test_chunks"

    def test_idempotent_when_present(self):
        client = MagicMock()
        existing = MagicMock()
        existing.name = "test_chunks"
        client.get_collections.return_value.collections = [existing]
        store = _store_with_mock_client(client)
        store.ensure_collection(dimension=1024)
        client.create_collection.assert_not_called()


class TestUpsert:
    def test_forwards_points(self):
        client = MagicMock()
        store = _store_with_mock_client(client)
        store.upsert([
            {"id": "chunk-a", "vector": [0.1, 0.2], "payload": {"project_id": "p1"}},
        ])
        client.upsert.assert_called_once()
        _, kwargs = client.upsert.call_args
        assert kwargs["collection_name"] == "test_chunks"
        assert len(kwargs["points"]) == 1

    def test_non_uuid_id_coerced_to_uuid_and_original_kept_in_payload(self):
        # Qdrant only accepts an unsigned int or a UUID as a point ID. Our stable
        # chunk_id ("clauseid:0:hash") is neither, so the store must coerce it to a
        # deterministic UUID while preserving the original in the payload.
        import uuid as _uuid

        client = MagicMock()
        store = _store_with_mock_client(client)
        chunk_id = "9c6396ff-0086-4c67-b0e1-ed5c56ce053f:0:8a951690d554405f"
        store.upsert([{"id": chunk_id, "vector": [0.1, 0.2], "payload": {"project_id": "p1"}}])

        _, kwargs = client.upsert.call_args
        point = kwargs["points"][0]
        # id is now a valid UUID (string form parses)
        _uuid.UUID(str(point.id))
        # deterministic: same chunk_id → same point id
        assert str(point.id) == str(_uuid.uuid5(_uuid.NAMESPACE_URL, chunk_id))
        # original chunk_id recoverable from payload
        assert point.payload["chunk_id"] == chunk_id

    def test_uuid_id_passes_through_unchanged(self):
        import uuid as _uuid

        client = MagicMock()
        store = _store_with_mock_client(client)
        real_uuid = str(_uuid.uuid4())
        store.upsert([{"id": real_uuid, "vector": [0.1], "payload": {}}])
        _, kwargs = client.upsert.call_args
        assert str(kwargs["points"][0].id) == real_uuid


class TestSearchScopeSafety:
    def test_empty_scope_filter_is_rejected(self):
        store = _store_with_mock_client(MagicMock())
        with pytest.raises(ValueError, match="scope_filter"):
            store.search([0.1, 0.2], scope_filter={}, limit=5)

    def _hit(self, id="chunk-a", score=0.87, payload=None):
        h = MagicMock()
        h.id = id
        h.score = score
        h.payload = payload if payload is not None else {"project_id": "p1", "chunk_text": "the clause"}
        return h

    def test_uses_query_points_on_newer_clients(self):
        # Newer qdrant-client (>=1.10) exposes query_points() and returns a
        # response object with a .points list.
        client = MagicMock(spec=["query_points"])
        resp = MagicMock()
        resp.points = [self._hit()]
        client.query_points.return_value = resp
        store = _store_with_mock_client(client)

        out = store.search([0.1, 0.2], scope_filter={"project_id": "p1"}, limit=5)

        assert out == [VectorHit(id="chunk-a", score=0.87,
                                 payload={"project_id": "p1", "chunk_text": "the clause"})]
        _, kwargs = client.query_points.call_args
        assert kwargs["collection_name"] == "test_chunks"
        assert kwargs["limit"] == 5
        assert kwargs["query_filter"] is not None

    def test_falls_back_to_search_on_older_clients(self):
        # Older clients (<=1.9) only expose search() and return a plain list.
        client = MagicMock(spec=["search"])
        client.search.return_value = [self._hit()]
        store = _store_with_mock_client(client)

        out = store.search([0.1, 0.2], scope_filter={"project_id": "p1"}, limit=5)

        assert out[0].id == "chunk-a"
        _, kwargs = client.search.call_args
        assert kwargs["query_filter"] is not None

    def test_returns_chunk_id_from_payload_for_fusion(self):
        # The hit id must be OUR chunk_id (from payload), not Qdrant's coerced
        # point id, so vector + lexical results share ids for RRF.
        client = MagicMock(spec=["query_points"])
        resp = MagicMock()
        resp.points = [self._hit(id="coerced-uuid",
                                 payload={"project_id": "p1", "chunk_id": "real-chunk-7",
                                          "chunk_text": "x"})]
        client.query_points.return_value = resp
        store = _store_with_mock_client(client)

        out = store.search([0.1], scope_filter={"project_id": "p1"}, limit=5)
        assert out[0].id == "real-chunk-7"


class TestDeleteScopeSafety:
    def test_empty_scope_filter_is_rejected(self):
        store = _store_with_mock_client(MagicMock())
        with pytest.raises(ValueError, match="scope_filter"):
            store.delete_scope({})

    def test_delete_with_scope_calls_client(self):
        client = MagicMock()
        store = _store_with_mock_client(client)
        store.delete_scope({"project_id": "p1"})
        client.delete.assert_called_once()
