"""
Integration tests for the 'similar clauses' endpoint (Improvements Item 2A).

When a reviewer opens a finding, the UI shows semantically related clauses FROM
THE SAME CONTRACT. This endpoint powers that panel: it takes the finding's clause
text as the query, runs Phase 6 hybrid retrieval scoped to the project, and
returns the related clauses — excluding the finding's own clause.

The retriever is PATCHED so no NVIDIA/Qdrant calls happen (credit-free). We seed
a finding + its clause directly so the endpoint has something to key off.
"""

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.core.config import settings
from tests.conftest import USER_A_ID

USER = USER_A_ID


async def _seed_finding(client: AsyncClient, headers: dict) -> tuple[str, str, str, str]:
    """
    Create project (via API) + file/clause/flag (via the no-RLS DB session), and
    return (project_id, flag_id, clause_id, tenant_id). The tenant is read from the
    created project's organization_id — the source of truth for which tenant the
    API is operating as — so seed and API always agree.
    """
    from app.core.database import get_db_no_rls
    from app.models.project import ProjectFile
    from app.models.clause import ClauseFlag, ParsedClause
    from app.models.task import AnalysisTask

    proj = await client.post("/api/v1/projects", json={"name": "Similar Test"},
                             headers=headers)
    proj_json = proj.json()
    proj_id = uuid.UUID(proj_json["id"])
    org_id = uuid.UUID(proj_json["organization_id"])
    file_id = uuid.uuid4()
    clause_id = uuid.uuid4()
    flag_id = uuid.uuid4()
    task_id = uuid.uuid4()

    # Seed via the no-RLS session so inserts aren't blocked and the API (which
    # sets app.tenant_id = org_id) can read them back.
    async for s in get_db_no_rls():
        s.add(AnalysisTask(id=task_id, project_id=proj_id, organization_id=org_id,
                           triggered_by_user_id=uuid.UUID(USER),
                           task_type="checklist_validation", status="completed"))
        s.add(ProjectFile(id=file_id, project_id=proj_id, organization_id=org_id,
                          uploaded_by_user_id=uuid.UUID(USER), file_role="B",
                          original_filename="c.docx", storage_key="k", file_size_bytes=1,
                          mime_type="application/vnd.openxmlformats-officedocument."
                          "wordprocessingml.document", parse_status="completed"))
        s.add(ParsedClause(id=clause_id, file_id=file_id, project_id=proj_id,
                           organization_id=org_id, heading="Liability",
                           body_text="Limitation of liability applies here.",
                           paragraph_index=0, char_start=0, char_end=30))
        s.add(ClauseFlag(id=flag_id, clause_id=clause_id, task_id=task_id,
                         project_id=proj_id, organization_id=org_id,
                         flag_type="missing_clause", severity="medium",
                         title="X", description="Y"))
        await s.commit()
        break
    return str(proj_id), str(flag_id), str(clause_id), str(org_id)


async def _cleanup(project_id: str) -> None:
    """Remove seeded rows in FK order so the shared session teardown can drop the
    project without a foreign-key violation. Uses the no-RLS session (like the
    conftest teardown) so DELETEs aren't blocked by row-level security."""
    from sqlalchemy import text

    from app.core.database import get_db_no_rls

    pid = uuid.UUID(project_id)
    async for s in get_db_no_rls():
        for tbl in ("clause_flags", "clause_embeddings", "parsed_clauses",
                    "analysis_tasks", "project_files"):
            await s.execute(text(f"DELETE FROM {tbl} WHERE project_id = :p"), {"p": pid})
        await s.execute(text("DELETE FROM projects WHERE id = :p"), {"p": pid})
        await s.commit()
        break


@pytest.mark.asyncio
async def test_similar_returns_related_clauses_excluding_self(
    client: AsyncClient, tenant_a_headers: dict
):
    project_id, flag_id, clause_id, tenant = await _seed_finding(client, tenant_a_headers)

    # retriever returns the finding's OWN clause + two others; endpoint must drop self.
    fake_hits = [
        {"chunk_id": "self", "chunk_text": "Limitation of liability applies here.",
         "score": 0.99, "payload": {"clause_id": clause_id}},
        {"chunk_id": "c-ind", "chunk_text": "Indemnification obligations of the parties.",
         "score": 0.82, "payload": {"clause_id": str(uuid.uuid4())}},
        {"chunk_id": "c-war", "chunk_text": "Warranty and representations.",
         "score": 0.70, "payload": {"clause_id": str(uuid.uuid4())}},
    ]
    fake_retriever = AsyncMock()
    fake_retriever.retrieve = AsyncMock(return_value=fake_hits)

    original = settings.ENABLE_EMBEDDINGS
    settings.ENABLE_EMBEDDINGS = True  # type: ignore[assignment]
    try:
        with patch("app.api.v1.endpoints.tasks.get_hybrid_retriever",
                   return_value=fake_retriever):
            resp = await client.get(
                f"/api/v1/projects/{project_id}/findings/{flag_id}/similar",
                headers=tenant_a_headers,
            )
    finally:
        settings.ENABLE_EMBEDDINGS = original  # type: ignore[assignment]

    try:
        assert resp.status_code == 200
        body = resp.json()
        ids = [r["clause_id"] for r in body["results"]]
        # the finding's own clause must NOT be in the results
        assert clause_id not in ids
        # the two genuinely-related clauses come back
        assert len(body["results"]) == 2

        # retrieval was scoped to org + project
        _, kwargs = fake_retriever.retrieve.call_args
        assert kwargs["scope_filter"]["project_id"] == project_id
        assert kwargs["scope_filter"]["organization_id"] == tenant
    finally:
        await _cleanup(project_id)


@pytest.mark.asyncio
async def test_similar_disabled_returns_clear_error(
    client: AsyncClient, tenant_a_headers: dict
):
    project_id, flag_id, _, _ = await _seed_finding(client, tenant_a_headers)
    original = settings.ENABLE_EMBEDDINGS
    settings.ENABLE_EMBEDDINGS = False  # type: ignore[assignment]
    try:
        resp = await client.get(
            f"/api/v1/projects/{project_id}/findings/{flag_id}/similar",
            headers=tenant_a_headers,
        )
    finally:
        settings.ENABLE_EMBEDDINGS = original  # type: ignore[assignment]
    try:
        assert resp.status_code in (400, 422, 503)
    finally:
        await _cleanup(project_id)


@pytest.mark.asyncio
async def test_similar_unknown_finding_404(client: AsyncClient, tenant_a_headers: dict):
    proj = await client.post("/api/v1/projects", json={"name": "NF"},
                             headers=tenant_a_headers)
    project_id = proj.json()["id"]
    original = settings.ENABLE_EMBEDDINGS
    settings.ENABLE_EMBEDDINGS = True  # type: ignore[assignment]
    try:
        resp = await client.get(
            f"/api/v1/projects/{project_id}/findings/{uuid.uuid4()}/similar",
            headers=tenant_a_headers,
        )
    finally:
        settings.ENABLE_EMBEDDINGS = original  # type: ignore[assignment]
    try:
        assert resp.status_code == 404
    finally:
        await _cleanup(project_id)
