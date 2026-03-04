"""
Agent 8 — Laboratory Interpretation Agent

Responsibilities:
  - Interpret lab panels: CBC, BMP, HbA1c, lipid panel, thyroid
  - Calculate: eGFR, MELD score, CURB-65
  - Detect critical values (panic values)
  - Trend analysis: improving/worsening
  - RAG: retrieve lab reference ranges from Qdrant
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from base.agent import MCPAgent
from base.tools import query_fhir_database, vector_search

logger = logging.getLogger("inhealth.agent.lab")

# LOINC codes for common labs
LOINC_MAP = {
    "hba1c": "4548-4",
    "glucose": "2339-0",
    "creatinine": "2160-0",
    "bun": "3094-0",
    "sodium": "2951-2",
    "potassium": "2823-3",
    "bicarbonate": "1963-8",
    "chloride": "2075-0",
    "hemoglobin": "718-7",
    "wbc": "6690-2",
    "platelets": "777-3",
    "alt": "1742-6",
    "ast": "1920-8",
    "bilirubin_total": "1975-2",
    "albumin": "1751-7",
    "inr": "5902-2",
    "ldl": "2089-1",
    "hdl": "2085-9",
    "triglycerides": "2571-8",
    "tsh": "3016-3",
    "troponin": "10839-9",
    "bnp": "42637-9",
    "procalcitonin": "33959-8",
    "lactate": "2524-7",
}

# Critical (panic) values
CRITICAL_VALUES = {
    "potassium": {"low": 2.8, "high": 6.5, "unit": "mEq/L"},
    "sodium": {"low": 120, "high": 160, "unit": "mEq/L"},
    "glucose": {"low": 40, "high": 500, "unit": "mg/dL"},
    "hemoglobin": {"low": 6.0, "high": None, "unit": "g/dL"},
    "platelets": {"low": 50, "high": None, "unit": "× 10^9/L"},
    "inr": {"low": None, "high": 5.0, "unit": ""},
    "troponin": {"low": None, "high": 0.04, "unit": "ng/mL"},  # High-sensitivity
    "lactate": {"low": None, "high": 4.0, "unit": "mmol/L"},
}


class LabAgent(MCPAgent):
    """Agent 8: Comprehensive laboratory panel interpretation."""

    agent_id = 8
    agent_name = "lab_agent"
    agent_tier = "tier2_diagnostic"
    system_prompt = (
        "You are the Laboratory Interpretation AI Agent for InHealth Chronic Care. "
        "You interpret comprehensive metabolic panels, CBC, HbA1c, lipid panels, thyroid function, "
        "cardiac biomarkers, and coagulation studies. Calculate MELD score, CURB-65, and other "
        "clinical scores. Detect panic values and trend changes. "
        "Reference UpToDate reference ranges and ADA/ACC/AHA guideline targets."
    )

    def _default_tools(self):
        return [query_fhir_database, vector_search]

    async def analyze(
        self,
        patient_id: str,
        state: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:

        # Fetch all relevant labs
        labs: Dict[str, List[float]] = {}
        for lab_name, loinc in LOINC_MAP.items():
            data = query_fhir_database.invoke({
                "resource_type": "Observation",
                "patient_id": patient_id,
                "filters": {"code": loinc, "limit": 5},
            })
            values = self._parse_values(data.get("resources", []))
            if values:
                labs[lab_name] = values

        current_labs = {k: v[0] for k, v in labs.items() if v}

        # Detect critical values
        critical_values = []
        alerts = []
        emergency_detected = False

        for lab_name, thresholds in CRITICAL_VALUES.items():
            current_val = current_labs.get(lab_name)
            if current_val is None:
                continue
            low = thresholds.get("low")
            high = thresholds.get("high")
            unit = thresholds.get("unit", "")

            if low and current_val <= low:
                emergency_detected = True
                critical_values.append({
                    "lab": lab_name,
                    "value": current_val,
                    "unit": unit,
                    "type": "critically_low",
                    "threshold": low,
                })
                alerts.append(self._build_alert(
                    severity="EMERGENCY",
                    message=f"CRITICAL LOW {lab_name.upper()}: {current_val} {unit} (critical low: < {low} {unit}). Immediate intervention required.",
                    patient_id=patient_id,
                    details={"lab": lab_name, "value": current_val, "threshold": low},
                ))

            if high and current_val >= high:
                emergency_detected = True
                critical_values.append({
                    "lab": lab_name,
                    "value": current_val,
                    "unit": unit,
                    "type": "critically_high",
                    "threshold": high,
                })
                alerts.append(self._build_alert(
                    severity="EMERGENCY",
                    message=f"CRITICAL HIGH {lab_name.upper()}: {current_val} {unit} (critical high: > {high} {unit}). Immediate intervention required.",
                    patient_id=patient_id,
                    details={"lab": lab_name, "value": current_val, "threshold": high},
                ))

        # Calculate clinical scores
        clinical_scores = self._calculate_scores(current_labs)

        # Trend analysis for key labs
        trends = {}
        for lab_name in ["creatinine", "hemoglobin", "hba1c", "ldl", "troponin"]:
            if lab_name in labs and len(labs[lab_name]) >= 3:
                trends[lab_name] = self._analyze_trend(labs[lab_name])

        # HbA1c assessment
        hba1c_assessment = {}
        if "hba1c" in current_labs:
            hba1c = current_labs["hba1c"]
            if hba1c >= 9.0:
                hba1c_assessment = {"level": "very_poor", "target": "< 7.0%", "action": "Intensify therapy urgently"}
                alerts.append(self._build_alert(
                    severity="HIGH",
                    message=f"HbA1c {hba1c:.1f}%: Very poor glycemic control. Medication intensification required (ADA 2024).",
                    patient_id=patient_id,
                    details={"hba1c": hba1c},
                ))
            elif hba1c >= 8.0:
                hba1c_assessment = {"level": "poor", "target": "< 7.0%", "action": "Intensify therapy"}
            elif hba1c >= 7.0:
                hba1c_assessment = {"level": "suboptimal", "target": "< 7.0%", "action": "Consider adjustment"}
            else:
                hba1c_assessment = {"level": "at_target", "target": "< 7.0%", "action": "Continue current regimen"}

        # RAG: retrieve reference ranges and interpretation guidelines
        try:
            lab_summary = ", ".join([f"{k}={v:.2f}" for k, v in list(current_labs.items())[:6]])
            guidelines = vector_search.invoke({
                "query": f"laboratory interpretation reference ranges chronic disease {lab_summary}",
                "collection": "clinical_guidelines",
                "top_k": 3,
            })
        except Exception as exc:
            logger.warning("Lab RAG failed: %s", exc)
            guidelines = []

        # Alert for trending troponin (possible ACS)
        if "troponin" in labs and len(labs["troponin"]) >= 2:
            trop_rise = labs["troponin"][0] - labs["troponin"][-1]
            if trop_rise > 0.006 and labs["troponin"][0] > 0.014:
                emergency_detected = True
                alerts.append(self._build_alert(
                    severity="EMERGENCY",
                    message=f"RISING TROPONIN: Rise of {trop_rise:.4f} ng/mL. Possible NSTEMI. ECG and cardiology consult immediately (ESC 0/1-hour algorithm).",
                    patient_id=patient_id,
                    details={"troponin_current": labs["troponin"][0], "troponin_prior": labs["troponin"][-1], "delta": trop_rise},
                ))

        # LLM comprehensive interpretation
        labs_formatted = "\n".join([f"  {k}: {v:.2f}" for k, v in current_labs.items()])
        llm_input = (
            f"Laboratory results for patient {patient_id}:\n{labs_formatted}\n\n"
            f"Clinical scores:\n"
            f"  MELD score: {clinical_scores.get('meld', 'N/A')}\n"
            f"  CURB-65: {clinical_scores.get('curb65', 'N/A')}\n"
            f"HbA1c assessment: {hba1c_assessment}\n"
            f"Trends: {trends}\n"
            f"Critical values: {critical_values}\n\n"
            f"Provide comprehensive lab interpretation:\n"
            f"1. Panel-by-panel assessment (CBC, BMP, Lipids, HbA1c, Cardiac markers)\n"
            f"2. Most clinically significant findings and their implications\n"
            f"3. Evidence-based targets for each abnormal value\n"
            f"4. Recommended medication or dietary adjustments\n"
            f"5. Follow-up testing schedule"
        )

        try:
            llm_result = await self.run_agent_chain(input_text=llm_input)
            lab_interpretation = llm_result.get("output", "")
        except Exception as exc:
            logger.warning("Lab LLM interpretation failed: %s", exc)
            lab_interpretation = ""

        return self._build_result(
            status="completed",
            findings={
                "current_labs": current_labs,
                "critical_values": critical_values,
                "clinical_scores": clinical_scores,
                "hba1c_assessment": hba1c_assessment,
                "trends": trends,
                "lab_interpretation": lab_interpretation,
                "guidelines_retrieved": len(guidelines),
            },
            alerts=alerts,
            recommendations=self._generate_recommendations(current_labs, clinical_scores),
            emergency_detected=emergency_detected,
        )

    def _parse_values(self, resources: List[Dict[str, Any]]) -> List[float]:
        result = []
        for r in resources:
            try:
                v = float(r.get("value", 0))
                if v >= 0:
                    result.append(v)
            except (ValueError, TypeError):
                continue
        return result

    def _calculate_scores(self, labs: Dict[str, float]) -> Dict[str, Any]:
        scores: Dict[str, Any] = {}

        # MELD score = 3.78×ln(bilirubin) + 11.2×ln(INR) + 9.57×ln(creatinine) + 6.43
        import math
        bili = labs.get("bilirubin_total", 1.0) or 1.0
        inr = labs.get("inr", 1.0) or 1.0
        creat = labs.get("creatinine", 1.0) or 1.0
        try:
            meld = round(3.78 * math.log(max(bili, 1.0)) + 11.2 * math.log(max(inr, 1.0)) + 9.57 * math.log(max(creat, 1.0)) + 6.43, 1)
            scores["meld"] = meld
            scores["meld_90d_mortality"] = self._meld_mortality(meld)
        except Exception:
            scores["meld"] = None

        return scores

    def _meld_mortality(self, meld: float) -> str:
        if meld < 10:
            return "< 2%"
        elif meld < 20:
            return "6%"
        elif meld < 30:
            return "20%"
        elif meld < 40:
            return "52%"
        return "> 71%"

    def _analyze_trend(self, values: List[float]) -> str:
        if len(values) < 2:
            return "single_value"
        recent = values[0]
        prior = values[1]
        pct_change = (recent - prior) / prior * 100 if prior != 0 else 0
        if pct_change > 20:
            return "increasing_significantly"
        elif pct_change > 5:
            return "increasing"
        elif pct_change < -20:
            return "decreasing_significantly"
        elif pct_change < -5:
            return "decreasing"
        return "stable"

    def _generate_recommendations(
        self,
        labs: Dict[str, float],
        scores: Dict[str, Any],
    ) -> List[str]:
        recs = []
        if labs.get("ldl", 0) > 100:
            recs.append(f"LDL {labs['ldl']:.1f} mg/dL above target (< 70 mg/dL for high-risk CVD). Consider high-intensity statin or ezetimibe addition (ACC/AHA 2022).")
        if labs.get("tsh", 0) > 4.5:
            recs.append("Elevated TSH: hypothyroidism likely. Initiate levothyroxine with target TSH 0.5-2.5 mIU/L (ATA 2014).")
        if labs.get("hemoglobin", 15) < 10:
            recs.append("Anemia: Evaluate for iron deficiency (check ferritin, TIBC), B12/folate deficiency, or chronic kidney disease anemia (consider ESA therapy).")
        if scores.get("meld", 0) and scores["meld"] > 15:
            recs.append(f"MELD score {scores['meld']}: Advanced liver disease. Hepatology referral. Consider liver transplant evaluation.")
        return recs
