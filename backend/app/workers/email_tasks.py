"""
Email lifecycle tasks — runs in the "email" Celery queue.

Trigger points:
  send_trial_start_email     → Clerk org.created webhook
  send_trial_day3_email      → Celery Beat, 3 days after trial start
  send_trial_day7_email      → Celery Beat, 7 days after trial start
  send_trial_day12_email     → Celery Beat, 12 days after trial start
  send_trial_ended_email     → Celery Beat, when trial_end passes
  send_payment_failed_email  → Stripe invoice.payment_failed
  send_cancellation_email    → Stripe customer.subscription.deleted
  send_invite_email          → User invitation flow
"""

import asyncio

from app.workers.celery_app import celery_app
from app.core.logging import get_logger

logger = get_logger(__name__)


async def _send(to: str, subject: str, html: str) -> None:
    from app.integrations.email_client import get_email_client
    client = get_email_client()
    await client.send(to=to, subject=subject, html=html)
    logger.info("email_sent", to=to, subject=subject)


# ---------------------------------------------------------------------------
# Trial lifecycle
# ---------------------------------------------------------------------------

@celery_app.task(name="app.workers.email_tasks.send_trial_start_email")
def send_trial_start_email(to: str, org_name: str) -> None:
    asyncio.run(_send(
        to=to,
        subject="Welcome to Contract Intelligence — your 14-day trial has started",
        html=f"""
        <p>Hi,</p>
        <p>Welcome to <b>Contract Intelligence</b>! Your 14-day trial for <b>{org_name}</b> is now active.</p>
        <p>During your trial you can:</p>
        <ul>
          <li>Upload up to 3 contracts for AI review</li>
          <li>Compare contracts against your master template</li>
          <li>Detect vendor redline changes with risk scores 1–10</li>
          <li>Validate clauses against Indian law (Contract Act, IT Act, MSME Act, and more)</li>
        </ul>
        <p><a href="https://app.contractintelligence.in">Log in and get started →</a></p>
        """,
    ))


@celery_app.task(name="app.workers.email_tasks.send_trial_day3_email")
def send_trial_day3_email(to: str, org_name: str) -> None:
    asyncio.run(_send(
        to=to,
        subject="Day 3 — Have you tried Template Comparison yet?",
        html=f"""
        <p>Hi,</p>
        <p>Your trial for <b>{org_name}</b> is 3 days in — 11 days remaining.</p>
        <p><b>Feature spotlight: Master Template Comparison</b></p>
        <p>Upload your master contract (File A) and a proposed draft (File B).
           Our AI flags every clause that is missing, weakened, or modified —
           with confidence scores and click-to-source citations.</p>
        <p><a href="https://app.contractintelligence.in">Start reviewing →</a></p>
        """,
    ))


@celery_app.task(name="app.workers.email_tasks.send_trial_day7_email")
def send_trial_day7_email(to: str, org_name: str) -> None:
    asyncio.run(_send(
        to=to,
        subject="Day 7 — Validate contracts against Indian law automatically",
        html=f"""
        <p>Hi,</p>
        <p>You are halfway through your trial for <b>{org_name}</b>.</p>
        <p><b>Feature spotlight: Indian Law Compliance</b></p>
        <p>Our AI cross-references every clause against the Indian Contract Act,
           IT Act, MSME Act, and more — citing the exact section number for any
           clause that may be non-compliant.</p>
        <p><a href="https://app.contractintelligence.in">Try Indian law validation →</a></p>
        """,
    ))


@celery_app.task(name="app.workers.email_tasks.send_trial_day12_email")
def send_trial_day12_email(to: str, org_name: str) -> None:
    asyncio.run(_send(
        to=to,
        subject="48 hours left on your trial — upgrade to keep reviewing contracts",
        html=f"""
        <p>Hi,</p>
        <p>Your trial for <b>{org_name}</b> ends in <b>48 hours</b>.</p>
        <p>Upgrade now to keep your review history, custom checklist rules, and approved clause library.</p>
        <ul>
          <li><b>Starter</b> — 25 contracts/month</li>
          <li><b>Professional</b> — 150 contracts/month, unlimited custom rules</li>
        </ul>
        <p><a href="https://app.contractintelligence.in/billing">Choose a plan →</a></p>
        """,
    ))


@celery_app.task(name="app.workers.email_tasks.send_trial_ended_email")
def send_trial_ended_email(to: str, org_name: str) -> None:
    asyncio.run(_send(
        to=to,
        subject="Your Contract Intelligence trial has ended",
        html=f"""
        <p>Hi,</p>
        <p>Your 14-day trial for <b>{org_name}</b> has ended.</p>
        <p>Your data is safe. Upgrade any time to resume full access.</p>
        <p><a href="https://app.contractintelligence.in/billing">Choose a plan →</a></p>
        <p>Questions? Reply to this email and we will be happy to help.</p>
        """,
    ))


# ---------------------------------------------------------------------------
# Payment and subscription events
# ---------------------------------------------------------------------------

@celery_app.task(name="app.workers.email_tasks.send_payment_failed_email")
def send_payment_failed_email(to: str, org_name: str) -> None:
    asyncio.run(_send(
        to=to,
        subject="Action required — payment failed for your Contract Intelligence subscription",
        html=f"""
        <p>Hi,</p>
        <p>We could not process your payment for <b>{org_name}</b>.</p>
        <p>Please update your billing details within 3 days to avoid service interruption.</p>
        <p><a href="https://app.contractintelligence.in/billing">Update payment method →</a></p>
        """,
    ))


@celery_app.task(name="app.workers.email_tasks.send_cancellation_email")
def send_cancellation_email(org_name: str) -> None:
    """Internal admin notification when a subscription is cancelled."""
    asyncio.run(_send(
        to="admin@contractintelligence.in",
        subject=f"Subscription cancelled — {org_name}",
        html=f"<p>The subscription for <b>{org_name}</b> has been cancelled via Stripe.</p>",
    ))


# ---------------------------------------------------------------------------
# Invitation
# ---------------------------------------------------------------------------

@celery_app.task(name="app.workers.email_tasks.send_invite_email")
def send_invite_email(to: str, org_name: str, invite_url: str) -> None:
    asyncio.run(_send(
        to=to,
        subject=f"You've been invited to join {org_name} on Contract Intelligence",
        html=f"""
        <p>Hi,</p>
        <p>You have been invited to join <b>{org_name}</b> on Contract Intelligence.</p>
        <p><a href="{invite_url}">Accept your invitation →</a></p>
        <p>This link expires in 7 days.</p>
        """,
    ))
