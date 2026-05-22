import stripe

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

stripe.api_key = settings.STRIPE_SECRET_KEY


async def create_customer(email: str, name: str, tenant_id: str) -> str:
    """Creates a Stripe customer and returns the customer ID."""
    customer = stripe.Customer.create(
        email=email,
        name=name,
        metadata={"tenant_id": tenant_id},
    )
    logger.info("stripe_customer_created", customer_id=customer.id, tenant_id=tenant_id)
    return customer.id


async def create_checkout_session(
    customer_id: str,
    price_id: str,
    success_url: str,
    cancel_url: str,
    tenant_id: str,
) -> str:
    """Creates a Stripe Checkout session and returns the URL."""
    session = stripe.checkout.Session.create(
        customer=customer_id,
        payment_method_types=["card"],
        line_items=[{"price": price_id, "quantity": 1}],
        mode="subscription",
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={"tenant_id": tenant_id},
    )
    return session.url


async def create_portal_session(customer_id: str, return_url: str) -> str:
    """Creates a Stripe Billing Portal session URL for subscription management."""
    session = stripe.billing_portal.Session.create(
        customer=customer_id,
        return_url=return_url,
    )
    return session.url


def construct_webhook_event(payload: bytes, sig_header: str) -> stripe.Event:
    """Validates a Stripe webhook signature and returns the event object."""
    return stripe.Webhook.construct_event(
        payload=payload,
        sig_header=sig_header,
        secret=settings.STRIPE_WEBHOOK_SECRET,
    )
