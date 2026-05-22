import uuid

from pydantic import BaseModel, ConfigDict, field_validator

from app.schemas.common import IDSchema, TimestampSchema


class OrganizationCreate(BaseModel):
    name: str
    clerk_org_id: str
    logo_url: str | None = None

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Name cannot be empty")
        return v.strip()


class OrganizationUpdate(BaseModel):
    name: str | None = None
    logo_url: str | None = None


class OrganizationOut(IDSchema, TimestampSchema):
    clerk_org_id: str
    name: str
    slug: str
    logo_url: str | None
    is_active: bool


class WorkspaceCreate(BaseModel):
    name: str
    description: str | None = None


class WorkspaceUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


class WorkspaceOut(IDSchema, TimestampSchema):
    organization_id: uuid.UUID
    name: str
    description: str | None
    is_active: bool
