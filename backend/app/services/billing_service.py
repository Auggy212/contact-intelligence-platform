"""
Billing service — owns all subscription and usage logic.

Responsibilities:
  - Create / upsert Subscription row from Stripe webhook data
  - Derive plan from Stripe price ID (config-driven, no hardcoding)
  - Increment UsageRecord counters (contracts processed, AI tokens)
  - Quota check before task creation
  - Convenience helpers used by the webhook handler
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.constants import (
    PLAN_LIMITS,
    SubscriptionPlan,
    SubscriptionStatus,
)
from app.core.exceptions import QuotaExceededError
from app.core.logging import get_logger
from app.models.billing import Subscription, UsageRecord

logger = get_logger(__name__)


def _billing_period() -> str:
    """Returns current billing period as 'YYYY-MM'."""
    return datetime.now(timezone.utc).strftime("%Y-%m")


def _derive_plan(stripe_data: dict) -> SubscriptionPlan:
    """
    Map Stripe price IDs back to our plan names.
    Falls back to TRIAL if no match (e.g. during initial checkout creation).
    """
    price_map = {
        settings.STRIPE_PRICE_STARTER: SubscriptionPlan.STARTER,
        settings.STRIPE_PRICE_PROFESSIONAL: SubscriptionPlan.PROFESSIONAL,
    }
    items = stripe_data.get("items", {}).get("data", [])
    for item in items:
        price_id = item.get("price", {}).get("id", "")
        if price_id in price_map:
            return price_map[price_id]
    return SubscriptionPlan.TRIAL


class BillingService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    # ------------------------------------------------------------------
    # Subscription management
    # ------------------------------------------------------------------

    async def get_subscription(self, org_id: uuid.UUID) -> Subscription | None:
        result = await self._db.execute(
            select(Subscription).where(Subscription.organization_id == org_id)
        )
        return result.scalar_one_or_none()

    async def create_trial_subscription(self, org_id: uuid.UUID) -> Subscription:
        """Seeds a TRIAL subscription row when a new org is created via Clerk webhook."""
        existing = await self.get_subscription(org_id)
        if existing:
            return existing

        sub = Subscription(
            organization_id=org_id,
            plan=SubscriptionPlan.TRIAL,
            status=SubscriptionStatus.TRIALING,
        )
        self._db.add(sub)
        await self._db.flush()
        logger.info("trial_subscription_created", org_id=str(org_id))
        return sub

    async def upsert_from_stripe(self, tenant_id: str, stripe_data: dict) -> Subscription:
        """
        Create or update a Subscription from a Stripe subscription object.
        Called by the webhook handler for subscription.created / .updated.
        """
        _status_map = {
            "active":   SubscriptionStatus.ACTIVE,
            "past_due": SubscriptionStatus.PAST_DUE,
            "canceled": SubscriptionStatus.CANCELED,
            "trialing": SubscriptionStatus.TRIALING,
            "unpaid":   SubscriptionStatus.PAST_DUE,
        }

        org_uuid = uuid.UUID(tenant_id)
        sub = await self.get_subscription(org_uuid)
        if not sub:
            sub = Subscription(organization_id=org_uuid)
            self._db.add(sub)

        sub.stripe_subscription_id = stripe_data.get("id")
        sub.stripe_customer_id = stripe_data.get("customer")
        sub.plan = _derive_plan(stripe_data)
        sub.status = _status_map.get(stripe_data.get("status", ""), SubscriptionStatus.ACTIVE)

        if stripe_data.get("current_period_start"):
            sub.current_period_start = datetime.fromtimestamp(
                stripe_data["current_period_start"], tz=timezone.utc
            )
        if stripe_data.get("current_period_end"):
            sub.current_period_end = datetime.fromtimestamp(
                stripe_data["current_period_end"], tz=timezone.utc
            )
        if stripe_data.get("trial_end"):
            sub.trial_end = datetime.fromtimestamp(
                stripe_data["trial_end"], tz=timezone.utc
            )

        await self._db.flush()
        logger.info("subscription_upserted", org_id=tenant_id, plan=sub.plan, status=sub.status)
        return sub

    async def cancel_subscription(self, tenant_id: str) -> None:
        sub = await self.get_subscription(uuid.UUID(tenant_id))
        if sub:
            sub.status = SubscriptionStatus.CANCELED
            await self._db.flush()

    async def mark_past_due(self, stripe_customer_id: str) -> None:
        result = await self._db.execute(
            select(Subscription).where(Subscription.stripe_customer_id == stripe_customer_id)
        )
        sub = result.scalar_one_or_none()
        if sub:
            sub.status = SubscriptionStatus.PAST_DUE
            await self._db.flush()

    async def clear_past_due(self, stripe_customer_id: str) -> None:
        result = await self._db.execute(
            select(Subscription).where(Subscription.stripe_customer_id == stripe_customer_id)
        )
        sub = result.scalar_one_or_none()
        if sub and sub.status == SubscriptionStatus.PAST_DUE:
            sub.status = SubscriptionStatus.ACTIVE
            await self._db.flush()
            logger.info("subscription_past_due_cleared", customer_id=stripe_customer_id)

    # ------------------------------------------------------------------
    # Usage tracking
    # ------------------------------------------------------------------

    async def _get_or_create_usage_record(self, org_id: uuid.UUID) -> UsageRecord:
        """Returns (or creates) the UsageRecord for the current billing period."""
        sub = await self.get_subscription(org_id)
        if not sub:
            sub = await self.create_trial_subscription(org_id)

        period = _billing_period()
        result = await self._db.execute(
            select(UsageRecord).where(
                UsageRecord.subscription_id == sub.id,
                UsageRecord.billing_period == period,
            )
        )
        record = result.scalar_one_or_none()
        if not record:
            record = UsageRecord(
                subscription_id=sub.id,
                organization_id=org_id,
                billing_period=period,
            )
            self._db.add(record)
            await self._db.flush()
        return record

    async def increment_usage(
        self,
        org_id: uuid.UUID,
        *,
        contracts: int = 0,
        ai_tokens: int = 0,
        storage_bytes: int = 0,
    ) -> None:
        """Increment usage counters for the current billing period."""
        record = await self._get_or_create_usage_record(org_id)
        record.contracts_processed += contracts
        record.ai_tokens_used += ai_tokens
        record.storage_bytes_used += storage_bytes
        await self._db.flush()
        logger.debug(
            "usage_incremented",
            org_id=str(org_id),
            contracts=contracts,
            ai_tokens=ai_tokens,
        )

    # ------------------------------------------------------------------
    # Quota enforcement
    # ------------------------------------------------------------------

    async def check_task_quota(self, org_id: uuid.UUID) -> None:
        """
        Raises QuotaExceededError if the tenant has hit their monthly
        contract processing limit for the current plan.
        """
        if settings.is_testing:
            return

        sub = await self.get_subscription(org_id)
        if sub is None:
            # No subscription row — treat as trial
            plan = SubscriptionPlan.TRIAL
        else:
            if sub.status not in (SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING):
                raise QuotaExceededError(
                    "Your subscription is not active. Please update your billing details."
                )
            plan = sub.plan

        limit = PLAN_LIMITS.get(plan, PLAN_LIMITS[SubscriptionPlan.TRIAL]).get(
            "projects_per_month", 3
        )
        if limit == -1:
            return  # unlimited plan

        period = _billing_period()
        if sub:
            result = await self._db.execute(
                select(UsageRecord).where(
                    UsageRecord.subscription_id == sub.id,
                    UsageRecord.billing_period == period,
                )
            )
            record = result.scalar_one_or_none()
            used = record.contracts_processed if record else 0
        else:
            used = 0

        if used >= limit:
            raise QuotaExceededError(
                f"Monthly contract limit of {limit} reached for your {plan} plan. "
                "Please upgrade to process more contracts."
            )
