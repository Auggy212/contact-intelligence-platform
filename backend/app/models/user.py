import uuid

from sqlalchemy import Boolean, Enum, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constants import Role
from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKey


class User(Base, UUIDPrimaryKey, TimestampMixin):
    __tablename__ = "users"

    clerk_user_id: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(256), nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    memberships: Mapped[list["Membership"]] = relationship(back_populates="user")


class Membership(Base, UUIDPrimaryKey, TimestampMixin):
    __tablename__ = "memberships"
    __table_args__ = (
        UniqueConstraint("user_id", "organization_id", name="uq_membership_user_org"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True
    )
    role: Mapped[Role] = mapped_column(Enum(Role, native_enum=False), nullable=False, default=Role.VIEWER)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    user: Mapped["User"] = relationship(back_populates="memberships")
    organization: Mapped["Organization"] = relationship(back_populates="memberships")
