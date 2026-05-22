import uuid

from sqlalchemy import BigInteger, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constants import FileRole, ProjectStatus
from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKey


class Project(Base, UUIDPrimaryKey, TimestampMixin):
    __tablename__ = "projects"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True
    )
    workspace_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=True, index=True
    )
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    name: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[ProjectStatus] = mapped_column(
        Enum(ProjectStatus, native_enum=False), nullable=False, default=ProjectStatus.DRAFT
    )

    organization: Mapped["Organization"] = relationship(back_populates="projects")
    workspace: Mapped["Workspace | None"] = relationship(back_populates="projects")
    files: Mapped[list["ProjectFile"]] = relationship(back_populates="project")
    analysis_tasks: Mapped[list["AnalysisTask"]] = relationship(back_populates="project")


class ProjectFile(Base, UUIDPrimaryKey, TimestampMixin):
    __tablename__ = "project_files"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    uploaded_by_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    file_role: Mapped[FileRole] = mapped_column(Enum(FileRole, native_enum=False), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(512), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(1024), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(128), nullable=False)
    parse_status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)

    project: Mapped["Project"] = relationship(back_populates="files")
    parsed_clauses: Mapped[list["ParsedClause"]] = relationship(back_populates="file")
