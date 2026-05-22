import uuid
from typing import Any

from pydantic import BaseModel

from app.core.constants import TaskStatus, TaskType
from app.schemas.common import IDSchema, TimestampSchema


class TaskTriggerRequest(BaseModel):
    task_types: list[TaskType]


class TaskOut(IDSchema, TimestampSchema):
    project_id: uuid.UUID
    task_type: TaskType
    status: TaskStatus
    model_version: str | None
    prompt_version: str | None
    error_message: str | None
    celery_task_id: str | None


class TaskResultOut(IDSchema, TimestampSchema):
    task_id: uuid.UUID
    raw_output: dict[str, Any]
    token_usage: dict[str, Any] | None


class ClauseFlagOut(IDSchema, TimestampSchema):
    clause_id: uuid.UUID
    task_id: uuid.UUID
    project_id: uuid.UUID
    flag_type: str
    severity: str
    title: str
    description: str
    recommendation: str | None
    source_clause_id: uuid.UUID | None
    confidence: float | None
    reasoning_trace: str | None
    risk_score: int | None
    # Law citation fields (populated for law_validation task findings)
    law_act_name: str | None
    law_section_number: str | None
    law_retrieved_text: str | None
    law_jurisdiction: str | None
    reviewer_status: str
    reviewer_note: str | None


class ReviewFlagRequest(BaseModel):
    status: str  # "approved" | "rejected"
    note: str | None = None
