import uuid

from pgvector.sqlalchemy import Vector
from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKey


class ClauseEmbedding(Base, UUIDPrimaryKey, TimestampMixin):
    """
    A chunk-level embedding row (Phase 6 — semantic / RAG).

    One ParsedClause can produce many chunks (an oversized clause is split; tiny
    fragments merge), so embeddings live at CHUNK granularity, not clause
    granularity. Postgres is the source of truth; the Qdrant collection is a
    rebuildable derived index whose points mirror these rows (by chunk_id).

    Tenant isolation is enforced two ways: RLS on this table (organization_id)
    AND a payload filter on every Qdrant search — defense in depth.
    """

    __tablename__ = "clause_embeddings"

    # ── Tenant scope (RLS + Qdrant payload filter) ──────────────────────────────
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )

    # ── Provenance: where this chunk came from ──────────────────────────────────
    clause_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("parsed_clauses.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )

    # ── Chunk payload (mirrors a chunk dict from chunking.py) ────────────────────
    # Stable, content-hashed id — unique so re-embedding a document is idempotent.
    chunk_id: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    char_start: Mapped[int | None] = mapped_column(Integer, nullable=True)
    char_end: Mapped[int | None] = mapped_column(Integer, nullable=True)
    clause_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    file_role: Mapped[str | None] = mapped_column(String(8), nullable=True)

    # ── The vector + who made it (so we know when to re-embed) ───────────────────
    # Variable-dimension on purpose: this column mirrors whatever the active
    # provider produced (nvidia 1024, local bge 384, …). We don't build an ANN
    # index on it — Qdrant is the search index — so a fixed dim isn't needed, and
    # leaving it free lets you switch EMBEDDING_PROVIDER without a schema change.
    embedding: Mapped[list[float] | None] = mapped_column(Vector(), nullable=True)
    embedding_provider: Mapped[str | None] = mapped_column(String(32), nullable=True)
    embedding_model: Mapped[str | None] = mapped_column(String(128), nullable=True)

    clause: Mapped["ParsedClause"] = relationship()
