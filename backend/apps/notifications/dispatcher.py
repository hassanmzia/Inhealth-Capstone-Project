"""
Notification priority routing engine.
CRITICAL → SMS + Push + EHR simultaneously (with escalation)
URGENT → SMS + Email
SOON → Email
ROUTINE → Email (batched)
"""

import logging
from typing import List

from .models import Notification

logger = logging.getLogger("apps.notifications")


PRIORITY_ROUTING = {
    Notification.NotificationType.CRITICAL: ["sms", "push", "ehr"],
    Notification.NotificationType.URGENT: ["sms", "email"],
    Notification.NotificationType.SOON: ["email"],
    Notification.NotificationType.ROUTINE: ["email"],
    Notification.NotificationType.EDUCATIONAL: ["email"],
    Notification.NotificationType.APPOINTMENT: ["sms", "email"],
}

ESCALATION_DELAYS_MINUTES = {
    Notification.NotificationType.CRITICAL: [5, 15, 30],     # Escalate at 5, 15, 30 min
    Notification.NotificationType.URGENT: [30, 120],          # Escalate at 30min, 2h
    Notification.NotificationType.SOON: [],                    # No escalation
    Notification.NotificationType.ROUTINE: [],
}


def get_channels_for_priority(notification_type: str) -> List[str]:
    """Return the list of channels to use for a given notification type."""
    return PRIORITY_ROUTING.get(notification_type, ["email"])


def dispatch_notification(notification: Notification, tenant_config=None) -> List[str]:
    """
    Dispatch a notification across all required channels based on priority.
    Returns list of Celery task IDs.

    Respects:
    - Patient notification preferences
    - Tenant channel configuration
    - Health literacy level (simplified body for lower literacy)
    """
    from .tasks import send_notification_via_channel

    channels = get_channels_for_priority(notification.notification_type)

    # Filter by patient preferences
    try:
        prefs = notification.patient.engagement.notification_preferences
        if prefs:
            channels = [c for c in channels if prefs.get(c, True)]
    except Exception:
        pass  # No engagement profile, use defaults

    # Filter by tenant config
    if tenant_config:
        allowed = tenant_config.get("notification_channels", {})
        channels = [c for c in channels if allowed.get(c, True)]

    task_ids = []
    for channel in channels:
        task = send_notification_via_channel.apply_async(
            kwargs={"notification_id": str(notification.id), "channel": channel},
            priority=_get_celery_priority(notification.notification_type),
        )
        task_ids.append(task.id)
        logger.info(
            f"Dispatched {notification.notification_type} notification {notification.id} "
            f"via {channel} (task: {task.id})"
        )

    # Schedule escalation if applicable
    delays = ESCALATION_DELAYS_MINUTES.get(notification.notification_type, [])
    for delay_minutes in delays:
        from .tasks import check_notification_acknowledgement
        check_notification_acknowledgement.apply_async(
            kwargs={"notification_id": str(notification.id), "escalation_level": delays.index(delay_minutes) + 1},
            countdown=delay_minutes * 60,
        )

    return task_ids


def _get_celery_priority(notification_type: str) -> int:
    priority_map = {
        Notification.NotificationType.CRITICAL: 9,
        Notification.NotificationType.URGENT: 7,
        Notification.NotificationType.SOON: 5,
        Notification.NotificationType.ROUTINE: 3,
        Notification.NotificationType.EDUCATIONAL: 2,
        Notification.NotificationType.APPOINTMENT: 4,
    }
    return priority_map.get(notification_type, 3)
