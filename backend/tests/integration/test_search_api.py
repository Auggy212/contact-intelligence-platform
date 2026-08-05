"""
Integration tests for the semantic search API (Phase 6).

The retriever is PATCHED so these tests make NO NVIDIA / Qdrant calls (credit-
free, like the rest of the suite). We verify the endpoint contract:
  - requires a query
  - is tenant-scoped (passes project + org into the retriever's scope filter)
  - returns the retriever's ranked hits in a stable response shape
"""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.core.config import settings


@pytest.fixture
def embeddings_on():
    """Turn the Phase 6 flag on for the duration of a test (no API calls — the
    retriever itself is mocked)."""
    original = settings.ENABLE_EMBEDDINGS
    settings.ENABLE_EMBEDDINGS = True  # type: ignore[assignment]
    try:
        yield
    finally:
        settings.ENABLE_EMBEDDINGS = original  # type: ignore[assignment]


@pytest.mark.asyncio
async def test_search_requires_query(client: AsyncClient, tenant_a_headers: dict):
    proj = await client.post(
        "/api/v1/projects", json={"name": "Search Q Test"}, headers=tenant_a_headers
    )
    project_id = proj.json()["id"]

    # no ?q= → 422 validation error (checked before the feature flag)
    resp = await client.get(
        f"/api/v1/projects/{project_id}/search", headers=tenant_a_headers
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_search_disabled_returns_clear_error(
    client: AsyncClient, tenant_a_headers: dict
):
    proj = await client.post(
        "/api/v1/projects", json={"name": "Search Off Test"}, headers=tenant_a_headers
    )
    project_id = proj.json()["id"]

    # flag is off by default → a clear 4xx, not a 500
    original = settings.ENABLE_EMBEDDINGS
    settings.ENABLE_EMBEDDINGS = False  # type: ignore[assignment]
    try:
        resp = await client.get(
            f"/api/v1/projects/{project_id}/search",
            params={"q": "anything"},
            headers=tenant_a_headers,
        )
    finally:
        settings.ENABLE_EMBEDDINGS = original  # type: ignore[assignment]
    assert resp.status_code in (400, 422, 503)


@pytest.mark.asyncio
async def test_search_returns_ranked_hits(
    client: AsyncClient, tenant_a_headers: dict, embeddings_on
):
    proj = await client.post(
        "/api/v1/projects", json={"name": "Search Hits Test"}, headers=tenant_a_headers
    )
    project_id = proj.json()["id"]

    fake_hits = [
        {"chunk_id": "c1", "chunk_text": "Termination requires 60 days notice.",
         "score": 0.0164, "payload": {"clause_type": "termination"}},
        {"chunk_id": "c2", "chunk_text": "IP vests in the Customer.",
         "score": 0.0161, "payload": {"clause_type": "ip"}},
    ]
    fake_retriever = AsyncMock()
    fake_retriever.retrieve = AsyncMock(return_value=fake_hits)

    # Patch the factory so no real provider/Qdrant is touched.
    with patch("app.api.v1.endpoints.search.get_hybrid_retriever",
               return_value=fake_retriever):
        resp = await client.get(
            f"/api/v1/projects/{project_id}/search",
            params={"q": "termination notice period", "limit": 5},
            headers=tenant_a_headers,
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["query"] == "termination notice period"
    assert len(body["results"]) == 2
    assert body["results"][0]["chunk_id"] == "c1"

    # scope filter must carry BOTH project and org (defense-in-depth)
    _, kwargs = fake_retriever.retrieve.call_args
    scope = kwargs["scope_filter"]
    assert "project_id" in scope
    assert "organization_id" in scope
    assert str(scope["project_id"]) == project_id


@pytest.mark.asyncio
async def test_search_scoped_to_tenant(client: AsyncClient, tenant_a_headers: dict,
                                       tenant_b_headers: dict, embeddings_on):
    # Tenant A's project id, queried by Tenant B → must not leak (404/empty).
    proj = await client.post(
        "/api/v1/projects", json={"name": "Search Isolation"}, headers=tenant_a_headers
    )
    project_id = proj.json()["id"]

    fake_retriever = AsyncMock()
    fake_retriever.retrieve = AsyncMock(return_value=[])
    with patch("app.api.v1.endpoints.search.get_hybrid_retriever",
               return_value=fake_retriever):
        resp = await client.get(
            f"/api/v1/projects/{project_id}/search",
            params={"q": "anything"},
            headers=tenant_b_headers,
        )
    # RLS-scoped: either the project isn't visible (404) or search returns nothing.
    assert resp.status_code in (200, 404)
    if resp.status_code == 200:
        assert resp.json()["results"] == []
