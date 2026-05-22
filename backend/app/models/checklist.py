import uuid

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKey


class ChecklistRule(Base, UUIDPrimaryKey, TimestampMixin):
    """
    Per-tenant configurable validation rule.
    Default rules are seeded from scripts/seed_checklist_rules.py.
    """

    __tablename__ = "checklist_rules"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True
    )
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    rule_code: Mapped[str] = mapped_column(String(16), nullable=False)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)

    # The actual rule parameters (thresholds, allowed values, etc.)
    # e.g. {"min_months": 12, "max_months": 36} for agreement duration
    rule_config: Mapped[dict] = mapped_column(JSONB, nullable=False)

    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    organization: Mapped["Organization"] = relationship(back_populates="checklist_rules")
