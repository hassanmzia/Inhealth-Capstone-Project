"""Celery tasks for patient data synchronization."""

import logging

from celery import shared_task

logger = logging.getLogger("apps.patients")


@shared_task
def sync_device_data():
    """
    Poll registered active devices and pull new readings.
    Runs every 60 seconds via Celery Beat.
    """
    from django.utils import timezone
    from .models import DeviceRegistration

    active_devices = DeviceRegistration.objects.filter(is_active=True).select_related("patient", "patient__tenant")
    synced = 0
    errors = 0

    for device in active_devices:
        try:
            # In production: call device vendor API (Dexcom, Withings, Apple Health, etc.)
            # Here we update last_sync timestamp as a placeholder
            DeviceRegistration.objects.filter(pk=device.pk).update(last_sync=timezone.now())
            synced += 1
        except Exception as e:
            logger.error(f"Device sync error for {device.device_id}: {e}")
            errors += 1

    logger.info(f"Device sync complete: {synced} synced, {errors} errors")
    return {"synced": synced, "errors": errors}


@shared_task(bind=True, max_retries=2)
def update_patient_engagement_scores(self):
    """Recalculate engagement scores for all active patients."""
    from .models import PatientEngagement

    updated = 0
    for eng in PatientEngagement.objects.select_related("patient").all():
        try:
            eng.update_engagement_score()
            updated += 1
        except Exception as e:
            logger.error(f"Engagement score update failed for {eng.patient_id}: {e}")

    logger.info(f"Updated engagement scores for {updated} patients")
    return {"updated": updated}
