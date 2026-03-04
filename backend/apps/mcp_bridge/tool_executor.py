"""
MCP tool executor — executes tool calls from AI agents against Django models.
"""

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger("apps.mcp_bridge")


class MCPToolExecutor:
    """
    Executes MCP tool calls received from AI agents.
    Each tool maps to one or more Django ORM operations or service calls.
    """

    def __init__(self, tenant, user):
        self.tenant = tenant
        self.user = user

    def execute(self, tool_name: str, parameters: Dict) -> Dict[str, Any]:
        """Execute a named MCP tool with given parameters."""
        tool_map = {
            "get_patient_vitals": self._get_patient_vitals,
            "get_patient_medications": self._get_patient_medications,
            "get_patient_conditions": self._get_patient_conditions,
            "create_notification": self._create_notification,
            "create_care_gap": self._create_care_gap,
            "search_literature": self._search_literature,
            "check_drug_interactions": self._check_drug_interactions,
            "get_risk_score": self._get_risk_score,
            "get_patient_context": self._get_patient_context,
            "update_care_plan": self._update_care_plan,
        }

        handler = tool_map.get(tool_name)
        if handler is None:
            return {"error": f"Unknown tool: {tool_name}", "status": "error"}

        try:
            result = handler(**parameters)
            return {"status": "success", "result": result, "tool": tool_name}
        except Exception as e:
            logger.error(f"Tool execution failed [{tool_name}]: {e}", exc_info=True)
            return {"status": "error", "error": str(e), "tool": tool_name}

    def _get_patient_vitals(self, patient_id: str, days: int = 7, loinc_code: str = None) -> Dict:
        from apps.fhir.models import FHIRObservation
        from django.utils import timezone
        from datetime import timedelta

        qs = FHIRObservation.objects.filter(
            patient_id=patient_id,
            tenant=self.tenant,
            effective_datetime__gte=timezone.now() - timedelta(days=days),
            status="final",
        ).order_by("-effective_datetime")

        if loinc_code:
            qs = qs.filter(code=loinc_code)

        return {
            "vitals": list(qs.values("code", "display", "value_quantity", "value_unit", "effective_datetime")[:50])
        }

    def _get_patient_medications(self, patient_id: str) -> Dict:
        from apps.fhir.models import FHIRMedicationRequest
        meds = FHIRMedicationRequest.objects.filter(
            patient_id=patient_id,
            tenant=self.tenant,
            status="active",
        ).values("medication_code", "medication_display", "dosage_text", "frequency", "route")
        return {"medications": list(meds)}

    def _get_patient_conditions(self, patient_id: str) -> Dict:
        from apps.fhir.models import FHIRCondition
        conditions = FHIRCondition.objects.filter(
            patient_id=patient_id,
            tenant=self.tenant,
            clinical_status="active",
        ).values("code", "display", "onset_datetime", "severity")
        return {"conditions": list(conditions)}

    def _create_notification(
        self, patient_id: str, type: str, title: str, body: str, metadata: dict = None
    ) -> Dict:
        from apps.notifications.tasks import dispatch_alert
        task = dispatch_alert.delay(
            patient_id=patient_id,
            notification_type=type,
            title=title,
            body=body,
            metadata=metadata or {},
            agent_source="mcp_bridge",
        )
        return {"task_id": task.id, "notification_queued": True}

    def _create_care_gap(
        self, patient_id: str, gap_type: str, due_date: str, priority: str = "medium", recommendation: str = ""
    ) -> Dict:
        from apps.clinical.models import CareGap
        from datetime import date
        gap, created = CareGap.objects.get_or_create(
            patient_id=patient_id,
            gap_type=gap_type,
            status=CareGap.Status.OPEN,
            defaults={
                "tenant": self.tenant,
                "due_date": due_date,
                "priority": priority,
                "ai_recommendation": recommendation,
            },
        )
        return {"care_gap_id": str(gap.id), "created": created}

    def _search_literature(self, query: str, max_results: int = 5) -> Dict:
        try:
            from vector.rag import RAGPipeline
            pipeline = RAGPipeline()
            results = pipeline.retrieve(query, collection="medical_literature", top_k=max_results)
            return {"results": results}
        except Exception as e:
            return {"results": [], "error": str(e)}

    def _check_drug_interactions(self, drug1: str, drug2: str) -> Dict:
        try:
            from graph.queries.drug import check_drug_interactions
            interactions = check_drug_interactions(drug1, drug2)
            return {"interactions": interactions, "drug1": drug1, "drug2": drug2}
        except Exception as e:
            return {"interactions": [], "error": str(e)}

    def _get_risk_score(self, patient_id: str, score_type: str = "7_day_hospitalization") -> Dict:
        from apps.analytics.models import RiskScore
        from django.utils import timezone
        try:
            rs = RiskScore.objects.filter(
                patient_id=patient_id,
                score_type=score_type,
                valid_until__gt=timezone.now(),
            ).order_by("-calculated_at").first()
            if rs:
                return {"score": rs.score, "risk_level": rs.risk_level, "features": rs.features}
            return {"score": None, "risk_level": None, "message": "No valid risk score found"}
        except Exception as e:
            return {"error": str(e)}

    def _get_patient_context(self, patient_id: str) -> Dict:
        from .context_builder import MCPContextBuilder
        builder = MCPContextBuilder(tenant=self.tenant)
        return builder.build_patient_context(patient_id)

    def _update_care_plan(self, patient_id: str, plan_id: str, updates: dict) -> Dict:
        from apps.fhir.models import FHIRCarePlan
        try:
            plan = FHIRCarePlan.objects.get(
                id=plan_id, patient_id=patient_id, tenant=self.tenant
            )
            for key, value in updates.items():
                if hasattr(plan, key):
                    setattr(plan, key, value)
            plan.save()
            return {"updated": True, "plan_id": str(plan.id)}
        except FHIRCarePlan.DoesNotExist:
            return {"updated": False, "error": "Care plan not found"}
