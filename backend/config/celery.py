"""
Celery application configuration for InHealth Chronic Care.
Handles async task processing for clinical alerts, analytics, and AI workflows.
"""

import os

from celery import Celery
from celery.signals import setup_logging
from celery.utils.log import get_task_logger
from kombu import Exchange, Queue

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")

app = Celery("inhealth")

# Load configuration from Django settings
app.config_from_object("django.conf:settings", namespace="CELERY")

# Auto-discover tasks from all installed apps
app.autodiscover_tasks()

# ---------------------------------------------------------------------------
# Task Queues
# ---------------------------------------------------------------------------
default_exchange = Exchange("default", type="direct")
notifications_exchange = Exchange("notifications", type="direct")
analytics_exchange = Exchange("analytics", type="direct")
clinical_exchange = Exchange("clinical", type="direct")
research_exchange = Exchange("research", type="direct")

app.conf.task_queues = (
    Queue("default", default_exchange, routing_key="default", queue_arguments={"x-max-priority": 5}),
    Queue("notifications", notifications_exchange, routing_key="notifications", queue_arguments={"x-max-priority": 10}),
    Queue("analytics", analytics_exchange, routing_key="analytics", queue_arguments={"x-max-priority": 3}),
    Queue("clinical", clinical_exchange, routing_key="clinical", queue_arguments={"x-max-priority": 8}),
    Queue("research", research_exchange, routing_key="research", queue_arguments={"x-max-priority": 3}),
)

app.conf.task_default_queue = "default"
app.conf.task_default_exchange = "default"
app.conf.task_default_routing_key = "default"

# ---------------------------------------------------------------------------
# Task routing by module pattern
# ---------------------------------------------------------------------------
app.conf.task_routes = {
    # High-priority: clinical alerts and notifications
    "apps.notifications.tasks.*": {"queue": "notifications", "priority": 9},
    "apps.clinical.tasks.monitor_*": {"queue": "clinical", "priority": 8},
    "apps.clinical.tasks.check_*": {"queue": "clinical", "priority": 6},
    # Medium-priority: patient data
    "apps.patients.tasks.*": {"queue": "clinical", "priority": 5},
    "apps.fhir.tasks.*": {"queue": "clinical", "priority": 5},
    # Lower-priority: analytics and research
    "apps.analytics.tasks.*": {"queue": "analytics", "priority": 3},
    "apps.research.tasks.*": {"queue": "research", "priority": 2},
    # Admin tasks
    "apps.accounts.tasks.*": {"queue": "default", "priority": 1},
    "apps.billing.tasks.*": {"queue": "default", "priority": 4},
}

# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------
app.conf.task_serializer = "json"
app.conf.result_serializer = "json"
app.conf.accept_content = ["json"]

# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------
app.conf.task_acks_late = True  # Acknowledge after completion (safer for clinical tasks)
app.conf.task_reject_on_worker_lost = True
app.conf.worker_prefetch_multiplier = 1  # Prevent one worker hoarding clinical tasks
app.conf.task_track_started = True

# ---------------------------------------------------------------------------
# Result backend
# ---------------------------------------------------------------------------
app.conf.result_expires = 3600  # 1 hour
app.conf.result_persistent = True

# ---------------------------------------------------------------------------
# Retry defaults
# ---------------------------------------------------------------------------
app.conf.task_max_retries = 3
app.conf.task_default_retry_delay = 60  # 1 minute

# ---------------------------------------------------------------------------
# Beat schedule (also in settings, duplicated here for clarity)
# ---------------------------------------------------------------------------
from celery.schedules import crontab  # noqa: E402

app.conf.beat_schedule = {
    "monitor-all-patients": {
        "task": "apps.clinical.tasks.monitor_all_patients",
        "schedule": 300.0,
        "options": {"queue": "clinical", "priority": 8},
    },
    "sync-device-data": {
        "task": "apps.patients.tasks.sync_device_data",
        "schedule": 60.0,
        "options": {"queue": "clinical", "priority": 7},
    },
    "generate-population-analytics": {
        "task": "apps.analytics.tasks.generate_population_analytics",
        "schedule": 3600.0,
        "options": {"queue": "analytics", "priority": 3},
    },
    "check-care-gaps": {
        "task": "apps.clinical.tasks.check_care_gaps",
        "schedule": crontab(hour=0, minute=0),
        "options": {"queue": "clinical", "priority": 5},
    },
    "sync-clinical-guidelines": {
        "task": "apps.research.tasks.sync_clinical_guidelines",
        "schedule": crontab(day_of_week=0, hour=2, minute=0),
        "options": {"queue": "research", "priority": 2},
    },
    "cleanup-expired-sessions": {
        "task": "apps.accounts.tasks.cleanup_expired_tokens",
        "schedule": crontab(hour=3, minute=0),
        "options": {"queue": "default", "priority": 1},
    },
    "evaluate-care-plan-outcomes": {
        "task": "apps.fhir.tasks.evaluate_care_plan_outcomes",
        "schedule": 600.0,  # every 10 minutes
        "options": {"queue": "clinical", "priority": 6},
    },
}

# ---------------------------------------------------------------------------
# Logging setup via signal (prevent Celery from hijacking Django logging)
# ---------------------------------------------------------------------------
@setup_logging.connect
def config_loggers(*args, **kwargs):
    from logging.config import dictConfig
    from django.conf import settings
    dictConfig(settings.LOGGING)


@app.task(bind=True)
def debug_task(self):
    """Debug task for verifying Celery is operational."""
    logger = get_task_logger(__name__)
    logger.info(f"Request: {self.request!r}")
    return {"status": "ok", "task_id": self.request.id}
