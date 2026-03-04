"""Celery tasks for notification delivery."""

import logging

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger("apps.notifications")


@shared_task(bind=True, max_retries=3, default_retry_delay=60, queue="notifications")
def send_notification_via_channel(self, notification_id: str, channel: str):
    """Send a single notification via the specified channel."""
    try:
        from .models import Notification
        from .channels import get_channel_adapter

        notification = Notification.objects.select_related(
            "patient", "patient__demographics"
        ).get(id=notification_id)

        if notification.status in (Notification.Status.ACKNOWLEDGED, Notification.Status.DELIVERED):
            return {"status": "skipped", "reason": "already acknowledged"}

        adapter = get_channel_adapter(channel)

        # Get patient contact info
        recipient = _get_recipient(notification, channel)
        if not recipient:
            logger.warning(f"No {channel} recipient found for notification {notification_id}")
            notification.mark_failed(f"No {channel} contact info for patient")
            return {"status": "failed", "reason": "no recipient"}

        success, ext_id = adapter.send(
            recipient=recipient,
            subject=notification.title,
            body=notification.body,
            metadata=notification.metadata,
        )

        if success:
            notification.mark_sent(ext_id)
            return {"status": "sent", "channel": channel, "external_id": ext_id}
        else:
            notification.mark_failed(ext_id)
            raise self.retry(exc=Exception(f"Send failed: {ext_id}"))

    except Notification.DoesNotExist:
        logger.error(f"Notification {notification_id} not found")
        return {"status": "error", "reason": "not found"}
    except Exception as exc:
        logger.error(f"Notification send error: {exc}")
        raise self.retry(exc=exc)


def _get_recipient(notification, channel: str) -> str | None:
    """Extract recipient address/token for the given channel."""
    patient = notification.patient
    if channel == "sms":
        return patient.phone or None
    elif channel == "email":
        return patient.email or None
    elif channel == "push":
        # FCM token stored in engagement preferences
        try:
            prefs = patient.engagement.notification_preferences
            return prefs.get("fcm_token") or None
        except Exception:
            return None
    elif channel == "ehr":
        return str(patient.fhir_id)
    return None


@shared_task(bind=True, max_retries=1, queue="notifications")
def check_notification_acknowledgement(self, notification_id: str, escalation_level: int):
    """
    Check if a critical notification has been acknowledged.
    If not, escalate to the care team.
    """
    from .models import Notification

    try:
        notification = Notification.objects.get(id=notification_id)
        if notification.status == Notification.Status.ACKNOWLEDGED:
            return {"status": "already_acknowledged"}

        # Escalate — notify the care team
        logger.warning(
            f"Critical notification {notification_id} not acknowledged after escalation level {escalation_level}. Escalating."
        )
        notification.status = Notification.Status.ESCALATED
        notification.escalation_level = escalation_level
        notification.escalated_at = timezone.now()
        notification.save(update_fields=["status", "escalation_level", "escalated_at"])

        # Alert the provider
        from apps.fhir.models import FHIRPatient
        patient = notification.patient
        if patient.primary_care_provider and patient.primary_care_provider.phone:
            from .channels import SMSAdapter
            sms = SMSAdapter()
            sms.send(
                recipient=patient.primary_care_provider.phone,
                subject="Patient Alert Escalation",
                body=f"ESCALATION (Level {escalation_level}): Patient {patient.full_name} — {notification.title}. Patient has not acknowledged the alert.",
            )

        return {"status": "escalated", "level": escalation_level}
    except Notification.DoesNotExist:
        return {"status": "not_found"}


@shared_task(bind=True, queue="notifications")
def dispatch_alert(
    self,
    patient_id: str,
    notification_type: str,
    title: str,
    body: str,
    metadata: dict = None,
    agent_source: str = "",
):
    """Create and dispatch a notification from an AI agent or clinical rule."""
    from apps.fhir.models import FHIRPatient
    from .models import Notification
    from .dispatcher import dispatch_notification

    try:
        patient = FHIRPatient.objects.select_related("tenant").get(id=patient_id)
    except FHIRPatient.DoesNotExist:
        logger.error(f"Patient {patient_id} not found for alert dispatch")
        return

    # Create notification record
    channel = Notification.Channel.SMS if notification_type == "CRITICAL" else Notification.Channel.EMAIL
    notification = Notification.objects.create(
        tenant=patient.tenant,
        patient=patient,
        notification_type=notification_type,
        channel=channel,
        title=title,
        body=body,
        metadata=metadata or {},
        agent_source=agent_source,
    )

    # Dispatch via priority routing
    dispatch_notification(notification)
    return {"notification_id": str(notification.id)}
