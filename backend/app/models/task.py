import uuid

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constants import TaskStatus, TaskType
from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKey


class AnalysisTask(Base, UUIDPrimaryKey, TimestampMixin):
    __tablename__ = "analysis_tasks"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    triggered_by_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    task_type: Mapped[TaskType] = mapped_column(String(64), nullable=False)
    status: Mapped[TaskStatus] = mapped_column(String(32), nullable=False, default=TaskStatus.QUEUED)

    celery_task_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    model_version: Mapped[str | None] = mapped_column(String(128), nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    input_file_ids: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    project: Mapped["Project"] = relationship(back_populates="analysis_tasks")
    result: Mapped["TaskResult | None"] = relationship(back_populates="task", uselist=False)
    clause_flags: Mapped[list["ClauseFlag"]] = relationship(back_populates="task")


class TaskResult(Base, UUIDPrimaryKey, TimestampMixin):
    __tablename__ = "task_results"

    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("analysis_tasks.id"), nullable=False, unique=True, index=True
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)

    raw_output: Mapped[dict] = mapped_column(JSONB, nullable=False)
    token_usage: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    task: Mapped["AnalysisTask"] = relationship(back_populates="result")
