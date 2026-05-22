"""
Unit tests for BillingService — no real DB, no network.
Uses cipdb_test (from conftest db_session fixture) with full schema.
"""

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import SubscriptionPlan, SubscriptionStatus
from app.core.exceptions import QuotaExceededError
from app.models.billing import Subscription, UsageRecord
from app.models.organization import Organization
from app.services.billing_service import BillingService, _billing_period, _derive_plan


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _seed_org(session: AsyncSession) -> Organization:
    org = Organization(
        clerk_org_id=f"test_{uuid.uuid4().hex[:8]}",
        name="Unit Test Org",
        slug=f"unit-{uuid.uuid4().hex[:8]}",
    )
    session.add(org)
    await session.flush()
    return org


# ---------------------------------------------------------------------------
# _billing_period
# ---------------------------------------------------------------------------

def test_billing_period_format():
    period = _billing_period()
    assert len(period) == 7
    assert period[4] == "-"
    assert period[:4].isdigit()
    assert period[5:].isdigit()


# ---------------------------------------------------------------------------
# _derive_plan
# ---------------------------------------------------------------------------

def test_derive_plan_starter(monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "STRIPE_PRICE_STARTER", "price_starter_123")
    monkeypatch.setattr(settings, "STRIPE_PRICE_PROFESSIONAL", "price_pro_456")

    stripe_data = {"items": {"data": [{"price": {"id": "price_starter_123"}}]}}
    assert _derive_plan(stripe_data) == SubscriptionPlan.STARTER


def test_derive_plan_professional(monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "STRIPE_PRICE_STARTER", "price_starter_123")
    monkeypatch.setattr(settings, "STRIPE_PRICE_PROFESSIONAL", "price_pro_456")

    stripe_data = {"items": {"data": [{"price": {"id": "price_pro_456"}}]}}
    assert _derive_plan(stripe_data) == SubscriptionPlan.PROFESSIONAL


def test_derive_plan_unknown_falls_back_to_trial():
    stripe_data = {"items": {"data": [{"price": {"id": "price_unknown"}}]}}
    assert _derive_plan(stripe_data) == SubscriptionPlan.TRIAL


def test_derive_plan_no_items():
    assert _derive_plan({}) == SubscriptionPlan.TRIAL


# ---------------------------------------------------------------------------
# create_trial_subscription
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_trial_subscription(db_session: AsyncSession):
    org = await _seed_org(db_session)
    svc = BillingService(db_session)

    sub = await svc.create_trial_subscription(org.id)

    assert sub.organization_id == org.id
    assert sub.plan == SubscriptionPlan.TRIAL
    assert sub.status == SubscriptionStatus.TRIALING


@pytest.mark.asyncio
async def test_create_trial_subscription_idempotent(db_session: AsyncSession):
    org = await _seed_org(db_session)
    svc = BillingService(db_session)

    sub1 = await svc.create_trial_subscription(org.id)
    sub2 = await svc.create_trial_subscription(org.id)

    assert sub1.id == sub2.id


