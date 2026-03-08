"""
Celery tasks for FHIR clinical workflows.

1. analyze_patient_vitals — evaluates recent vitals, generates AI recommendations
2. process_approved_recommendation — creates care plan + closes care gaps on approval
3. evaluate_care_plan_outcomes — feedback loop: checks if vitals improved after care plan
"""

import logging
import uuid
from datetime import date, timedelta

from celery import shared_task
from django.db import models
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

    # 5. Ensure patient has vital target policies (auto-create from guidelines)
    _ensure_vital_targets(patient, org, care_plan, log)

    # 6. Create audit trail entry
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


def _ensure_vital_targets(patient, org, care_plan, source_log):
    """Ensure the patient has vital target policies. Auto-create defaults if missing."""
    from apps.clinical.models import VitalTargetPolicy
    from apps.clinical.views import _create_default_vital_targets

    existing_count = VitalTargetPolicy.objects.filter(
        patient=patient, is_active=True,
    ).count()

    if existing_count == 0:
        created = _create_default_vital_targets(patient, org)
        # Link to care plan and mark source
        for target in created:
            target.care_plan = care_plan
            target.source = VitalTargetPolicy.Source.CARE_PLAN
            target.save(update_fields=["care_plan", "source"])
        if created:
            logger.info(
                "Auto-created %d default vital targets for patient %s (from care plan %s)",
                len(created), patient.id, care_plan.id,
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


# ──────────────────────────────────────────────────────────────────────────────
# FEEDBACK LOOP: Evaluate care plan outcomes and feed back into the cycle
# ──────────────────────────────────────────────────────────────────────────────

# Map LOINC codes to their "normal" thresholds for outcome evaluation
OUTCOME_THRESHOLDS = {
    "8867-4":  {"name": "Heart Rate",   "normal_low": 60,  "normal_high": 100,  "unit": "bpm"},
    "8480-6":  {"name": "Systolic BP",  "normal_low": 90,  "normal_high": 130,  "unit": "mmHg"},
    "8462-4":  {"name": "Diastolic BP", "normal_low": 60,  "normal_high": 80,   "unit": "mmHg"},
    "59408-5": {"name": "SpO2",         "normal_low": 95,  "normal_high": 100,  "unit": "%"},
    "8310-5":  {"name": "Temperature",  "normal_low": 36.1,"normal_high": 37.2, "unit": "°C"},
    "2339-0":  {"name": "Glucose",      "normal_low": 70,  "normal_high": 180,  "unit": "mg/dL"},
}

# Map recommendation trigger conditions back to the LOINC code to monitor
CONDITION_TO_LOINC = {
    "high": "8867-4",
    "low": "8867-4",
    "hypertensive_crisis": "8480-6",
    "stage2_htn": "8480-6",
    "hypoxemia": "59408-5",
    "mild_hypoxemia": "59408-5",
    "fever": "8310-5",
    "severe_hyperglycemia": "2339-0",
    "hyperglycemia": "2339-0",
    "hypoglycemia": "2339-0",
}


def _evaluate_care_plan_outcomes_sync():
    """
    Feedback loop: evaluate all active care plans.

    For each active care plan:
    1. Look at the vital sign that triggered the original recommendation
    2. Compare current readings to the period before the care plan
    3. Score the outcome: improved / stable / worsened
    4. Update care plan status + goals accordingly
    5. If worsened → escalate with new recommendation
    6. If improved and sustained → complete the care plan
    7. Track effectiveness on the original recommendation
    """
    from apps.clinical.models import VitalTargetPolicy
    from apps.fhir.models import AgentActionLog, FHIRCarePlan, FHIRObservation

    now = timezone.now()
    active_plans = FHIRCarePlan.objects.filter(
        status=FHIRCarePlan.Status.ACTIVE,
        ai_generated=True,
    ).select_related("patient", "patient__tenant")

    plans_evaluated = 0
    plans_completed = 0
    plans_escalated = 0

    for plan in active_plans:
        # Skip plans created less than 1 hour ago (too early to evaluate)
        if plan.created and (now - plan.created).total_seconds() < 3600:
            continue

        patient = plan.patient
        org = plan.tenant if hasattr(plan, 'tenant') else patient.tenant

        # Find the source recommendation to know what vital triggered it
        source_rec_id = None
        source_condition = None
        for activity in (plan.activities or []):
            if activity.get("created_from_recommendation"):
                source_rec_id = activity["created_from_recommendation"]
                break

        if source_rec_id:
            try:
                source_log = AgentActionLog.objects.get(id=source_rec_id)
                source_condition = (source_log.input_context or {}).get("condition")
            except AgentActionLog.DoesNotExist:
                pass

        # Determine which LOINC code to monitor
        loinc_code = None
        if source_condition:
            loinc_code = CONDITION_TO_LOINC.get(source_condition)

        if not loinc_code:
            # Try to infer from plan category/description
            desc_lower = (plan.description or "").lower()
            if "heart rate" in desc_lower or "tachycardia" in desc_lower or "bradycardia" in desc_lower:
                loinc_code = "8867-4"
            elif "blood pressure" in desc_lower or "hypertens" in desc_lower:
                loinc_code = "8480-6"
            elif "spo2" in desc_lower or "oxygen" in desc_lower or "hypoxemia" in desc_lower:
                loinc_code = "59408-5"
            elif "glucose" in desc_lower or "hyperglycemia" in desc_lower or "hypoglycemia" in desc_lower:
                loinc_code = "2339-0"
            elif "temperature" in desc_lower or "fever" in desc_lower:
                loinc_code = "8310-5"

        if not loinc_code:
            continue

        # Patient-specific targets take priority over global defaults
        patient_targets = VitalTargetPolicy.get_patient_targets(patient)
        if loinc_code in patient_targets:
            thresholds = patient_targets[loinc_code]
        else:
            thresholds = OUTCOME_THRESHOLDS.get(loinc_code)
        if not thresholds:
            continue

        # Get vitals BEFORE care plan (1 hour before creation)
        pre_window_start = plan.created - timedelta(hours=2)
        pre_window_end = plan.created
        pre_readings = list(
            FHIRObservation.objects.filter(
                patient=patient,
                code=loinc_code,
                effective_datetime__gte=pre_window_start,
                effective_datetime__lte=pre_window_end,
                value_quantity__isnull=False,
            ).values_list("value_quantity", flat=True)
        )

        # Get vitals AFTER care plan (last 2 hours)
        post_window_start = now - timedelta(hours=2)
        post_readings = list(
            FHIRObservation.objects.filter(
                patient=patient,
                code=loinc_code,
                effective_datetime__gte=post_window_start,
                value_quantity__isnull=False,
            ).values_list("value_quantity", flat=True)
        )

        if not post_readings:
            continue  # No recent data to evaluate

        plans_evaluated += 1

        # Calculate averages
        pre_avg = sum(pre_readings) / len(pre_readings) if pre_readings else None
        post_avg = sum(post_readings) / len(post_readings)

        normal_low = thresholds["normal_low"]
        normal_high = thresholds["normal_high"]
        normal_mid = (normal_low + normal_high) / 2

        # Determine outcome
        post_in_range = normal_low <= post_avg <= normal_high
        outcome = _classify_outcome(pre_avg, post_avg, normal_low, normal_high)

        # Update care plan goals with progress
        updated_goals = []
        for goal in (plan.goals or []):
            goal = dict(goal)  # copy
            goal["last_evaluated"] = now.isoformat()
            goal["outcome"] = outcome
            goal["pre_avg"] = round(pre_avg, 1) if pre_avg else None
            goal["post_avg"] = round(post_avg, 1)
            goal["in_normal_range"] = post_in_range
            if outcome == "improved" and post_in_range:
                goal["status"] = "achieved"
            elif outcome == "worsened":
                goal["status"] = "at-risk"
            else:
                goal["status"] = "in-progress"
            updated_goals.append(goal)

        # Update activities
        updated_activities = []
        for activity in (plan.activities or []):
            activity = dict(activity)
            if outcome == "improved" and post_in_range:
                activity["status"] = "completed"
            elif outcome == "worsened":
                activity["status"] = "needs-escalation"
            else:
                activity["status"] = "in-progress"
            updated_activities.append(activity)

        # Decide plan status transition
        if outcome == "improved" and post_in_range:
            plan.status = FHIRCarePlan.Status.COMPLETED
            plan.note = (plan.note or "") + f"\n[{now.isoformat()}] COMPLETED: Vitals normalized ({thresholds['name']} avg {post_avg:.1f} in range {normal_low}-{normal_high})."
            plans_completed += 1

            # Log outcome in audit trail
            AgentActionLog.objects.create(
                tenant=org,
                patient=patient,
                agent_type="care_plan",
                action_type=AgentActionLog.ActionType.CARE_PLAN_UPDATED,
                action_details={
                    "description": f"Care plan completed — {thresholds['name']} normalized",
                    "care_plan_id": str(plan.id),
                    "outcome": "improved",
                },
                input_context={
                    "trigger_source": "feedback_loop",
                    "loinc_code": loinc_code,
                    "pre_avg": round(pre_avg, 1) if pre_avg else None,
                    "post_avg": round(post_avg, 1),
                },
                output={
                    "title": f"Care Plan Completed: {plan.title}",
                    "recommendation": f"{thresholds['name']} has returned to normal range. Care plan goals achieved.",
                    "outcome_score": 1.0,
                },
                model_used="feedback-loop-v1",
            )

            # Track effectiveness on the source recommendation
            if source_rec_id:
                _record_recommendation_effectiveness(
                    source_rec_id, outcome="improved", score=1.0,
                    details=f"Vitals normalized: {post_avg:.1f} {thresholds['unit']}",
                )

        elif outcome == "worsened":
            plan.note = (plan.note or "") + f"\n[{now.isoformat()}] ESCALATION: {thresholds['name']} worsened (avg {post_avg:.1f}, was {pre_avg:.1f if pre_avg else 'N/A'})."
            plans_escalated += 1

            # Generate escalation recommendation
            _escalate_care_plan(plan, patient, org, thresholds, pre_avg, post_avg, loinc_code)

            # Track effectiveness
            if source_rec_id:
                _record_recommendation_effectiveness(
                    source_rec_id, outcome="worsened", score=0.0,
                    details=f"Vitals worsened: {post_avg:.1f} {thresholds['unit']}",
                )

        else:
            # Stable or slightly improved but not yet in range
            plan.note = (plan.note or "") + f"\n[{now.isoformat()}] MONITORING: {thresholds['name']} avg {post_avg:.1f} (target: {normal_low}-{normal_high})."

            # Check if plan has been active too long (>7 days without improvement)
            days_active = (now - plan.created).days
            if days_active > 7 and not post_in_range:
                plan.note += " Plan active >7d without reaching target — consider reassessment."
                # Generate a follow-up recommendation
                _generate_followup_recommendation(plan, patient, org, thresholds, post_avg, days_active)

        plan.goals = updated_goals
        plan.activities = updated_activities
        plan.save(update_fields=["status", "goals", "activities", "note"])

        # Update adherence stats on the patient's vital target policy
        policy_id = thresholds.get("policy_id")
        if policy_id:
            VitalTargetPolicy.objects.filter(id=policy_id).update(
                times_evaluated=models.F("times_evaluated") + 1,
                times_in_range=models.F("times_in_range") + (1 if post_in_range else 0),
            )

    logger.info(
        "Feedback loop: evaluated=%d, completed=%d, escalated=%d",
        plans_evaluated, plans_completed, plans_escalated,
    )
    return {
        "plans_evaluated": plans_evaluated,
        "plans_completed": plans_completed,
        "plans_escalated": plans_escalated,
    }


def _classify_outcome(pre_avg, post_avg, normal_low, normal_high):
    """Classify the outcome as improved, worsened, or stable."""
    normal_mid = (normal_low + normal_high) / 2

    if pre_avg is None:
        # No pre-data: just check if post is in range
        if normal_low <= post_avg <= normal_high:
            return "improved"
        return "stable"

    # Distance from normal midpoint
    pre_distance = abs(pre_avg - normal_mid)
    post_distance = abs(post_avg - normal_mid)

    # Improvement threshold: 10% closer to normal
    if post_distance < pre_distance * 0.9:
        return "improved"
    elif post_distance > pre_distance * 1.1:
        return "worsened"
    return "stable"


def _escalate_care_plan(plan, patient, org, thresholds, pre_avg, post_avg, loinc_code):
    """Generate an escalation recommendation when a care plan's vitals worsen."""
    from apps.fhir.models import AgentActionLog

    vital_name = thresholds["name"]
    unit = thresholds["unit"]

    AgentActionLog.objects.create(
        tenant=org,
        patient=patient,
        agent_type="triage",
        action_type=AgentActionLog.ActionType.RECOMMENDATION,
        action_details={
            "description": f"Escalation: {vital_name} worsened despite active care plan",
            "trigger": "feedback_loop_escalation",
            "source_care_plan_id": str(plan.id),
        },
        input_context={
            "trigger_source": "feedback_loop",
            "vital_type": loinc_code,
            "pre_avg": round(pre_avg, 1) if pre_avg else None,
            "post_avg": round(post_avg, 1),
            "care_plan_title": plan.title,
            "days_active": (timezone.now() - plan.created).days,
        },
        output={
            "title": f"Escalation: {vital_name} Worsening Despite Treatment",
            "recommendation": (
                f"Patient's {vital_name} has worsened from {pre_avg:.1f} to {post_avg:.1f} {unit} "
                f"despite an active care plan ('{plan.title}'). Current treatment may be "
                f"insufficient. Consider: (1) medication dose adjustment, (2) adding a second "
                f"agent, (3) specialist referral, (4) in-person evaluation for underlying cause."
            ),
            "evidence_level": "B",
            "confidence": 0.90,
            "source_guideline": "Clinical feedback loop — automated outcome monitoring",
            "category": "escalation",
            "priority": "urgent",
            "feature_importance": [
                {"feature": f"{vital_name} Trend", "value": round(abs(post_avg - (pre_avg or post_avg)), 1), "direction": "negative"},
                {"feature": "Days on Plan", "value": (timezone.now() - plan.created).days, "direction": "negative"},
            ],
        },
        model_used="feedback-loop-v1",
    )
    logger.warning(
        "Escalated care plan %s for patient %s: %s worsened (%s → %s)",
        plan.id, patient.id, vital_name, pre_avg, post_avg,
    )


def _generate_followup_recommendation(plan, patient, org, thresholds, post_avg, days_active):
    """Generate a follow-up recommendation when a care plan stalls."""
    from apps.fhir.models import AgentActionLog

    vital_name = thresholds["name"]
    unit = thresholds["unit"]
    normal_range = f"{thresholds['normal_low']}-{thresholds['normal_high']}"

    # Dedup: don't create follow-up if one exists in last 24h
    recent_followup = AgentActionLog.objects.filter(
        patient=patient,
        action_type=AgentActionLog.ActionType.RECOMMENDATION,
        created_at__gte=timezone.now() - timedelta(hours=24),
        output__category="follow_up",
        input_context__source_care_plan_id=str(plan.id),
    ).exists()
    if recent_followup:
        return

    AgentActionLog.objects.create(
        tenant=org,
        patient=patient,
        agent_type="care_plan",
        action_type=AgentActionLog.ActionType.RECOMMENDATION,
        action_details={
            "description": f"Follow-up: {vital_name} not at target after {days_active} days",
            "trigger": "feedback_loop_stalled",
            "source_care_plan_id": str(plan.id),
        },
        input_context={
            "trigger_source": "feedback_loop",
            "source_care_plan_id": str(plan.id),
            "vital_type": thresholds["name"],
            "post_avg": round(post_avg, 1),
            "days_active": days_active,
        },
        output={
            "title": f"Follow-Up Needed: {vital_name} Not at Target ({days_active}d)",
            "recommendation": (
                f"Patient's {vital_name} remains at {post_avg:.1f} {unit} after "
                f"{days_active} days on current care plan (target: {normal_range} {unit}). "
                f"Recommend reassessment: (1) verify medication adherence, (2) consider "
                f"dose titration, (3) evaluate for contributing factors, (4) discuss "
                f"lifestyle modifications with patient."
            ),
            "evidence_level": "C",
            "confidence": 0.80,
            "source_guideline": "Clinical feedback loop — stalled care plan",
            "category": "follow_up",
            "priority": "soon",
            "feature_importance": [
                {"feature": f"Days Without Improvement", "value": days_active, "direction": "negative"},
                {"feature": f"Current {vital_name}", "value": round(post_avg, 1), "direction": "negative"},
            ],
        },
        model_used="feedback-loop-v1",
    )
    logger.info(
        "Follow-up recommendation for patient %s: %s stalled at %s after %dd",
        patient.id, vital_name, post_avg, days_active,
    )


def _record_recommendation_effectiveness(rec_id, outcome, score, details):
    """Record outcome data on the original recommendation for effectiveness tracking."""
    from apps.fhir.models import AgentActionLog

    try:
        log = AgentActionLog.objects.get(id=rec_id)
        output = dict(log.output or {})
        output["_outcome"] = {
            "result": outcome,
            "score": score,
            "details": details,
            "evaluated_at": timezone.now().isoformat(),
        }
        AgentActionLog.objects.filter(id=rec_id).update(output=output)
    except AgentActionLog.DoesNotExist:
        pass


@shared_task(bind=True, max_retries=1, default_retry_delay=60, queue="clinical")
def evaluate_care_plan_outcomes(self):
    """Celery task: periodic feedback loop evaluation."""
    try:
        return _evaluate_care_plan_outcomes_sync()
    except Exception as exc:
        logger.exception("Feedback loop evaluation failed")
        raise self.retry(exc=exc)
