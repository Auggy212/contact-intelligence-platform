import uuid

from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constants import EMBEDDING_DIMENSIONS
from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKey


class ParsedClause(Base, UUIDPrimaryKey, TimestampMixin):
    __tablename__ = "parsed_clauses"

    file_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("project_files.id"), nullable=False, index=True
    )
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)

    clause_number: Mapped[str | None] = mapped_column(String(64), nullable=True)
    heading: Mapped[str | None] = mapped_column(String(512), nullable=True)
    body_text: Mapped[str] = mapped_column(Text, nullable=False)
    paragraph_index: Mapped[int] = mapped_column(Integer, nullable=False)
    char_start: Mapped[int] = mapped_column(Integer, nullable=False)
    char_end: Mapped[int] = mapped_column(Integer, nullable=False)

    # OOXML change tracking
    has_tracked_insertion: Mapped[bool] = mapped_column(Boolean, default=False)
    has_tracked_deletion: Mapped[bool] = mapped_column(Boolean, default=False)
    has_strikethrough: Mapped[bool] = mapped_column(Boolean, default=False)
    has_comment: Mapped[bool] = mapped_column(Boolean, default=False)
    change_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Vector embedding (voyage-law-2 = 1024 dimensions)
    embedding: Mapped[list[float] | None] = mapped_column(
        Vector(EMBEDDING_DIMENSIONS), nullable=True
    )

    file: Mapped["ProjectFile"] = relationship(back_populates="parsed_clauses")
    clause_flags: Mapped[list["ClauseFlag"]] = relationship(back_populates="clause")


class ClauseFlag(Base, UUIDPrimaryKey, TimestampMixin):
    """A finding/flag raised by an AI agent on a specific clause."""

    __tablename__ = "clause_flags"

    clause_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("parsed_clauses.id"), nullable=False, index=True
    )
    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("analysis_tasks.id"), nullable=False, index=True
    )
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)

    flag_type: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    recommendation: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Citation fields for exact provenance
    source_clause_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    reasoning_trace: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Numeric risk score 1–10 (vendor diff and template comparison agents)
    risk_score: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Law citation fields (Agent 3 — Indian Law Validator)
    law_act_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    law_section_number: Mapped[str | None] = mapped_column(String(64), nullable=True)
    law_retrieved_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    law_jurisdiction: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Reviewer decision
    reviewer_status: Mapped[str] = mapped_column(String(16), default="pending", nullable=False)
    reviewer_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    clause: Mapped["ParsedClause"] = relationship(back_populates="clause_flags")
    task: Mapped["AnalysisTask"] = relationship(back_populates="clause_flags")