# ---------------------------------------------------------------------------
# get_subscription
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_subscription_returns_none_when_missing(db_session: AsyncSession):
    svc = BillingService(db_session)
    result = await svc.get_subscription(uuid.uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_get_subscription_returns_existing(db_session: AsyncSession):
    org = await _seed_org(db_session)
    svc = BillingService(db_session)
    await svc.create_trial_subscription(org.id)

    sub = await svc.get_subscription(org.id)
    assert sub is not None
    assert sub.organization_id == org.id


# ---------------------------------------------------------------------------
# cancel_subscription
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_cancel_subscription(db_session: AsyncSession):
    org = await _seed_org(db_session)
    svc = BillingService(db_session)
    await svc.create_trial_subscription(org.id)

    await svc.cancel_subscription(str(org.id))

    sub = await svc.get_subscription(org.id)
    assert sub.status == SubscriptionStatus.CANCELED


# ---------------------------------------------------------------------------
# mark_past_due / clear_past_due
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_mark_and_clear_past_due(db_session: AsyncSession):
    org = await _seed_org(db_session)
    svc = BillingService(db_session)
    sub = await svc.create_trial_subscription(org.id)
    sub.stripe_customer_id = "cus_unit_test"
    sub.status = SubscriptionStatus.ACTIVE
    await db_session.flush()

    await svc.mark_past_due("cus_unit_test")
    sub = await svc.get_subscription(org.id)
    assert sub.status == SubscriptionStatus.PAST_DUE

    await svc.clear_past_due("cus_unit_test")
    sub = await svc.get_subscription(org.id)
    assert sub.status == SubscriptionStatus.ACTIVE


# ---------------------------------------------------------------------------
# increment_usage
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_increment_usage_creates_record(db_session: AsyncSession):
    org = await _seed_org(db_session)
    svc = BillingService(db_session)
    await svc.create_trial_subscription(org.id)

    await svc.increment_usage(org.id, contracts=2, ai_tokens=5000)

    record = await svc._get_or_create_usage_record(org.id)
    assert record.contracts_processed == 2
    assert record.ai_tokens_used == 5000


@pytest.mark.asyncio
async def test_increment_usage_accumulates(db_session: AsyncSession):
    org = await _seed_org(db_session)
    svc = BillingService(db_session)
    await svc.create_trial_subscription(org.id)

    await svc.increment_usage(org.id, contracts=1, ai_tokens=1000)
    await svc.increment_usage(org.id, contracts=1, ai_tokens=2000)

    record = await svc._get_or_create_usage_record(org.id)
    assert record.contracts_processed == 2
    assert record.ai_tokens_used == 3000


# ---------------------------------------------------------------------------
# check_task_quota
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_quota_passes_under_limit(db_session: AsyncSession):
    org = await _seed_org(db_session)
    svc = BillingService(db_session)
    await svc.create_trial_subscription(org.id)
    # Trial limit is 3 projects/month; 0 used → should pass
    await svc.check_task_quota(org.id)  # must not raise


@pytest.mark.asyncio
async def test_quota_raises_when_limit_reached(db_session: AsyncSession):
    org = await _seed_org(db_session)
    svc = BillingService(db_session)
    sub = await svc.create_trial_subscription(org.id)

    # Manually set usage to the trial limit (3)
    record = await svc._get_or_create_usage_record(org.id)
    record.contracts_processed = 3
    await db_session.flush()

    with pytest.raises(QuotaExceededError):
        await svc.check_task_quota(org.id)


@pytest.mark.asyncio
async def test_quota_raises_when_subscription_inactive(db_session: AsyncSession):
    org = await _seed_org(db_session)
    svc = BillingService(db_session)
    sub = await svc.create_trial_subscription(org.id)
    sub.status = SubscriptionStatus.CANCELED
    await db_session.flush()

    with pytest.raises(QuotaExceededError, match="not active"):
        await svc.check_task_quota(org.id)


# ---------------------------------------------------------------------------
# upsert_from_stripe
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_upsert_from_stripe_creates_subscription(db_session: AsyncSession, monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "STRIPE_PRICE_STARTER", "price_s")
    monkeypatch.setattr(settings, "STRIPE_PRICE_PROFESSIONAL", "price_p")

    org = await _seed_org(db_session)
    svc = BillingService(db_session)

    stripe_data = {
        "id": "sub_stripe_123",
        "customer": "cus_stripe_123",
        "status": "active",
        "items": {"data": [{"price": {"id": "price_s"}}]},
    }
    sub = await svc.upsert_from_stripe(str(org.id), stripe_data)

    assert sub.stripe_subscription_id == "sub_stripe_123"
    assert sub.stripe_customer_id == "cus_stripe_123"
    assert sub.plan == SubscriptionPlan.STARTER
    assert sub.status == SubscriptionStatus.ACTIVE
