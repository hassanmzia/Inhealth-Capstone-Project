"""
Agent 5 — ECG Analysis Agent

Responsibilities:
  - Analyze ECG FHIR DiagnosticReport resources
  - Detect: ST elevation (STEMI pattern), ST depression, T-wave changes, QT prolongation, AFib
  - Trigger STEMI emergency protocol via A2A if detected
  - Explainable output: which ECG features triggered detection
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

from base.agent import MCPAgent
from base.tools import (
    find_nearest_hospital,
    query_fhir_database,
    send_notification,
    vector_search,
)

logger = logging.getLogger("inhealth.agent.ecg")

# LOINC / SNOMED codes for ECG
LOINC_ECG_REPORT = "11524-6"          # ECG study
SNOMED_STEMI = "57054005"
SNOMED_AFIB = "49436004"

# ECG thresholds
QTC_PROLONGED_MS = 470     # ms (men: >450, women: >470 — using conservative)
ST_ELEVATION_MV = 0.1      # mV in ≥2 contiguous leads
QRS_WIDE_MS = 120          # Wide QRS


class ECGAgent(MCPAgent):
    """Agent 5: ECG analysis and critical cardiac event detection."""

    agent_id = 5
    agent_name = "ecg_agent"
    agent_tier = "tier2_diagnostic"
    system_prompt = (
        "You are the ECG Analysis AI Agent for InHealth Chronic Care. "
        "You analyze ECG reports to detect STEMI, NSTEMI, AFib, QT prolongation, "
        "and other critical arrhythmias. Provide explainable findings specifying which "
        "ECG features triggered each detection. Reference AHA/ACC STEMI guidelines 2022 "
        "and ESC AFib guidelines 2023. Flag STEMI as EMERGENCY immediately."
    )

    def _default_tools(self):
        return [query_fhir_database, vector_search, send_notification, find_nearest_hospital]

    async def analyze(
        self,
        patient_id: str,
        state: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:

        # Fetch ECG diagnostic reports from FHIR
        ecg_data = query_fhir_database.invoke({
            "resource_type": "DiagnosticReport",
            "patient_id": patient_id,
            "filters": {"code": LOINC_ECG_REPORT, "limit": 5},
        })

        reports = ecg_data.get("resources", [])
        if not reports:
            return self._build_result(
                status="no_data",
                findings={"message": "No ECG reports found"},
            )

        latest_report = reports[0]
        report_text = self._extract_report_text(latest_report)

        # NLP-based ECG feature extraction
        ecg_features = self._extract_ecg_features(report_text)

        alerts = []
        emergency_detected = False
        critical_findings = []

        # ── STEMI detection ────────────────────────────────────────────────
        if ecg_features.get("st_elevation"):
            emergency_detected = True
            stemi_details = ecg_features["st_elevation"]
            critical_findings.append("STEMI pattern")

            alerts.append(self._build_alert(
                severity="EMERGENCY",
                message=(
                    f"STEMI DETECTED: ST elevation in leads {stemi_details.get('leads', [])}. "
                    "Activate STEMI protocol. Target door-to-balloon ≤ 90 minutes (AHA/ACC 2022)."
                ),
                patient_id=patient_id,
                details=stemi_details,
            ))

            # Trigger STEMI protocol
            await self._stemi_protocol(patient_id, context, stemi_details)

        # ── ST depression / NSTEMI ─────────────────────────────────────────
        elif ecg_features.get("st_depression"):
            critical_findings.append("ST depression (possible NSTEMI/UA)")
            alerts.append(self._build_alert(
                severity="HIGH",
                message=f"ST depression detected in leads {ecg_features['st_depression'].get('leads', [])}. Possible NSTEMI/UA. Serial troponins required.",
                patient_id=patient_id,
                details=ecg_features["st_depression"],
            ))

        # ── AFib detection ─────────────────────────────────────────────────
        if ecg_features.get("afib"):
            critical_findings.append("Atrial Fibrillation")
            alerts.append(self._build_alert(
                severity="HIGH",
                message="Atrial Fibrillation detected. Calculate CHA2DS2-VASc score. Rate/rhythm control and anticoagulation per ESC 2023.",
                patient_id=patient_id,
                details={"rhythm": "afib", "features": ecg_features["afib"]},
            ))

        # ── QT prolongation ────────────────────────────────────────────────
        if ecg_features.get("qt_prolonged"):
            qt_ms = ecg_features["qt_prolonged"].get("qtc_ms", 0)
            severity = "EMERGENCY" if qt_ms > 500 else "HIGH"
            if qt_ms > 500:
                emergency_detected = True
                critical_findings.append("Critical QTc prolongation (>500ms)")
            alerts.append(self._build_alert(
                severity=severity,
                message=(
                    f"QTc prolongation: {qt_ms}ms (threshold: {QTC_PROLONGED_MS}ms). "
                    "Risk of Torsades de Pointes. Review QT-prolonging medications."
                ),
                patient_id=patient_id,
                details=ecg_features["qt_prolonged"],
            ))

        # ── T-wave changes ─────────────────────────────────────────────────
        if ecg_features.get("t_wave_changes"):
            alerts.append(self._build_alert(
                severity="NORMAL",
                message=f"T-wave abnormalities: {ecg_features['t_wave_changes'].get('description', '')}. Correlate with clinical presentation.",
                patient_id=patient_id,
                details=ecg_features["t_wave_changes"],
            ))

        # ── LLM explainability ────────────────────────────────────────────
        llm_input = (
            f"ECG report for patient {patient_id}:\n\n{report_text}\n\n"
            f"Extracted features: {ecg_features}\n"
            f"Critical findings: {critical_findings}\n\n"
            f"Provide:\n"
            f"1. Detailed ECG interpretation with lead-by-lead analysis\n"
            f"2. Specific ECG criteria that triggered each finding (explainability)\n"
            f"3. Differential diagnosis ranked by probability\n"
            f"4. Immediate management steps per AHA/ACC/ESC guidelines\n"
            f"5. Additional workup needed (labs, imaging, cardiology consult)"
        )

        try:
            llm_result = await self.run_agent_chain(input_text=llm_input)
            ecg_interpretation = llm_result.get("output", "")
        except Exception as exc:
            logger.warning("ECG LLM interpretation failed: %s", exc)
            ecg_interpretation = ""

        return self._build_result(
            status="completed",
            findings={
                "report_id": latest_report.get("id", ""),
                "ecg_features": ecg_features,
                "critical_findings": critical_findings,
                "ecg_interpretation": ecg_interpretation,
                "report_date": latest_report.get("effective_datetime", ""),
            },
            alerts=alerts,
            recommendations=self._generate_recommendations(ecg_features, critical_findings),
            emergency_detected=emergency_detected,
        )

    def _extract_report_text(self, report: Dict[str, Any]) -> str:
        """Extract text content from a FHIR DiagnosticReport."""
        meta = report.get("meta", {})
        if isinstance(meta, dict):
            return meta.get("text", report.get("value", ""))
        return report.get("value", "")

    def _extract_ecg_features(self, text: str) -> Dict[str, Any]:
        """Rule-based + regex ECG feature extraction from report text."""
        text_lower = text.lower()
        features: Dict[str, Any] = {}

        # ST elevation patterns
        st_elev_patterns = [
            r"st[\s-]*elevation",
            r"st[\s-]*segment[\s-]*elevation",
            r"stemi",
            r"acute[\s-]*mi",
            r"current[\s-]*of[\s-]*injury",
        ]
        if any(re.search(p, text_lower) for p in st_elev_patterns):
            # Try to extract affected leads
            lead_match = re.findall(r"\b(I{1,3}|a[VF]{1,2}|V[1-6])\b", text, re.IGNORECASE)
            features["st_elevation"] = {
                "detected": True,
                "leads": list(set(lead_match[:6])),
                "trigger_patterns": [p for p in st_elev_patterns if re.search(p, text_lower)],
            }

        # ST depression
        if re.search(r"st[\s-]*depression|st[\s-]*segment[\s-]*depression|subendocardial", text_lower):
            lead_match = re.findall(r"\b(I{1,3}|a[VF]{1,2}|V[1-6])\b", text, re.IGNORECASE)
            features["st_depression"] = {
                "detected": True,
                "leads": list(set(lead_match[:6])),
            }

        # AFib
        if re.search(r"atrial[\s-]*fibrillation|a[\s-]*fib|irregular[\s-]*rhythm|absent[\s-]*p[\s-]*wave", text_lower):
            features["afib"] = {
                "detected": True,
                "description": "Irregularly irregular rhythm without discernible P-waves",
            }

        # QT prolongation
        qtc_match = re.search(r"qtc?\s*[=:]\s*(\d{3,4})", text_lower)
        if qtc_match:
            qtc_ms = int(qtc_match.group(1))
            if qtc_ms > QTC_PROLONGED_MS:
                features["qt_prolonged"] = {
                    "detected": True,
                    "qtc_ms": qtc_ms,
                    "threshold_ms": QTC_PROLONGED_MS,
                }
        elif re.search(r"qt[\s-]*prolongation|prolonged[\s-]*qt", text_lower):
            features["qt_prolonged"] = {"detected": True, "qtc_ms": None}

        # T-wave changes
        if re.search(r"t[\s-]*wave[\s-]*(inversion|flattening|changes|abnormal)", text_lower):
            t_match = re.search(r"t[\s-]*wave[\s-]*(inversion|flattening|changes|abnormal)", text_lower)
            features["t_wave_changes"] = {
                "detected": True,
                "description": t_match.group(0) if t_match else "T-wave abnormality",
            }

        return features

    async def _stemi_protocol(
        self,
        patient_id: str,
        context: Dict[str, Any],
        stemi_details: Dict[str, Any],
    ) -> None:
        """Activate STEMI protocol: notify EMS, find cath lab, alert cardiology."""
        # Notify patient / emergency contacts
        send_notification.invoke({
            "patient_id": patient_id,
            "notification_type": "CRITICAL",
            "message": "EMERGENCY: ECG findings require immediate hospital evaluation. Call 911 NOW. Do not drive yourself.",
            "channel": "sms",
        })

        # Find nearest PCI-capable hospital
        patient_location = context.get("patient", {}).get("location", {})
        if patient_location:
            try:
                hospital = find_nearest_hospital.invoke({
                    "patient_location": patient_location,
                    "capabilities_needed": ["cath_lab", "primary_pci", "cardiac_icu"],
                })
                logger.critical(
                    "STEMI PROTOCOL: patient=%s nearest_cath_lab=%s distance=%s km",
                    patient_id,
                    hospital.get("name", "unknown"),
                    hospital.get("distance_km", "unknown"),
                )
                # A2A broadcast to triage agent
                await self.send_a2a_message(
                    recipient_id="triage_agent",
                    message_type="EMERGENCY",
                    payload={
                        "protocol": "STEMI",
                        "patient_id": patient_id,
                        "nearest_hospital": hospital,
                        "stemi_details": stemi_details,
                    },
                    priority="CRITICAL",
                )
            except Exception as exc:
                logger.error("STEMI hospital lookup failed: %s", exc)

    def _generate_recommendations(
        self,
        features: Dict[str, Any],
        critical_findings: List[str],
    ) -> List[str]:
        recs = []
        if features.get("st_elevation"):
            recs.append("STEMI: Activate cath lab. Dual antiplatelet therapy (aspirin 325mg + P2Y12 inhibitor). Primary PCI target ≤ 90 min (AHA/ACC 2022).")
        if features.get("st_depression"):
            recs.append("NSTEMI/UA: Serial troponins q3-6h. Anticoagulation (heparin/enoxaparin). Risk stratify with GRACE score. Early invasive strategy if high-risk.")
        if features.get("afib"):
            recs.append("AFib: Rate control (beta-blocker or CCB). Anticoagulation if CHA2DS2-VASc ≥2 (men) or ≥3 (women) — DOAC preferred (ESC 2023).")
        if features.get("qt_prolonged"):
            recs.append("QTc prolongation: Discontinue/reduce QT-prolonging drugs. Correct electrolytes (K+, Mg2+). Cardiology/electrophysiology consult if >500ms.")
        return recs
