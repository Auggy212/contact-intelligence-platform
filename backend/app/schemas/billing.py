import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.core.constants import SubscriptionPlan, SubscriptionStatus
from app.schemas.common import IDSchema, TimestampSchema


class SubscriptionOut(IDSchema, TimestampSchema):
    organization_id: uuid.UUID
    stripe_customer_id: str | None
    stripe_subscription_id: str | None
    plan: SubscriptionPlan
    status: SubscriptionStatus
    current_period_start: datetime | None
    current_period_end: datetime | None
    trial_end: datetime | None


class UsageRecordOut(IDSchema, TimestampSchema):
    organization_id: uuid.UUID
    billing_period: str
    contracts_processed: int
    ai_tokens_used: int
    storage_bytes_used: int


class CreateCheckoutSessionRequest(BaseModel):
    plan: SubscriptionPlan
    success_url: str
    cancel_url: str


class CreateCheckoutSessionResponse(BaseModel):
    checkout_url: str


class CreatePortalSessionResponse(BaseModel):
    portal_url: str
