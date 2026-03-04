"""
Agent 9 — Comorbidity Risk Agent

Responsibilities:
  - Analyze co-existing chronic conditions (T2DM + CKD + HTN + CHF)
  - Calculate Charlson Comorbidity Index (CCI)
  - Graph query: disease-disease risk relationships in Neo4j
  - Identify highest-priority comorbidity to address
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from base.agent import MCPAgent
from base.tools import query_fhir_database, query_graph_database, vector_search

logger = logging.getLogger("inhealth.agent.comorbidity")

# Charlson Comorbidity Index weights (Charlson 1987 / Quan 2011 updated)
CCI_WEIGHTS = {
    "myocardial_infarction": 1,
    "congestive_heart_failure": 1,
    "peripheral_vascular_disease": 1,
    "cerebrovascular_disease": 1,
    "dementia": 1,
    "chronic_pulmonary_disease": 1,
    "connective_tissue_disease": 1,
    "peptic_ulcer_disease": 1,
    "mild_liver_disease": 1,
    "diabetes_without_complications": 1,
    "diabetes_with_complications": 2,
    "hemiplegia_paraplegia": 2,
    "renal_disease": 2,
    "solid_tumor": 2,
    "leukemia": 2,
    "lymphoma": 2,
    "moderate_severe_liver_disease": 3,
    "metastatic_solid_tumor": 6,
    "aids_hiv": 6,
}

# SNOMED CT condition codes (simplified)
CONDITION_SNOMED_MAP = {
    "44054006": "diabetes_type2",
    "38341003": "hypertension",
    "73211009": "diabetes_mellitus",
    "46635009": "diabetes_type1",
    "431855005": "chronic_kidney_disease",
    "84114007": "heart_failure",
    "22298006": "myocardial_infarction",
    "230690007": "stroke",
    "13645005": "chronic_pulmonary_disease",
    "363346000": "malignant_tumor",
}


class ComorbidityAgent(MCPAgent):
    """Agent 9: Comorbidity risk analysis and Charlson Index calculation."""

    agent_id = 9
    agent_name = "comorbidity_agent"
    agent_tier = "tier3_risk"
    system_prompt = (
        "You are the Comorbidity Risk AI Agent for InHealth Chronic Care. "
        "You analyze co-existing chronic conditions, calculate the Charlson Comorbidity Index, "
        "and identify high-risk condition combinations. Use the disease knowledge graph to identify "
        "synergistic risk patterns (e.g., T2DM + CKD + HTN = cardiorenal-metabolic syndrome). "
        "Reference current clinical practice guidelines for each condition combination."
    )

    def _default_tools(self):
        return [query_fhir_database, query_graph_database, vector_search]

    async def analyze(
        self,
        patient_id: str,
        state: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:

        # Fetch active conditions from FHIR
        conditions_data = query_fhir_database.invoke({
            "resource_type": "Condition",
            "patient_id": patient_id,
            "filters": {"limit": 50},
        })

        conditions = conditions_data.get("resources", [])
        active_conditions = self._parse_conditions(conditions)

        # Calculate Charlson Comorbidity Index
        cci_result = self._calculate_cci(active_conditions)

        # Query Neo4j for disease interaction graph
        try:
            disease_interaction_query = """
            UNWIND $conditions AS cond1
            UNWIND $conditions AS cond2
            WITH cond1, cond2
            WHERE cond1 <> cond2
            MATCH (d1:Disease {name: cond1})-[r:INCREASES_RISK_OF|EXACERBATES|SYNERGIZES_WITH]->(d2:Disease {name: cond2})
            RETURN d1.name AS disease1, type(r) AS relationship, d2.name AS disease2,
                   r.risk_multiplier AS risk_multiplier, r.mechanism AS mechanism
            ORDER BY r.risk_multiplier DESC
            LIMIT 20
            """
            disease_interactions = query_graph_database.invoke({
                "cypher_query": disease_interaction_query,
                "params": {"conditions": list(active_conditions.keys())},
            })
        except Exception as exc:
            logger.warning("Disease interaction graph query failed: %s", exc)
            disease_interactions = []

        # Identify high-risk condition clusters
        risk_clusters = self._identify_risk_clusters(active_conditions)

        # RAG: retrieve comorbidity management guidelines
        try:
            conditions_str = ", ".join(list(active_conditions.keys())[:5])
            guidelines = vector_search.invoke({
                "query": f"comorbidity management {conditions_str} chronic disease",
                "collection": "clinical_guidelines",
                "top_k": 3,
            })
        except Exception as exc:
            logger.warning("Comorbidity RAG failed: %s", exc)
            guidelines = []

        alerts = []
        if cci_result["score"] >= 6:
            alerts.append(self._build_alert(
                severity="HIGH",
                message=f"High comorbidity burden: Charlson Index {cci_result['score']} — estimated 10-year survival {cci_result['ten_year_survival']}. Comprehensive care planning indicated.",
                patient_id=patient_id,
                details=cci_result,
            ))

        for cluster in risk_clusters:
            if cluster.get("risk_level") == "CRITICAL":
                alerts.append(self._build_alert(
                    severity="HIGH",
                    message=f"High-risk condition cluster: {cluster['name']} — {cluster['description']}",
                    patient_id=patient_id,
                    details=cluster,
                ))

        # LLM prioritization analysis
        llm_input = (
            f"Patient {patient_id} has the following active conditions:\n"
            + "\n".join([f"  - {name} (severity: {info.get('severity', 'unknown')})" for name, info in active_conditions.items()])
            + f"\n\nCharlson Comorbidity Index: {cci_result['score']} ({cci_result['risk_category']})\n"
            f"Estimated 10-year survival: {cci_result['ten_year_survival']}\n\n"
            f"Disease interactions from knowledge graph:\n"
            + "\n".join([f"  {i.get('disease1', '')} → {i.get('relationship', '')} → {i.get('disease2', '')} (risk multiplier: {i.get('risk_multiplier', 'N/A')})" for i in disease_interactions[:5]])
            + f"\n\nRisk clusters: {risk_clusters}\n\n"
            f"Provide:\n"
            f"1. Prioritized list of conditions to address (highest clinical impact first)\n"
            f"2. Synergistic risks that require coordinated management\n"
            f"3. Care coordination recommendations (which specialists to involve)\n"
            f"4. Overall prognosis assessment based on comorbidity profile\n"
            f"5. Quality-of-life optimization strategies"
        )

        try:
            llm_result = await self.run_agent_chain(input_text=llm_input)
            prioritization_analysis = llm_result.get("output", "")
        except Exception as exc:
            logger.warning("Comorbidity LLM analysis failed: %s", exc)
            prioritization_analysis = ""

        return self._build_result(
            status="completed",
            findings={
                "active_conditions": active_conditions,
                "condition_count": len(active_conditions),
                "charlson_index": cci_result,
                "disease_interactions": disease_interactions,
                "risk_clusters": risk_clusters,
                "prioritization_analysis": prioritization_analysis,
                "guidelines_retrieved": len(guidelines),
            },
            alerts=alerts,
            recommendations=self._generate_recommendations(cci_result, risk_clusters),
        )

    def _parse_conditions(self, resources: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Parse FHIR Condition resources into a structured dict."""
        conditions: Dict[str, Any] = {}
        for r in resources:
            code = r.get("code", "")
            name = CONDITION_SNOMED_MAP.get(code, code.replace("_", " ").title())
            if name and name not in conditions:
                conditions[name] = {
                    "code": code,
                    "onset": r.get("effective_datetime", ""),
                    "severity": r.get("status", "active"),
                }
        return conditions

    def _calculate_cci(self, conditions: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate Charlson Comorbidity Index with 10-year survival estimate."""
        score = 0
        matched_conditions = []

        for cci_name, weight in CCI_WEIGHTS.items():
            condition_key = cci_name.replace("_", " ")
            for patient_condition in conditions.keys():
                if condition_key in patient_condition.lower() or patient_condition.lower() in condition_key:
                    score += weight
                    matched_conditions.append({"condition": cci_name, "weight": weight})
                    break

        # Age adjustment (+1 per decade > 40 years, max +4)
        # We don't have age here; the LLM will handle age-adjusted scoring

        # 10-year survival estimate (Charlson 1994)
        survival_map = {
            (0, 0): "> 90%",
            (1, 2): "89%",
            (3, 4): "77%",
            (5, 6): "53%",
            (7, 10): "21%",
        }
        survival = "> 20%"  # default
        for (low, high), pct in survival_map.items():
            if low <= score <= high:
                survival = pct
                break

        if score == 0:
            risk_category = "Low"
        elif score <= 2:
            risk_category = "Low-Moderate"
        elif score <= 4:
            risk_category = "Moderate"
        elif score <= 6:
            risk_category = "High"
        else:
            risk_category = "Very High"

        return {
            "score": score,
            "risk_category": risk_category,
            "ten_year_survival": survival,
            "matched_conditions": matched_conditions,
        }

    def _identify_risk_clusters(self, conditions: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Identify known high-risk condition combinations."""
        clusters = []
        names_lower = [k.lower() for k in conditions.keys()]

        # Cardiorenal-metabolic syndrome
        has_dm = any("diabet" in n for n in names_lower)
        has_ckd = any("kidney" in n or "renal" in n for n in names_lower)
        has_htn = any("hypertens" in n for n in names_lower)
        has_hf = any("heart fail" in n for n in names_lower)

        if has_dm and has_ckd and has_htn:
            clusters.append({
                "name": "Cardiorenal-Metabolic Syndrome",
                "conditions": ["T2DM", "CKD", "Hypertension"],
                "risk_level": "CRITICAL",
                "description": "Synergistic cardiovascular and renal risk. 3-5× increased CV mortality. Requires integrated management with SGLT2i/GLP-1RA, ACE/ARB, and intensive BP control.",
            })

        if has_hf and has_ckd:
            clusters.append({
                "name": "Cardiorenal Syndrome",
                "conditions": ["Heart Failure", "CKD"],
                "risk_level": "CRITICAL",
                "description": "Bidirectional cardiac-renal dysfunction. Complex fluid and medication management. Cardiology + nephrology co-management essential.",
            })

        return clusters

    def _generate_recommendations(
        self,
        cci: Dict[str, Any],
        clusters: List[Dict[str, Any]],
    ) -> List[str]:
        recs = []
        if cci["score"] >= 4:
            recs.append("High comorbidity burden: Establish comprehensive care plan with primary care + relevant specialists. Advance care planning discussion recommended.")
        for cluster in clusters:
            if "Cardiorenal-Metabolic" in cluster.get("name", ""):
                recs.append("Cardiorenal-metabolic syndrome: SGLT2 inhibitor (empagliflozin/dapagliflozin) addresses CV, renal, and metabolic risk simultaneously (EMPA-REG, DAPA-HF, CREDENCE).")
        return recs
