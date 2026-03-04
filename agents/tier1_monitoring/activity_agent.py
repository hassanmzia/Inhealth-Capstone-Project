"""
Agent 3 — Activity Monitoring Agent

Responsibilities:
  - Analyze steps, exercise minutes, sedentary time
  - Detect prolonged inactivity (> 4 hours)
  - Personalized activity coaching recommendations
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from base.agent import MCPAgent
from base.tools import query_fhir_database, send_notification, vector_search

logger = logging.getLogger("inhealth.agent.activity")

# LOINC codes for activity
LOINC_STEPS = "55423-8"               # Daily step count
LOINC_SEDENTARY_MINUTES = "82291-6"   # Sedentary minutes per day
LOINC_EXERCISE_MINUTES = "55411-3"    # Exercise minutes

# Targets (AHA 2024)
DAILY_STEPS_TARGET = 7500
MODERATE_EXERCISE_TARGET_MIN = 150    # per week
SEDENTARY_ALERT_HOURS = 4            # consecutive sedentary hours


class ActivityAgent(MCPAgent):
    """Agent 3: Physical activity monitoring and coaching."""

    agent_id = 3
    agent_name = "activity_agent"
    agent_tier = "tier1_monitoring"
    system_prompt = (
        "You are the Activity Monitoring AI Agent for InHealth Chronic Care. "
        "You analyze wearable device data to track physical activity, detect prolonged inactivity, "
        "and provide personalized coaching. Reference AHA physical activity guidelines (2024). "
        "Be encouraging and specific. Adapt recommendations to the patient's chronic conditions."
    )

    def _default_tools(self):
        return [query_fhir_database, vector_search, send_notification]

    async def analyze(
        self,
        patient_id: str,
        state: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:

        steps_data = query_fhir_database.invoke({
            "resource_type": "Observation",
            "patient_id": patient_id,
            "filters": {"code": LOINC_STEPS, "limit": 7},
        })
        sedentary_data = query_fhir_database.invoke({
            "resource_type": "Observation",
            "patient_id": patient_id,
            "filters": {"code": LOINC_SEDENTARY_MINUTES, "limit": 7},
        })
        exercise_data = query_fhir_database.invoke({
            "resource_type": "Observation",
            "patient_id": patient_id,
            "filters": {"code": LOINC_EXERCISE_MINUTES, "limit": 7},
        })

        steps_7d = self._parse_values(steps_data.get("resources", []))
        sedentary_7d = self._parse_values(sedentary_data.get("resources", []))
        exercise_7d = self._parse_values(exercise_data.get("resources", []))

        today_steps = steps_7d[0] if steps_7d else 0
        avg_steps = sum(steps_7d) / len(steps_7d) if steps_7d else 0
        today_sedentary_min = sedentary_7d[0] if sedentary_7d else 0
        weekly_exercise_min = sum(exercise_7d)

        alerts = []

        # Prolonged inactivity alert
        if today_sedentary_min >= SEDENTARY_ALERT_HOURS * 60:
            alerts.append(self._build_alert(
                severity="NORMAL",
                message=f"Prolonged inactivity: {today_sedentary_min:.0f} minutes sedentary today. Recommend movement break.",
                patient_id=patient_id,
                details={"sedentary_minutes": today_sedentary_min},
            ))
            send_notification.invoke({
                "patient_id": patient_id,
                "notification_type": "ROUTINE",
                "message": "Reminder: You've been sitting for over 4 hours. Take a 5-minute walk to improve blood sugar control and circulation.",
                "channel": "push",
            })

        # Low weekly exercise
        if weekly_exercise_min < MODERATE_EXERCISE_TARGET_MIN:
            alerts.append(self._build_alert(
                severity="NORMAL",
                message=f"Below AHA physical activity target: {weekly_exercise_min:.0f} min/week (target: {MODERATE_EXERCISE_TARGET_MIN} min/week).",
                patient_id=patient_id,
                details={"weekly_exercise_min": weekly_exercise_min},
            ))

        step_achievement_pct = (today_steps / DAILY_STEPS_TARGET * 100) if DAILY_STEPS_TARGET > 0 else 0

        llm_input = (
            f"Patient {patient_id} physical activity data (7-day summary):\n"
            f"  Today's steps: {today_steps:.0f} (target: {DAILY_STEPS_TARGET})\n"
            f"  7-day average steps: {avg_steps:.0f}\n"
            f"  Step goal achievement: {step_achievement_pct:.1f}%\n"
            f"  Today's sedentary time: {today_sedentary_min:.0f} minutes\n"
            f"  Weekly exercise minutes: {weekly_exercise_min:.0f} (AHA target: {MODERATE_EXERCISE_TARGET_MIN})\n"
            f"\nPatient conditions from context: {context.get('patient', {})}\n"
            f"\nProvide:\n"
            f"1. Personalized, encouraging activity coaching message\n"
            f"2. Specific, achievable activity goals for this week\n"
            f"3. Safety considerations given patient's chronic conditions\n"
            f"4. Gamification suggestion (badge or achievement to work toward)"
        )

        try:
            llm_result = await self.run_agent_chain(input_text=llm_input)
            coaching_message = llm_result.get("output", "")
        except Exception as exc:
            logger.warning("Activity LLM coaching failed: %s", exc)
            coaching_message = self._default_coaching(today_steps, weekly_exercise_min)

        return self._build_result(
            status="completed",
            findings={
                "today_steps": today_steps,
                "avg_daily_steps_7d": round(avg_steps, 0),
                "step_goal_percent": round(step_achievement_pct, 1),
                "sedentary_minutes_today": today_sedentary_min,
                "weekly_exercise_minutes": weekly_exercise_min,
                "aha_exercise_target_met": weekly_exercise_min >= MODERATE_EXERCISE_TARGET_MIN,
                "coaching_message": coaching_message,
            },
            alerts=alerts,
            recommendations=[
                "Aim for 7,500+ steps daily (AHA 2024 — associated with 40-53% lower CVD mortality).",
                "150+ minutes moderate aerobic exercise per week reduces HbA1c by ~0.7%.",
                "Break sitting time every 30 minutes with 2-3 minutes of light movement.",
                "Resistance training 2x/week improves insulin sensitivity by 25-30%.",
            ],
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

    def _default_coaching(self, steps: float, exercise_min: float) -> str:
        if steps >= DAILY_STEPS_TARGET:
            return f"Great job! You've reached your daily step goal of {DAILY_STEPS_TARGET:,} steps. Keep it up!"
        deficit = DAILY_STEPS_TARGET - steps
        return (
            f"You're {deficit:,.0f} steps away from your daily goal. "
            f"A short 10-minute walk adds ~1,000 steps. You can do this!"
        )
