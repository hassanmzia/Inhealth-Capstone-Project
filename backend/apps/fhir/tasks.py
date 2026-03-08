"""
Celery tasks for FHIR clinical workflows.

1. analyze_patient_vitals — evaluates recent vitals, generates AI recommendations
2. process_approved_recommendation — creates care plan + closes care gaps on approval
"""

import logging
import uuid
from datetime import date, timedelta

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger("apps.fhir.tasks")

# ──────────────────────────────────────────────────────────────────────────────
# Vitals thresholds for triggering AI recommendations
# Each rule: LOINC code → condition, threshold, recommendation template
# ──────────────────────────────────────────────────────────────────────────────
VITALS_RULES = [
    {
        "loinc": "8867-4",
        "vital_name": "Heart Rate",
        "agent_type": "triage",
        "rules": [
            {
                "condition": "high",
                "threshold": 120,
                "op": "gt",
                "priority": "urgent",
                "title": "Tachycardia Detected — Heart Rate > 120 bpm",
                "recommendation": (
                    "Patient's heart rate has exceeded 120 bpm. Consider evaluating for "
                    "dehydration, anemia, infection, thyroid dysfunction, or cardiac arrhythmia. "
                    "If persistent, obtain 12-lead ECG and check troponin levels."
                ),
                "evidence_level": "A",
                "confidence": 0.92,
                "source_guideline": "ACC/AHA 2023 Arrhythmia Guidelines",
                "category": "urgent_care",
            },
            {
                "condition": "low",
                "threshold": 50,
                "op": "lt",
                "priority": "urgent",
                "title": "Bradycardia Detected — Heart Rate < 50 bpm",
                "recommendation": (
                    "Patient's heart rate has dropped below 50 bpm. Assess for symptoms "
                    "(dizziness, syncope). Review medications — beta-blockers and calcium "
                    "channel blockers are common causes. May need cardiology consult."
                ),
                "evidence_level": "B",
                "confidence": 0.88,
                "source_guideline": "ACC/AHA 2023 Bradycardia Guidelines",
                "category": "urgent_care",
            },
        ],
    },
    {
        "loinc": "8480-6",
        "vital_name": "Systolic BP",
        "agent_type": "care_plan",
        "rules": [
            {
                "condition": "hypertensive_crisis",
                "threshold": 180,
                "op": "gt",
                "priority": "critical",
                "title": "Hypertensive Crisis — Systolic BP > 180 mmHg",
                "recommendation": (
                    "Patient's systolic blood pressure exceeds 180 mmHg, indicating a "
                    "hypertensive crisis. Assess for end-organ damage (headache, vision "
                    "changes, chest pain). Consider IV antihypertensive if symptomatic. "
                    "Target 25% reduction in first hour per JNC-8."
                ),
                "evidence_level": "A",
                "confidence": 0.95,
                "source_guideline": "ACC/AHA 2023 Hypertension Guidelines",
                "category": "urgent_care",
            },
            {
                "condition": "stage2_htn",
                "threshold": 140,
                "op": "gt",
                "priority": "soon",
                "title": "Elevated Blood Pressure — Systolic > 140 mmHg",
                "recommendation": (
                    "Patient's systolic BP exceeds 140 mmHg across recent readings. Per "
                    "ACC/AHA guidelines, target is <130/80 mmHg. Consider uptitrating "
                    "current antihypertensive or adding a second agent. Schedule follow-up "
                    "in 2-4 weeks."
                ),
                "evidence_level": "A",
                "confidence": 0.89,
                "source_guideline": "ACC/AHA 2023 Hypertension Guidelines",
                "category": "chronic_management",
            },
        ],
    },
    {
        "loinc": "59408-5",
        "vital_name": "SpO2",
        "agent_type": "triage",
        "rules": [
            {
                "condition": "hypoxemia",
                "threshold": 90,
                "op": "lt",
                "priority": "critical",
                "title": "Hypoxemia Alert — SpO2 < 90%",
                "recommendation": (
                    "Patient's oxygen saturation has dropped below 90%. This requires "
                    "immediate evaluation. Start supplemental oxygen. Assess for pneumonia, "
                    "PE, COPD exacerbation, or heart failure decompensation. Obtain ABG and "
                    "chest X-ray."
                ),
                "evidence_level": "A",
                "confidence": 0.96,
                "source_guideline": "ATS/ERS 2024 Guidelines",
                "category": "urgent_care",
            },
            {
                "condition": "mild_hypoxemia",
                "threshold": 93,
                "op": "lt",
                "priority": "urgent",
                "title": "Low Oxygen Saturation — SpO2 < 93%",
                "recommendation": (
                    "Patient's SpO2 is below 93%. Monitor closely. For COPD patients, "
                    "target SpO2 88-92% per GOLD guidelines. For other patients, investigate "
                    "respiratory cause and consider pulmonology referral."
                ),
                "evidence_level": "B",
                "confidence": 0.87,
                "source_guideline": "GOLD 2024 / ATS Guidelines",
                "category": "urgent_care",
            },
        ],
    },
    {
        "loinc": "8310-5",
        "vital_name": "Temperature",
        "agent_type": "triage",
        "rules": [
            {
                "condition": "fever",
                "threshold": 38.5,
                "op": "gt",
                "priority": "urgent",
                "title": "Fever Detected — Temperature > 38.5°C",
                "recommendation": (
                    "Patient has a temperature above 38.5°C indicating fever. Evaluate for "
                    "infection source. Order CBC, blood cultures, urinalysis, and chest X-ray "
                    "as clinically indicated. Start empiric antibiotics if sepsis is suspected."
                ),
                "evidence_level": "B",
                "confidence": 0.85,
                "source_guideline": "Surviving Sepsis Campaign 2024",
                "category": "urgent_care",
            },
        ],
    },
    {
        "loinc": "2339-0",
        "vital_name": "Glucose",
        "agent_type": "medication",
        "rules": [
            {
                "condition": "severe_hyperglycemia",
                "threshold": 300,
                "op": "gt",
                "priority": "critical",
                "title": "Severe Hyperglycemia — Glucose > 300 mg/dL",
                "recommendation": (
                    "Patient's blood glucose exceeds 300 mg/dL. Check for DKA/HHS: order BMP, "
                    "ABG, ketones, and urinalysis. Consider insulin correction per sliding scale. "
                    "Ensure adequate IV hydration."
                ),
                "evidence_level": "A",
                "confidence": 0.94,
                "source_guideline": "ADA Standards of Care 2024, Section 16",
                "category": "urgent_care",
            },
            {
                "condition": "hyperglycemia",
                "threshold": 200,
                "op": "gt",
                "priority": "soon",
                "title": "Hyperglycemia — Glucose > 200 mg/dL",
                "recommendation": (
                    "Patient's glucose is above 200 mg/dL. Review current diabetes medications "
                    "and adherence. Consider A1c testing if not done recently. May need "
                    "medication adjustment per ADA step-therapy guidelines."
                ),
                "evidence_level": "A",
                "confidence": 0.88,
                "source_guideline": "ADA Standards of Care 2024",
                "category": "chronic_management",
            },
            {
                "condition": "hypoglycemia",
                "threshold": 70,
                "op": "lt",
                "priority": "urgent",
                "title": "Hypoglycemia — Glucose < 70 mg/dL",
                "recommendation": (
                    "Patient's glucose has dropped below 70 mg/dL. Apply the Rule of 15: "
                    "15g fast-acting carbs, recheck in 15 min. Review insulin/sulfonylurea "
                    "dosing. If recurrent, reduce basal insulin by 10-20%."
                ),
                "evidence_level": "A",
                "confidence": 0.93,
                "source_guideline": "ADA Standards of Care 2024, Section 6",
                "category": "medication_safety",
            },
        ],
    },
]

