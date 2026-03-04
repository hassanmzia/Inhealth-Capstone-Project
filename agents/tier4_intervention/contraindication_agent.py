"""
Agent 18 — Contraindication & Safety Agent

Responsibilities:
  - Backtracking graph search in Neo4j for drug-drug interactions
  - Check drug-disease contraindications
  - Check drug-allergy conflicts
  - Calculate interaction severity (contraindicated/major/moderate/minor)
  - Generate safety alert with intervention recommendations
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from base.agent import MCPAgent
from base.tools import check_drug_interactions, query_fhir_database, query_graph_database, vector_search

logger = logging.getLogger("inhealth.agent.contraindication")

# Severity mapping to alert level
SEVERITY_ALERT_MAP = {
    "contraindicated": "EMERGENCY",
    "major": "HIGH",
    "moderate": "NORMAL",
    "minor": "NORMAL",
}


class ContraindicationAgent(MCPAgent):
    """Agent 18: Drug safety, contraindication, and interaction verification."""

    agent_id = 18
    agent_name = "contraindication_agent"
    agent_tier = "tier4_intervention"
    system_prompt = (
        "You are the Contraindication and Safety AI Agent for InHealth Chronic Care. "
        "You perform comprehensive drug safety analysis including drug-drug interactions, "
        "drug-disease contraindications, and allergy conflicts. Use the knowledge graph backtracking "
        "to identify all potential safety issues. Reference FDA drug interaction labels, "
        "Micromedex, Clinical Pharmacology, and condition-specific contraindication databases."
    )

    def _default_tools(self):
        return [check_drug_interactions, query_fhir_database, query_graph_database, vector_search]

    async def analyze(
        self,
        patient_id: str,
        state: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:

        # Fetch medications and allergies
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

        current_meds = [r.get("value", r.get("code", "")) for r in meds_data.get("resources", []) if r.get("value") or r.get("code")]
        current_allergies = [r.get("value", "") for r in allergies_data.get("resources", []) if r.get("value")]
        current_conditions = [r.get("value", r.get("code", "")) for r in conditions_data.get("resources", []) if r.get("value") or r.get("code")]

        # Also check any proposed medications from prescription agent
        interventions = state.get("interventions", [])
        proposed_meds = []
        for intervention in interventions:
            if intervention.get("type") == "medication":
                proposed = intervention.get("proposed_medications", [])
                proposed_meds.extend(proposed)

        all_meds = list(set(current_meds + proposed_meds))

        alerts = []
        emergency_detected = False

        # 1. Drug-drug interactions
        ddi_result = {}
        if len(all_meds) >= 2:
            try:
                ddi_result = check_drug_interactions.invoke({"drug_list": all_meds})
            except Exception as exc:
                logger.warning("DDI check failed: %s", exc)

        ddi_interactions = ddi_result.get("interactions", [])
        for interaction in ddi_interactions:
            severity = interaction.get("severity", "minor")
            alert_level = SEVERITY_ALERT_MAP.get(severity, "NORMAL")
            if severity == "contraindicated":
                emergency_detected = True

            alerts.append(self._build_alert(
                severity=alert_level,
                message=(
                    f"Drug interaction [{severity.upper()}]: {interaction.get('drug1', '')} ↔ {interaction.get('drug2', '')}. "
                    f"Effect: {interaction.get('clinical_effect', 'N/A')}. "
                    f"Management: {interaction.get('management', 'Monitor closely')}"
                ),
                patient_id=patient_id,
                details=interaction,
            ))

        # 2. Drug-disease contraindications (Neo4j backtracking)
        drug_disease_contraindications = []
        if all_meds and current_conditions:
            try:
                dd_cypher = """
                UNWIND $drugs AS drug
                UNWIND $conditions AS condition
                MATCH (d:Drug {name: drug})-[r:CONTRAINDICATED_IN]->(c:Disease {name: condition})
                RETURN d.name AS drug, c.name AS condition, r.severity AS severity,
                       r.rationale AS rationale, r.alternative AS alternative
                """
                dd_results = query_graph_database.invoke({
                    "cypher_query": dd_cypher,
                    "params": {"drugs": all_meds, "conditions": current_conditions},
                })
                drug_disease_contraindications = dd_results
            except Exception as exc:
                logger.warning("Drug-disease graph query failed: %s", exc)

        for contra in drug_disease_contraindications:
            severity = contra.get("severity", "major")
            if severity == "absolute":
                emergency_detected = True
            alerts.append(self._build_alert(
                severity="EMERGENCY" if severity == "absolute" else "HIGH",
                message=(
                    f"Drug-disease contraindication: {contra.get('drug', '')} contraindicated in {contra.get('condition', '')}. "
                    f"Rationale: {contra.get('rationale', 'N/A')}. "
                    f"Alternative: {contra.get('alternative', 'Consult physician')}"
                ),
                patient_id=patient_id,
                details=contra,
            ))

        # 3. Drug-allergy conflicts
        allergy_conflicts = []
        for med in all_meds:
            for allergy in current_allergies:
                if allergy.lower() in med.lower() or med.lower() in allergy.lower():
                    allergy_conflicts.append({"drug": med, "allergy": allergy})
                    emergency_detected = True
                    alerts.append(self._build_alert(
                        severity="EMERGENCY",
                        message=f"ALLERGY CONFLICT: {med} — patient has documented allergy to {allergy}. STOP — do not administer.",
                        patient_id=patient_id,
                        details={"drug": med, "allergy": allergy},
                    ))

        # 4. QT-prolonging medication check
        qt_prolonging = self._check_qt_prolonging(all_meds)
        if len(qt_prolonging) >= 2:
            alerts.append(self._build_alert(
                severity="HIGH",
                message=f"Multiple QT-prolonging medications: {', '.join(qt_prolonging)}. Risk of Torsades de Pointes. Monitor QTc interval.",
                patient_id=patient_id,
                details={"qt_prolonging_meds": qt_prolonging},
            ))

        # LLM comprehensive safety narrative
        llm_input = (
            f"Patient {patient_id} medication safety analysis:\n\n"
            f"Current medications: {', '.join(current_meds[:20])}\n"
            f"Proposed medications: {', '.join(proposed_meds)}\n"
            f"Allergies: {', '.join(current_allergies) or 'None'}\n"
            f"Conditions: {', '.join(current_conditions[:10])}\n\n"
            f"Drug-drug interactions found: {len(ddi_interactions)}\n"
            f"Contraindicated pairs: {ddi_result.get('severity_summary', {}).get('contraindicated', 0)}\n"
            f"Drug-disease contraindications: {len(drug_disease_contraindications)}\n"
            f"Allergy conflicts: {len(allergy_conflicts)}\n"
            f"QT-prolonging medications: {qt_prolonging}\n\n"
            f"Provide:\n"
            f"1. Safety priority list (most dangerous issues first)\n"
            f"2. Specific management for each interaction/contraindication\n"
            f"3. Safe alternative medications for contraindicated drugs\n"
            f"4. Required monitoring parameters and frequency\n"
            f"5. Patient counseling points regarding drug safety"
        )

        try:
            llm_result = await self.run_agent_chain(input_text=llm_input)
            safety_narrative = llm_result.get("output", "")
        except Exception as exc:
            logger.warning("Contraindication LLM failed: %s", exc)
            safety_narrative = ""

        return self._build_result(
            status="completed",
            findings={
                "ddi_count": len(ddi_interactions),
                "drug_disease_contraindications": len(drug_disease_contraindications),
                "allergy_conflicts": len(allergy_conflicts),
                "qt_prolonging_meds": qt_prolonging,
                "contraindications": ddi_interactions + drug_disease_contraindications,
                "severity_summary": ddi_result.get("severity_summary", {}),
                "safety_narrative": safety_narrative,
                "meds_analyzed": len(all_meds),
            },
            alerts=alerts,
            recommendations=self._generate_recommendations(ddi_interactions, allergy_conflicts),
            emergency_detected=emergency_detected,
        )

    def _check_qt_prolonging(self, meds: List[str]) -> List[str]:
        """Identify medications known to prolong QT interval."""
        qt_known = [
            "azithromycin", "clarithromycin", "erythromycin",
            "haloperidol", "quetiapine", "risperidone", "olanzapine",
            "amiodarone", "sotalol", "dofetilide",
            "methadone", "ondansetron", "hydroxychloroquine",
            "ciprofloxacin", "levofloxacin", "moxifloxacin",
        ]
        return [med for med in meds if any(qt.lower() in med.lower() for qt in qt_known)]

    def _generate_recommendations(
        self,
        interactions: List[Dict[str, Any]],
        allergy_conflicts: List[Dict[str, Any]],
    ) -> List[str]:
        recs = []
        if allergy_conflicts:
            recs.append("CRITICAL: Remove allergenic medications from order. Document allergy reaction type. Select safe alternative.")
        contraindicated = [i for i in interactions if i.get("severity") == "contraindicated"]
        if contraindicated:
            recs.append(f"CONTRAINDICATED combination(s) detected: {', '.join([i.get('drug1', '') + '+' + i.get('drug2', '') for i in contraindicated[:3]])}. Discontinue and replace with safe alternatives.")
        if not recs:
            recs.append("No critical safety issues identified. Continue current medication regimen with standard monitoring.")
        return recs
