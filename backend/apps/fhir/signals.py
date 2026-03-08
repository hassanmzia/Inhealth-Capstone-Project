"""
Django signals for FHIR resources.

Observation post_save  → trigger vitals analysis → AI recommendations
AgentActionLog post_save → on approval → create care plan, close care gaps
"""

import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

logger = logging.getLogger("apps.fhir.signals")

# LOINC codes for vitals that should trigger analysis
VITALS_LOINC_CODES = {
    "8867-4",   # Heart rate
    "8480-6",   # Systolic BP
    "8462-4",   # Diastolic BP
    "59408-5",  # SpO2
    "8310-5",   # Temperature
    "9279-1",   # Respiratory rate
    "2339-0",   # Glucose
}


@receiver(post_save, sender="fhir.FHIRObservation")
def observation_saved(sender, instance, created, **kwargs):
    """When a new vital-sign observation is saved, queue analysis."""
    if not created:
        return
    if instance.code not in VITALS_LOINC_CODES:
        return

    try:
        from apps.fhir.tasks import analyze_patient_vitals
        # Debounce: use countdown so rapid simulator ticks batch together
        analyze_patient_vitals.apply_async(
            kwargs={
                "patient_id": str(instance.patient_id),
                "tenant_id": str(instance.tenant_id),
            },
            countdown=10,  # wait 10s for simulator burst to finish
        )
    except Exception:
        # Celery may not be running in dev — fall back to synchronous
        logger.debug("Celery not available; running vitals analysis synchronously")
        from apps.fhir.tasks import _analyze_patient_vitals_sync
        try:
            _analyze_patient_vitals_sync(
                patient_id=str(instance.patient_id),
                tenant_id=str(instance.tenant_id),
            )
        except Exception:
            logger.exception("Synchronous vitals analysis failed")


@receiver(post_save, sender="fhir.AgentActionLog")
def recommendation_reviewed(sender, instance, **kwargs):
    """When a recommendation is approved, create care plan and close gaps."""
    if instance.action_type != "recommendation":
        return
    if instance.was_accepted is not True:
        return
    # Only run once — check if care plan already exists for this log
    if instance.output.get("_care_plan_created"):
        return

    try:
        from apps.fhir.tasks import process_approved_recommendation
        process_approved_recommendation.apply_async(
            kwargs={"action_log_id": str(instance.id)},
        )
    except Exception:
        logger.debug("Celery not available; processing approval synchronously")
        from apps.fhir.tasks import _process_approved_recommendation_sync
        try:
            _process_approved_recommendation_sync(action_log_id=str(instance.id))
        except Exception:
            logger.exception("Synchronous approval processing failed")
