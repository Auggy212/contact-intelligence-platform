import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.deps import get_session, get_tenant_id, require_admin
from app.core.config import settings
from app.core.logging import get_logger
from app.integrations import stripe_client
from app.models.billing import Subscription, UsageRecord
from app.schemas.billing import (
    CreateCheckoutSessionRequest,
    CreateCheckoutSessionResponse,
    CreatePortalSessionResponse,
    SubscriptionOut,
    UsageRecordOut,
)

router = APIRouter(prefix="/billing", tags=["Billing"])
logger = get_logger(__name__)

_DEV_TENANT_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


def _dev_subscription() -> SubscriptionOut:
    """Stub subscription returned in APP_ENV=testing (no Stripe key needed)."""
    now = datetime.now(timezone.utc)
    trial_end = datetime(now.year, now.month + 1 if now.month < 12 else 1,
                         now.day, tzinfo=timezone.utc)
    return SubscriptionOut(
        id=uuid.UUID("00000000-0000-0000-0000-000000000010"),
        organization_id=_DEV_TENANT_ID,
        stripe_customer_id=None,
        stripe_subscription_id=None,
        plan="trial",
        status="trialing",
        current_period_start=now,
        current_period_end=trial_end,
        trial_end=trial_end,
        created_at=now,
        updated_at=now,
    )


@router.get("/subscription", response_model=SubscriptionOut)
async def get_subscription(
    tenant_id: str = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    if settings.is_testing:
        return _dev_subscription()

    result = await session.execute(
        select(Subscription).where(Subscription.organization_id == uuid.UUID(tenant_id))
    )
    sub = result.scalar_one_or_none()
    if not sub:
        from app.core.exceptions import not_found
        raise not_found("Subscription")
    return sub


@router.post("/checkout", response_model=CreateCheckoutSessionResponse, dependencies=[Depends(require_admin)])
async def create_checkout_session(
    data: CreateCheckoutSessionRequest,
    tenant_id: str = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    if settings.is_testing:
        # Redirect to billing page with a demo notice instead of hitting Stripe
        demo_url = (
            f"http://localhost:3000/billing"
            f"?demo=1&plan={data.plan.value}"
        )
        return CreateCheckoutSessionResponse(checkout_url=demo_url)

    result = await session.execute(
        select(Subscription).where(Subscription.organization_id == uuid.UUID(tenant_id))
    )
    sub = result.scalar_one_or_none()

    price_map = {
        "starter": settings.STRIPE_PRICE_STARTER,
        "professional": settings.STRIPE_PRICE_PROFESSIONAL,
    }
    price_id = price_map.get(data.plan.value, settings.STRIPE_PRICE_STARTER)

    url = await stripe_client.create_checkout_session(
        customer_id=sub.stripe_customer_id if sub else "",
        price_id=price_id,
        success_url=data.success_url,
        cancel_url=data.cancel_url,
        tenant_id=tenant_id,
    )
    return CreateCheckoutSessionResponse(checkout_url=url)


@router.post("/portal", response_model=CreatePortalSessionResponse, dependencies=[Depends(require_admin)])
async def create_portal_session(
    request: Request,
    tenant_id: str = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    if settings.is_testing:
        return CreatePortalSessionResponse(portal_url="http://localhost:3000/billing?demo=1&portal=1")

    result = await session.execute(
        select(Subscription).where(Subscription.organization_id == uuid.UUID(tenant_id))
    )
    sub = result.scalar_one_or_none()
    if not sub or not sub.stripe_customer_id:
        from app.core.exceptions import bad_request
        raise bad_request("No Stripe customer found for this organization")

    return_url = str(request.base_url) + "billing"
    url = await stripe_client.create_portal_session(sub.stripe_customer_id, return_url)
    return CreatePortalSessionResponse(portal_url=url)


@router.get("/usage", response_model=list[UsageRecordOut])
async def get_usage(
    tenant_id: str = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    sub_result = await session.execute(
        select(Subscription).where(Subscription.organization_id == uuid.UUID(tenant_id))
    )
    sub = sub_result.scalar_one_or_none()
    if not sub:
        return []
    usage_result = await session.execute(
        select(UsageRecord).where(UsageRecord.subscription_id == sub.id)
        .order_by(UsageRecord.billing_period.desc())
        .limit(12)
    )
    return usage_result.scalars().all()
