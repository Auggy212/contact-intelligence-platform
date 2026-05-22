import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.schemas.common import IDSchema, TimestampSchema


class AuditLogOut(IDSchema, TimestampSchema):
    organization_id: uuid.UUID
    user_id: uuid.UUID | None
    action: str
    resource_type: str | None
    resource_id: uuid.UUID | None
    extra_data: dict[str, Any] | None = None
    model_version: str | None
    prompt_version: str | None
    ip_address: str | None
