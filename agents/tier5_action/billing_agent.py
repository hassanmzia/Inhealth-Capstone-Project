"""
Agent 24 — Billing & RPM Agent

Responsibilities:
  - Generate CPT codes for encounters
  - RPM billing: calculate time, select codes (99453/99454/99457/99458)
  - Pre-authorization check
  - Create billing claim record via Django API
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx

from base.agent import MCPAgent
from base.tools import query_fhir_database

logger = logging.getLogger("inhealth.agent.billing")

# RPM CPT codes
RPM_CPT_CODES = {
    "99453": {
        "description": "Remote monitoring — initial device setup and patient education",
        "billing_period": "one_time",
        "requirements": "First time patient enrolled in RPM. Device setup and education required.",
        "reimbursement_approx_usd": 19.0,
    },
    "99454": {
        "description": "Remote monitoring — device supply with daily recordings or alerts",
        "billing_period": "monthly",
        "requirements": "≥16 days of monitoring data in 30-day period.",
        "reimbursement_approx_usd": 50.0,
    },
    "99457": {
        "description": "Remote physiologic monitoring treatment management — first 20 minutes",
        "billing_period": "monthly",
        "requirements": "≥20 minutes interactive communication with clinical staff per month. Requires interactive communication with patient.",
        "reimbursement_approx_usd": 50.0,
    },
    "99458": {
        "description": "Remote physiologic monitoring treatment management — each additional 20 minutes",
        "billing_period": "monthly",
        "requirements": "Each additional 20-min block beyond first (99457). Max 2 add-ons per month.",
        "reimbursement_approx_usd": 43.0,
    },
}

# Common E&M CPT codes
EM_CPT_CODES = {
    "99213": "Office visit — established patient, moderate complexity, 20-29 min",
    "99214": "Office visit — established patient, moderate-high complexity, 30-39 min",
    "99215": "Office visit — established patient, high complexity, 40-54 min",
    "99241": "Telehealth — established patient, low complexity",
    "99242": "Telehealth — established patient, moderate complexity",
}


class BillingAgent(MCPAgent):
    """Agent 24: Automated CPT coding and RPM billing claim generation."""

    agent_id = 24
    agent_name = "billing_agent"
    agent_tier = "tier5_action"
    system_prompt = (
        "You are the Billing and RPM AI Agent for InHealth Chronic Care. "
        "You generate accurate CPT codes for clinical encounters and RPM services. "
        "Calculate billable RPM time, select appropriate codes, and generate billing claims. "
        "Reference CMS 2024 RPM billing guidelines (MLN booklet), AMA CPT coding guidelines, "
        "and payer-specific authorization requirements. Ensure compliance with documentation requirements."
    )

    def _default_tools(self):
        return [query_fhir_database]

    async def analyze(
        self,
        patient_id: str,
        state: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:

        patient = context.get("patient", {})
        tenant_id = state.get("tenant_id", "")
        timestamp = datetime.now(timezone.utc).isoformat()

        # Calculate RPM metrics from monitoring data
        monitoring = state.get("monitoring_results", {})
        actions_taken = state.get("actions_taken", [])

        rpm_metrics = self._calculate_rpm_metrics(monitoring, actions_taken)

        # Select appropriate CPT codes
        cpt_codes = self._select_cpt_codes(rpm_metrics, state)

        # Calculate estimated reimbursement
        estimated_reimbursement = sum(
            RPM_CPT_CODES.get(code, {}).get("reimbursement_approx_usd", 0)
            for code in cpt_codes
            if code in RPM_CPT_CODES
        )

        # Pre-authorization check
        auth_result = await self._check_preauthorization(
            patient_id=patient_id,
            cpt_codes=cpt_codes,
            tenant_id=tenant_id,
        )

        # Build billing claim
        claim = self._build_billing_claim(
            patient_id=patient_id,
            tenant_id=tenant_id,
            cpt_codes=cpt_codes,
            rpm_metrics=rpm_metrics,
            auth_result=auth_result,
            timestamp=timestamp,
        )

        # Submit claim to Django billing API
        submission_result = await self._submit_claim(claim)

        # LLM billing summary
        llm_input = (
            f"Generate a billing summary for patient {patient_id}:\n\n"
            f"RPM metrics this month:\n"
            f"  Monitoring days: {rpm_metrics.get('monitoring_days', 0)}\n"
            f"  Clinical staff time (minutes): {rpm_metrics.get('clinical_time_minutes', 0)}\n"
            f"  Interactive sessions: {rpm_metrics.get('interactive_sessions', 0)}\n\n"
            f"CPT codes selected: {', '.join(cpt_codes)}\n"
            f"Estimated reimbursement: ${estimated_reimbursement:.2f}\n"
            f"Pre-authorization required: {auth_result.get('required', False)}\n"
            f"Authorization status: {auth_result.get('status', 'pending')}\n\n"
            f"Verify code selection and provide:\n"
            f"1. Justification for each CPT code with documentation requirements\n"
            f"2. Any missing documentation that could jeopardize reimbursement\n"
            f"3. Compliance checklist for CMS RPM requirements\n"
            f"4. Estimated revenue cycle timeline"
        )

        try:
            llm_result = await self.run_agent_chain(input_text=llm_input)
            billing_summary = llm_result.get("output", "")
        except Exception as exc:
            logger.warning("Billing LLM failed: %s", exc)
            billing_summary = self._fallback_billing_summary(cpt_codes, estimated_reimbursement)

        return self._build_result(
            status="completed",
            findings={
                "cpt_codes": cpt_codes,
                "rpm_metrics": rpm_metrics,
                "estimated_reimbursement_usd": round(estimated_reimbursement, 2),
                "preauth_required": auth_result.get("required", False),
                "preauth_status": auth_result.get("status", "not_required"),
                "claim_id": claim.get("claim_id"),
                "submission_status": submission_result.get("status", "pending"),
                "billing_summary": billing_summary,
            },
            recommendations=[
                f"RPM billing: {len(cpt_codes)} CPT codes generated. Estimated reimbursement: ${estimated_reimbursement:.2f}.",
                "Ensure ≥16 days monitoring data in billing period for 99454.",
                "Document interactive communication time for 99457/99458 compliance.",
            ],
        )

    def _calculate_rpm_metrics(
        self,
        monitoring: Dict[str, Any],
        actions_taken: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Calculate RPM billing metrics from monitoring activity."""
        monitoring_days = 0
        for agent_name, data in monitoring.items():
            if data.get("status") == "completed":
                monitoring_days = max(monitoring_days, data.get("readings_analyzed", 0) // 12)  # Estimate from readings

        clinical_time_minutes = 0
        interactive_sessions = 0
        for action in actions_taken:
            if action.get("type") in ("notification_sent", "physician_contacted"):
                clinical_time_minutes += 5
                interactive_sessions += 1

        return {
            "monitoring_days": min(monitoring_days, 31),
            "clinical_time_minutes": clinical_time_minutes,
            "interactive_sessions": interactive_sessions,
            "qualifies_99454": monitoring_days >= 16,
            "qualifies_99457": clinical_time_minutes >= 20,
            "additional_20min_blocks": max(0, (clinical_time_minutes - 20) // 20),
        }

    def _select_cpt_codes(
        self,
        metrics: Dict[str, Any],
        state: Dict[str, Any],
    ) -> List[str]:
        """Select appropriate CPT codes based on documented activity."""
        codes = []

        # RPM codes
        if metrics.get("qualifies_99454"):
            codes.append("99454")
        if metrics.get("qualifies_99457"):
            codes.append("99457")
            additional = min(metrics.get("additional_20min_blocks", 0), 2)  # Max 2 add-ons
            for _ in range(additional):
                codes.append("99458")

        # If first monitoring setup (check state for new enrollment flag)
        if state.get("first_enrollment"):
            codes.insert(0, "99453")

        # If no RPM codes, add basic E&M
        if not codes:
            risk_level = state.get("risk_scores", {}).get("ml_ensemble_agent", {}).get("findings", {}).get("risk_level", "MEDIUM")
            if risk_level in ("CRITICAL", "HIGH"):
                codes.append("99215")
            else:
                codes.append("99214")

        return list(dict.fromkeys(codes))  # Deduplicate while preserving order

    async def _check_preauthorization(
        self,
        patient_id: str,
        cpt_codes: List[str],
        tenant_id: str,
    ) -> Dict[str, Any]:
        """Check if pre-authorization is required for selected CPT codes."""
        try:
            api_url = os.getenv("DJANGO_API_URL", "http://backend:8000")
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    f"{api_url}/api/billing/preauth-check/",
                    json={
                        "patient_id": patient_id,
                        "cpt_codes": cpt_codes,
                        "tenant_id": tenant_id,
                    },
                    headers={"X-Internal-Token": os.getenv("INTERNAL_API_TOKEN", "")},
                )
                if resp.status_code == 200:
                    return resp.json()
        except Exception as exc:
            logger.debug("Pre-auth check failed: %s", exc)

        return {"required": False, "status": "not_checked", "message": "Pre-auth check unavailable"}

    def _build_billing_claim(
        self,
        patient_id: str,
        tenant_id: str,
        cpt_codes: List[str],
        rpm_metrics: Dict,
        auth_result: Dict,
        timestamp: str,
    ) -> Dict[str, Any]:
        import uuid

        return {
            "claim_id": str(uuid.uuid4()),
            "patient_id": patient_id,
            "tenant_id": tenant_id,
            "service_date": timestamp[:10],
            "claim_type": "RPM" if "99454" in cpt_codes else "ENCOUNTER",
            "cpt_codes": cpt_codes,
            "rpm_monitoring_days": rpm_metrics.get("monitoring_days", 0),
            "rpm_clinical_time_minutes": rpm_metrics.get("clinical_time_minutes", 0),
            "preauth_number": auth_result.get("auth_number", ""),
            "status": "draft",
            "created_at": timestamp,
            "generated_by": "billing_agent",
        }

    async def _submit_claim(self, claim: Dict[str, Any]) -> Dict[str, Any]:
        """Submit billing claim to the Django billing API."""
        try:
            api_url = os.getenv("DJANGO_API_URL", "http://backend:8000")
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(
                    f"{api_url}/api/billing/claims/",
                    json=claim,
                    headers={"X-Internal-Token": os.getenv("INTERNAL_API_TOKEN", "")},
                )
                if resp.status_code in (200, 201):
                    return {"status": "submitted", "claim_id": resp.json().get("id")}
                return {"status": "failed", "http_status": resp.status_code}
        except Exception as exc:
            logger.warning("Claim submission failed: %s", exc)
            return {"status": "error", "error": str(exc)}

    def _fallback_billing_summary(self, codes: List[str], revenue: float) -> str:
        code_list = ", ".join(codes) if codes else "None"
        return (
            f"CPT codes generated: {code_list}. "
            f"Estimated reimbursement: ${revenue:.2f}. "
            f"Review documentation requirements for each code before submission."
        )