# Map recommendation categories to care gap types
CATEGORY_TO_GAP_TYPE = {
    "chronic_management": "BP_check_overdue",
    "screening": "A1C_overdue",
    "medication_safety": "medication_adherence",
    "patient_education": "follow_up_missed",
}


def _analyze_patient_vitals_sync(patient_id: str, tenant_id: str):
    """
    Analyze the patient's recent vitals and create AI recommendations
    if any thresholds are exceeded.
    """
    from apps.fhir.models import AgentActionLog, FHIRObservation, FHIRPatient
    from apps.tenants.models import Organization

    try:
        patient = FHIRPatient.objects.get(id=patient_id)
    except FHIRPatient.DoesNotExist:
        logger.warning("Patient %s not found for vitals analysis", patient_id)
        return

    try:
        org = Organization.objects.get(id=tenant_id)
    except Organization.DoesNotExist:
        logger.warning("Tenant %s not found", tenant_id)
        return

    # Get the most recent observations per vital type (last 30 minutes)
    lookback = timezone.now() - timedelta(minutes=30)
    recent_obs = FHIRObservation.objects.filter(
        patient_id=patient_id,
        effective_datetime__gte=lookback,
        status="final",
    ).order_by("-effective_datetime")

    # Group by LOINC code → latest value
    latest_by_code = {}
    for obs in recent_obs:
        if obs.code not in latest_by_code and obs.value_quantity is not None:
            latest_by_code[obs.code] = obs

    recommendations_created = 0

    for rule_group in VITALS_RULES:
        loinc = rule_group["loinc"]
        obs = latest_by_code.get(loinc)
        if not obs:
            continue

        value = obs.value_quantity

        for rule in rule_group["rules"]:
            triggered = False
            if rule["op"] == "gt" and value > rule["threshold"]:
                triggered = True
            elif rule["op"] == "lt" and value < rule["threshold"]:
                triggered = True

            if not triggered:
                continue

            # Dedup: don't create same recommendation within 2 hours
            recent_same = AgentActionLog.objects.filter(
                tenant=org,
                patient=patient,
                agent_type=rule_group["agent_type"],
                action_type=AgentActionLog.ActionType.RECOMMENDATION,
                created_at__gte=timezone.now() - timedelta(hours=2),
                output__title=rule["title"],
            ).exists()

            if recent_same:
                continue

            # Create the recommendation
            feature_importance = [
                {
                    "feature": rule_group["vital_name"],
                    "value": round(abs(value - rule["threshold"]) / rule["threshold"], 2),
                    "direction": "negative",
                },
                {
                    "feature": f"Threshold ({rule['op'].upper()} {rule['threshold']})",
                    "value": round(value, 1),
                    "direction": "negative" if rule["op"] == "gt" else "positive",
                },
            ]

            AgentActionLog.objects.create(
                tenant=org,
                patient=patient,
                agent_type=rule_group["agent_type"],
                action_type=AgentActionLog.ActionType.RECOMMENDATION,
                action_details={
                    "description": f"Vitals analysis: {rule_group['vital_name']} = {value} {obs.value_unit}",
                    "trigger": "vital_sign_threshold",
                    "observation_id": str(obs.id),
                },
                input_context={
                    "trigger_source": "vitals_monitor",
                    "vital_type": loinc,
                    "vital_value": value,
                    "vital_unit": obs.value_unit,
                    "threshold": rule["threshold"],
                    "condition": rule["condition"],
                },
                output={
                    "title": rule["title"],
                    "recommendation": rule["recommendation"],
                    "evidence_level": rule["evidence_level"],
                    "confidence": rule["confidence"],
                    "source_guideline": rule["source_guideline"],
                    "category": rule["category"],
                    "priority": rule["priority"],
                    "feature_importance": feature_importance,
                },
                model_used="rules-engine-v1",
            )
            recommendations_created += 1
            logger.info(
                "Created recommendation for patient %s: %s (value=%s)",
                patient_id, rule["title"], value,
            )

    if recommendations_created:
        logger.info(
            "Vitals analysis for patient %s: created %d recommendation(s)",
            patient_id, recommendations_created,
        )


