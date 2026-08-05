"""
Semantic search endpoint (Phase 6) — the API surface for hybrid retrieval.

Lets you query a project's contract clauses in natural language and get back the
most relevant chunks, ranked. This is what makes Phase 6 observable end-to-end:
upload → (embed on upload) → search here → see the right clauses come back.

Retrieval = vector (Qdrant) + lexical (Postgres full-text), fused by RRF, and
MANDATORILY scoped to the caller's org + the requested project (RLS + payload
filter). Requires ENABLE_EMBEDDINGS=true (otherwise there are no vectors to
search); returns a clear 503 when it's off.
"""

import uuid

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session, get_tenant_id
from app.core.config import settings
from app.services.retrieval_service import get_hybrid_retriever

router = APIRouter(prefix="/projects/{project_id}/search", tags=["Search"])


class SearchHit(BaseModel):
    chunk_id: str
    chunk_text: str
    score: float
    payload: dict


class SearchResponse(BaseModel):
    query: str
    project_id: uuid.UUID
    count: int
    results: list[SearchHit]


@router.get("", response_model=SearchResponse)
async def search_project(
    project_id: uuid.UUID,
    q: str = Query(..., min_length=1, description="Natural-language search query"),
    limit: int = Query(10, ge=1, le=50),
    tenant_id: str = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
) -> SearchResponse:
    if not settings.ENABLE_EMBEDDINGS:
        from app.core.exceptions import ValidationError

        raise ValidationError(
            "Semantic search is disabled. Set ENABLE_EMBEDDINGS=true and upload a "
            "document so its clauses get embedded, then try again."
        )

    scope = {"organization_id": tenant_id, "project_id": str(project_id)}
    retriever = get_hybrid_retriever(session)
    hits = await retriever.retrieve(q, scope_filter=scope, limit=limit)

    results = [
        SearchHit(
            chunk_id=h["chunk_id"],
            chunk_text=h["chunk_text"],
            score=h["score"],
            payload=h.get("payload", {}),
        )
        for h in hits
    ]
    return SearchResponse(
        query=q, project_id=project_id, count=len(results), results=results
    )
