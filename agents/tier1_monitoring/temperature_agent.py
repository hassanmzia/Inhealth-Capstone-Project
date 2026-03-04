"""
Agent 4 — Temperature / Infection Agent

Responsibilities:
  - Monitor body temperature from wearable FHIR Observations
  - Detect fever (> 38.0°C) and hypothermia (< 35.5°C)
  - Cross-reference with recent labs (WBC, CRP)
  - Infection risk assessment
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from base.agent import MCPAgent
from base.tools import query_fhir_database, send_notification, vector_search

logger = logging.getLogger("inhealth.agent.temperature")

# LOINC codes
LOINC_TEMP = "8310-5"       # Body temperature
LOINC_WBC = "6690-2"        # White blood cell count
LOINC_CRP = "1988-5"        # C-reactive protein
LOINC_PROCALCITONIN = "33959-8"

# Clinical thresholds
TEMP_HYPOTHERMIA_CRITICAL = 35.0   # °C
TEMP_HYPOTHERMIA = 35.5
TEMP_FEVER = 38.0
TEMP_HIGH_FEVER = 39.5
TEMP_CRITICAL = 41.0

# Lab thresholds
WBC_HIGH = 11.0   # × 10^9/L
WBC_LOW = 4.0
CRP_ELEVATED = 10.0  # mg/L
CRP_HIGH = 100.0


class TemperatureAgent(MCPAgent):
    """Agent 4: Temperature monitoring and infection risk assessment."""

    agent_id = 4
    agent_name = "temperature_agent"
    agent_tier = "tier1_monitoring"
    system_prompt = (
        "You are the Temperature and Infection Risk AI Agent for InHealth Chronic Care. "
        "You monitor body temperature and cross-reference with laboratory markers (WBC, CRP, procalcitonin) "
        "to assess infection risk. Flag fever and hypothermia. Consider immunocompromised states. "
        "Reference Surviving Sepsis Campaign 2021 guidelines and IDSA fever management guidelines."
    )

    def _default_tools(self):
        return [query_fhir_database, vector_search, send_notification]

    async def analyze(
        self,
        patient_id: str,
        state: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:

        temp_data = query_fhir_database.invoke({
            "resource_type": "Observation",
            "patient_id": patient_id,
            "filters": {"code": LOINC_TEMP, "limit": 12},
        })
        wbc_data = query_fhir_database.invoke({
            "resource_type": "Observation",
            "patient_id": patient_id,
            "filters": {"code": LOINC_WBC, "limit": 3},
        })
        crp_data = query_fhir_database.invoke({
            "resource_type": "Observation",
            "patient_id": patient_id,
            "filters": {"code": LOINC_CRP, "limit": 3},
        })

        temp_values = self._parse_values(temp_data.get("resources", []))
        wbc_values = self._parse_values(wbc_data.get("resources", []))
        crp_values = self._parse_values(crp_data.get("resources", []))

        current_temp = temp_values[0] if temp_values else None
        current_wbc = wbc_values[0] if wbc_values else None
        current_crp = crp_values[0] if crp_values else None

        alerts = []
        emergency_detected = False

        # Temperature checks
        if current_temp is not None:
            if current_temp >= TEMP_CRITICAL:
                emergency_detected = True
                alerts.append(self._build_alert(
                    severity="EMERGENCY",
                    message=f"HYPERPYREXIA: Temperature {current_temp:.1f}°C (>= {TEMP_CRITICAL}°C). Life-threatening. Immediate cooling and evaluation.",
                    patient_id=patient_id,
                    details={"temp_celsius": current_temp},
                ))
                send_notification.invoke({
                    "patient_id": patient_id,
                    "notification_type": "CRITICAL",
                    "message": f"EMERGENCY: Temperature critically elevated at {current_temp:.1f}°C. Call 911 immediately.",
                    "channel": "sms",
                })
            elif current_temp >= TEMP_HIGH_FEVER:
                alerts.append(self._build_alert(
                    severity="HIGH",
                    message=f"High fever: {current_temp:.1f}°C. Infectious etiology likely. Blood cultures and broad-spectrum coverage may be needed.",
                    patient_id=patient_id,
                    details={"temp_celsius": current_temp},
                ))
            elif current_temp >= TEMP_FEVER:
                alerts.append(self._build_alert(
                    severity="NORMAL",
                    message=f"Fever detected: {current_temp:.1f}°C (>= {TEMP_FEVER}°C). Monitor and evaluate source.",
                    patient_id=patient_id,
                    details={"temp_celsius": current_temp},
                ))
            elif current_temp <= TEMP_HYPOTHERMIA_CRITICAL:
                emergency_detected = True
                alerts.append(self._build_alert(
                    severity="EMERGENCY",
                    message=f"CRITICAL HYPOTHERMIA: Temperature {current_temp:.1f}°C (< {TEMP_HYPOTHERMIA_CRITICAL}°C). Risk of cardiac arrest.",
                    patient_id=patient_id,
                    details={"temp_celsius": current_temp},
                ))
            elif current_temp <= TEMP_HYPOTHERMIA:
                alerts.append(self._build_alert(
                    severity="HIGH",
                    message=f"Hypothermia: Temperature {current_temp:.1f}°C (< {TEMP_HYPOTHERMIA}°C). Warming measures required.",
                    patient_id=patient_id,
                    details={"temp_celsius": current_temp},
                ))

        # Infection risk from labs
        infection_risk = self._assess_infection_risk(
            temp=current_temp, wbc=current_wbc, crp=current_crp
        )

        if infection_risk["level"] in ("HIGH", "CRITICAL"):
            alerts.append(self._build_alert(
                severity="HIGH" if infection_risk["level"] == "HIGH" else "EMERGENCY",
                message=f"Infection risk {infection_risk['level']}: {infection_risk['rationale']}",
                patient_id=patient_id,
                details=infection_risk,
            ))

        # Sepsis screening (SIRS-like: fever + elevated WBC + CRP)
        sirs_criteria_met = self._check_sirs(
            temp=current_temp, wbc=current_wbc
        )
        if sirs_criteria_met >= 2:
            emergency_detected = True
            alerts.append(self._build_alert(
                severity="EMERGENCY",
                message=f"SEPSIS SCREEN POSITIVE: {sirs_criteria_met}/4 SIRS criteria met. Evaluate for sepsis (Surviving Sepsis Campaign 2021).",
                patient_id=patient_id,
                details={"sirs_criteria_count": sirs_criteria_met},
            ))

        # LLM analysis
        llm_input = (
            f"Patient {patient_id} temperature and infection markers:\n"
            f"  Temperature: {current_temp}°C\n"
            f"  WBC: {current_wbc} × 10^9/L (normal: 4.0-11.0)\n"
            f"  CRP: {current_crp} mg/L (normal: < 10 mg/L)\n"
            f"  SIRS criteria met: {sirs_criteria_met}/4\n"
            f"  Infection risk: {infection_risk}\n"
            f"\nProvide:\n"
            f"1. Most likely infectious source based on available data\n"
            f"2. Workup recommendations (blood cultures, imaging, additional labs)\n"
            f"3. Empiric treatment consideration (if appropriate)\n"
            f"4. Monitoring plan"
        )
        try:
            llm_result = await self.run_agent_chain(input_text=llm_input)
            clinical_assessment = llm_result.get("output", "")
        except Exception as exc:
            logger.warning("Temperature LLM analysis failed: %s", exc)
            clinical_assessment = ""

        return self._build_result(
            status="completed",
            findings={
                "temperature_celsius": current_temp,
                "temperature_fahrenheit": round(current_temp * 9 / 5 + 32, 1) if current_temp else None,
                "wbc": current_wbc,
                "crp_mgL": current_crp,
                "sirs_criteria_met": sirs_criteria_met,
                "infection_risk": infection_risk,
                "clinical_assessment": clinical_assessment,
            },
            alerts=alerts,
            recommendations=self._generate_recommendations(
                temp=current_temp, infection_risk=infection_risk, sirs=sirs_criteria_met
            ),
            emergency_detected=emergency_detected,
        )

    def _parse_values(self, resources: List[Dict[str, Any]]) -> List[float]:
        result = []
        for r in resources:
            try:
                v = float(r.get("value", 0))
                if v > 0:
                    result.append(v)
            except (ValueError, TypeError):
                continue
        return result

    def _assess_infection_risk(
        self,
        temp: Optional[float],
        wbc: Optional[float],
        crp: Optional[float],
    ) -> Dict[str, Any]:
        score = 0
        reasons = []

        if temp and temp >= TEMP_FEVER:
            score += 2
            reasons.append(f"Fever {temp:.1f}°C")
        if wbc and wbc > WBC_HIGH:
            score += 2
            reasons.append(f"Leukocytosis WBC {wbc:.1f}")
        elif wbc and wbc < WBC_LOW:
            score += 1
            reasons.append(f"Leukopenia WBC {wbc:.1f} (immunocompromised)")
        if crp and crp >= CRP_HIGH:
            score += 2
            reasons.append(f"Markedly elevated CRP {crp:.1f} mg/L")
        elif crp and crp >= CRP_ELEVATED:
            score += 1
            reasons.append(f"Elevated CRP {crp:.1f} mg/L")

        if score >= 4:
            level = "CRITICAL"
        elif score >= 2:
            level = "HIGH"
        elif score >= 1:
            level = "MEDIUM"
        else:
            level = "LOW"

        return {
            "level": level,
            "score": score,
            "rationale": "; ".join(reasons) if reasons else "No significant infection markers",
        }

    def _check_sirs(
        self,
        temp: Optional[float],
        wbc: Optional[float],
    ) -> int:
        """Count SIRS criteria (simplified; full SIRS requires HR, RR, PaCO2)."""
        count = 0
        if temp and (temp > 38.0 or temp < 36.0):
            count += 1
        if wbc and (wbc > 12.0 or wbc < 4.0):
            count += 1
        return count

    def _generate_recommendations(
        self,
        temp: Optional[float],
        infection_risk: Dict[str, Any],
        sirs: int,
    ) -> List[str]:
        recs = []
        if temp and temp >= TEMP_FEVER:
            recs.append("Fever management: Acetaminophen 650mg q6h PRN (avoid NSAIDs in CKD). Adequate hydration.")
            recs.append("Workup: Blood cultures x2, CBC, BMP, UA/UC, chest X-ray if respiratory symptoms.")
        if sirs >= 2:
            recs.append("SEPSIS BUNDLE: 30 mL/kg IV crystalloid within 3 hours. Broad-spectrum antibiotics within 1 hour of recognition. Serial lactate measurement (Surviving Sepsis Campaign 2021).")
        if infection_risk.get("level") in ("HIGH", "CRITICAL"):
            recs.append("Infectious disease consultation recommended. Consider procalcitonin-guided antibiotic therapy.")
        return recs