@shared_task(bind=True, max_retries=2, default_retry_delay=30, queue="clinical")
def analyze_patient_vitals(self, patient_id: str, tenant_id: str):
    """Celery wrapper for vitals analysis."""
    try:
        _analyze_patient_vitals_sync(patient_id, tenant_id)
    except Exception as exc:
        logger.exception("Vitals analysis task failed for patient %s", patient_id)
        raise self.retry(exc=exc)


def _process_approved_recommendation_sync(action_log_id: str):
    """
    When a recommendation is approved:
    1. Create a FHIRCarePlan linked to the patient
    2. Close related care gaps
    3. Dispatch notification to patient
    4. Mark the recommendation as processed
    """
    from apps.fhir.models import AgentActionLog, FHIRCarePlan

    try:
        log = AgentActionLog.objects.select_related("patient", "patient__tenant").get(id=action_log_id)
    except AgentActionLog.DoesNotExist:
        logger.warning("AgentActionLog %s not found", action_log_id)
        return

    if not log.was_accepted:
        return

    patient = log.patient
    if not patient:
        logger.warning("No patient linked to recommendation %s", action_log_id)
        return

    org = log.tenant
    output = log.output or {}
    title = output.get("title", "AI Recommendation")
    recommendation = output.get("recommendation", "")
    category = output.get("category", "assess-plan")
    priority = output.get("priority", "routine")

    # 1. Create Care Plan
    care_plan = FHIRCarePlan.objects.create(
        tenant=org,
        fhir_id=str(uuid.uuid4()),
        patient=patient,
        status=FHIRCarePlan.Status.ACTIVE,
        intent=FHIRCarePlan.Intent.PLAN,
        title=f"Care Plan: {title}",
        description=recommendation,
        category=category,
        goals=[{
            "description": title,
            "priority": priority,
            "status": "in-progress",
            "start_date": date.today().isoformat(),
        }],
        activities=[{
            "detail": recommendation,
            "status": "scheduled",
            "source": output.get("source_guideline", ""),
            "evidence_level": output.get("evidence_level", "C"),
            "created_from_recommendation": str(log.id),
        }],
        period_start=date.today(),
        period_end=date.today() + timedelta(days=90),
        ai_generated=True,
        ai_model_used=log.model_used or "rules-engine-v1",
        author_id=log.reviewed_by_id,
        note=f"Auto-created from approved AI recommendation ({log.agent_type})",
    )

    logger.info(
        "Created care plan %s for patient %s from recommendation %s",
        care_plan.fhir_id, patient.id, action_log_id,
    )

    # 2. Close related care gaps
    _close_related_care_gaps(patient, category, org)

    # 3. Dispatch notification to patient
    _notify_patient_care_plan(patient, title, recommendation, priority, org)

    # 4. Mark recommendation as processed (prevent re-processing)
    output["_care_plan_created"] = True
    output["care_plan_id"] = str(care_plan.id)
    output["care_plan_fhir_id"] = care_plan.fhir_id
    AgentActionLog.objects.filter(id=log.id).update(output=output)

    # 5. Create audit trail entry
    AgentActionLog.objects.create(
        tenant=org,
        patient=patient,
        agent_type=log.agent_type,
        action_type=AgentActionLog.ActionType.CARE_PLAN_UPDATED,
        action_details={
            "description": f"Care plan created from approved recommendation",
            "care_plan_id": str(care_plan.id),
            "source_recommendation_id": str(log.id),
            "approved_by": str(log.reviewed_by_id) if log.reviewed_by_id else None,
        },
        input_context={"trigger_source": "recommendation_approval"},
        output={"care_plan_fhir_id": care_plan.fhir_id, "title": care_plan.title},
        model_used=log.model_used or "",
    )


