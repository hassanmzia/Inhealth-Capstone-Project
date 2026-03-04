"""
Agent 6 — Kidney Function Agent

Responsibilities:
  - Track eGFR and creatinine trends from FHIR Observations
  - Calculate CKD stage (1-5) using CKD-EPI formula
  - Detect acute kidney injury (AKI) by creatinine rise
  - Flag medications requiring dose adjustment for CKD
  - RAG: retrieve CKD management guidelines from Qdrant
"""

from __future__ import annotations

import logging
import math
from typing import Any, Dict, List, Optional

from base.agent import MCPAgent
from base.tools import query_fhir_database, query_graph_database, vector_search

logger = logging.getLogger("inhealth.agent.kidney")

# LOINC codes
LOINC_CREATININE = "2160-0"
LOINC_EGFR = "62238-1"
LOINC_BUN = "3094-0"
LOINC_URINE_ALBUMIN = "14959-1"    # Urine albumin-creatinine ratio (UACR)
LOINC_POTASSIUM = "2823-3"
LOINC_BICARBONATE = "1963-8"

# CKD stages by eGFR
CKD_STAGES = [
    (90, None, 1, "Normal or high"),
    (60, 89, 2, "Mildly decreased"),
    (45, 59, 3, "Mildly to moderately decreased"),
    (30, 44, 3, "Moderately to severely decreased"),
    (15, 29, 4, "Severely decreased"),
    (0, 14, 5, "Kidney failure"),
]

# AKI criteria (KDIGO 2012)
AKI_CREATININE_RISE_48H = 0.3   # mg/dL rise within 48 hours
AKI_CREATININE_RISE_7D = 1.5    # 1.5× baseline within 7 days


