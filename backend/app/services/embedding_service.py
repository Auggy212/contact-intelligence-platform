"""
Embedding service (Phase 6.5) — turn parsed clauses into chunk embeddings and
write them to BOTH stores:

  - Postgres `clause_embeddings`  → source of truth (survives, RLS-protected)
  - the pluggable vector store    → rebuildable derived ANN index (Qdrant/pgvector)

The heavy lifting is a PURE, dependency-injected core (`build_chunk_embeddings`)
that takes a provider + store, so it's fully unit-testable offline with fakes —
no API key, no credits, no DB. The DB-facing wrapper (`embed_document`) reads
clauses for a document, calls the core, and persists ClauseEmbedding rows.

Provider/store are chosen by config via the factory, so switching NVIDIA↔local
or Qdrant↔pgvector is a config change, never a code change.
"""

from __future__ import annotations

import uuid
from typing import Any

from app.ai.chunking import DEFAULT_MAX_TOKENS, DEFAULT_OVERLAP_TOKENS, chunk_clauses
from app.ai.providers.base import EmbeddingProvider, VectorStore
from app.core.logging import get_logger

logger = get_logger(__name__)

# Payload keys pushed to the vector store. MUST include the tenant scope so every
# search can filter server-side (defense-in-depth with Postgres RLS).
_PAYLOAD_KEYS = (
    "organization_id", "project_id", "document_id", "clause_id",
    "clause_type", "file_role", "char_start", "char_end",
)


def build_chunk_embeddings(
    clauses: list[dict[str, Any]],
    *,
    provider: EmbeddingProvider,
    store: VectorStore,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    overlap_tokens: int = DEFAULT_OVERLAP_TOKENS,
) -> list[dict[str, Any]]:
    """
    Chunk → embed → upsert to the vector store. Returns one row-dict per chunk,
    shaped for the ClauseEmbedding model. Pure orchestration (no DB, no config).

    Empty input is a no-op: no embed call (no credits), no upsert.
    """
    chunks = chunk_clauses(clauses, max_tokens=max_tokens, overlap_tokens=overlap_tokens)
    if not chunks:
        return []

    vectors = provider.embed([c["text"] for c in chunks])
    if len(vectors) != len(chunks):
        raise RuntimeError(
            f"embedding provider returned {len(vectors)} vectors for {len(chunks)} chunks"
        )

    store.ensure_collection(provider.dimension)

    rows: list[dict[str, Any]] = []
    points: list[dict[str, Any]] = []
    for chunk, vector in zip(chunks, vectors):
        rows.append({
            "chunk_id": chunk["chunk_id"],
            "chunk_text": chunk["text"],
            "token_count": chunk["token_count"],
            "clause_id": chunk["clause_id"],
            "document_id": chunk["document_id"],
            "project_id": chunk["project_id"],
            "organization_id": chunk["organization_id"],
            "clause_type": chunk.get("clause_type"),
            "file_role": chunk.get("file_role"),
            "char_start": chunk.get("char_start"),
            "char_end": chunk.get("char_end"),
            "embedding": vector,
            "embedding_provider": provider.name,
        })
        points.append({
            "id": chunk["chunk_id"],
            "vector": vector,
            "payload": {k: chunk.get(k) for k in _PAYLOAD_KEYS} | {"chunk_text": chunk["text"]},
        })

    store.upsert(points)
    return rows


def _clause_to_dict(pc: Any) -> dict[str, Any]:
    """Map a ParsedClause row into the chunker's clause-dict shape."""
    return {
        "id": str(pc.id),
        "heading": pc.heading,
        "body_text": pc.body_text,
        "char_start": pc.char_start,
        "char_end": pc.char_end,
        "clause_type": None,  # ParsedClause has no clause_type; agents classify later
        "file_role": None,
        "document_id": str(pc.file_id),
        "project_id": str(pc.project_id),
        "organization_id": str(pc.organization_id),
    }


async def embed_document(file_id: str, tenant_id: str) -> dict[str, Any]:
    """
    DB-facing wrapper: read a document's clauses, embed their chunks, and persist
    ClauseEmbedding rows (upserting the vector store as a side effect). Uses the
    config-selected provider + store via the factory.

    Idempotent: existing embeddings for the document are cleared first, so a
    re-parse/re-embed replaces cleanly (chunk_ids are content-stable anyway).
    """
    from sqlalchemy import delete, select

    from app.ai.providers.factory import get_embedding_provider, get_vector_store
    from app.core.config import settings
    from app.core.database import get_db
    from app.models.clause import ParsedClause
    from app.models.embedding import ClauseEmbedding

    provider = get_embedding_provider(settings.EMBEDDING_PROVIDER)
    store = get_vector_store(settings.VECTOR_STORE)
    model_name = _provider_model_name(settings)

    async for session in get_db(tenant_id):
        result = await session.execute(
            select(ParsedClause).where(ParsedClause.file_id == uuid.UUID(file_id))
        )
        parsed = result.scalars().all()
        if not parsed:
            return {"file_id": file_id, "chunks_embedded": 0}

        clauses = [_clause_to_dict(pc) for pc in parsed]
        rows = build_chunk_embeddings(clauses, provider=provider, store=store)

        # Idempotent replace: drop prior embeddings for this document first.
        await session.execute(
            delete(ClauseEmbedding).where(ClauseEmbedding.document_id == uuid.UUID(file_id))
        )
        for r in rows:
            session.add(ClauseEmbedding(
                organization_id=uuid.UUID(r["organization_id"]),
                project_id=uuid.UUID(r["project_id"]),
                clause_id=uuid.UUID(r["clause_id"]),
                document_id=uuid.UUID(r["document_id"]),
                chunk_id=r["chunk_id"],
                chunk_text=r["chunk_text"],
                token_count=r["token_count"],
                char_start=r["char_start"],
                char_end=r["char_end"],
                clause_type=r["clause_type"],
                file_role=r["file_role"],
                embedding=r["embedding"],
                embedding_provider=r["embedding_provider"],
                embedding_model=model_name,
            ))
        await session.flush()

    logger.info("embed_document_complete", file_id=file_id, chunks=len(rows))
    return {"file_id": file_id, "chunks_embedded": len(rows)}


def _provider_model_name(settings: Any) -> str:
    """Best-effort model identifier for provenance, based on the active provider."""
    prov = settings.EMBEDDING_PROVIDER
    return {
        "nvidia": settings.NVIDIA_EMBEDDING_MODEL,
        "local": settings.LOCAL_EMBEDDING_MODEL,
        "voyage": settings.VOYAGE_MODEL,
        "openai": settings.OPENAI_EMBEDDING_MODEL,
    }.get(prov, prov)
