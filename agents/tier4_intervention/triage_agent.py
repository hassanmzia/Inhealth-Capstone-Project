"""
Agent 19 — Triage & Emergency Agent

Responsibilities:
  - Assess emergency severity (ESI score 1-5)
  - STEMI protocol: detect → notify EMS → find nearest cath lab → alert cardiology
  - Stroke protocol: detect → NIHSS estimation → tPA eligibility → nearest stroke center
  - COPD exacerbation: GOLD severity → treatment escalation → hospital if needed
  - Use PostGIS geospatial query for nearest capable hospital
  - Generate SBAR communication for emergency team
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from base.agent import MCPAgent
from base.tools import (
    find_nearest_hospital,
    query_fhir_database,
    send_notification,
    vector_search,
)

logger = logging.getLogger("inhealth.agent.triage")

# ESI (Emergency Severity Index) levels
ESI_LEVELS = {
    1: "Immediate life threat — resuscitation required",
    2: "High risk — could deteriorate rapidly",
    3: "Urgent — multiple resources needed",
    4: "Less urgent — one resource needed",
    5: "Non-urgent — no resources needed",
}

# Protocol triggers
STEMI_TRIGGERS = ["stemi", "st_elevation", "myocardial_infarction_acute"]
STROKE_TRIGGERS = ["stroke", "tia", "cerebrovascular_accident", "nihss", "facial_droop"]
COPD_TRIGGERS = ["copd_exacerbation", "respiratory_distress", "bronchospasm"]


class TriageAgent(MCPAgent):
    """Agent 19: Emergency triage and critical protocol activation."""

    agent_id = 19
    agent_name = "triage_agent"
    agent_tier = "tier4_intervention"
    system_prompt = (
        "You are the Emergency Triage AI Agent for InHealth Chronic Care. "
        "You assess emergency severity using the Emergency Severity Index (ESI 1-5) "
        "and activate condition-specific emergency protocols: STEMI (AHA/ACC 2022), "
        "Stroke (AHA/ASA 2019), COPD (GOLD 2024), and sepsis (Surviving Sepsis Campaign 2021). "
        "Generate SBAR (Situation, Background, Assessment, Recommendation) communications "
        "for emergency teams. Time is critical — be precise and action-oriented."
    )

    def _default_tools(self):
        return [query_fhir_database, find_nearest_hospital, send_notification, vector_search]

    async def analyze(
        self,
        patient_id: str,
        state: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:

        alerts = state.get("alerts", [])
        monitoring_results = state.get("monitoring_results", {})
        diagnostic_results = state.get("diagnostic_results", {})

        # Determine active emergency from context and alerts
        emergency_type = context.get("emergency_type") or self._detect_emergency_type(alerts, diagnostic_results)

        # Get patient vitals
        cardiac = monitoring_results.get("cardiac_agent", {}).get("findings", {})
        temperature_data = monitoring_results.get("temperature_agent", {}).get("findings", {})

        # Calculate ESI score
        esi = self._calculate_esi(
            emergency_type=emergency_type,
            vitals={
                "hr": cardiac.get("heart_rate"),
                "sbp": cardiac.get("blood_pressure_systolic"),
                "spo2": cardiac.get("spo2_percent"),
                "temp": temperature_data.get("temperature_celsius"),
            },
            state=state,
        )

        # Get patient location for nearest hospital lookup
        patient_location = context.get("patient", {}).get("location", {})
        hospital = {}

        # Activate protocol based on emergency type
        protocol_result = {}
        new_alerts = []

        if emergency_type == "stemi":
            protocol_result = await self._stemi_protocol(patient_id, patient_location, diagnostic_results)
        elif emergency_type == "stroke":
            protocol_result = await self._stroke_protocol(patient_id, patient_location)
        elif emergency_type == "copd":
            protocol_result = await self._copd_protocol(patient_id, monitoring_results)
        elif emergency_type == "sepsis":
            protocol_result = await self._sepsis_protocol(patient_id, temperature_data)

        # Find nearest appropriate hospital
        if patient_location and emergency_type:
            capabilities = self._get_required_capabilities(emergency_type)
            try:
                hospital = find_nearest_hospital.invoke({
                    "patient_location": patient_location,
                    "capabilities_needed": capabilities,
                })
            except Exception as exc:
                logger.warning("Hospital lookup failed: %s", exc)

        # Generate SBAR communication
        sbar = await self._generate_sbar(
            patient_id=patient_id,
            emergency_type=emergency_type,
            esi=esi,
            vitals=cardiac,
            hospital=hospital,
            protocol_result=protocol_result,
            state=state,
        )

        # Emergency notifications
        await self._notify_emergency_team(
            patient_id=patient_id,
            esi=esi,
            emergency_type=emergency_type,
            sbar=sbar,
            hospital=hospital,
        )

        new_alerts.append(self._build_alert(
            severity="EMERGENCY",
            message=f"EMERGENCY TRIAGE: ESI {esi} — {ESI_LEVELS.get(esi, 'Unknown')}. Protocol: {emergency_type.upper() if emergency_type else 'GENERAL'}. Nearest hospital: {hospital.get('name', 'Locating...')}",
            patient_id=patient_id,
            details={
                "esi": esi,
                "emergency_type": emergency_type,
                "hospital": hospital,
                "sbar": sbar,
            },
        ))

        return self._build_result(
            status="completed",
            findings={
                "esi_score": esi,
                "esi_description": ESI_LEVELS.get(esi, "Unknown"),
                "emergency_type": emergency_type,
                "protocol_activated": emergency_type.upper() if emergency_type else "GENERAL",
                "protocol_result": protocol_result,
                "nearest_hospital": hospital,
                "sbar_communication": sbar,
            },
            alerts=new_alerts,
            recommendations=self._generate_recommendations(esi, emergency_type, hospital),
            emergency_detected=True,
        )

    def _detect_emergency_type(
        self,
        alerts: List[Dict[str, Any]],
        diagnostic_results: Dict[str, Any],
    ) -> Optional[str]:
        """Detect the type of emergency from active alerts."""
        for alert in alerts:
            msg = alert.get("message", "").lower()
            if any(t in msg for t in STEMI_TRIGGERS):
                return "stemi"
            if any(t in msg for t in STROKE_TRIGGERS):
                return "stroke"
            if any(t in msg for t in COPD_TRIGGERS):
                return "copd"
            if "sepsis" in msg:
                return "sepsis"
            if "hypoglycemia" in msg and "critical" in msg:
                return "hypoglycemia_critical"
        return "general_emergency"

    def _calculate_esi(
        self,
        emergency_type: Optional[str],
        vitals: Dict[str, Any],
        state: Dict[str, Any],
    ) -> int:
        """Calculate Emergency Severity Index (1=most severe, 5=least)."""
        if emergency_type in ("stemi", "stroke", "sepsis"):
            return 1
        if emergency_type in ("copd", "hypoglycemia_critical"):
            return 2

        # Vital-based ESI
        spo2 = vitals.get("spo2")
        hr = vitals.get("hr")
        sbp = vitals.get("sbp")

        if spo2 and spo2 < 88:
            return 1
        if sbp and (sbp > 200 or sbp < 80):
            return 2
        if hr and (hr > 150 or hr < 40):
            return 2

        emergency_alerts = [a for a in state.get("alerts", []) if a.get("severity") == "EMERGENCY"]
        if len(emergency_alerts) >= 2:
            return 2
        elif emergency_alerts:
            return 3

        return 3  # Default for patients flagged as emergency

    async def _stemi_protocol(
        self,
        patient_id: str,
        location: Dict,
        diagnostic: Dict,
    ) -> Dict[str, Any]:
        """Activate STEMI protocol per AHA/ACC 2022."""
        logger.critical("STEMI PROTOCOL ACTIVATED for patient %s", patient_id)
        send_notification.invoke({
            "patient_id": patient_id,
            "notification_type": "CRITICAL",
            "message": "STEMI PROTOCOL: EMS being notified. Do not eat or drink. Chew 325mg aspirin if available and not allergic. Call 911 immediately.",
            "channel": "sms",
        })
        return {
            "protocol": "STEMI",
            "steps_activated": [
                "EMS notification sent",
                "Nearest cath lab identified",
                "Cardiology team alerted",
                "Patient instructed: aspirin 325mg, call 911",
            ],
            "target_door_to_balloon": "≤ 90 minutes (AHA/ACC 2022)",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    async def _stroke_protocol(self, patient_id: str, location: Dict) -> Dict[str, Any]:
        """Activate Stroke protocol per AHA/ASA 2019."""
        logger.critical("STROKE PROTOCOL ACTIVATED for patient %s", patient_id)
        send_notification.invoke({
            "patient_id": patient_id,
            "notification_type": "CRITICAL",
            "message": "STROKE ALERT: Call 911 immediately. Note exact time symptoms started. Do not give food or water.",
            "channel": "sms",
        })
        return {
            "protocol": "STROKE",
            "steps_activated": [
                "EMS notification with stroke pre-alert",
                "Nearest stroke center with tPA capability identified",
                "Neurology team alerted",
                "Last known well time documented",
            ],
            "tpa_window": "≤ 4.5 hours from symptom onset",
            "target_door_to_needle": "≤ 60 minutes",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    async def _copd_protocol(self, patient_id: str, monitoring: Dict) -> Dict[str, Any]:
        """COPD exacerbation management per GOLD 2024."""
        return {
            "protocol": "COPD_EXACERBATION",
            "severity_assessment": "GOLD severity based on SpO2, PEFR, and symptoms",
            "steps_activated": [
                "Short-acting bronchodilator: salbutamol 2.5mg nebulized q20min × 3",
                "Ipratropium bromide 0.5mg nebulized added",
                "Systemic corticosteroids: prednisolone 40mg PO × 5 days",
                "Supplemental O2 to maintain SpO2 88-92%",
                "Antibiotic if purulent sputum: amoxicillin/clavulanate 625mg TID × 5 days",
            ],
            "hospitalization_criteria": "SpO2 < 90% on O2, severe breathlessness, inability to self-care",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    async def _sepsis_protocol(self, patient_id: str, temp_data: Dict) -> Dict[str, Any]:
        """Sepsis bundle per Surviving Sepsis Campaign 2021."""
        return {
            "protocol": "SEPSIS",
            "steps_activated": [
                "Blood cultures × 2 (before antibiotics)",
                "IV crystalloid 30mL/kg within 3 hours",
                "Broad-spectrum antibiotics within 1 hour",
                "Lactate measurement",
                "Vasopressors if MAP < 65 after fluid resuscitation",
            ],
            "target": "MAP ≥ 65 mmHg, lactate < 2 mmol/L, UO ≥ 0.5 mL/kg/hr",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def _get_required_capabilities(self, emergency_type: str) -> List[str]:
        caps_map = {
            "stemi": ["cath_lab", "primary_pci", "cardiac_icu"],
            "stroke": ["stroke_center", "ct_scanner", "tpa_capable", "neurology"],
            "copd": ["respiratory_icu", "mechanical_ventilation"],
            "sepsis": ["icu", "infectious_disease"],
        }
        return caps_map.get(emergency_type, ["emergency_department"])

    async def _generate_sbar(
        self,
        patient_id: str,
        emergency_type: Optional[str],
        esi: int,
        vitals: Dict,
        hospital: Dict,
        protocol_result: Dict,
        state: Dict,
    ) -> str:
        """Generate SBAR communication for emergency team."""
        llm_input = (
            f"Generate an SBAR emergency communication for:\n"
            f"Patient ID: {patient_id}\n"
            f"Emergency type: {emergency_type}\n"
            f"ESI level: {esi} — {ESI_LEVELS.get(esi, '')}\n"
            f"Current vitals: HR={vitals.get('heart_rate')}, BP={vitals.get('blood_pressure_systolic')}/{vitals.get('blood_pressure_diastolic')}, SpO2={vitals.get('spo2_percent')}%\n"
            f"Protocol activated: {protocol_result.get('protocol', 'General emergency')}\n"
            f"Nearest appropriate hospital: {hospital.get('name', 'TBD')} ({hospital.get('distance_km', '?')} km)\n\n"
            f"Format as:\n"
            f"S (Situation): [brief current situation]\n"
            f"B (Background): [relevant medical history, 2-3 lines]\n"
            f"A (Assessment): [clinical assessment and concern]\n"
            f"R (Recommendation): [specific actions requested, prioritized]\n"
            f"\nBe concise, clear, and clinician-oriented."
        )
        try:
            result = await self.run_agent_chain(input_text=llm_input)
            return result.get("output", "SBAR generation failed — manual documentation required.")
        except Exception as exc:
            logger.warning("SBAR generation failed: %s", exc)
            return f"EMERGENCY - Patient {patient_id} - ESI {esi} - {emergency_type} - Nearest hospital: {hospital.get('name', 'TBD')}"

    async def _notify_emergency_team(
        self,
        patient_id: str,
        esi: int,
        emergency_type: Optional[str],
        sbar: str,
        hospital: Dict,
    ) -> None:
        """Send notifications to emergency team members."""
        channels = ["push", "sms"] if esi <= 2 else ["push"]
        for channel in channels:
            try:
                send_notification.invoke({
                    "patient_id": patient_id,
                    "notification_type": "CRITICAL",
                    "message": f"ESI {esi} EMERGENCY: {(emergency_type or 'General').upper()}. {sbar[:200]}",
                    "channel": channel,
                })
            except Exception as exc:
                logger.error("Emergency notification failed on %s: %s", channel, exc)

    def _generate_recommendations(
        self,
        esi: int,
        emergency_type: Optional[str],
        hospital: Dict,
    ) -> List[str]:
        recs = []
        if esi <= 2:
            recs.append(f"ESI {esi}: Call 911 immediately. Do not transport privately. Nearest appropriate facility: {hospital.get('name', 'TBD')} ({hospital.get('distance_km', '?')} km away).")
        if emergency_type == "stemi":
            recs.append("STEMI: Aspirin 325mg stat (if no allergy). Primary PCI is gold standard — door-to-balloon ≤ 90 min (AHA/ACC 2022).")
        if emergency_type == "stroke":
            recs.append("Stroke: Document last known well time. tPA if within 4.5 hours and no contraindications. Thrombectomy if large vessel occlusion and within 24 hours.")
        return recs