class KidneyAgent(MCPAgent):
    """Agent 6: Kidney function monitoring, CKD staging, and AKI detection."""

    agent_id = 6
    agent_name = "kidney_agent"
    agent_tier = "tier2_diagnostic"
    system_prompt = (
        "You are the Kidney Function AI Agent for InHealth Chronic Care. "
        "You monitor eGFR and creatinine trends, calculate CKD stage using CKD-EPI, "
        "detect AKI by KDIGO 2012 criteria, and flag nephrotoxic medications. "
        "Reference KDIGO 2024 CKD guidelines, ADA 2024 Standards of Care for diabetic kidney disease, "
        "and ACC/AHA heart failure guidelines for cardiorenal syndrome."
    )

    def _default_tools(self):
        return [query_fhir_database, query_graph_database, vector_search]

    async def analyze(
        self,
        patient_id: str,
        state: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:

        # Fetch labs
        creat_data = query_fhir_database.invoke({
            "resource_type": "Observation",
            "patient_id": patient_id,
            "filters": {"code": LOINC_CREATININE, "limit": 10},
        })
        egfr_data = query_fhir_database.invoke({
            "resource_type": "Observation",
            "patient_id": patient_id,
            "filters": {"code": LOINC_EGFR, "limit": 10},
        })
        uacr_data = query_fhir_database.invoke({
            "resource_type": "Observation",
            "patient_id": patient_id,
            "filters": {"code": LOINC_URINE_ALBUMIN, "limit": 3},
        })
        k_data = query_fhir_database.invoke({
            "resource_type": "Observation",
            "patient_id": patient_id,
            "filters": {"code": LOINC_POTASSIUM, "limit": 3},
        })

        creat_values = self._parse_values(creat_data.get("resources", []))
        egfr_values = self._parse_values(egfr_data.get("resources", []))
        uacr_values = self._parse_values(uacr_data.get("resources", []))
        k_values = self._parse_values(k_data.get("resources", []))

        current_creat = creat_values[0] if creat_values else None
        current_egfr = egfr_values[0] if egfr_values else None
        current_uacr = uacr_values[0] if uacr_values else None
        current_k = k_values[0] if k_values else None

        # Get patient demographics for CKD-EPI
        patient_info = context.get("patient", {})
        age = int(patient_info.get("age", 60))
        sex = patient_info.get("gender", "male")
        is_female = sex.lower() in ("female", "f")

        # Calculate eGFR using CKD-EPI if not available
        if current_egfr is None and current_creat is not None:
            current_egfr = self._ckd_epi(current_creat, age, is_female)

        # CKD staging
        ckd_stage = self._get_ckd_stage(current_egfr)
        albuminuria_category = self._get_albuminuria_category(current_uacr)

        # AKI detection
        aki_detected = False
        aki_stage = 0
        if len(creat_values) >= 2:
            baseline_creat = creat_values[-1]   # Oldest available as baseline
            if current_creat and baseline_creat:
                rise = current_creat - baseline_creat
                ratio = current_creat / baseline_creat if baseline_creat > 0 else 0
                if rise >= AKI_CREATININE_RISE_48H:
                    aki_detected = True
                    aki_stage = 1
                if ratio >= 2.0:
                    aki_stage = 2
                if ratio >= 3.0 or current_creat >= 4.0:
                    aki_stage = 3

        # Trend analysis
        egfr_trend = self._analyze_trend(egfr_values)

        # Medications requiring dose adjustment (from Neo4j)
        try:
            drug_adjustment_query = """
            MATCH (d:Drug)-[:REQUIRES_DOSE_ADJUSTMENT_FOR]->(c:Condition {name: 'CKD'})
            WHERE d.egfr_threshold >= $egfr
            RETURN d.name AS drug, d.adjustment_recommendation AS recommendation, d.egfr_threshold AS threshold
            ORDER BY d.egfr_threshold DESC
            LIMIT 10
            """
            drug_adjustments = query_graph_database.invoke({
                "cypher_query": drug_adjustment_query,
                "params": {"egfr": current_egfr or 60},
            })
        except Exception as exc:
            logger.warning("Drug adjustment query failed: %s", exc)
            drug_adjustments = []

        # RAG: CKD guidelines
        try:
            guidelines = vector_search.invoke({
                "query": f"CKD stage {ckd_stage.get('stage', '?')} management eGFR {current_egfr} KDIGO",
                "collection": "clinical_guidelines",
                "top_k": 3,
            })
        except Exception as exc:
            logger.warning("RAG guideline retrieval failed: %s", exc)
            guidelines = []

        alerts = []
        emergency_detected = False

        # Critical eGFR
        if current_egfr is not None and current_egfr < 15:
            alerts.append(self._build_alert(
                severity="HIGH",
                message=f"CKD Stage 5 (kidney failure): eGFR {current_egfr:.1f} mL/min/1.73m². Nephrology referral urgent. Dialysis planning needed (KDIGO 2024).",
                patient_id=patient_id,
                details={"egfr": current_egfr, "ckd_stage": 5},
            ))
        elif current_egfr is not None and current_egfr < 30:
            alerts.append(self._build_alert(
                severity="HIGH",
                message=f"Advanced CKD Stage {ckd_stage.get('stage')}: eGFR {current_egfr:.1f}. Urgent nephrology referral. Avoid nephrotoxins (NSAIDs, contrast).",
                patient_id=patient_id,
                details={"egfr": current_egfr, "ckd_stage": ckd_stage},
            ))

        if aki_detected:
            emergency_detected = aki_stage >= 2
            alerts.append(self._build_alert(
                severity="EMERGENCY" if aki_stage >= 2 else "HIGH",
                message=f"ACUTE KIDNEY INJURY Stage {aki_stage} (KDIGO 2012): creatinine rise {creat_values[0] - creat_values[-1]:.2f} mg/dL. Identify and treat precipitating cause.",
                patient_id=patient_id,
                details={"aki_stage": aki_stage, "creatinine_current": current_creat, "creatinine_baseline": creat_values[-1]},
            ))

        if current_k and current_k > 5.5:
            alerts.append(self._build_alert(
                severity="HIGH" if current_k > 6.0 else "NORMAL",
                message=f"Hyperkalemia: K+ {current_k:.1f} mEq/L. Risk of cardiac arrhythmia. Dietary restriction, consider patiromer/sodium zirconium cyclosilicate.",
                patient_id=patient_id,
                details={"potassium": current_k},
            ))

        # Declining eGFR trend
        if egfr_trend == "declining_rapid":
            alerts.append(self._build_alert(
                severity="HIGH",
                message="Rapid eGFR decline detected. Evaluate for AKI superimposed on CKD, malignant hypertension, or obstruction.",
                patient_id=patient_id,
                details={"egfr_values": egfr_values[:5]},
            ))

        # LLM analysis
        llm_input = (
            f"Patient {patient_id} kidney function data:\n"
            f"  Creatinine: {current_creat} mg/dL\n"
            f"  eGFR: {current_egfr} mL/min/1.73m² (CKD-EPI)\n"
            f"  CKD Stage: {ckd_stage}\n"
            f"  UACR: {current_uacr} mg/g\n"
            f"  Albuminuria category: {albuminuria_category}\n"
            f"  Potassium: {current_k} mEq/L\n"
            f"  AKI detected: {aki_detected} (Stage {aki_stage})\n"
            f"  eGFR trend: {egfr_trend}\n"
            f"  Medications requiring dose adjustment: {drug_adjustments}\n"
            f"  Relevant guidelines: {[g.get('title', '') for g in guidelines]}\n"
            f"\nProvide comprehensive KDIGO 2024-aligned management plan including:\n"
            f"1. CKD progression risk assessment\n"
            f"2. Renoprotective strategies (ACE/ARB, SGLT2i, finerenone per FIDELIO-DKD/CREDENCE)\n"
            f"3. Medication adjustments for current eGFR\n"
            f"4. Nephrology referral urgency\n"
            f"5. Diet modifications (protein, potassium, phosphorus)"
        )

        try:
            llm_result = await self.run_agent_chain(input_text=llm_input)
            clinical_plan = llm_result.get("output", "")
        except Exception as exc:
            logger.warning("Kidney LLM analysis failed: %s", exc)
            clinical_plan = ""

        return self._build_result(
            status="completed",
            findings={
                "creatinine_mgdl": current_creat,
                "egfr_ml_min": round(current_egfr, 1) if current_egfr else None,
                "ckd_stage": ckd_stage,
                "albuminuria_category": albuminuria_category,
                "uacr_mg_g": current_uacr,
                "potassium_meq_l": current_k,
                "aki_detected": aki_detected,
                "aki_stage": aki_stage,
                "egfr_trend": egfr_trend,
                "drug_adjustments_needed": drug_adjustments,
                "clinical_plan": clinical_plan,
                "guidelines_retrieved": len(guidelines),
            },
            alerts=alerts,
            recommendations=self._generate_recommendations(current_egfr, ckd_stage, aki_detected),
            emergency_detected=emergency_detected,
        )

    def _ckd_epi(self, creat: float, age: int, is_female: bool) -> float:
        """CKD-EPI 2021 (race-free) eGFR formula."""
        kappa = 0.7 if is_female else 0.9
        alpha = -0.241 if is_female else -0.302
        sex_factor = 1.012 if is_female else 1.0

        ratio = creat / kappa
        if ratio < 1:
            egfr = 142 * (ratio ** alpha) * (0.9938 ** age) * sex_factor
        else:
            egfr = 142 * (ratio ** -1.200) * (0.9938 ** age) * sex_factor

        return round(egfr, 1)

    def _get_ckd_stage(self, egfr: Optional[float]) -> Dict[str, Any]:
        if egfr is None:
            return {"stage": "unknown", "description": "eGFR not available"}
        for low, high, stage, desc in CKD_STAGES:
            if high is None:
                if egfr >= low:
                    return {"stage": stage, "egfr_range": f">= {low}", "description": desc}
            elif low <= egfr <= high:
                return {"stage": stage, "egfr_range": f"{low}-{high}", "description": desc}
        return {"stage": 5, "description": "Kidney failure"}

    def _get_albuminuria_category(self, uacr: Optional[float]) -> str:
        if uacr is None:
            return "unknown"
        if uacr < 30:
            return "A1 - Normal to mildly increased (< 30 mg/g)"
        elif uacr < 300:
            return "A2 - Moderately increased (30-300 mg/g)"
        return "A3 - Severely increased (> 300 mg/g)"

    def _analyze_trend(self, values: List[float]) -> str:
        if len(values) < 3:
            return "insufficient_data"
        recent = values[:3]
        older = values[3:6] if len(values) >= 6 else values
        recent_avg = sum(recent) / len(recent)
        older_avg = sum(older) / len(older)
        delta = recent_avg - older_avg
        if delta < -10:
            return "declining_rapid"
        elif delta < -5:
            return "declining"
        elif delta > 5:
            return "improving"
        return "stable"

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

    def _generate_recommendations(
        self,
        egfr: Optional[float],
        ckd_stage: Dict[str, Any],
        aki: bool,
    ) -> List[str]:
        recs = []
        stage = ckd_stage.get("stage", 0)
        if stage >= 3:
            recs.append("Renoprotection: ACE inhibitor/ARB for albuminuria. SGLT2i (empagliflozin/dapagliflozin) if eGFR ≥ 20 and T2DM or HF — CREDENCE/DAPA-CKD trials.")
            recs.append("Avoid nephrotoxins: NSAIDs, contrast dye without pre-hydration, aminoglycosides.")
        if stage >= 4:
            recs.append("Nephrology referral: CKD progression counseling, dialysis/transplant planning (KDIGO 2024).")
            recs.append("Dietary: Protein restriction 0.6-0.8g/kg/day. Potassium and phosphorus restriction if elevated.")
        if aki:
            recs.append("AKI management: Identify and remove precipitating cause. Optimize fluid status. Avoid nephrotoxins. Monitor daily creatinine. Nephrology consult if Stage 2-3.")
        return recs
