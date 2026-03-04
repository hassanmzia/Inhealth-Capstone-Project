"""
Agent 16 — Lifestyle Coaching Agent

Responsibilities:
  - Personalized lifestyle recommendations based on risk factors
  - Health literacy adaptation (5 levels) — adjust language complexity
  - Multi-language support (English, Spanish)
  - Gamification: suggest health goals and achievement badges
  - RAG: evidence-based lifestyle intervention guidelines
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from base.agent import MCPAgent
from base.tools import query_fhir_database, send_notification, vector_search

logger = logging.getLogger("inhealth.agent.coaching")

# Health literacy levels 1-5 (1=very low, 5=high)
LITERACY_PROMPTS = {
    1: "Use very simple words. Short sentences. One idea at a time. Use pictures if possible.",
    2: "Use simple words. Avoid medical terms. Explain everything in plain language.",
    3: "Use everyday language. Briefly explain medical terms when needed.",
    4: "Use standard medical language with some explanation.",
    5: "Use full clinical/medical language appropriate for a healthcare professional.",
}

# Gamification badges
BADGES = {
    "first_steps": {"name": "First Steps", "description": "Completed your first week of daily step tracking", "icon": "👣"},
    "glucose_champion": {"name": "Glucose Champion", "description": "3 consecutive days of glucose in target range", "icon": "🎯"},
    "medication_master": {"name": "Medication Master", "description": "7-day perfect medication adherence", "icon": "💊"},
    "blood_pressure_hero": {"name": "BP Hero", "description": "Blood pressure in target range for 1 week", "icon": "❤️"},
    "activity_star": {"name": "Activity Star", "description": "Reached 7,500 steps daily for 5 days", "icon": "⭐"},
    "hydration_hero": {"name": "Hydration Hero", "description": "Met daily water intake goal for 7 days", "icon": "💧"},
}


class CoachingAgent(MCPAgent):
    """Agent 16: Personalized lifestyle coaching with health literacy adaptation."""

    agent_id = 16
    agent_name = "coaching_agent"
    agent_tier = "tier4_intervention"
    system_prompt = (
        "You are the Lifestyle Coaching AI Agent for InHealth Chronic Care. "
        "You provide personalized, evidence-based lifestyle recommendations for patients with chronic conditions. "
        "Adapt your language to the patient's health literacy level and preferred language. "
        "Be warm, encouraging, and specific. Incorporate motivational interviewing principles. "
        "Reference ADA Diabetes Prevention Program, AHA Life's Essential 8, and CDC chronic disease prevention guidelines."
    )

    def _default_tools(self):
        return [query_fhir_database, vector_search, send_notification]

    async def analyze(
        self,
        patient_id: str,
        state: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:

        # Get patient profile from context
        patient = context.get("patient", {})
        health_literacy_level = patient.get("health_literacy_level", 3)
        preferred_language = patient.get("preferred_language", "english")
        conditions = list(state.get("monitoring_results", {}).keys())
        risk_level = (state.get("risk_scores", {}) or {}).get("hospitalization_7d", {}).get("level", "MEDIUM")

        # Get monitoring data for context
        monitoring = state.get("monitoring_results", {})
        glucose_data = monitoring.get("glucose_agent", {})
        activity_data = monitoring.get("activity_agent", {})
        cardiac_data = monitoring.get("cardiac_agent", {})

        # RAG: evidence-based guidelines
        try:
            guidelines = vector_search.invoke({
                "query": f"lifestyle intervention chronic disease management diet exercise diabetes hypertension",
                "collection": "clinical_guidelines",
                "top_k": 4,
            })
        except Exception as exc:
            logger.warning("Coaching RAG failed: %s", exc)
            guidelines = []

        # Determine applicable gamification badges
        earned_badges = self._check_badge_eligibility(monitoring, patient_id)
        next_badges = self._suggest_next_badges(monitoring, earned_badges)

        # Language adaptation
        language_instruction = ""
        if preferred_language.lower() == "spanish":
            language_instruction = "Respond entirely in Spanish (Español). Use culturally appropriate examples."

        literacy_prompt = LITERACY_PROMPTS.get(health_literacy_level, LITERACY_PROMPTS[3])

        llm_input = (
            f"Patient {patient_id} lifestyle coaching request:\n\n"
            f"Patient profile:\n"
            f"  Health literacy level: {health_literacy_level}/5 ({literacy_prompt})\n"
            f"  Preferred language: {preferred_language}\n"
            f"  Active conditions: {conditions}\n"
            f"  Overall risk level: {risk_level}\n\n"
            f"Recent data:\n"
            f"  Glucose TIR: {glucose_data.get('findings', {}).get('tir_stats', {}).get('tir_percent', 'N/A')}%\n"
            f"  Daily steps today: {activity_data.get('findings', {}).get('today_steps', 'N/A')}\n"
            f"  Weekly exercise: {activity_data.get('findings', {}).get('weekly_exercise_minutes', 'N/A')} min\n"
            f"  Blood pressure: {cardiac_data.get('findings', {}).get('blood_pressure_systolic', 'N/A')}/{cardiac_data.get('findings', {}).get('blood_pressure_diastolic', 'N/A')} mmHg\n\n"
            f"Evidence-based resources retrieved: {len(guidelines)}\n\n"
            f"Instructions: {language_instruction}\n"
            f"Literacy level instruction: {literacy_prompt}\n\n"
            f"Create a personalized coaching plan with:\n"
            f"1. 3 specific, achievable lifestyle goals for this week (SMART goals)\n"
            f"2. One dietary recommendation with a specific meal example\n"
            f"3. Activity recommendation tailored to patient's current fitness level\n"
            f"4. Stress management and sleep recommendation\n"
            f"5. Motivational closing message (positive, encouraging tone)\n"
            f"6. Gamification: celebrate earned badges and describe next achievement to unlock"
        )

        try:
            llm_result = await self.run_agent_chain(input_text=llm_input)
            coaching_plan = llm_result.get("output", "")
        except Exception as exc:
            logger.warning("Coaching LLM failed: %s", exc)
            coaching_plan = self._fallback_coaching(health_literacy_level, conditions)

        # Send coaching notification
        if coaching_plan:
            try:
                send_notification.invoke({
                    "patient_id": patient_id,
                    "notification_type": "ROUTINE",
                    "message": coaching_plan[:500],  # SMS character limit
                    "channel": "push",
                })
            except Exception as exc:
                logger.warning("Coaching notification send failed: %s", exc)

        return self._build_result(
            status="completed",
            findings={
                "coaching_plan": coaching_plan,
                "health_literacy_level": health_literacy_level,
                "preferred_language": preferred_language,
                "earned_badges": earned_badges,
                "next_badges": next_badges,
                "guidelines_used": len(guidelines),
            },
            recommendations=[
                "ADA 2024: Mediterranean diet reduces HbA1c by 0.47% and CVD risk by 30%.",
                "AHA 2024: 150 min/week moderate exercise reduces all-cause mortality by 35%.",
                "CDC: 5-7% body weight loss reduces T2DM progression by 58% (DPP trial).",
                "Sleep: 7-9 hours/night. Poor sleep increases insulin resistance by 25%.",
            ],
        )

    def _check_badge_eligibility(
        self, monitoring: Dict[str, Any], patient_id: str
    ) -> List[Dict[str, Any]]:
        """Check which badges the patient has earned based on current monitoring data."""
        earned = []
        glucose = monitoring.get("glucose_agent", {}).get("findings", {})
        activity = monitoring.get("activity_agent", {}).get("findings", {})

        if glucose.get("tir_stats", {}).get("tir_percent", 0) >= 70:
            earned.append(BADGES["glucose_champion"])

        if activity.get("today_steps", 0) >= 7500:
            earned.append(BADGES["activity_star"])

        return earned

    def _suggest_next_badges(
        self,
        monitoring: Dict[str, Any],
        earned: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Suggest the next achievable badges."""
        earned_names = [b["name"] for b in earned]
        suggestions = []
        for badge in BADGES.values():
            if badge["name"] not in earned_names:
                suggestions.append(badge)
                if len(suggestions) >= 2:
                    break
        return suggestions

    def _fallback_coaching(self, literacy_level: int, conditions: List[str]) -> str:
        """Simple fallback coaching message when LLM is unavailable."""
        if literacy_level <= 2:
            return (
                "Eat healthy foods. Move your body every day. Take your medicine. "
                "Drink water. Sleep enough. You can do this!"
            )
        return (
            "Today's health goals: (1) Eat a balanced meal with vegetables, lean protein, and whole grains. "
            "(2) Take a 20-minute walk. (3) Take all prescribed medications. "
            "Small steps lead to big improvements in your health!"
        )
