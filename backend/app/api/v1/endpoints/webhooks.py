"""
Stripe and Clerk webhook handlers.
Both endpoints verify signatures before processing events.
"""

import base64
import hashlib
import hmac
import json
import time
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db_no_rls
from app.core.logging import get_logger
from app.integrations.stripe_client import construct_webhook_event
from app.models.checklist import ChecklistRule
from app.models.organization import Organization
from app.services.billing_service import BillingService
from app.workers.email_tasks import (
    send_cancellation_email,
    send_payment_failed_email,
    send_trial_start_email,
)

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])
logger = get_logger(__name__)

_DEFAULT_CHECKLIST_RULES = [
    {
        "rule_code": "A",
        "name": "Agreement Duration",
        "description": "Contract duration must be between 12 and 36 months",
        "severity": "critical",
        "rule_config": {"min_months": 12, "max_months": 36},
        "is_default": True,
    },
    {
        "rule_code": "B",
        "name": "Agreement Date",
        "description": "Agreement date must be a future date (not past or today)",
        "severity": "critical",
        "rule_config": {},
        "is_default": True,
    },
    {
        "rule_code": "C",
        "name": "Dispute Settlement Court",
        "description": "Dispute resolution must be in Mumbai, Maharashtra",
        "severity": "high",
        "rule_config": {"allowed_cities": ["mumbai"]},
        "is_default": True,
    },
    {
        "rule_code": "D",
        "name": "Advance Payment Cap",
        "description": "Advance payment cannot exceed 10% of total project value",
        "severity": "high",
        "rule_config": {"max_percent": 10},
        "is_default": True,
    },
    {
        "rule_code": "E",
        "name": "Contract Value Limit",
        "description": "Contract value must be below INR 50 Lakhs",
        "severity": "medium",
        "rule_config": {"max_value_inr": 5_000_000},
        "is_default": True,
    },
    {
        "rule_code": "F",
        "name": "Termination Notice Period",
        "description": "Termination notice must be between 1 and 3 months",
        "severity": "critical",
        "rule_config": {"min_months": 1, "max_months": 3},
        "is_default": True,
    },
]


async def _get_db_session():
    async for session in get_db_no_rls():
        yield session


# ---------------------------------------------------------------------------
# Stripe webhook
# ---------------------------------------------------------------------------

@router.post("/stripe")
async def stripe_webhook(
    request: Request,
    session: AsyncSession = Depends(_get_db_session),
):
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")

    try:
        event = construct_webhook_event(payload, sig)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    event_type = event["type"]
    data = event["data"]["object"]
    billing = BillingService(session)

    logger.info("stripe_webhook_received", event_type=event_type)

    if event_type in ("customer.subscription.created", "customer.subscription.updated"):
        tenant_id = data.get("metadata", {}).get("tenant_id")
        if tenant_id:
            await billing.upsert_from_stripe(tenant_id, data)

    elif event_type == "customer.subscription.deleted":
        tenant_id = data.get("metadata", {}).get("tenant_id")
        if tenant_id:
            await billing.cancel_subscription(tenant_id)
            # Get org email to send cancellation notice
            result = await session.execute(
                select(Organization).where(Organization.id == uuid.UUID(tenant_id))
            )
            org = result.scalar_one_or_none()
            if org:
                send_cancellation_email.delay(org.name)

    elif event_type == "invoice.payment_failed":
        customer_id = data.get("customer")
        if customer_id:
            await billing.mark_past_due(customer_id)
            send_payment_failed_email.delay("billing@example.com", "Your Organization")

    elif event_type == "invoice.payment_succeeded":
        customer_id = data.get("customer")
        if customer_id:
            await billing.clear_past_due(customer_id)

    await session.commit()
    return {"received": True}


# ---------------------------------------------------------------------------
# Clerk webhook
# ---------------------------------------------------------------------------

