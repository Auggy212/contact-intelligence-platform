import uuid

from pydantic import BaseModel, EmailStr

from app.core.constants import Role
from app.schemas.common import IDSchema, TimestampSchema


class UserOut(IDSchema, TimestampSchema):
    clerk_user_id: str
    email: str
    full_name: str
    avatar_url: str | None
    is_active: bool


class MembershipOut(IDSchema, TimestampSchema):
    user_id: uuid.UUID
    organization_id: uuid.UUID
    role: Role
    is_active: bool
    user: UserOut | None = None


class InviteMemberRequest(BaseModel):
    email: EmailStr
    role: Role = Role.VIEWER


class UpdateMemberRoleRequest(BaseModel):
    role: Role
