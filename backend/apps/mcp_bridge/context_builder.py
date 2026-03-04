"""
MCP (Model Context Protocol) context builder.
Assembles structured context from Django models for LLM agents.
"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("apps.mcp_bridge")


class MCPContextBuilder:
    """
    Builds MCP-formatted context objects from Django model data.
    Used by AI agents to get structured patient and clinical context.
    """

    def __init__(self, tenant=None):
        self.tenant = tenant

    def build_patient_context(self, patient_id: str) -> Dict[str, Any]:
        """Build comprehensive patient context for AI agents."""
        from apps.fhir.models import (
            FHIRAllergyIntolerance,
            FHIRCarePlan,
            FHIRCondition,
            FHIRMedicationRequest,
            FHIRObservation,
            FHIRPatient,
        )
        from apps.analytics.models import RiskScore
        from apps.clinical.models import CareGap
        from django.utils import timezone

        try:
            patient = FHIRPatient.objects.select_related("tenant").get(
                id=patient_id,
                tenant=self.tenant,
            )
        except FHIRPatient.DoesNotExist:
            return {"error": f"Patient {patient_id} not found"}

        # Active conditions
        conditions = list(
            FHIRCondition.objects.filter(
                patient=patient, clinical_status="active"
            ).values("code", "display", "onset_datetime")[:20]
        )

        # Active medications
        medications = list(
            FHIRMedicationRequest.objects.filter(
                patient=patient, status="active"
            ).values("medication_code", "medication_display", "dosage_text", "frequency")[:20]
        )

        # Recent vitals (last 7 days)
        recent_vitals = list(
            FHIRObservation.objects.filter(
                patient=patient,
                effective_datetime__gte=timezone.now() - __import__("datetime").timedelta(days=7),
                status="final",
            ).order_by("-effective_datetime").values(
                "code", "display", "value_quantity", "value_unit", "effective_datetime"
            )[:30]
        )

        # Allergies
        allergies = list(
            FHIRAllergyIntolerance.objects.filter(
                patient=patient, clinical_status="active"
            ).values("code", "display", "criticality", "category")
        )

        # Risk scores
        risk_scores = {}
        for rs in RiskScore.objects.filter(
            patient=patient, valid_until__gt=timezone.now()
        ).order_by("-calculated_at"):
            if rs.score_type not in risk_scores:
                risk_scores[rs.score_type] = {
                    "score": rs.score,
                    "risk_level": rs.risk_level,
                    "key_features": dict(list(rs.features.items())[:3]) if rs.features else {},
                }

        # Open care gaps
        care_gaps = list(
            CareGap.objects.filter(
                patient=patient, status=CareGap.Status.OPEN
            ).values("gap_type", "priority", "due_date", "ai_recommendation")
        )

        # Active care plans
        care_plans = list(
            FHIRCarePlan.objects.filter(
                patient=patient, status="active"
            ).values("title", "description", "goals", "activities")[:3]
        )

        return {
            "mcp_version": "1.0",
            "resource_type": "PatientContext",
            "patient": {
                "id": str(patient.id),
                "fhir_id": patient.fhir_id,
                "name": patient.full_name,
                "mrn": patient.mrn,
                "birth_date": str(patient.birth_date),
                "gender": patient.gender,
                "age": patient.age,
            },
            "clinical_summary": {
                "active_conditions": conditions,
                "active_medications": medications,
                "allergies": allergies,
                "recent_vitals": [
                    {**v, "effective_datetime": v["effective_datetime"].isoformat() if v.get("effective_datetime") else None}
                    for v in recent_vitals
                ],
            },
            "risk_profile": risk_scores,
            "care_gaps": care_gaps,
            "care_plans": care_plans,
        }

    def build_population_context(self, cohort_id: str) -> Dict[str, Any]:
        """Build population-level context for analytics agents."""
        from apps.analytics.models import PopulationCohort, ClinicalKPI
        from django.utils import timezone

        try:
            cohort = PopulationCohort.objects.get(id=cohort_id, tenant=self.tenant)
        except PopulationCohort.DoesNotExist:
            return {"error": f"Cohort {cohort_id} not found"}

        # Latest KPIs
        latest_kpis = {}
        for kpi in ClinicalKPI.objects.filter(tenant=self.tenant).order_by("metric_name", "-metric_date").distinct("metric_name"):
            latest_kpis[kpi.metric_name] = {"value": kpi.metric_value, "unit": kpi.unit, "date": str(kpi.metric_date)}

        return {
            "mcp_version": "1.0",
            "resource_type": "PopulationContext",
            "cohort": {
                "id": str(cohort.id),
                "name": cohort.name,
                "patient_count": cohort.patient_count,
                "filters": cohort.condition_filter,
            },
            "kpis": latest_kpis,
        }

    def build_tool_list(self) -> List[Dict]:
        """Return available MCP tools for agent use."""
        return [
            {
                "name": "get_patient_vitals",
                "description": "Retrieve recent vital signs for a patient",
                "parameters": {"patient_id": "string", "days": "integer", "loinc_code": "string (optional)"},
            },
            {
                "name": "get_patient_medications",
                "description": "List active medications for a patient",
                "parameters": {"patient_id": "string"},
            },
            {
                "name": "get_patient_conditions",
                "description": "List active diagnoses for a patient",
                "parameters": {"patient_id": "string"},
            },
            {
                "name": "create_notification",
                "description": "Send a clinical notification to patient or provider",
                "parameters": {"patient_id": "string", "type": "CRITICAL|URGENT|SOON|ROUTINE", "title": "string", "body": "string"},
            },
            {
                "name": "create_care_gap",
                "description": "Create a care gap for a patient",
                "parameters": {"patient_id": "string", "gap_type": "string", "due_date": "date", "priority": "string"},
            },
            {
                "name": "search_literature",
                "description": "Search medical literature for evidence",
                "parameters": {"query": "string", "max_results": "integer"},
            },
            {
                "name": "check_drug_interactions",
                "description": "Check for drug-drug interactions using the knowledge graph",
                "parameters": {"drug1": "string", "drug2": "string"},
            },
            {
                "name": "get_risk_score",
                "description": "Get current risk score for a patient",
                "parameters": {"patient_id": "string", "score_type": "string"},
            },
        ]
