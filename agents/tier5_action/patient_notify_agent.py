"""
Agent 21 — Patient Notification Agent

Responsibilities:
  - Health literacy-adapted patient messages (5 levels)
  - Multi-language (English, Spanish)
  - Positive, encouraging tone
  - Include action items and when to seek emergency care
  - Patient portal notification + SMS + email
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from base.agent import MCPAgent
from base.tools import query_fhir_database, send_notification, vector_search

logger = logging.getLogger("inhealth.agent.patient_notify")

LITERACY_GUIDANCE = {
    1: "Grade 1-3 reading level. Use simple pictures/diagrams if possible. Single concept per sentence. Use 'you' and 'your doctor'. Max 3 action items.",
    2: "Grade 4-6 reading level. Short sentences. Common everyday words. Avoid medical jargon. Clear action steps.",
    3: "Grade 7-9 reading level. Plain language. Brief explanations of medical terms. Numbered steps.",
    4: "Grade 10-12 reading level. Standard health information language. Include clinical context.",
    5: "College level. Full medical terminology. Detailed information. Patient is highly health-literate.",
}

LANGUAGE_MAP = {
    "english": "English",
    "spanish": "Español (Spanish)",
    "mandarin": "Mandarin Chinese",
    "portuguese": "Portuguese",
    "tagalog": "Tagalog",
}


class PatientNotifyAgent(MCPAgent):
    """Agent 21: Health literacy-adapted patient notifications."""

    agent_id = 21
    agent_name = "patient_notify_agent"
    agent_tier = "tier5_action"
    system_prompt = (
        "You are the Patient Notification AI Agent for InHealth Chronic Care. "
        "You generate warm, supportive, and clear health messages for patients. "
        "Adapt your language to the patient's health literacy level and preferred language. "
        "Always end with specific action items and clear guidance on when to call 911 or seek emergency care. "
        "Use motivational, empowering language. Avoid medical jargon unless literacy level is high. "
        "Never create fear or panic — be calm, informative, and solution-focused."
    )

    def _default_tools(self):
        return [query_fhir_database, send_notification, vector_search]

    async def analyze(
        self,
        patient_id: str,
        state: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:

        patient = context.get("patient", {})
        literacy_level = patient.get("health_literacy_level", 3)
        preferred_language = patient.get("preferred_language", "english").lower()
        patient_name = patient.get("name", "there").split()[0] if patient.get("name") else "there"

        alerts = state.get("alerts", [])
        monitoring = state.get("monitoring_results", {})
        interventions = state.get("interventions", [])
        risk_data = state.get("risk_scores", {}).get("ml_ensemble_agent", {}).get("findings", {})

        # Categorize alerts by type
        critical_alerts = [a for a in alerts if a.get("severity") in ("EMERGENCY", "CRITICAL")]
        high_alerts = [a for a in alerts if a.get("severity") == "HIGH"]
        routine_alerts = [a for a in alerts if a.get("severity") in ("NORMAL", "LOW")]

        # Build message context
        monitoring_highlights = self._extract_monitoring_highlights(monitoring)
        action_items = self._extract_action_items(interventions, alerts)

        literacy_guidance = LITERACY_GUIDANCE.get(literacy_level, LITERACY_GUIDANCE[3])
        language_name = LANGUAGE_MAP.get(preferred_language, "English")
        language_instruction = f"Write in {language_name}." if preferred_language != "english" else ""

        emergency_guidance = self._build_emergency_guidance(critical_alerts, literacy_level)

        llm_input = (
            f"Generate a patient health update message for patient {patient_id} (call them '{patient_name}'):\n\n"
            f"Literacy guidance: {literacy_guidance}\n"
            f"Language: {language_instruction}\n\n"
            f"Health update context:\n"
            f"  Today's monitoring highlights: {monitoring_highlights}\n"
            f"  Critical concerns: {len(critical_alerts)} (severe, needing immediate action)\n"
            f"  Health alerts: {len(high_alerts)} (important, need attention today)\n"
            f"  Routine updates: {len(routine_alerts)}\n"
            f"  Risk level: {risk_data.get('risk_level', 'Not assessed')}\n\n"
            f"Action items for patient:\n"
            + "\n".join([f"  {i+1}. {item}" for i, item in enumerate(action_items[:5])])
            + f"\n\nEmergency guidance to include:\n{emergency_guidance}\n\n"
            f"Create a patient message with:\n"
            f"1. Warm, personal greeting using patient's first name\n"
            f"2. Brief summary of their health today (positive framing where appropriate)\n"
            f"3. What's going well (celebrate progress!)\n"
            f"4. What needs attention (clear, calm, specific)\n"
            f"5. Action items (3-5 maximum, numbered, simple)\n"
            f"6. When to call 911 or go to ER (clear criteria)\n"
            f"7. Encouraging closing message\n\n"
            f"Tone: warm, supportive, empowering. Never alarming. Never condescending."
        )

        try:
            llm_result = await self.run_agent_chain(input_text=llm_input)
            patient_message = llm_result.get("output", "")
        except Exception as exc:
            logger.warning("Patient notify LLM failed: %s", exc)
            patient_message = self._fallback_patient_message(
                patient_name, literacy_level, critical_alerts, action_items
            )

        # Send via multiple channels
        channels_sent = []
        channels_to_use = ["push", "in_app"]
        if high_alerts or critical_alerts:
            channels_to_use.append("sms")

        for channel in channels_to_use:
            try:
                send_notification.invoke({
                    "patient_id": patient_id,
                    "notification_type": "CRITICAL" if critical_alerts else "URGENT" if high_alerts else "ROUTINE",
                    "message": patient_message[:1000],
                    "channel": channel,
                })
                channels_sent.append(channel)
            except Exception as exc:
                logger.warning("Patient notification send failed on %s: %s", channel, exc)

        return self._build_result(
            status="completed",
            findings={
                "patient_message": patient_message,
                "literacy_level": literacy_level,
                "language": preferred_language,
                "channels_sent": channels_sent,
                "action_items": action_items,
                "critical_alerts_count": len(critical_alerts),
            },
            recommendations=["Patient notified via " + ", ".join(channels_sent)],
        )

    def _extract_monitoring_highlights(self, monitoring: Dict[str, Any]) -> str:
        highlights = []
        glucose = monitoring.get("glucose_agent", {}).get("findings", {})
        if glucose:
            tir = glucose.get("tir_stats", {}).get("tir_percent", "N/A")
            current = glucose.get("current_glucose_mgdl", "N/A")
            highlights.append(f"Blood sugar: {current} mg/dL (time in range: {tir}%)")

        activity = monitoring.get("activity_agent", {}).get("findings", {})
        if activity:
            steps = activity.get("today_steps", 0)
            highlights.append(f"Steps today: {steps:,.0f}")

        cardiac = monitoring.get("cardiac_agent", {}).get("findings", {})
        if cardiac:
            bp = f"{cardiac.get('blood_pressure_systolic', '?')}/{cardiac.get('blood_pressure_diastolic', '?')}"
            highlights.append(f"Blood pressure: {bp} mmHg")

        return "; ".join(highlights) or "Monitoring data collected"

    def _extract_action_items(
        self,
        interventions: List[Dict[str, Any]],
        alerts: List[Dict[str, Any]],
    ) -> List[str]:
        items = []
        for intervention in interventions:
            if intervention.get("type") == "lifestyle":
                recs = intervention.get("recommendations", [])
                items.extend(recs[:2])
        for alert in alerts[:3]:
            if alert.get("severity") in ("HIGH", "NORMAL"):
                items.append(alert.get("message", "")[:80])
        return items[:5]

    def _build_emergency_guidance(
        self,
        critical_alerts: List[Dict[str, Any]],
        literacy_level: int,
    ) -> str:
        if literacy_level <= 2:
            return "Call 911 if you: can't breathe, have chest pain, feel very dizzy, or pass out."
        elif literacy_level <= 3:
            return "Go to the ER or call 911 if you have: chest pain or pressure, difficulty breathing, sudden severe headache, signs of low blood sugar that don't improve with sugar intake."
        return "Seek emergency care (call 911) for: chest pain/pressure, dyspnea at rest, severe hypoglycemia unresponsive to treatment, neurological symptoms (FAST: face drooping, arm weakness, speech difficulty, time to call 911), or any rapidly worsening symptom."

    def _fallback_patient_message(
        self,
        name: str,
        literacy: int,
        critical: List,
        actions: List[str],
    ) -> str:
        if literacy <= 2:
            msg = f"Hello {name}! We checked your health today. "
            if critical:
                msg += "Something needs attention right away. Call your doctor now. "
            else:
                msg += "Things look okay. Keep taking your medicine. "
            msg += "We are here for you!"
            return msg
        return (
            f"Hello {name}, your InHealth care team has reviewed your health data today. "
            + ("We've identified some areas that need attention. " if critical else "Your readings are being monitored. ")
            + "Action items: " + "; ".join(actions[:3]) + ". "
            + "Contact us or call 911 if you feel unsafe."
        )
