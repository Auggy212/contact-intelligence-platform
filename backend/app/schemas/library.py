import uuid

from pydantic import BaseModel

from app.schemas.common import IDSchema, TimestampSchema


class ClauseLibraryCreate(BaseModel):
    title: str
    body_text: str
    category: str | None = None
    tags: str | None = None
    status: str = "approved"


class ClauseLibraryUpdate(BaseModel):
    title: str | None = None
    body_text: str | None = None
    category: str | None = None
    tags: str | None = None
    status: str | None = None
    is_active: bool | None = None


class ClauseLibraryOut(IDSchema, TimestampSchema):
    organization_id: uuid.UUID
    title: str
    body_text: str
    category: str | None
    tags: str | None
    status: str
    is_active: bool