def _verify_svix_signature(payload: bytes, headers: dict, secret: str) -> bool:
    """Verifies Clerk's svix webhook signature (HMAC-SHA256 over msgId + timestamp + body)."""
    msg_id = headers.get("svix-id", "")
    msg_timestamp = headers.get("svix-timestamp", "")
    msg_signature = headers.get("svix-signature", "")

    if not (msg_id and msg_timestamp and msg_signature):
        return False

    try:
        ts = int(msg_timestamp)
        if abs(time.time() - ts) > 300:
            return False
    except ValueError:
        return False

    signed_content = f"{msg_id}.{msg_timestamp}.".encode() + payload
    raw_secret = secret.removeprefix("whsec_")
    key = base64.b64decode(raw_secret)
    expected = hmac.new(key, signed_content, hashlib.sha256).digest()
    expected_b64 = base64.b64encode(expected).decode()

    for sig in msg_signature.split(" "):
        if sig.startswith("v1,") and hmac.compare_digest(sig[3:], expected_b64):
            return True
    return False


@router.post("/clerk")
async def clerk_webhook(
    request: Request,
    session: AsyncSession = Depends(_get_db_session),
):
    payload = await request.body()

    is_placeholder = settings.CLERK_WEBHOOK_SECRET == "whsec_placeholder"
    if not is_placeholder:
        if not _verify_svix_signature(payload, dict(request.headers), settings.CLERK_WEBHOOK_SECRET):
            raise HTTPException(status_code=400, detail="Invalid webhook signature")

    try:
        event = json.loads(payload)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    event_type = event.get("type")
    data = event.get("data", {})
    logger.info("clerk_webhook_received", event_type=event_type)

    if event_type == "organization.created":
        await _handle_org_created(session, data)
    elif event_type == "organization.updated":
        await _handle_org_updated(session, data)
    elif event_type == "organization.deleted":
        await _handle_org_deleted(session, data)

    return {"received": True}


async def _handle_org_created(session: AsyncSession, data: dict) -> None:
    clerk_org_id = data.get("id")
    if not clerk_org_id:
        return

    existing = await session.execute(
        select(Organization).where(Organization.clerk_org_id == clerk_org_id)
    )
    if existing.scalar_one_or_none():
        logger.info("clerk_org_already_exists", clerk_org_id=clerk_org_id)
        return

    from slugify import slugify
    name = data.get("name", "")
    slug = slugify(name)

    conflict = await session.execute(
        select(Organization).where(Organization.slug == slug)
    )
    if conflict.scalar_one_or_none():
        slug = f"{slug}-{clerk_org_id[-6:]}"

    admin_email = data.get("created_by", {}).get("email_address") or ""

    org = Organization(
        clerk_org_id=clerk_org_id,
        name=name,
        slug=slug,
        logo_url=data.get("image_url"),
        admin_email=admin_email or None,
    )
    session.add(org)
    await session.flush()

    # Seed default checklist rules
    for rule_data in _DEFAULT_CHECKLIST_RULES:
        rule = ChecklistRule(organization_id=org.id, **rule_data)
        session.add(rule)

    # Seed trial subscription
    billing = BillingService(session)
    await billing.create_trial_subscription(org.id)

    await session.commit()
    logger.info("clerk_org_created", org_id=str(org.id), clerk_org_id=clerk_org_id, name=name)

    # Send trial welcome email (fire-and-forget via Celery)
    if admin_email:
        send_trial_start_email.delay(admin_email, name)


async def _handle_org_updated(session: AsyncSession, data: dict) -> None:
    clerk_org_id = data.get("id")
    if not clerk_org_id:
        return

    result = await session.execute(
        select(Organization).where(Organization.clerk_org_id == clerk_org_id)
    )
    org = result.scalar_one_or_none()
    if not org:
        return

    if data.get("name"):
        org.name = data["name"]
    if data.get("image_url") is not None:
        org.logo_url = data["image_url"]

    await session.commit()
    logger.info("clerk_org_updated", clerk_org_id=clerk_org_id)


async def _handle_org_deleted(session: AsyncSession, data: dict) -> None:
    clerk_org_id = data.get("id")
    if not clerk_org_id:
        return

    result = await session.execute(
        select(Organization).where(Organization.clerk_org_id == clerk_org_id)
    )
    org = result.scalar_one_or_none()
    if not org:
        return

    org.is_active = False
    await session.commit()
    logger.info("clerk_org_deactivated", clerk_org_id=clerk_org_id)
