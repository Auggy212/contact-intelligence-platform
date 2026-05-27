import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constants import SubscriptionPlan, SubscriptionStatus
from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKey


class Subscription(Base, UUIDPrimaryKey, TimestampMixin):
    __tablename__ = "subscriptions"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, unique=True, index=True
    )
    stripe_customer_id: Mapped[str | None] = mapped_column(String(128), nullable=True, unique=True)
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(128), nullable=True, unique=True)

    plan: Mapped[SubscriptionPlan] = mapped_column(String(32), nullable=False, default=SubscriptionPlan.TRIAL)
    status: Mapped[SubscriptionStatus] = mapped_column(String(32), nullable=False, default=SubscriptionStatus.TRIALING)

    current_period_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    current_period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    trial_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    trial_emails_sent: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    organization: Mapped["Organization"] = relationship(back_populates="subscription")
    usage_records: Mapped[list["UsageRecord"]] = relationship(back_populates="subscription")


class UsageRecord(Base, UUIDPrimaryKey, TimestampMixin):
    __tablename__ = "usage_records"

    subscription_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("subscriptions.id"), nullable=False, index=True
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)

    billing_period: Mapped[str] = mapped_column(String(7), nullable=False)

    contracts_processed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    ai_tokens_used: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    storage_bytes_used: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)

    subscription: Mapped["Subscription"] = relationship(back_populates="usage_records")
