"""
Agent 17 — Prescription Agent

Responsibilities:
  - RAG-assisted medication recommendation for chronic disease management
  - Check current medications, allergies, comorbidities
  - Use MCP tools: check_drug_interactions, query_graph_database, vector_search
  - Generate structured prescription recommendation
  - HITL checkpoint: all prescriptions require physician approval
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from base.agent import MCPAgent
from base.tools import (
    check_drug_interactions,
    query_fhir_database,
    query_graph_database,
    vector_search,
)

logger = logging.getLogger("inhealth.agent.prescription")

# Evidence levels
EVIDENCE_LEVELS = {
    "A": "Strong evidence from RCTs or systematic reviews",
    "B": "Moderate evidence from well-designed studies",
    "C": "Consensus or expert opinion",
    "D": "Case series, limited evidence",
}


class PrescriptionAgent(MCPAgent):
    """Agent 17: RAG-assisted medication recommendation with HITL approval."""

    agent_id = 17
    agent_name = "prescription_agent"
    agent_tier = "tier4_intervention"
    system_prompt = (
        "You are the Prescription AI Agent for InHealth Chronic Care. "
        "You generate evidence-based medication recommendations for chronic disease management. "
        "Always check drug interactions, allergies, and contraindications before recommending. "
        "All medication recommendations require physician review and approval (HITL). "
        "Reference ADA 2024, ACC/AHA 2023, KDIGO 2024, JNC-8, and GOLD 2024 guidelines. "
        "Include dosing, monitoring parameters, patient education, and alternatives."
    )

    def _default_tools(self):
        return [
            query_fhir_database,
            check_drug_interactions,
            query_graph_database,
            vector_search,
        ]

    async def analyze(
        self,
        patient_id: str,
        state: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:

        # Fetch current medications, allergies, and conditions
        meds_data = query_fhir_database.invoke({
            "resource_type": "MedicationRequest",
            "patient_id": patient_id,
            "filters": {"limit": 50},
        })
        allergies_data = query_fhir_database.invoke({
            "resource_type": "AllergyIntolerance",
            "patient_id": patient_id,
            "filters": {"limit": 20},
        })
        conditions_data = query_fhir_database.invoke({
            "resource_type": "Condition",
            "patient_id": patient_id,
            "filters": {"limit": 30},
        })
        labs_from_state = state.get("diagnostic_results", {}).get("lab_agent", {}).get("findings", {})

        current_meds = [r.get("value", r.get("code", "")) for r in meds_data.get("resources", [])]
        current_allergies = [r.get("value", "") for r in allergies_data.get("resources", [])]
        current_conditions = [r.get("value", r.get("code", "")) for r in conditions_data.get("resources", [])]

        # Check existing drug interactions
        interaction_result = {}
        if current_meds:
            try:
                interaction_result = check_drug_interactions.invoke({
                    "drug_list": current_meds[:20]
                })
            except Exception as exc:
                logger.warning("Drug interaction check failed: %s", exc)

        # RAG: retrieve guideline-based medication recommendations
        risk_level = (state.get("risk_scores", {}) or {}).get("hospitalization_7d", {}).get("level", "MEDIUM")
        hba1c = (labs_from_state.get("current_labs") or {}).get("hba1c", None)
        egfr = (labs_from_state.get("current_labs") or {}).get("egfr", None)

        try:
            guidelines = vector_search.invoke({
                "query": f"medication management {' '.join(current_conditions[:3])} guideline recommendation first-line second-line",
                "collection": "clinical_guidelines",
                "top_k": 5,
            })
        except Exception as exc:
            logger.warning("Prescription RAG failed: %s", exc)
            guidelines = []

        # Generate recommendation via LLM
        allergies_str = ", ".join(current_allergies) if current_allergies else "None documented"
        conditions_str = ", ".join(current_conditions[:10]) if current_conditions else "None"
        meds_str = ", ".join(current_meds[:20]) if current_meds else "None"
        interactions_str = f"{interaction_result.get('total_interactions', 0)} interactions found" if interaction_result else "Not checked"
        guidelines_str = "\n".join([f"  [{i+1}] {g.get('title', '')}: {g.get('content', '')[:150]}" for i, g in enumerate(guidelines[:3])])

        llm_input = (
            f"Patient {patient_id} medication recommendation request:\n\n"
            f"Current conditions: {conditions_str}\n"
            f"Current medications: {meds_str}\n"
            f"Known allergies: {allergies_str}\n"
            f"Lab values: HbA1c={hba1c}, eGFR={egfr}\n"
            f"Drug interactions: {interactions_str}\n"
            f"Risk level: {risk_level}\n\n"
            f"Evidence-based guidelines retrieved:\n{guidelines_str}\n\n"
            f"Generate structured medication recommendation(s) for medication gaps or optimization:\n"
            f"For each recommendation include:\n"
            f"1. Drug name (generic + brand name)\n"
            f"2. Dose, frequency, route, duration\n"
            f"3. Evidence level (A/B/C) with guideline citation\n"
            f"4. Indication and rationale\n"
            f"5. Monitoring requirements (labs, timing, frequency)\n"
            f"6. Contraindications check against current medications and allergies\n"
            f"7. Patient education points (3-5 key points)\n"
            f"8. Alternative options if first-line not appropriate\n"
            f"9. Expected clinical outcome / benefit\n"
            f"10. Confidence score (0.0-1.0)\n\n"
            f"IMPORTANT: Flag any prescription that modifies existing medications as requiring physician approval (HITL)."
        )

        try:
            llm_result = await self.run_agent_chain(input_text=llm_input)
            prescription_recommendation = llm_result.get("output", "")
        except Exception as exc:
            logger.warning("Prescription LLM failed: %s", exc)
            prescription_recommendation = "Unable to generate recommendation. Manual review required."

        # Structure the recommendation
        recommendation_payload = {
            "recommendation_text": prescription_recommendation,
            "patient_id": patient_id,
            "current_medications": current_meds,
            "current_conditions": current_conditions,
            "allergies": current_allergies,
            "drug_interactions_found": interaction_result.get("total_interactions", 0),
            "has_contraindications": interaction_result.get("has_contraindications", False),
            "guidelines_consulted": len(guidelines),
            "requires_hitl": True,  # All prescriptions require physician approval
            "type": "medication",
        }

        alerts = []
        if interaction_result.get("has_contraindications"):
            alerts.append(self._build_alert(
                severity="HIGH",
                message="CONTRAINDICATED DRUG COMBINATION detected in current medication list. Physician review required before any prescription changes.",
                patient_id=patient_id,
                details={"interactions": interaction_result.get("interactions", [])},
            ))

        # All medication recommendations require HITL
        interventions = list(state.get("interventions", []))
        interventions.append(recommendation_payload)

        return self._build_result(
            status="completed",
            findings=recommendation_payload,
            alerts=alerts,
            recommendations=[
                "HITL REQUIRED: Physician must review and approve all medication recommendations before implementation.",
                f"Drug interactions: {interaction_result.get('total_interactions', 0)} interactions found — review before prescribing.",
            ],
            requires_hitl=True,
        )
