"""
Agent 7 — Imaging Analysis Agent

Responsibilities:
  - Process radiology report text from FHIR DiagnosticReport
  - NLP extraction: findings, impressions, critical findings
  - Flag CRITICAL: pneumothorax, PE, hemorrhage, fracture
  - RAG retrieval of relevant imaging guidelines
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List

from base.agent import MCPAgent
from base.tools import query_fhir_database, send_notification, vector_search

logger = logging.getLogger("inhealth.agent.imaging")

# LOINC codes for radiology reports
LOINC_CXR = "24627-2"          # Chest X-ray
LOINC_CT_CHEST = "24630-6"     # CT chest
LOINC_CT_HEAD = "24725-4"      # CT head
LOINC_MRI_BRAIN = "24558-9"    # MRI brain
LOINC_ECHO = "59282-4"         # Echocardiogram

# Critical imaging findings (triggers EMERGENCY)
CRITICAL_FINDINGS = [
    "pneumothorax",
    "tension pneumothorax",
    "pulmonary embolism",
    "pe",
    "intracranial hemorrhage",
    "subarachnoid hemorrhage",
    "epidural hematoma",
    "subdural hematoma",
    "aortic dissection",
    "aortic aneurysm rupture",
    "mesenteric ischemia",
    "bowel perforation",
    "free air",
    "pneumoperitoneum",
    "large pleural effusion",
]


class ImagingAgent(MCPAgent):
    """Agent 7: Radiology report analysis and critical finding flagging."""

    agent_id = 7
    agent_name = "imaging_agent"
    agent_tier = "tier2_diagnostic"
    system_prompt = (
        "You are the Medical Imaging AI Agent for InHealth Chronic Care. "
        "You analyze radiology reports (CXR, CT, MRI, Echo) to extract findings, "
        "impressions, and critical incidental findings. Flag life-threatening findings "
        "(pneumothorax, PE, hemorrhage) as EMERGENCY. "
        "Reference ACR Appropriateness Criteria and Radiology Critical Findings guidelines."
    )

    def _default_tools(self):
        return [query_fhir_database, vector_search, send_notification]

    async def analyze(
        self,
        patient_id: str,
        state: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:

        # Fetch latest radiology reports
        all_reports = []
        for loinc_code in [LOINC_CXR, LOINC_CT_CHEST, LOINC_CT_HEAD, LOINC_MRI_BRAIN]:
            data = query_fhir_database.invoke({
                "resource_type": "DiagnosticReport",
                "patient_id": patient_id,
                "filters": {"code": loinc_code, "limit": 2},
            })
            all_reports.extend(data.get("resources", []))

        if not all_reports:
            return self._build_result(
                status="no_data",
                findings={"message": "No radiology reports found"},
            )

        alerts = []
        emergency_detected = False
        all_findings = []

        for report in all_reports[:5]:  # Process up to 5 most recent reports
            report_text = report.get("value", "") or report.get("meta", {}).get("text", "")
            report_code = report.get("code", "")

            if not report_text:
                continue

            # Extract structured findings
            structured = self._extract_findings(report_text)
            structured["report_id"] = report.get("id", "")
            structured["report_type"] = self._get_modality(report_code)
            structured["report_date"] = report.get("effective_datetime", "")
            all_findings.append(structured)

            # Check for critical findings
            critical_detected = []
            text_lower = report_text.lower()
            for finding in CRITICAL_FINDINGS:
                if finding in text_lower:
                    # Verify it's not negated (no pneumothorax)
                    context_window = self._get_context_window(text_lower, finding, chars=50)
                    if not self._is_negated(context_window):
                        critical_detected.append(finding)

            if critical_detected:
                emergency_detected = True
                for finding in critical_detected:
                    send_notification.invoke({
                        "patient_id": patient_id,
                        "notification_type": "CRITICAL",
                        "message": f"CRITICAL RADIOLOGY FINDING: {finding.upper()} detected on {structured['report_type']}. Immediate medical attention required.",
                        "channel": "sms",
                    })
                    alerts.append(self._build_alert(
                        severity="EMERGENCY",
                        message=f"CRITICAL IMAGING FINDING: {finding.title()} detected on {structured['report_type']}. Immediate intervention required.",
                        patient_id=patient_id,
                        details={
                            "finding": finding,
                            "modality": structured["report_type"],
                            "impression": structured.get("impression", ""),
                        },
                    ))

        # RAG: retrieve relevant imaging guidelines
        try:
            critical_terms = " ".join(
                [f.get("critical_findings", [""])[0] if f.get("critical_findings") else "" for f in all_findings if f.get("critical_findings")]
            )
            guidelines = vector_search.invoke({
                "query": f"radiology critical findings management {critical_terms}",
                "collection": "clinical_guidelines",
                "top_k": 3,
            })
        except Exception as exc:
            logger.warning("Imaging RAG failed: %s", exc)
            guidelines = []

        # LLM analysis
        findings_summary = "\n".join([
            f"  {f['report_type']} ({f['report_date']}):\n"
            f"    Findings: {f.get('findings_text', '')[:200]}\n"
            f"    Impression: {f.get('impression', '')[:200]}"
            for f in all_findings[:3]
        ])

        llm_input = (
            f"Radiology reports for patient {patient_id}:\n\n{findings_summary}\n\n"
            f"Critical findings detected: {[a['details'].get('finding', '') for a in alerts if a.get('severity') == 'EMERGENCY']}\n"
            f"Relevant guidelines: {[g.get('title', '') for g in guidelines]}\n\n"
            f"Provide:\n"
            f"1. Integrated interpretation of all imaging findings\n"
            f"2. Urgency classification per ACR Critical Findings reporting standards\n"
            f"3. Management recommendations for each significant finding\n"
            f"4. Follow-up imaging recommendations (type, timing)\n"
            f"5. Differential diagnoses for incidental findings"
        )

        try:
            llm_result = await self.run_agent_chain(input_text=llm_input)
            integrated_interpretation = llm_result.get("output", "")
        except Exception as exc:
            logger.warning("Imaging LLM analysis failed: %s", exc)
            integrated_interpretation = ""

        return self._build_result(
            status="completed",
            findings={
                "reports_analyzed": len(all_findings),
                "structured_findings": all_findings,
                "critical": emergency_detected,
                "integrated_interpretation": integrated_interpretation,
                "guidelines_retrieved": len(guidelines),
            },
            alerts=alerts,
            recommendations=self._generate_recommendations(all_findings, emergency_detected),
            emergency_detected=emergency_detected,
        )

    def _extract_findings(self, text: str) -> Dict[str, Any]:
        """Extract structured sections from a radiology report."""
        result: Dict[str, Any] = {"raw_text": text[:500]}

        # Extract impression section
        impression_match = re.search(
            r"impression[:\s]+(.*?)(?:\n\n|\Z)",
            text,
            re.IGNORECASE | re.DOTALL,
        )
        if impression_match:
            result["impression"] = impression_match.group(1).strip()[:500]

        # Extract findings section
        findings_match = re.search(
            r"findings[:\s]+(.*?)(?:impression|conclusion|$)",
            text,
            re.IGNORECASE | re.DOTALL,
        )
        if findings_match:
            result["findings_text"] = findings_match.group(1).strip()[:500]

        # Tag critical findings
        text_lower = text.lower()
        critical = [f for f in CRITICAL_FINDINGS if f in text_lower and not self._is_negated(self._get_context_window(text_lower, f))]
        result["critical_findings"] = critical

        return result

    def _get_context_window(self, text: str, term: str, chars: int = 30) -> str:
        idx = text.find(term)
        if idx == -1:
            return ""
        start = max(0, idx - chars)
        return text[start : idx + len(term) + chars]

    def _is_negated(self, context: str) -> bool:
        """Check if a finding is negated in the context window."""
        negation_words = ["no ", "not ", "without ", "negative for ", "absent ", "rules out ", "no evidence of "]
        return any(neg in context for neg in negation_words)

    def _get_modality(self, code: str) -> str:
        mapping = {
            LOINC_CXR: "Chest X-ray",
            LOINC_CT_CHEST: "CT Chest",
            LOINC_CT_HEAD: "CT Head",
            LOINC_MRI_BRAIN: "MRI Brain",
            LOINC_ECHO: "Echocardiogram",
        }
        return mapping.get(code, "Radiology Report")

    def _generate_recommendations(
        self, findings: List[Dict[str, Any]], emergency: bool
    ) -> List[str]:
        recs = []
        if emergency:
            recs.append("CRITICAL FINDING: Notify ordering physician and radiologist immediately per ACR Critical Results Communication standards.")
        for f in findings:
            for cf in f.get("critical_findings", []):
                if "pneumothorax" in cf:
                    recs.append("Pneumothorax: Supplemental O2. Small (<2cm apex, stable): observation. Large/tension: chest tube insertion.")
                if "pulmonary embolism" in cf or cf == "pe":
                    recs.append("Pulmonary Embolism: Anticoagulation (DOAC or heparin bridge). PESI score for severity. Massive PE: thrombolysis or embolectomy (ESC 2019).")
                if "hemorrhage" in cf:
                    recs.append("Intracranial Hemorrhage: Urgent neurosurgery consult. Reversal of anticoagulation. Blood pressure management per AHA/ASA 2022.")
        return recs
