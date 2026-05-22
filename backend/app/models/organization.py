import uuid

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKey


class Organization(Base, UUIDPrimaryKey, TimestampMixin):
    __tablename__ = "organizations"

    # clerk_org_id is the external Clerk organization ID used to map JWTs → tenants
    clerk_org_id: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    slug: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    logo_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    admin_email: Mapped[str | None] = mapped_column(String(256), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    workspaces: Mapped[list["Workspace"]] = relationship(back_populates="organization")
    memberships: Mapped[list["Membership"]] = relationship(back_populates="organization")
    projects: Mapped[list["Project"]] = relationship(back_populates="organization")
    subscription: Mapped["Subscription | None"] = relationship(back_populates="organization", uselist=False)
    checklist_rules: Mapped[list["ChecklistRule"]] = relationship(back_populates="organization")
    clause_library_entries: Mapped[list["ClauseLibraryEntry"]] = relationship(back_populates="organization")
    audit_logs: Mapped[list["AuditLog"]] = relationship(back_populates="organization")


class Workspace(Base, UUIDPrimaryKey, TimestampMixin):
    __tablename__ = "workspaces"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    organization: Mapped["Organization"] = relationship(back_populates="workspaces")
    projects: Mapped[list["Project"]] = relationship(back_populates="workspace")
