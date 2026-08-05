from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

celery_app = Celery(
    "contract_intelligence",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "app.workers.parse_tasks",
        "app.workers.embed_tasks",
        "app.workers.agent_tasks",
        "app.workers.email_tasks",
        "app.workers.beat_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Kolkata",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_routes={
        "app.workers.parse_tasks.*": {"queue": "parsing"},
        "app.workers.embed_tasks.*": {"queue": "parsing"},
        "app.workers.agent_tasks.*": {"queue": "agents"},
        "app.workers.email_tasks.*": {"queue": "email"},
        "app.workers.beat_tasks.*": {"queue": "email"},
    },
    task_default_retry_delay=30,
    task_max_retries=3,
    # ---------------------------------------------------------------------------
    # Celery Beat — periodic task schedule
    # ---------------------------------------------------------------------------
    beat_schedule={
        # Scan all trialing orgs every hour and dispatch milestone emails.
        # Uses a bitmask (trial_emails_sent) to guarantee each email fires exactly once.
        "trial-lifecycle-emails-hourly": {
            "task": "app.workers.beat_tasks.send_trial_lifecycle_emails",
            "schedule": crontab(minute=0),  # top of every hour
        },
    },
    beat_schedule_filename="celerybeat-schedule",
)
