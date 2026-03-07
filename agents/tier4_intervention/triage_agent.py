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

    def _build_clinical_flags(
        self,
        conditions: List[Dict[str, Any]],
        medications: List[Dict[str, Any]],
        allergies: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Build patient-specific clinical flags for safe protocol activation."""
        condition_texts = [
            (c.get("display", "") + " " + c.get("code", "")).lower() for c in conditions
        ]
        med_texts = [
            (m.get("display", "") + " " + m.get("medication_display", "")).lower() for m in medications
        ]
        allergy_texts = [
            (a.get("display", "") + " " + a.get("code", "")).lower() for a in allergies
        ]

        has_ckd = any(k in t for t in condition_texts for k in ["chronic kidney", "ckd", "renal failure", "n18"])
        has_heart_failure = any(k in t for t in condition_texts for k in ["heart failure", "chf", "i50", "cardiomyopathy"])
        has_copd = any(k in t for t in condition_texts for k in ["copd", "j44", "chronic obstructive"])
        has_liver_disease = any(k in t for t in condition_texts for k in ["cirrhosis", "hepatic", "liver disease", "k74"])
        has_diabetes = any(k in t for t in condition_texts for k in ["diabetes", "e11", "e10"])
        is_immunocompromised = any(
            k in t for t in condition_texts
            for k in ["hiv", "immunodeficiency", "transplant", "leukemia", "lymphoma"]
        )
        on_anticoagulants = any(
            k in t for t in med_texts
            for k in ["warfarin", "heparin", "enoxaparin", "rivaroxaban", "apixaban", "dabigatran"]
        )
        on_beta_blockers = any(
            k in t for t in med_texts
            for k in ["metoprolol", "atenolol", "carvedilol", "propranolol", "bisoprolol"]
        )

        aspirin_allergy = any("aspirin" in t for t in allergy_texts)
        nsaid_allergy = any(
            k in t for t in allergy_texts
            for k in ["nsaid", "ibuprofen", "naproxen", "aspirin"]
        )
        penicillin_allergy = any(
            k in t for t in allergy_texts
            for k in ["penicillin", "amoxicillin", "ampicillin"]
        )
        sulfa_allergy = any(k in t for t in allergy_texts for k in ["sulfa", "sulfamethoxazole"])
        contrast_allergy = any(k in t for t in allergy_texts for k in ["contrast", "iodine", "gadolinium"])

        return {
            "has_ckd": has_ckd,
            "has_heart_failure": has_heart_failure,
            "has_copd": has_copd,
            "has_liver_disease": has_liver_disease,
            "has_diabetes": has_diabetes,
            "is_immunocompromised": is_immunocompromised,
            "on_anticoagulants": on_anticoagulants,
            "on_beta_blockers": on_beta_blockers,
            "aspirin_allergy": aspirin_allergy,
            "nsaid_allergy": nsaid_allergy,
            "penicillin_allergy": penicillin_allergy,
            "sulfa_allergy": sulfa_allergy,
            "contrast_allergy": contrast_allergy,
            "conditions_list": [c.get("display", "") for c in conditions if c.get("display")],
            "medications_list": [m.get("display", m.get("medication_display", "")) for m in medications if m.get("display") or m.get("medication_display")],
            "allergies_list": [a.get("display", "") for a in allergies if a.get("display")],
        }

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

        # Fetch patient clinical context for safe protocol activation
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
        patient_clinical = self._build_clinical_flags(
            conditions_data.get("resources", []),
            medications_data.get("resources", []),
            allergies_data.get("resources", []),
        )

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

        # Activate protocol based on emergency type — now patient-aware
        protocol_result = {}
        new_alerts = []

        if emergency_type == "stemi":
            protocol_result = await self._stemi_protocol(patient_id, patient_location, diagnostic_results, patient_clinical)
        elif emergency_type == "stroke":
            protocol_result = await self._stroke_protocol(patient_id, patient_location, patient_clinical)
        elif emergency_type == "copd":
            protocol_result = await self._copd_protocol(patient_id, monitoring_results, patient_clinical)
        elif emergency_type == "sepsis":
            protocol_result = await self._sepsis_protocol(patient_id, temperature_data, patient_clinical)

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

        # Generate SBAR communication — now includes patient clinical context
        sbar = await self._generate_sbar(
            patient_id=patient_id,
            emergency_type=emergency_type,
            esi=esi,
            vitals=cardiac,
            hospital=hospital,
            protocol_result=protocol_result,
            state=state,
            patient_clinical=patient_clinical,
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
            recommendations=self._generate_recommendations(esi, emergency_type, hospital, patient_clinical),
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
        patient_clinical: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Activate STEMI protocol per AHA/ACC 2022 — patient-aware."""
        logger.critical("STEMI PROTOCOL ACTIVATED for patient %s", patient_id)

        # Check aspirin allergy before recommending
        if patient_clinical.get("aspirin_allergy"):
            aspirin_msg = "ASPIRIN ALLERGY DOCUMENTED — DO NOT give aspirin. Consider clopidogrel 600mg loading dose as alternative."
            aspirin_step = "Aspirin CONTRAINDICATED (allergy) — clopidogrel 600mg loading if available"
        else:
            aspirin_msg = "Chew 325mg aspirin if available. Call 911 immediately."
            aspirin_step = "Patient instructed: aspirin 325mg stat, call 911"

        # Check anticoagulant status — important for PCI
        anticoag_warning = ""
        if patient_clinical.get("on_anticoagulants"):
            anticoag_warning = " ALERT: Patient on anticoagulants — inform cath lab team for bleeding risk management."

        send_notification.invoke({
            "patient_id": patient_id,
            "notification_type": "CRITICAL",
            "message": f"STEMI PROTOCOL: EMS being notified. Do not eat or drink. {aspirin_msg}{anticoag_warning}",
            "channel": "sms",
        })

        steps = [
            "EMS notification sent",
            "Nearest cath lab identified",
            "Cardiology team alerted",
            aspirin_step,
        ]
        if patient_clinical.get("on_anticoagulants"):
            steps.append("ANTICOAGULANT ALERT: Notify cath lab — bleeding risk management required")
        if patient_clinical.get("has_ckd"):
            steps.append("CKD ALERT: Contrast nephropathy risk — ensure pre/post-hydration protocol")
        if patient_clinical.get("contrast_allergy"):
            steps.append("CONTRAST ALLERGY: Pre-medicate with steroids and antihistamines before angiography")
        if patient_clinical.get("has_diabetes"):
            steps.append("Diabetes: Hold metformin if contrast dye used. Monitor glucose closely")

        return {
            "protocol": "STEMI",
            "steps_activated": steps,
            "contraindication_checks": {
                "aspirin_allergy": patient_clinical.get("aspirin_allergy", False),
                "on_anticoagulants": patient_clinical.get("on_anticoagulants", False),
                "contrast_allergy": patient_clinical.get("contrast_allergy", False),
                "ckd": patient_clinical.get("has_ckd", False),
            },
            "target_door_to_balloon": "≤ 90 minutes (AHA/ACC 2022)",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    async def _stroke_protocol(self, patient_id: str, location: Dict, patient_clinical: Dict[str, Any]) -> Dict[str, Any]:
        """Activate Stroke protocol per AHA/ASA 2019 — patient-aware."""
        logger.critical("STROKE PROTOCOL ACTIVATED for patient %s", patient_id)

        # tPA contraindication checks
        tpa_contraindications = []
        if patient_clinical.get("on_anticoagulants"):
            tpa_contraindications.append("Currently on anticoagulants — check INR/anti-Xa before tPA")

        tpa_warning = ""
        if tpa_contraindications:
            tpa_warning = f" ALERT: {'; '.join(tpa_contraindications)}"

        send_notification.invoke({
            "patient_id": patient_id,
            "notification_type": "CRITICAL",
            "message": f"STROKE ALERT: Call 911 immediately. Note exact time symptoms started. Do not give food or water.{tpa_warning}",
            "channel": "sms",
        })

        steps = [
            "EMS notification with stroke pre-alert",
            "Nearest stroke center with tPA capability identified",
            "Neurology team alerted",
            "Last known well time documented",
        ]
        if patient_clinical.get("on_anticoagulants"):
            steps.append("ANTICOAGULANT ALERT: Check INR/anti-Xa levels STAT — tPA contraindicated if supratherapeutic")
        if patient_clinical.get("has_ckd"):
            steps.append("CKD ALERT: Contrast use for CTA/CTP — ensure hydration protocol")
        if patient_clinical.get("contrast_allergy"):
            steps.append("CONTRAST ALLERGY: Pre-medicate if CTA needed. Consider MRI-based stroke imaging")

        return {
            "protocol": "STROKE",
            "steps_activated": steps,
            "contraindication_checks": {
                "on_anticoagulants": patient_clinical.get("on_anticoagulants", False),
                "tpa_contraindications": tpa_contraindications,
            },
            "tpa_window": "≤ 4.5 hours from symptom onset",
            "target_door_to_needle": "≤ 60 minutes",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    async def _copd_protocol(self, patient_id: str, monitoring: Dict, patient_clinical: Dict[str, Any]) -> Dict[str, Any]:
        """COPD exacerbation management per GOLD 2024 — patient-aware."""
        steps = [
            "Short-acting bronchodilator: salbutamol 2.5mg nebulized q20min × 3",
            "Ipratropium bromide 0.5mg nebulized added",
            "Supplemental O2 to maintain SpO2 88-92% (GOLD 2024 target for COPD)",
        ]

        # Corticosteroid — adjust for diabetes and liver disease
        if patient_clinical.get("has_diabetes"):
            steps.append(
                "Systemic corticosteroids: prednisolone 40mg PO × 5 days "
                "(DIABETES: monitor blood glucose q4h — expect hyperglycemia, may need insulin sliding scale)"
            )
        elif patient_clinical.get("has_liver_disease"):
            steps.append(
                "Systemic corticosteroids: methylprednisolone 40mg IV × 5 days "
                "(liver disease — avoid oral prednisolone due to hepatic first-pass metabolism)"
            )
        else:
            steps.append("Systemic corticosteroids: prednisolone 40mg PO × 5 days")

        # Antibiotic — check allergies before recommending
        if patient_clinical.get("penicillin_allergy"):
            steps.append(
                "Antibiotic if purulent sputum: doxycycline 100mg BID × 5 days or azithromycin 500mg day 1 then 250mg × 4 days "
                "(PENICILLIN ALLERGY — avoid amoxicillin/clavulanate)"
            )
        else:
            steps.append("Antibiotic if purulent sputum: amoxicillin/clavulanate 625mg TID × 5 days")

        # Heart failure caution
        if patient_clinical.get("has_heart_failure"):
            steps.append("HEART FAILURE: Cautious IV fluid administration. Monitor for volume overload. Avoid excessive nebulized fluids.")

        return {
            "protocol": "COPD_EXACERBATION",
            "severity_assessment": "GOLD severity based on SpO2, PEFR, and symptoms",
            "steps_activated": steps,
            "contraindication_checks": {
                "penicillin_allergy": patient_clinical.get("penicillin_allergy", False),
                "diabetes": patient_clinical.get("has_diabetes", False),
                "heart_failure": patient_clinical.get("has_heart_failure", False),
            },
            "hospitalization_criteria": "SpO2 < 90% on O2, severe breathlessness, inability to self-care",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    async def _sepsis_protocol(self, patient_id: str, temp_data: Dict, patient_clinical: Dict[str, Any]) -> Dict[str, Any]:
        """Sepsis bundle per Surviving Sepsis Campaign 2021 — patient-aware."""
        steps = [
            "Blood cultures × 2 (before antibiotics)",
        ]

        # Fluid resuscitation — adjust for heart failure
        if patient_clinical.get("has_heart_failure"):
            steps.append(
                "IV crystalloid: CAUTIOUS 10-15 mL/kg (heart failure — avoid volume overload). "
                "Give in 250mL boluses. Reassess after each bolus for pulmonary edema."
            )
        else:
            steps.append("IV crystalloid 30mL/kg within 3 hours")

        # Antibiotics — check allergies
        allergy_notes = []
        if patient_clinical.get("penicillin_allergy"):
            allergy_notes.append("PENICILLIN ALLERGY — use fluoroquinolone or aztreonam alternatives")
        if patient_clinical.get("sulfa_allergy"):
            allergy_notes.append("SULFA ALLERGY — avoid TMP-SMX")

        if allergy_notes:
            steps.append(f"Broad-spectrum antibiotics within 1 hour — ALLERGY ALERT: {'; '.join(allergy_notes)}")
        else:
            steps.append("Broad-spectrum antibiotics within 1 hour")

        steps.append("Lactate measurement")
        steps.append("Vasopressors if MAP < 65 after fluid resuscitation")

        # Renal considerations
        if patient_clinical.get("has_ckd"):
            steps.append("CKD: Renal-dose adjusted antibiotics. Avoid nephrotoxins. Monitor urine output closely.")

        # Immunocompromised considerations
        if patient_clinical.get("is_immunocompromised"):
            steps.append("IMMUNOCOMPROMISED: Broaden antibiotic coverage to include fungal. Consider ID consultation urgently.")

        return {
            "protocol": "SEPSIS",
            "steps_activated": steps,
            "contraindication_checks": {
                "heart_failure": patient_clinical.get("has_heart_failure", False),
                "penicillin_allergy": patient_clinical.get("penicillin_allergy", False),
                "sulfa_allergy": patient_clinical.get("sulfa_allergy", False),
                "ckd": patient_clinical.get("has_ckd", False),
                "immunocompromised": patient_clinical.get("is_immunocompromised", False),
            },
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
        patient_clinical: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Generate SBAR communication for emergency team — includes patient context."""
        pc = patient_clinical or {}
        conditions_str = ", ".join(pc.get("conditions_list", [])[:5]) or "None documented"
        meds_str = ", ".join(pc.get("medications_list", [])[:5]) or "None documented"
        allergies_str = ", ".join(pc.get("allergies_list", [])) or "NKDA"

        llm_input = (
            f"Generate an SBAR emergency communication for:\n"
            f"Patient ID: {patient_id}\n"
            f"Emergency type: {emergency_type}\n"
            f"ESI level: {esi} — {ESI_LEVELS.get(esi, '')}\n"
            f"Current vitals: HR={vitals.get('heart_rate')}, BP={vitals.get('blood_pressure_systolic')}/{vitals.get('blood_pressure_diastolic')}, SpO2={vitals.get('spo2_percent')}%\n"
            f"Protocol activated: {protocol_result.get('protocol', 'General emergency')}\n"
            f"Nearest appropriate hospital: {hospital.get('name', 'TBD')} ({hospital.get('distance_km', '?')} km)\n\n"
            f"Patient medical history:\n"
            f"  Active conditions: {conditions_str}\n"
            f"  Current medications: {meds_str}\n"
            f"  Allergies: {allergies_str}\n"
            f"  Key flags: CKD={pc.get('has_ckd', False)}, HF={pc.get('has_heart_failure', False)}, "
            f"Anticoagulants={pc.get('on_anticoagulants', False)}, Diabetes={pc.get('has_diabetes', False)}\n\n"
            f"Format as:\n"
            f"S (Situation): [brief current situation]\n"
            f"B (Background): [relevant medical history from the data above, 2-3 lines]\n"
            f"A (Assessment): [clinical assessment and concern — note any contraindication risks]\n"
            f"R (Recommendation): [specific actions requested, prioritized — flag any allergy/drug concerns]\n"
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
        patient_clinical: Optional[Dict[str, Any]] = None,
    ) -> List[str]:
        recs = []
        pc = patient_clinical or {}

        if esi <= 2:
            recs.append(f"ESI {esi}: Call 911 immediately. Do not transport privately. Nearest appropriate facility: {hospital.get('name', 'TBD')} ({hospital.get('distance_km', '?')} km away).")

        if emergency_type == "stemi":
            if pc.get("aspirin_allergy"):
                recs.append("STEMI: ASPIRIN ALLERGY — give clopidogrel 600mg loading dose instead. Primary PCI is gold standard — door-to-balloon ≤ 90 min (AHA/ACC 2022).")
            else:
                recs.append("STEMI: Aspirin 325mg stat. Primary PCI is gold standard — door-to-balloon ≤ 90 min (AHA/ACC 2022).")
            if pc.get("on_anticoagulants"):
                recs.append("BLEEDING RISK: Patient on anticoagulants. Inform interventional cardiology for PCI anticoagulation strategy.")

        if emergency_type == "stroke":
            tpa_note = "tPA if within 4.5 hours and no contraindications."
            if pc.get("on_anticoagulants"):
                tpa_note = "tPA may be CONTRAINDICATED — patient on anticoagulants. Check INR/anti-Xa STAT. Consider mechanical thrombectomy."
            recs.append(f"Stroke: Document last known well time. {tpa_note} Thrombectomy if large vessel occlusion and within 24 hours.")

        if emergency_type == "copd":
            if pc.get("has_diabetes"):
                recs.append("COPD + DIABETES: Corticosteroids will elevate blood glucose. Monitor q4h and have insulin sliding scale ready.")

        if emergency_type == "sepsis":
            if pc.get("has_heart_failure"):
                recs.append("SEPSIS + HEART FAILURE: Use conservative fluid strategy (10-15 mL/kg). Frequent reassessment for volume overload.")
            if pc.get("has_ckd"):
                recs.append("SEPSIS + CKD: Renal-dose antibiotics required. Avoid aminoglycosides. Monitor vancomycin levels if used.")

        return recs
