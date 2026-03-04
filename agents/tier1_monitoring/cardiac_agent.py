"""
Agent 2 — Cardiac Monitoring Agent

Responsibilities:
  - Monitor HR, BP, SpO2 from wearable FHIR Observations
  - Detect: tachycardia, bradycardia, hypertensive crisis, low SpO2
  - Send CRITICAL A2A alert if BP > 180/120 or SpO2 < 88%
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from base.agent import MCPAgent
from base.tools import query_fhir_database, send_notification, vector_search

logger = logging.getLogger("inhealth.agent.cardiac")

# LOINC codes
LOINC_HR = "8867-4"       # Heart rate
LOINC_SBP = "8480-6"      # Systolic BP
LOINC_DBP = "8462-4"      # Diastolic BP
LOINC_SPO2 = "59408-5"    # SpO2

# Clinical thresholds
HR_TACHY = 100
HR_BRADY = 50
HR_CRITICAL_HIGH = 150
HR_CRITICAL_LOW = 40
SBP_HYPERTENSIVE_URGENCY = 180
DBP_HYPERTENSIVE_URGENCY = 120
SPO2_LOW = 92
SPO2_CRITICAL = 88


class CardiacAgent(MCPAgent):
    """Agent 2: Continuous cardiac vital sign monitoring."""

    agent_id = 2
    agent_name = "cardiac_agent"
    agent_tier = "tier1_monitoring"
    system_prompt = (
        "You are the Cardiac Monitoring AI Agent for InHealth Chronic Care. "
        "You monitor heart rate, blood pressure, and oxygen saturation from wearable devices. "
        "Detect arrhythmias, hypertensive crises, and hypoxemia. Flag CRITICAL values immediately. "
        "Reference ACC/AHA guidelines for hypertension and ESC guidelines for arrhythmia management."
    )

    def _default_tools(self):
        return [query_fhir_database, vector_search, send_notification]

    async def analyze(
        self,
        patient_id: str,
        state: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:

        # Fetch vital signs from FHIR
        hr_data = query_fhir_database.invoke({
            "resource_type": "Observation",
            "patient_id": patient_id,
            "filters": {"code": LOINC_HR, "limit": 12},
        })
        sbp_data = query_fhir_database.invoke({
            "resource_type": "Observation",
            "patient_id": patient_id,
            "filters": {"code": LOINC_SBP, "limit": 6},
        })
        dbp_data = query_fhir_database.invoke({
            "resource_type": "Observation",
            "patient_id": patient_id,
            "filters": {"code": LOINC_DBP, "limit": 6},
        })
        spo2_data = query_fhir_database.invoke({
            "resource_type": "Observation",
            "patient_id": patient_id,
            "filters": {"code": LOINC_SPO2, "limit": 6},
        })

        # Parse values
        hr_values = self._parse_numeric(hr_data.get("resources", []))
        sbp_values = self._parse_numeric(sbp_data.get("resources", []))
        dbp_values = self._parse_numeric(dbp_data.get("resources", []))
        spo2_values = self._parse_numeric(spo2_data.get("resources", []))

        current_hr = hr_values[0] if hr_values else None
        current_sbp = sbp_values[0] if sbp_values else None
        current_dbp = dbp_values[0] if dbp_values else None
        current_spo2 = spo2_values[0] if spo2_values else None

        alerts = []
        emergency_detected = False
        findings: Dict[str, Any] = {
            "heart_rate": current_hr,
            "blood_pressure_systolic": current_sbp,
            "blood_pressure_diastolic": current_dbp,
            "spo2_percent": current_spo2,
        }

        # ── HR checks ────────────────────────────────────────────────────────
        if current_hr is not None:
            if current_hr >= HR_CRITICAL_HIGH:
                emergency_detected = True
                alerts.append(self._build_alert(
                    severity="EMERGENCY",
                    message=f"CRITICAL TACHYCARDIA: HR {current_hr:.0f} bpm. Risk of hemodynamic compromise.",
                    patient_id=patient_id,
                    details={"hr": current_hr, "threshold": HR_CRITICAL_HIGH},
                ))
            elif current_hr >= HR_TACHY:
                alerts.append(self._build_alert(
                    severity="HIGH",
                    message=f"Tachycardia: HR {current_hr:.0f} bpm (> {HR_TACHY} bpm).",
                    patient_id=patient_id,
                    details={"hr": current_hr},
                ))
            elif current_hr <= HR_CRITICAL_LOW:
                emergency_detected = True
                alerts.append(self._build_alert(
                    severity="EMERGENCY",
                    message=f"CRITICAL BRADYCARDIA: HR {current_hr:.0f} bpm. Risk of syncope/arrest.",
                    patient_id=patient_id,
                    details={"hr": current_hr, "threshold": HR_CRITICAL_LOW},
                ))
            elif current_hr <= HR_BRADY:
                alerts.append(self._build_alert(
                    severity="HIGH",
                    message=f"Bradycardia: HR {current_hr:.0f} bpm (< {HR_BRADY} bpm).",
                    patient_id=patient_id,
                    details={"hr": current_hr},
                ))

        # ── BP checks ─────────────────────────────────────────────────────────
        if current_sbp is not None and current_dbp is not None:
            if current_sbp >= SBP_HYPERTENSIVE_URGENCY and current_dbp >= DBP_HYPERTENSIVE_URGENCY:
                emergency_detected = True
                alerts.append(self._build_alert(
                    severity="EMERGENCY",
                    message=(
                        f"HYPERTENSIVE CRISIS: BP {current_sbp:.0f}/{current_dbp:.0f} mmHg "
                        f"(>= {SBP_HYPERTENSIVE_URGENCY}/{DBP_HYPERTENSIVE_URGENCY}). "
                        "Assess for end-organ damage (ACC/AHA 2017)."
                    ),
                    patient_id=patient_id,
                    details={"sbp": current_sbp, "dbp": current_dbp},
                ))
                send_notification.invoke({
                    "patient_id": patient_id,
                    "notification_type": "CRITICAL",
                    "message": f"EMERGENCY: Blood pressure critically elevated at {current_sbp:.0f}/{current_dbp:.0f} mmHg. Seek immediate emergency care.",
                    "channel": "sms",
                })
            elif current_sbp >= 160 or current_dbp >= 100:
                alerts.append(self._build_alert(
                    severity="HIGH",
                    message=f"Stage 2 Hypertension: BP {current_sbp:.0f}/{current_dbp:.0f} mmHg. Medication review needed.",
                    patient_id=patient_id,
                    details={"sbp": current_sbp, "dbp": current_dbp},
                ))
            elif current_sbp < 90 or current_dbp < 60:
                alerts.append(self._build_alert(
                    severity="HIGH",
                    message=f"Hypotension: BP {current_sbp:.0f}/{current_dbp:.0f} mmHg. Evaluate for orthostatic hypotension or volume depletion.",
                    patient_id=patient_id,
                    details={"sbp": current_sbp, "dbp": current_dbp},
                ))

        # ── SpO2 checks ────────────────────────────────────────────────────────
        if current_spo2 is not None:
            if current_spo2 < SPO2_CRITICAL:
                emergency_detected = True
                alerts.append(self._build_alert(
                    severity="EMERGENCY",
                    message=f"CRITICAL HYPOXEMIA: SpO2 {current_spo2:.1f}% (< {SPO2_CRITICAL}%). Immediate oxygen therapy required.",
                    patient_id=patient_id,
                    details={"spo2": current_spo2, "threshold": SPO2_CRITICAL},
                ))
                send_notification.invoke({
                    "patient_id": patient_id,
                    "notification_type": "CRITICAL",
                    "message": f"EMERGENCY: Oxygen saturation critically low at {current_spo2:.1f}%. Call 911 immediately.",
                    "channel": "sms",
                })
            elif current_spo2 < SPO2_LOW:
                alerts.append(self._build_alert(
                    severity="HIGH",
                    message=f"Low SpO2: {current_spo2:.1f}% (< {SPO2_LOW}%). Assess for respiratory distress.",
                    patient_id=patient_id,
                    details={"spo2": current_spo2},
                ))

        # ── HR trend analysis ────────────────────────────────────────────────
        hr_trend = self._analyze_trend(hr_values)
        findings["hr_trend"] = hr_trend

        # ── LLM narrative ────────────────────────────────────────────────────
        if current_hr or current_sbp or current_spo2:
            llm_input = (
                f"Cardiac vital signs for patient {patient_id}:\n"
                f"  Heart rate: {current_hr} bpm (trend: {hr_trend})\n"
                f"  Blood pressure: {current_sbp}/{current_dbp} mmHg\n"
                f"  SpO2: {current_spo2}%\n"
                f"  Alerts generated: {len(alerts)}\n"
                f"\nProvide a brief clinical assessment and ACC/AHA-based recommendations."
            )
            try:
                llm_result = await self.run_agent_chain(input_text=llm_input)
                findings["clinical_narrative"] = llm_result.get("output", "")
            except Exception as exc:
                logger.warning("LLM narrative failed: %s", exc)

        recommendations = self._generate_recommendations(
            hr=current_hr, sbp=current_sbp, dbp=current_dbp, spo2=current_spo2
        )

        return self._build_result(
            status="completed",
            findings=findings,
            alerts=alerts,
            recommendations=recommendations,
            emergency_detected=emergency_detected,
        )

    def _parse_numeric(self, resources: List[Dict[str, Any]]) -> List[float]:
        values = []
        for r in resources:
            try:
                v = float(r.get("value", 0))
                if v > 0:
                    values.append(v)
            except (ValueError, TypeError):
                continue
        return values

    def _analyze_trend(self, values: List[float]) -> str:
        if len(values) < 3:
            return "insufficient_data"
        recent_avg = sum(values[:3]) / 3
        older_avg = sum(values[-3:]) / 3
        delta = recent_avg - older_avg
        if delta > 10:
            return "increasing"
        elif delta < -10:
            return "decreasing"
        return "stable"

    def _generate_recommendations(
        self,
        hr: Optional[float],
        sbp: Optional[float],
        dbp: Optional[float],
        spo2: Optional[float],
    ) -> List[str]:
        recs = []
        if hr and hr >= HR_TACHY:
            recs.append("Investigate cause of tachycardia: fever, dehydration, anemia, arrhythmia, medication effect. 12-lead ECG if sustained.")
        if hr and hr <= HR_BRADY:
            recs.append("Evaluate bradycardia: check medications (beta-blockers, digoxin), thyroid function. Cardiology referral if symptomatic.")
        if sbp and sbp >= SBP_HYPERTENSIVE_URGENCY:
            recs.append("Hypertensive urgency/emergency: assess end-organ damage (creatinine, troponin, fundoscopy). Urgent antihypertensive therapy per ACC/AHA 2017.")
        if spo2 and spo2 < SPO2_LOW:
            recs.append("Supplemental oxygen to maintain SpO2 ≥ 92%. Evaluate for COPD exacerbation, heart failure, or pulmonary embolism.")
        return recs
