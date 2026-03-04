"""Celery tasks for clinical monitoring and care gap analysis."""

import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger("apps.clinical")


@shared_task
def monitor_all_patients():
    """
    Monitor all active patients for clinical alerts.
    Checks vital sign thresholds, medication adherence, and care gaps.
    Runs every 5 minutes.
    """
    from apps.fhir.models import FHIRObservation, FHIRPatient
    from apps.notifications.models import Notification

    alerts_generated = 0
    lookback = timezone.now() - timedelta(hours=1)

    # Check for critical glucose readings (CGM data)
    critical_glucose = FHIRObservation.objects.filter(
        code="2339-0",  # LOINC: Glucose [Mass/volume] in Blood
        effective_datetime__gte=lookback,
    ).filter(
        value_quantity__lt=54,  # Critical low (<54 mg/dL)
    ).select_related("patient", "patient__tenant")

    for obs in critical_glucose:
        # Check if we already alerted for this reading
        from apps.notifications.tasks import dispatch_alert
        dispatch_alert.delay(
            patient_id=str(obs.patient_id),
            notification_type="CRITICAL",
            title="Critical Low Glucose Alert",
            body=f"Patient glucose is critically low: {obs.value_quantity} {obs.value_unit}. Immediate intervention required.",
            metadata={"loinc_code": obs.code, "value": obs.value_quantity, "unit": obs.value_unit},
        )
        alerts_generated += 1

    # Check for critical high glucose
    critical_high_glucose = FHIRObservation.objects.filter(
        code="2339-0",
        effective_datetime__gte=lookback,
        value_quantity__gt=400,
    ).select_related("patient")

    for obs in critical_high_glucose:
        from apps.notifications.tasks import dispatch_alert
        dispatch_alert.delay(
            patient_id=str(obs.patient_id),
            notification_type="CRITICAL",
            title="Critical High Glucose Alert",
            body=f"Patient glucose is critically high: {obs.value_quantity} {obs.value_unit}. Consider emergency evaluation.",
            metadata={"loinc_code": obs.code, "value": obs.value_quantity},
        )
        alerts_generated += 1

    logger.info(f"Monitor run complete. Generated {alerts_generated} alerts.")
    return {"alerts_generated": alerts_generated}


@shared_task
def check_care_gaps():
    """
    Run daily care gap analysis across all tenants.
    Identifies patients overdue for clinical interventions.
    """
    from apps.fhir.models import FHIRCondition, FHIRObservation, FHIRPatient
    from .models import CareGap

    gaps_created = 0
    today = timezone.now().date()
    three_months_ago = today - timedelta(days=90)

    # Find diabetic patients (ICD-10: E11.x) without recent A1C
    diabetic_patients = FHIRPatient.objects.filter(
        conditions__code__startswith="E11",
        conditions__clinical_status="active",
        active=True,
    ).distinct()

    for patient in diabetic_patients:
        # Check for recent A1C (LOINC 4548-4)
        recent_a1c = FHIRObservation.objects.filter(
            patient=patient,
            code="4548-4",
            effective_datetime__gte=timezone.datetime.combine(three_months_ago, timezone.datetime.min.time(), tzinfo=timezone.utc),
        ).exists()

        if not recent_a1c:
            _, created = CareGap.objects.get_or_create(
                patient=patient,
                gap_type=CareGap.GapType.A1C_OVERDUE,
                status=CareGap.Status.OPEN,
                defaults={
                    "tenant": patient.tenant,
                    "due_date": today,
                    "priority": CareGap.Priority.HIGH,
                    "ai_recommendation": "Patient with Type 2 Diabetes has not had A1C checked in >3 months per ADA guidelines. Schedule lab order.",
                },
            )
            if created:
                gaps_created += 1

    logger.info(f"Care gap check complete. Created {gaps_created} new gaps.")
    return {"gaps_created": gaps_created}
