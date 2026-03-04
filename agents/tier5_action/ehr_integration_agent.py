"""
Agent 23 — EHR Integration Agent

Responsibilities:
  - Write FHIR resources back to FHIR server
  - Generate clinical summary note (SOAP format) via LLM
  - Update CarePlan with AI recommendations
  - Create DiagnosticReport for agent analysis results
  - Export FHIR Bundle for external EHR integration
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx

from base.agent import MCPAgent
from base.tools import query_fhir_database, vector_search

logger = logging.getLogger("inhealth.agent.ehr_integration")


class EHRIntegrationAgent(MCPAgent):
    """Agent 23: FHIR write-back and clinical documentation generation."""

    agent_id = 23
    agent_name = "ehr_integration_agent"
    agent_tier = "tier5_action"
    system_prompt = (
        "You are the EHR Integration AI Agent for InHealth Chronic Care. "
        "You generate clinical documentation in SOAP note format, create FHIR resources, "
        "and maintain care plan continuity. Write precise, clinically accurate documentation "
        "following JCAHO, CMS, and HL7 FHIR R4 standards. "
        "Use clinical terminology appropriate for medical records."
    )

    def _default_tools(self):
        return [query_fhir_database, vector_search]

    async def analyze(
        self,
        patient_id: str,
        state: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:

        fhir_base = os.getenv("FHIR_SERVER_URL", "http://fhir-server:8080/fhir")
        timestamp = datetime.now(timezone.utc).isoformat()

        monitoring = state.get("monitoring_results", {})
        diagnostics = state.get("diagnostic_results", {})
        interventions = state.get("interventions", [])
        risk_scores = state.get("risk_scores", {})
        alerts = state.get("alerts", [])

        # 1. Generate SOAP note via LLM
        soap_note = await self._generate_soap_note(
            patient_id=patient_id,
            monitoring=monitoring,
            diagnostics=diagnostics,
            interventions=interventions,
            risk_scores=risk_scores,
            timestamp=timestamp,
        )

        # 2. Create FHIR DiagnosticReport for AI analysis
        diagnostic_report = self._build_fhir_diagnostic_report(
            patient_id=patient_id,
            monitoring=monitoring,
            diagnostics=diagnostics,
            risk_scores=risk_scores,
            timestamp=timestamp,
        )

        # 3. Update CarePlan with new recommendations
        care_plan_update = self._build_fhir_care_plan_update(
            patient_id=patient_id,
            interventions=interventions,
            timestamp=timestamp,
        )

        # 4. Create Clinical Note as FHIR DocumentReference
        doc_reference = self._build_fhir_document_reference(
            patient_id=patient_id,
            soap_note=soap_note,
            timestamp=timestamp,
        )

        # 5. Write resources to FHIR server
        written_resources = []
        for resource_type, resource_data in [
            ("DiagnosticReport", diagnostic_report),
            ("CarePlan", care_plan_update),
            ("DocumentReference", doc_reference),
        ]:
            result = await self._write_fhir_resource(
                fhir_base=fhir_base,
                resource_type=resource_type,
                resource_data=resource_data,
            )
            written_resources.append({
                "resource_type": resource_type,
                "status": result.get("status", "error"),
                "resource_id": result.get("id", ""),
            })

        # 6. Build FHIR Bundle for external EHR export
        fhir_bundle = self._build_fhir_bundle(
            patient_id=patient_id,
            resources=[diagnostic_report, care_plan_update, doc_reference],
        )

        alerts_out = []
        write_errors = [r for r in written_resources if r.get("status") == "error"]
        if write_errors:
            alerts_out.append(self._build_alert(
                severity="NORMAL",
                message=f"EHR write-back errors: {len(write_errors)} resource(s) failed to write. Manual documentation may be required.",
                patient_id=patient_id,
                details={"failed_resources": write_errors},
            ))

        return self._build_result(
            status="completed",
            findings={
                "soap_note": soap_note,
                "resources_written": len([r for r in written_resources if r.get("status") != "error"]),
                "write_errors": len(write_errors),
                "written_resources": written_resources,
                "fhir_bundle_size": len(fhir_bundle.get("entry", [])),
                "timestamp": timestamp,
            },
            alerts=alerts_out,
            recommendations=["EHR documentation complete. Review clinical note in FHIR server for accuracy before co-signing."],
        )

    async def _generate_soap_note(
        self,
        patient_id: str,
        monitoring: Dict,
        diagnostics: Dict,
        interventions: List,
        risk_scores: Dict,
        timestamp: str,
    ) -> str:
        """Generate a SOAP-format clinical note via LLM."""
        monitoring_summary = json.dumps(
            {k: v.get("findings", {}) for k, v in monitoring.items()}, default=str
        )[:500]
        diagnostic_summary = json.dumps(
            {k: v.get("findings", {}) for k, v in diagnostics.items()}, default=str
        )[:500]
        risk_summary = json.dumps(risk_scores, default=str)[:300]

        llm_input = (
            f"Generate a SOAP clinical note for patient {patient_id}:\n\n"
            f"Date/Time: {timestamp}\n"
            f"Generated by: InHealth AI Agent System v1.0\n\n"
            f"Monitoring data: {monitoring_summary}\n"
            f"Diagnostic data: {diagnostic_summary}\n"
            f"Risk assessment: {risk_summary}\n"
            f"Interventions planned: {len(interventions)}\n\n"
            f"Create a complete SOAP note with:\n"
            f"SUBJECTIVE: Patient-reported symptoms (based on monitoring data)\n"
            f"OBJECTIVE: Vital signs, lab values, and objective measurements\n"
            f"ASSESSMENT: Clinical assessment with differential diagnoses\n"
            f"PLAN: Specific interventions, medication changes, follow-up schedule\n\n"
            f"Format as proper clinical documentation. Include relevant values and dates."
        )

        try:
            result = await self.run_agent_chain(input_text=llm_input)
            return result.get("output", "SOAP note generation failed.")
        except Exception as exc:
            logger.warning("SOAP note LLM failed: %s", exc)
            return f"[AI-GENERATED NOTE — {timestamp}]\nClinical note generation incomplete. Manual documentation required."

    def _build_fhir_diagnostic_report(
        self,
        patient_id: str,
        monitoring: Dict,
        diagnostics: Dict,
        risk_scores: Dict,
        timestamp: str,
    ) -> Dict[str, Any]:
        """Build FHIR R4 DiagnosticReport resource for AI analysis results."""
        return {
            "resourceType": "DiagnosticReport",
            "id": str(uuid.uuid4()),
            "status": "final",
            "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/v2-0074", "code": "AI", "display": "AI Analysis"}]}],
            "code": {
                "coding": [{"system": "http://loinc.org", "code": "81248-8", "display": "Clinical decision support report"}],
                "text": "InHealth AI Agent Analysis",
            },
            "subject": {"reference": f"Patient/{patient_id}"},
            "effectiveDateTime": timestamp,
            "issued": timestamp,
            "performer": [{"display": "InHealth AI Agent System v1.0"}],
            "conclusion": f"AI agent analysis completed. Risk level: {risk_scores.get('ml_ensemble_agent', {}).get('findings', {}).get('risk_level', 'UNKNOWN')}.",
            "presentedForm": [{
                "contentType": "application/json",
                "data": json.dumps({
                    "monitoring_summary": {k: v.get("findings", {}) for k, v in monitoring.items()},
                    "diagnostic_summary": {k: v.get("findings", {}) for k, v in diagnostics.items()},
                    "risk_assessment": risk_scores,
                }, default=str)[:4096],
            }],
        }

    def _build_fhir_care_plan_update(
        self,
        patient_id: str,
        interventions: List[Dict[str, Any]],
        timestamp: str,
    ) -> Dict[str, Any]:
        """Build FHIR R4 CarePlan resource with AI recommendations."""
        activities = []
        for intervention in interventions[:10]:
            activities.append({
                "detail": {
                    "kind": "ServiceRequest",
                    "status": "scheduled" if not intervention.get("requires_hitl") else "on-hold",
                    "intent": "proposal",
                    "description": intervention.get("recommendation_text", str(intervention))[:200],
                    "doNotPerform": intervention.get("requires_hitl", False),
                }
            })

        return {
            "resourceType": "CarePlan",
            "id": str(uuid.uuid4()),
            "status": "active",
            "intent": "proposal",
            "category": [{"coding": [{"system": "http://loinc.org", "code": "38717-5", "display": "Chronic disease management care plan"}]}],
            "title": "InHealth AI Care Plan Update",
            "subject": {"reference": f"Patient/{patient_id}"},
            "period": {"start": timestamp},
            "created": timestamp,
            "author": {"display": "InHealth AI Agent System"},
            "activity": activities,
        }

    def _build_fhir_document_reference(
        self,
        patient_id: str,
        soap_note: str,
        timestamp: str,
    ) -> Dict[str, Any]:
        """Build FHIR R4 DocumentReference for the SOAP note."""
        import base64

        encoded_note = base64.b64encode(soap_note.encode()).decode()
        return {
            "resourceType": "DocumentReference",
            "id": str(uuid.uuid4()),
            "status": "current",
            "type": {
                "coding": [{"system": "http://loinc.org", "code": "34109-9", "display": "Note"}],
                "text": "AI-Generated Clinical Note",
            },
            "category": [{"coding": [{"system": "http://loinc.org", "code": "11488-4", "display": "Consultation note"}]}],
            "subject": {"reference": f"Patient/{patient_id}"},
            "date": timestamp,
            "author": [{"display": "InHealth AI Agent System v1.0"}],
            "description": "AI-generated clinical summary — requires physician review and co-signature",
            "content": [{"attachment": {"contentType": "text/plain", "data": encoded_note, "creation": timestamp}}],
            "context": {"period": {"start": timestamp}},
        }

    def _build_fhir_bundle(
        self,
        patient_id: str,
        resources: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Build a FHIR R4 Bundle containing all generated resources."""
        return {
            "resourceType": "Bundle",
            "id": str(uuid.uuid4()),
            "type": "document",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "entry": [
                {"resource": r, "fullUrl": f"urn:uuid:{r.get('id', str(uuid.uuid4()))}"}
                for r in resources
            ],
        }

    async def _write_fhir_resource(
        self,
        fhir_base: str,
        resource_type: str,
        resource_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Write a FHIR resource to the FHIR server."""
        resource_id = resource_data.get("id", str(uuid.uuid4()))
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.put(
                    f"{fhir_base}/{resource_type}/{resource_id}",
                    json=resource_data,
                    headers={
                        "Content-Type": "application/fhir+json",
                        "Accept": "application/fhir+json",
                    },
                )
                if resp.status_code in (200, 201):
                    response_data = resp.json()
                    return {"status": "success", "id": response_data.get("id", resource_id)}
                else:
                    logger.warning("FHIR write failed: %s %s", resp.status_code, resp.text[:200])
                    return {"status": "error", "http_status": resp.status_code}
        except Exception as exc:
            logger.error("FHIR resource write failed for %s: %s", resource_type, exc)
            return {"status": "error", "error": str(exc)}