def _close_related_care_gaps(patient, category, org):
    """Close care gaps that match the recommendation category."""
    from apps.clinical.models import CareGap

    gap_type = CATEGORY_TO_GAP_TYPE.get(category)
    if not gap_type:
        return

    open_gaps = CareGap.objects.filter(
        patient=patient,
        tenant=org,
        status=CareGap.Status.OPEN,
        gap_type=gap_type,
    )
    closed = open_gaps.update(status=CareGap.Status.CLOSED, closed_at=timezone.now())
    if closed:
        logger.info("Closed %d care gap(s) for patient %s (type=%s)", closed, patient.id, gap_type)


def _notify_patient_care_plan(patient, title, recommendation, priority, org):
    """Send notification to patient about the new care plan."""
    from apps.notifications.models import Notification

    priority_map = {
        "critical": Notification.NotificationType.CRITICAL,
        "urgent": Notification.NotificationType.URGENT,
        "soon": Notification.NotificationType.SOON,
        "routine": Notification.NotificationType.ROUTINE,
    }
    notification_type = priority_map.get(priority, Notification.NotificationType.ROUTINE)

    notification = Notification.objects.create(
        tenant=org,
        patient=patient,
        notification_type=notification_type,
        channel=Notification.Channel.EHR,
        title=f"New Care Plan: {title}",
        body=(
            f"Your care team has approved a new care plan based on AI analysis:\n\n"
            f"{recommendation}\n\n"
            f"Please discuss this plan with your provider at your next visit."
        ),
        metadata={
            "source": "ai_recommendation_approval",
            "recommendation_title": title,
        },
        agent_source="recommendation_approval_handler",
    )

    # Dispatch via priority routing
    try:
        from apps.notifications.dispatcher import dispatch_notification
        dispatch_notification(notification)
    except Exception:
        logger.debug("Notification dispatch failed (channels may not be configured)")


@shared_task(bind=True, max_retries=2, default_retry_delay=30, queue="clinical")
def process_approved_recommendation(self, action_log_id: str):
    """Celery wrapper for recommendation approval processing."""
    try:
        _process_approved_recommendation_sync(action_log_id)
    except Exception as exc:
        logger.exception("Recommendation processing failed for %s", action_log_id)
        raise self.retry(exc=exc)
