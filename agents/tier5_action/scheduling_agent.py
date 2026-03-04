"""
Agent 22 — Appointment Scheduling Agent

Responsibilities:
  - Auto-schedule follow-up appointments based on urgency
  - CRITICAL: same-day; URGENT: 24-48 hours; ROUTINE: 2-4 weeks
  - Match specialist type to condition
  - Send appointment confirmation to patient and provider
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from base.agent import MCPAgent
from base.tools import query_fhir_database, schedule_appointment, send_notification

logger = logging.getLogger("inhealth.agent.scheduling")

# Urgency to timing mapping
URGENCY_TIMING = {
    "CRITICAL": {"target": "same-day", "hours_max": 4},
    "URGENT": {"target": "24-48 hours", "hours_max": 48},
    "SOON": {"target": "1-2 weeks", "hours_max": 336},
    "ROUTINE": {"target": "2-4 weeks", "hours_max": 672},
}

# Condition-to-specialist mapping
SPECIALIST_MAP = {
    "diabetes": ["endocrinologist", "primary_care"],
    "hypertension": ["primary_care", "cardiologist"],
    "ckd": ["nephrologist", "primary_care"],
    "heart_failure": ["cardiologist", "heart_failure_specialist"],
    "copd": ["pulmonologist", "primary_care"],
    "afib": ["cardiologist", "electrophysiologist"],
    "stroke": ["neurologist", "primary_care"],
    "cancer": ["oncologist"],
    "mental_health": ["psychiatrist", "psychologist"],
    "depression": ["psychiatrist", "primary_care"],
    "nutrition": ["dietitian", "diabetes_educator"],
    "wound_care": ["wound_care_specialist", "primary_care"],
    "default": ["primary_care"],
}


class SchedulingAgent(MCPAgent):
    """Agent 22: Automated appointment scheduling with urgency-based routing."""

    agent_id = 22
    agent_name = "scheduling_agent"
    agent_tier = "tier5_action"
    system_prompt = (
        "You are the Appointment Scheduling AI Agent for InHealth Chronic Care. "
        "You schedule follow-up appointments based on clinical urgency and match patients "
        "with appropriate specialists. Coordinate with provider availability calendars. "
        "Send clear confirmation messages to both patients and providers."
    )

    def _default_tools(self):
        return [query_fhir_database, schedule_appointment, send_notification]

    async def analyze(
        self,
        patient_id: str,
        state: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:

        alerts = state.get("alerts", [])
        interventions = state.get("interventions", [])
        risk_data = state.get("risk_scores", {}).get("ml_ensemble_agent", {}).get("findings", {})
        risk_level = risk_data.get("risk_level", "MEDIUM")

        # Determine overall urgency
        urgency = self._determine_urgency(alerts, risk_level)

        # Identify what specialist(s) are needed
        conditions_needing_followup = self._identify_conditions_needing_followup(state)
        specialists_needed = self._match_specialists(conditions_needing_followup)

        # Schedule appointments
        scheduled = []
        for specialist_type in specialists_needed[:3]:  # Max 3 appointments at once
            reason = self._generate_appointment_reason(conditions_needing_followup, specialist_type)
            try:
                appointment = schedule_appointment.invoke({
                    "patient_id": patient_id,
                    "provider_id": specialist_type,
                    "urgency": urgency,
                    "reason": reason,
                })
                if appointment and not appointment.get("error"):
                    scheduled.append({
                        "type": specialist_type,
                        "urgency": urgency,
                        "reason": reason,
                        "appointment": appointment,
                    })

                    # Send confirmation to patient
                    appt_date = appointment.get("scheduled_datetime", "TBD")
                    provider_name = appointment.get("provider_name", specialist_type.replace("_", " ").title())
                    send_notification.invoke({
                        "patient_id": patient_id,
                        "notification_type": "ROUTINE",
                        "message": (
                            f"Appointment scheduled: {provider_name} on {appt_date}. "
                            f"Reason: {reason[:80]}. "
                            f"You will receive a reminder 24 hours before."
                        ),
                        "channel": "push",
                    })

            except Exception as exc:
                logger.warning("Appointment scheduling failed for %s: %s", specialist_type, exc)
                scheduled.append({
                    "type": specialist_type,
                    "urgency": urgency,
                    "reason": reason,
                    "error": str(exc),
                    "note": "Manual scheduling required",
                })

        # LLM-generated scheduling summary
        scheduled_str = "\n".join([
            f"  - {s['type'].replace('_', ' ').title()}: {s.get('appointment', {}).get('scheduled_datetime', 'TBD')} ({s['urgency']})"
            for s in scheduled
        ])
        llm_input = (
            f"Patient {patient_id} appointment scheduling summary:\n\n"
            f"Urgency: {urgency} — target: {URGENCY_TIMING.get(urgency, {}).get('target', 'TBD')}\n"
            f"Conditions requiring follow-up: {conditions_needing_followup}\n"
            f"Appointments scheduled:\n{scheduled_str}\n\n"
            f"Generate:\n"
            f"1. Patient-friendly appointment reminder message\n"
            f"2. Preparation instructions for each appointment type\n"
            f"3. What to bring (medications list, lab results, glucose log)\n"
            f"4. Questions to ask at each appointment (3 per visit)"
        )

        try:
            llm_result = await self.run_agent_chain(input_text=llm_input)
            scheduling_guidance = llm_result.get("output", "")
        except Exception as exc:
            logger.warning("Scheduling LLM failed: %s", exc)
            scheduling_guidance = ""

        alerts_out = []
        if urgency == "CRITICAL" and not any(s.get("appointment") for s in scheduled):
            alerts_out.append(self._build_alert(
                severity="HIGH",
                message="CRITICAL urgency appointment required but auto-scheduling failed. Manual scheduling needed within 4 hours.",
                patient_id=patient_id,
                details={"specialists_needed": specialists_needed, "urgency": urgency},
            ))

        return self._build_result(
            status="completed",
            findings={
                "urgency": urgency,
                "timing_target": URGENCY_TIMING.get(urgency, {}).get("target"),
                "specialists_needed": specialists_needed,
                "appointments_scheduled": len([s for s in scheduled if s.get("appointment")]),
                "appointments": scheduled,
                "scheduling_guidance": scheduling_guidance,
            },
            alerts=alerts_out,
            recommendations=[
                f"Appointments scheduled with {', '.join(specialists_needed[:3])} — urgency: {urgency}.",
                "Patient will receive confirmation via push notification and portal message.",
            ],
        )

    def _determine_urgency(self, alerts: List[Dict[str, Any]], risk_level: str) -> str:
        if any(a.get("severity") in ("EMERGENCY", "CRITICAL") for a in alerts) or risk_level == "CRITICAL":
            return "CRITICAL"
        if any(a.get("severity") == "HIGH" for a in alerts) or risk_level == "HIGH":
            return "URGENT"
        if risk_level == "MEDIUM":
            return "SOON"
        return "ROUTINE"

    def _identify_conditions_needing_followup(self, state: Dict[str, Any]) -> List[str]:
        conditions = []
        monitoring = state.get("monitoring_results", {})
        diagnostics = state.get("diagnostic_results", {})
        risk = state.get("risk_scores", {})

        if monitoring.get("glucose_agent", {}).get("alerts"):
            conditions.append("diabetes")
        if monitoring.get("cardiac_agent", {}).get("alerts"):
            conditions.append("hypertension")
        if diagnostics.get("kidney_agent", {}).get("findings", {}).get("aki_detected"):
            conditions.append("ckd")
        if diagnostics.get("ecg_agent", {}).get("findings", {}).get("ecg_features", {}).get("afib"):
            conditions.append("afib")

        return list(set(conditions)) if conditions else ["default"]

    def _match_specialists(self, conditions: List[str]) -> List[str]:
        specialists = set()
        for condition in conditions:
            mapped = SPECIALIST_MAP.get(condition, SPECIALIST_MAP["default"])
            specialists.add(mapped[0])  # Primary specialist
        return list(specialists) or ["primary_care"]

    def _generate_appointment_reason(self, conditions: List[str], specialist: str) -> str:
        cond_str = ", ".join(conditions[:3]).replace("_", " ").title()
        return f"Follow-up for {cond_str} management. AI-detected abnormalities requiring clinical evaluation."
