import uuid

from sqlalchemy import Boolean, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKey


class ClauseLibraryEntry(Base, UUIDPrimaryKey, TimestampMixin):
    """Per-tenant approved/rejected clause library, also indexed in Qdrant."""

    __tablename__ = "clause_library_entries"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True
    )
    added_by_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    title: Mapped[str] = mapped_column(String(512), nullable=False)
    body_text: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str | None] = mapped_column(String(128), nullable=True)
    tags: Mapped[str | None] = mapped_column(String(512), nullable=True)

    # "approved" = use this clause, "rejected" = flag when seen
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="approved")

    # Qdrant point ID for this entry (set after vector upsert)
    qdrant_point_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    organization: Mapped["Organization"] = relationship(back_populates="clause_library_entries")
