"""
Integration tests for the projects API — full CRUD cycle.
Uses real DB (cipdb) with seeded test orgs from conftest.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_project_returns_201(client: AsyncClient, tenant_a_headers: dict):
    resp = await client.post(
        "/api/v1/projects",
        json={"name": "My MSA Project"},
        headers=tenant_a_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "My MSA Project"
    assert "id" in data
    assert data["status"] == "draft"


@pytest.mark.asyncio
async def test_create_project_missing_name_returns_422(client: AsyncClient, tenant_a_headers: dict):
    resp = await client.post("/api/v1/projects", json={}, headers=tenant_a_headers)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_list_projects_returns_own_projects(client: AsyncClient, tenant_a_headers: dict):
    # Create two projects
    await client.post("/api/v1/projects", json={"name": "P1"}, headers=tenant_a_headers)
    await client.post("/api/v1/projects", json={"name": "P2"}, headers=tenant_a_headers)

    resp = await client.get("/api/v1/projects", headers=tenant_a_headers)
    assert resp.status_code == 200
    names = [p["name"] for p in resp.json()]
    assert "P1" in names
    assert "P2" in names


@pytest.mark.asyncio
async def test_get_project_by_id(client: AsyncClient, tenant_a_headers: dict):
    create_resp = await client.post(
        "/api/v1/projects",
        json={"name": "Detail Test Project"},
        headers=tenant_a_headers,
    )
    project_id = create_resp.json()["id"]

    get_resp = await client.get(f"/api/v1/projects/{project_id}", headers=tenant_a_headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == project_id
    assert get_resp.json()["name"] == "Detail Test Project"


@pytest.mark.asyncio
async def test_get_nonexistent_project_returns_404(client: AsyncClient, tenant_a_headers: dict):
    import uuid
    resp = await client.get(f"/api/v1/projects/{uuid.uuid4()}", headers=tenant_a_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_project_name(client: AsyncClient, tenant_a_headers: dict):
    create_resp = await client.post(
        "/api/v1/projects",
        json={"name": "Old Name"},
        headers=tenant_a_headers,
    )
    project_id = create_resp.json()["id"]

    patch_resp = await client.patch(
        f"/api/v1/projects/{project_id}",
        json={"name": "New Name"},
        headers=tenant_a_headers,
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["name"] == "New Name"


@pytest.mark.asyncio
async def test_delete_project(client: AsyncClient, tenant_a_headers: dict):
    create_resp = await client.post(
        "/api/v1/projects",
        json={"name": "To Be Deleted"},
        headers=tenant_a_headers,
    )
    project_id = create_resp.json()["id"]

    del_resp = await client.delete(f"/api/v1/projects/{project_id}", headers=tenant_a_headers)
    assert del_resp.status_code == 204

    get_resp = await client.get(f"/api/v1/projects/{project_id}", headers=tenant_a_headers)
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_create_project_requires_auth(client: AsyncClient):
    resp = await client.post("/api/v1/projects", json={"name": "No Auth"})
    assert resp.status_code == 401
