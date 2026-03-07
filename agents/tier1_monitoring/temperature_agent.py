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

        # Fetch vitals AND patient clinical context in parallel
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

        # Fetch patient conditions, medications, allergies for safe recommendations
        conditions_data = query_fhir_database.invoke({
            "resource_type": "Condition",
            "patient_id": patient_id,
            "filters": {"status": "active", "limit": 30},
        })
        medications_data = query_fhir_database.invoke({
            "resource_type": "MedicationRequest",
            "patient_id": patient_id,
            "filters": {"status": "active", "limit": 30},
        })
        allergies_data = query_fhir_database.invoke({
            "resource_type": "AllergyIntolerance",
            "patient_id": patient_id,
            "filters": {"limit": 30},
        })
        # Fetch recent encounters and diagnostic reports for clinical context
        encounters_data = query_fhir_database.invoke({
            "resource_type": "Encounter",
            "patient_id": patient_id,
            "filters": {"limit": 5},
        })
        diagnostic_data = query_fhir_database.invoke({
            "resource_type": "DiagnosticReport",
            "patient_id": patient_id,
            "filters": {"limit": 10},
        })

        # Build patient clinical flags
        patient_clinical = self._build_clinical_flags(
            conditions_data.get("resources", []),
            medications_data.get("resources", []),
            allergies_data.get("resources", []),
        )

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

        # Build clinical context strings for LLM
        conditions_list = [r.get("display", "") for r in conditions_data.get("resources", []) if r.get("display")]
        medications_list = [r.get("display", "") for r in medications_data.get("resources", []) if r.get("display")]
        allergies_list = [r.get("display", "") for r in allergies_data.get("resources", []) if r.get("display")]
        recent_encounters_list = [
            f"{r.get('type_display', 'Visit')} ({r.get('period_start', 'unknown date')}): {r.get('reason_display', '')}"
            for r in encounters_data.get("resources", []) if r.get("type_display")
        ]
        recent_reports_list = [
            f"{r.get('display', 'Report')} ({r.get('effective_datetime', '')}): {r.get('conclusion', 'pending')}"
            for r in diagnostic_data.get("resources", []) if r.get("display")
        ]

        # LLM analysis — now includes full patient context
        llm_input = (
            f"Patient {patient_id} temperature and infection markers:\n"
            f"  Temperature: {current_temp}°C\n"
            f"  WBC: {current_wbc} × 10^9/L (normal: 4.0-11.0)\n"
            f"  CRP: {current_crp} mg/L (normal: < 10 mg/L)\n"
            f"  SIRS criteria met: {sirs_criteria_met}/4\n"
            f"  Infection risk: {infection_risk}\n"
            f"\nPatient clinical context:\n"
            f"  Active conditions: {', '.join(conditions_list) or 'None documented'}\n"
            f"  Active medications: {', '.join(medications_list) or 'None documented'}\n"
            f"  Allergies: {', '.join(allergies_list) or 'NKDA'}\n"
            f"  Clinical flags: CKD={patient_clinical['has_ckd']}, Liver disease={patient_clinical['has_liver_disease']}, "
            f"HF={patient_clinical['has_heart_failure']}, Immunocompromised={patient_clinical['is_immunocompromised']}, "
            f"On anticoagulants={patient_clinical['on_anticoagulants']}\n"
            f"\nRecent encounters:\n  {chr(10).join(recent_encounters_list[:3]) or 'None recent'}\n"
            f"\nRecent diagnostic reports:\n  {chr(10).join(recent_reports_list[:5]) or 'None recent'}\n"
            f"\nProvide:\n"
            f"1. Most likely infectious source based on available data and patient history\n"
            f"2. Workup recommendations (blood cultures, imaging, additional labs) — consider existing reports\n"
            f"3. Empiric treatment consideration — CHECK ALLERGIES AND CONTRAINDICATIONS before recommending any medication\n"
            f"4. Monitoring plan personalized to patient's comorbidities\n"
            f"5. Any contraindication warnings based on current medications and conditions"
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
                temp=current_temp, infection_risk=infection_risk, sirs=sirs_criteria_met,
                patient_clinical=patient_clinical,
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

    def _build_clinical_flags(
        self,
        conditions: List[Dict[str, Any]],
        medications: List[Dict[str, Any]],
        allergies: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Build patient-specific clinical flags for safe recommendation generation."""
        condition_texts = [
            (c.get("display", "") + " " + c.get("code", "")).lower() for c in conditions
        ]
        med_texts = [
            (m.get("display", "") + " " + m.get("medication_display", "")).lower() for m in medications
        ]
        allergy_texts = [
            (a.get("display", "") + " " + a.get("code", "")).lower() for a in allergies
        ]

        # Condition flags
        has_ckd = any(k in t for t in condition_texts for k in ["chronic kidney", "ckd", "renal failure", "n18"])
        has_liver_disease = any(k in t for t in condition_texts for k in ["cirrhosis", "hepatic", "liver disease", "k74", "k70"])
        has_heart_failure = any(k in t for t in condition_texts for k in ["heart failure", "chf", "i50", "cardiomyopathy"])
        has_copd = any(k in t for t in condition_texts for k in ["copd", "j44", "chronic obstructive"])
        has_asthma = any(k in t for t in condition_texts for k in ["asthma", "j45"])
        has_diabetes = any(k in t for t in condition_texts for k in ["diabetes", "e11", "e10"])
        is_immunocompromised = any(
            k in t for t in condition_texts
            for k in ["hiv", "immunodeficiency", "transplant", "leukemia", "lymphoma", "chemotherapy", "d84"]
        )

        # Medication flags
        anticoag_keywords = ["warfarin", "heparin", "enoxaparin", "rivaroxaban", "apixaban", "dabigatran", "edoxaban"]
        nsaid_keywords = ["ibuprofen", "naproxen", "diclofenac", "celecoxib", "meloxicam", "indomethacin", "ketorolac", "aspirin"]
        on_anticoagulants = any(k in t for t in med_texts for k in anticoag_keywords)
        on_nsaids = any(k in t for t in med_texts for k in nsaid_keywords)
        on_immunosuppressants = any(
            k in t for t in med_texts
            for k in ["methotrexate", "cyclosporine", "tacrolimus", "mycophenolate", "azathioprine", "prednisone", "dexamethasone"]
        )
        on_ace_inhibitors = any(k in t for t in med_texts for k in ["lisinopril", "enalapril", "ramipril", "captopril", "benazepril"])

        # Allergy flags
        nsaid_allergy = any(k in t for t in allergy_texts for k in nsaid_keywords + ["nsaid"])
        acetaminophen_allergy = any(k in t for t in allergy_texts for k in ["acetaminophen", "paracetamol", "tylenol"])
        penicillin_allergy = any(k in t for t in allergy_texts for k in ["penicillin", "amoxicillin", "ampicillin"])
        sulfa_allergy = any(k in t for t in allergy_texts for k in ["sulfa", "sulfamethoxazole", "trimethoprim"])
        aspirin_allergy = any("aspirin" in t for t in allergy_texts)

        return {
            "has_ckd": has_ckd,
            "has_liver_disease": has_liver_disease,
            "has_heart_failure": has_heart_failure,
            "has_copd": has_copd,
            "has_asthma": has_asthma,
            "has_diabetes": has_diabetes,
            "is_immunocompromised": is_immunocompromised or on_immunosuppressants,
            "on_anticoagulants": on_anticoagulants,
            "on_nsaids": on_nsaids,
            "on_ace_inhibitors": on_ace_inhibitors,
            "nsaid_allergy": nsaid_allergy,
            "acetaminophen_allergy": acetaminophen_allergy,
            "penicillin_allergy": penicillin_allergy,
            "sulfa_allergy": sulfa_allergy,
            "aspirin_allergy": aspirin_allergy,
        }

    def _generate_recommendations(
        self,
        temp: Optional[float],
        infection_risk: Dict[str, Any],
        sirs: int,
        patient_clinical: Optional[Dict[str, Any]] = None,
    ) -> List[str]:
        recs = []
        pc = patient_clinical or {}

        if temp and temp >= TEMP_FEVER:
            # Antipyretic recommendation — patient-aware
            if pc.get("acetaminophen_allergy"):
                if not pc.get("nsaid_allergy") and not pc.get("has_ckd") and not pc.get("on_anticoagulants"):
                    recs.append("Fever management: Ibuprofen 400mg q6h PRN (acetaminophen allergy documented). Adequate hydration.")
                else:
                    recs.append("Fever management: Physical cooling measures (cooling blanket, ice packs). Both acetaminophen and NSAIDs contraindicated for this patient. Adequate hydration.")
            elif pc.get("has_liver_disease"):
                recs.append("Fever management: Acetaminophen 500mg q8h PRN (REDUCED DOSE — liver disease). Max 2g/day. Avoid NSAIDs. Adequate hydration.")
            else:
                contraindications = []
                if pc.get("has_ckd"):
                    contraindications.append("CKD")
                if pc.get("on_anticoagulants"):
                    contraindications.append("anticoagulant therapy")
                if pc.get("nsaid_allergy"):
                    contraindications.append("NSAID allergy")
                nsaid_warning = f" AVOID NSAIDs ({', '.join(contraindications)})." if contraindications else " Avoid NSAIDs if CKD, GI risk, or anticoagulant use."
                recs.append(f"Fever management: Acetaminophen 650mg q6h PRN.{nsaid_warning} Adequate hydration.")

            recs.append("Workup: Blood cultures x2, CBC, BMP, UA/UC, chest X-ray if respiratory symptoms.")

            if pc.get("is_immunocompromised"):
                recs.append("IMMUNOCOMPROMISED PATIENT: Lower threshold for empiric antibiotics. Consider fungal and atypical infections. Infectious disease consultation strongly recommended.")

        if sirs >= 2:
            # Sepsis bundle — adjust fluid volume for heart failure
            if pc.get("has_heart_failure"):
                recs.append(
                    "SEPSIS BUNDLE (HF-ADAPTED): Cautious IV crystalloid 10-15 mL/kg (heart failure — avoid volume overload). "
                    "Reassess after each 250mL bolus. Monitor for pulmonary edema. "
                    "Broad-spectrum antibiotics within 1 hour. Serial lactate (Surviving Sepsis Campaign 2021)."
                )
            else:
                recs.append(
                    "SEPSIS BUNDLE: 30 mL/kg IV crystalloid within 3 hours. "
                    "Broad-spectrum antibiotics within 1 hour of recognition. "
                    "Serial lactate measurement (Surviving Sepsis Campaign 2021)."
                )
            # Antibiotic allergy awareness
            allergy_warnings = []
            if pc.get("penicillin_allergy"):
                allergy_warnings.append("PENICILLIN ALLERGY — avoid beta-lactams, use fluoroquinolone or aztreonam alternatives")
            if pc.get("sulfa_allergy"):
                allergy_warnings.append("SULFA ALLERGY — avoid TMP-SMX")
            if allergy_warnings:
                recs.append(f"ALLERGY ALERT for empiric antibiotics: {'; '.join(allergy_warnings)}.")
            if pc.get("has_ckd"):
                recs.append("RENAL DOSING REQUIRED: Adjust antibiotic doses for renal function (check eGFR). Avoid nephrotoxic agents (aminoglycosides, vancomycin requires level monitoring).")

        if infection_risk.get("level") in ("HIGH", "CRITICAL"):
            recs.append("Infectious disease consultation recommended. Consider procalcitonin-guided antibiotic therapy.")

        return recs
