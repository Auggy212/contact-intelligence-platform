"""
Celery Beat periodic tasks — runs on the "email" queue via the Beat scheduler.

Trial lifecycle email milestones (days since subscription created_at):
  DAY3_BIT  = 0  → send_trial_day3_email  (bit 0)
  DAY7_BIT  = 1  → send_trial_day7_email  (bit 1)
  DAY12_BIT = 2  → send_trial_day12_email (bit 2)
  ENDED_BIT = 3  → send_trial_ended_email (bit 3, trial_end has passed)

Each bit is set atomically after the email is dispatched so re-runs are idempotent.
"""

import asyncio
from datetime import datetime, timezone

from app.workers.celery_app import celery_app
from app.core.logging import get_logger

logger = get_logger(__name__)

_DAY3_BIT = 1 << 0   # 1
_DAY7_BIT = 1 << 1   # 2
_DAY12_BIT = 1 << 2  # 4
_ENDED_BIT = 1 << 3  # 8

# Trial is 14 days; check milestones by days elapsed since subscription.created_at
_MILESTONES = [
    (3,  _DAY3_BIT,  "send_trial_day3_email"),
    (7,  _DAY7_BIT,  "send_trial_day7_email"),
    (12, _DAY12_BIT, "send_trial_day12_email"),
]


@celery_app.task(name="app.workers.beat_tasks.send_trial_lifecycle_emails")
def send_trial_lifecycle_emails() -> dict:
    return asyncio.run(_send_trial_lifecycle_emails_async())


async def _send_trial_lifecycle_emails_async() -> dict:
    from sqlalchemy import select
    from app.core.database import get_db_no_rls
    from app.models.billing import Subscription
    from app.models.organization import Organization
    from app.core.constants import SubscriptionStatus
    from app.workers.email_tasks import (
        send_trial_day3_email,
        send_trial_day7_email,
        send_trial_day12_email,
        send_trial_ended_email,
    )

    _task_map = {
        "send_trial_day3_email": send_trial_day3_email,
        "send_trial_day7_email": send_trial_day7_email,
        "send_trial_day12_email": send_trial_day12_email,
    }

    dispatched = 0
    now = datetime.now(timezone.utc)

    async for session in get_db_no_rls():
        # Load all trialing subscriptions joined to their org (for email + name)
        result = await session.execute(
            select(Subscription, Organization)
            .join(Organization, Organization.id == Subscription.organization_id)
            .where(Subscription.status == SubscriptionStatus.TRIALING)
        )
        rows = result.all()

        for sub, org in rows:
            # Days elapsed since trial started (subscription row created_at)
            trial_start = sub.created_at.replace(tzinfo=timezone.utc) if sub.created_at.tzinfo is None else sub.created_at
            elapsed_days = (now - trial_start).days

            # Day-milestone emails
            for target_day, bit, task_name in _MILESTONES:
                if elapsed_days >= target_day and not (sub.trial_emails_sent & bit):
                    admin_email = _get_org_admin_email(org)
                    if admin_email:
                        _task_map[task_name].delay(admin_email, org.name)
                        logger.info(
                            "trial_email_dispatched",
                            task=task_name,
                            org_id=str(org.id),
                            elapsed_days=elapsed_days,
                        )
                    sub.trial_emails_sent = sub.trial_emails_sent | bit
                    dispatched += 1

            # Trial-ended email: fire when trial_end has passed and bit not set
            if (
                sub.trial_end is not None
                and now > sub.trial_end
                and not (sub.trial_emails_sent & _ENDED_BIT)
            ):
                admin_email = _get_org_admin_email(org)
                if admin_email:
                    send_trial_ended_email.delay(admin_email, org.name)
                    logger.info("trial_ended_email_dispatched", org_id=str(org.id))
                sub.trial_emails_sent = sub.trial_emails_sent | _ENDED_BIT
                dispatched += 1

        await session.commit()

    logger.info("trial_lifecycle_emails_complete", dispatched=dispatched)
    return {"dispatched": dispatched}


def _get_org_admin_email(org) -> str | None:
    return org.admin_email or None
