import uuid

from pydantic import BaseModel

from app.core.constants import FileRole, ProjectStatus
from app.schemas.common import IDSchema, TimestampSchema


class ProjectCreate(BaseModel):
    name: str
    description: str | None = None
    workspace_id: uuid.UUID | None = None


class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    status: ProjectStatus | None = None


class ProjectOut(IDSchema, TimestampSchema):
    organization_id: uuid.UUID
    workspace_id: uuid.UUID | None
    name: str
    description: str | None
    status: ProjectStatus


class ProjectFileOut(IDSchema, TimestampSchema):
    project_id: uuid.UUID
    file_role: FileRole
    original_filename: str
    file_size_bytes: int
    mime_type: str
    parse_status: str


class DocumentUploadResponse(BaseModel):
    file_id: uuid.UUID
    storage_key: str
    presigned_url: str | None = None
    parse_status: str = "pending"
