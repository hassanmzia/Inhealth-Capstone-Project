"""
Agent 12 — SDOH Risk Agent

Responsibilities:
  - Retrieve SDOH assessment from database
  - Calculate composite SDOH risk score
  - RAG: retrieve SDOH intervention resources (food banks, transportation, housing)
  - Generate social work referral recommendations
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from base.agent import MCPAgent
from base.tools import query_fhir_database, vector_search

logger = logging.getLogger("inhealth.agent.sdoh")

# SDOH domains and their clinical impact weights
SDOH_DOMAINS = {
    "food_insecurity": {"weight": 2.0, "loinc": "88122-7"},
    "housing_instability": {"weight": 2.0, "loinc": "71802-3"},
    "transportation_need": {"weight": 1.5, "loinc": "93030-5"},
    "financial_strain": {"weight": 1.5, "loinc": "77594-0"},
    "social_isolation": {"weight": 1.5, "loinc": "93025-5"},
    "health_literacy_low": {"weight": 1.0, "loinc": ""},
    "unsafe_neighborhood": {"weight": 1.0, "loinc": ""},
    "domestic_violence": {"weight": 2.5, "loinc": "76499-3"},
    "substance_use": {"weight": 2.0, "loinc": "68517-2"},
    "mental_health_need": {"weight": 1.5, "loinc": "44249-1"},
}

# Max possible score
MAX_SDOH_SCORE = sum(d["weight"] for d in SDOH_DOMAINS.values())


class SDOHAgent(MCPAgent):
    """Agent 12: Social Determinants of Health risk assessment and resource matching."""

    agent_id = 12
    agent_name = "sdoh_agent"
    agent_tier = "tier3_risk"
    system_prompt = (
        "You are the Social Determinants of Health (SDOH) AI Agent for InHealth Chronic Care. "
        "You assess social, economic, and environmental factors affecting patient health outcomes. "
        "Calculate composite SDOH risk scores and match patients with community resources. "
        "Reference NACHC PRAPARE assessment tool, AHC Health-Related Social Needs screening, "
        "and Healthy People 2030 SDOH framework."
    )

    def _default_tools(self):
        return [query_fhir_database, vector_search]

    async def analyze(
        self,
        patient_id: str,
        state: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:

        # Fetch SDOH observations from FHIR (structured screening responses)
        sdoh_data = query_fhir_database.invoke({
            "resource_type": "Observation",
            "patient_id": patient_id,
            "filters": {"limit": 30},
        })

        # Also fetch QuestionnaireResponse for PRAPARE / AHC screening
        questionnaire_data = query_fhir_database.invoke({
            "resource_type": "QuestionnaireResponse",
            "patient_id": patient_id,
            "filters": {"limit": 5},
        })

        # Parse SDOH screen results
        sdoh_screen = self._parse_sdoh_screen(sdoh_data.get("resources", []))
        questionnaire_results = self._parse_questionnaire(questionnaire_data.get("resources", []))

        # Merge
        combined_sdoh = {**sdoh_screen, **questionnaire_results}

        # Calculate composite SDOH score
        sdoh_score_result = self._calculate_sdoh_score(combined_sdoh)

        # RAG: retrieve matching community resources
        needs_list = [domain for domain, present in combined_sdoh.items() if present]
        resources = []
        if needs_list:
            try:
                patient_location = context.get("patient", {}).get("location", {})
                location_str = f"{patient_location.get('city', '')} {patient_location.get('state', '')}"
                resources = vector_search.invoke({
                    "query": f"community resources {' '.join(needs_list[:3])} {location_str}",
                    "collection": "community_resources",
                    "top_k": 5,
                })
            except Exception as exc:
                logger.warning("SDOH resource RAG failed: %s", exc)

        alerts = []
        if sdoh_score_result["risk_level"] in ("HIGH", "CRITICAL"):
            alerts.append(self._build_alert(
                severity="HIGH",
                message=f"High SDOH risk: Score {sdoh_score_result['score']:.1f}/{MAX_SDOH_SCORE:.1f} ({sdoh_score_result['risk_level']}). Social work referral recommended.",
                patient_id=patient_id,
                details=sdoh_score_result,
            ))

        if combined_sdoh.get("domestic_violence"):
            alerts.append(self._build_alert(
                severity="HIGH",
                message="Domestic violence/safety concern identified. Immediate social work consultation and safety planning required.",
                patient_id=patient_id,
                details={"domain": "domestic_violence"},
            ))

        if combined_sdoh.get("food_insecurity"):
            alerts.append(self._build_alert(
                severity="NORMAL",
                message="Food insecurity identified. Link to food assistance programs. Consider nutrition counseling. Food insecurity increases HbA1c by 0.5-1.0%.",
                patient_id=patient_id,
                details={"domain": "food_insecurity"},
            ))

        # LLM intervention planning
        needs_formatted = "\n".join([f"  - {n.replace('_', ' ').title()}" for n in needs_list]) or "  No significant SDOH needs identified"
        resources_formatted = "\n".join([f"  - {r.get('title', 'Resource')}: {r.get('content', '')[:100]}" for r in resources[:3]])

        llm_input = (
            f"Patient {patient_id} SDOH assessment:\n\n"
            f"Identified social needs:\n{needs_formatted}\n\n"
            f"SDOH Risk Score: {sdoh_score_result['score']:.1f}/{MAX_SDOH_SCORE:.1f} ({sdoh_score_result['risk_level']})\n\n"
            f"Available community resources:\n{resources_formatted}\n\n"
            f"Provide:\n"
            f"1. Prioritized SDOH intervention plan (highest health impact first)\n"
            f"2. Specific community resource referrals with contact information\n"
            f"3. Trauma-informed, culturally sensitive communication approach\n"
            f"4. Impact of unaddressed SDOH on chronic disease control\n"
            f"5. Social work referral urgency and scope"
        )

        try:
            llm_result = await self.run_agent_chain(input_text=llm_input)
            intervention_plan = llm_result.get("output", "")
        except Exception as exc:
            logger.warning("SDOH LLM analysis failed: %s", exc)
            intervention_plan = ""

        return self._build_result(
            status="completed",
            findings={
                "sdoh_needs": combined_sdoh,
                "needs_count": len(needs_list),
                "sdoh_score": sdoh_score_result,
                "community_resources": resources,
                "intervention_plan": intervention_plan,
            },
            alerts=alerts,
            recommendations=self._generate_recommendations(needs_list, sdoh_score_result),
        )

    def _parse_sdoh_screen(self, resources: List[Dict[str, Any]]) -> Dict[str, bool]:
        """Parse FHIR Observation resources for SDOH screening results."""
        screen: Dict[str, bool] = {domain: False for domain in SDOH_DOMAINS}
        for r in resources:
            code = r.get("code", "")
            value = r.get("value", "")
            for domain, info in SDOH_DOMAINS.items():
                if code == info.get("loinc") and value in ("positive", "yes", "1", "true"):
                    screen[domain] = True
        return screen

    def _parse_questionnaire(self, resources: List[Dict[str, Any]]) -> Dict[str, bool]:
        """Parse QuestionnaireResponse for PRAPARE-style SDOH screens."""
        result: Dict[str, bool] = {}
        for r in resources:
            meta = r.get("meta", {})
            answers = meta.get("answers", {}) if isinstance(meta, dict) else {}
            for domain in SDOH_DOMAINS:
                if answers.get(domain) in (True, "yes", 1, "positive"):
                    result[domain] = True
        return result

    def _calculate_sdoh_score(self, sdoh: Dict[str, bool]) -> Dict[str, Any]:
        """Calculate weighted SDOH composite score."""
        score = 0.0
        active_needs = []
        for domain, present in sdoh.items():
            if present and domain in SDOH_DOMAINS:
                weight = SDOH_DOMAINS[domain]["weight"]
                score += weight
                active_needs.append(domain)

        percentage = (score / MAX_SDOH_SCORE) * 100

        if percentage >= 50:
            risk_level = "CRITICAL"
        elif percentage >= 30:
            risk_level = "HIGH"
        elif percentage >= 15:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"

        return {
            "score": round(score, 2),
            "max_score": MAX_SDOH_SCORE,
            "percentage": round(percentage, 1),
            "risk_level": risk_level,
            "active_needs": active_needs,
        }

    def _generate_recommendations(
        self,
        needs: List[str],
        score_result: Dict[str, Any],
    ) -> List[str]:
        recs = []
        if "food_insecurity" in needs:
            recs.append("Food insecurity: Refer to local food bank, SNAP enrollment assistance, and diabetes-appropriate nutrition programs.")
        if "housing_instability" in needs:
            recs.append("Housing instability: Social work referral for housing assistance. Unstable housing is associated with 2× hospital readmission risk.")
        if "transportation_need" in needs:
            recs.append("Transportation need: Connect with medical transportation services. Consider telehealth as alternative for routine visits.")
        if score_result.get("risk_level") in ("HIGH", "CRITICAL"):
            recs.append("High SDOH burden: Assign dedicated care coordinator. Monthly social work follow-up. CHW (Community Health Worker) engagement.")
        return recs
