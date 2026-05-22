import uuid

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKey


class AuditLog(Base, UUIDPrimaryKey, TimestampMixin):
    """
    Immutable audit trail. Every AI task, approve/reject, and admin action is logged.
    Rows are INSERT-only — never updated or deleted.
    """

    __tablename__ = "audit_log"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)

    action: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    resource_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    resource_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    # Full context snapshot for the audit entry (named extra_data to avoid SQLAlchemy reserved 'metadata')
    extra_data: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)

    # For AI tasks: model version and prompt version at time of execution
    model_version: Mapped[str | None] = mapped_column(String(128), nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String(64), nullable=True)

    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)

    organization: Mapped["Organization"] = relationship(back_populates="audit_logs")
