"""
Agent 1 — Glucose Monitoring Agent

Responsibilities:
  - Fetch latest CGM readings from FHIR Observations (LOINC: 2339-0)
  - Run LSTM model for 2-hour glucose prediction
  - Detect patterns: hypoglycemia, hyperglycemia, Somogyi effect, dawn phenomenon
  - Generate time-in-range statistics
  - Send A2A ALERT if glucose < 70 or > 300 mg/dL
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from base.agent import MCPAgent
from base.tools import (
    calculate_risk_score,
    query_fhir_database,
    send_notification,
    vector_search,
)

logger = logging.getLogger("inhealth.agent.glucose")

# LOINC code for continuous glucose monitoring
CGM_LOINC = "2339-0"

# Clinical thresholds (mg/dL)
HYPO_CRITICAL = 54
HYPO_LEVEL1 = 70
HYPER_LEVEL1 = 180
HYPER_CRITICAL = 300

# Time-in-range targets (ADA 2024)
TIR_NORMAL_LOW = 70
TIR_NORMAL_HIGH = 180
TIR_TARGET_PERCENT = 70.0  # ≥70% TIR is target for T2DM


class GlucoseAgent(MCPAgent):
    """Agent 1: Continuous glucose monitoring and pattern detection."""

    agent_id = 1
    agent_name = "glucose_agent"
    agent_tier = "tier1_monitoring"
    system_prompt = (
        "You are the Glucose Monitoring AI Agent for InHealth Chronic Care. "
        "You analyze continuous glucose monitor (CGM) data to detect hypoglycemia, "
        "hyperglycemia, Somogyi effect, and dawn phenomenon. You generate time-in-range "
        "statistics and predict glucose trajectories. Always flag critical values "
        "(< 54 mg/dL or > 300 mg/dL) as EMERGENCY. Cite ADA guidelines."
    )

    def _default_tools(self):
        return [query_fhir_database, calculate_risk_score, vector_search, send_notification]

    async def analyze(
        self,
        patient_id: str,
        state: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Main analysis: fetch CGM data, detect patterns, predict, generate alerts."""

        # 1. Fetch CGM readings from FHIR
        fhir_result = query_fhir_database.invoke({
            "resource_type": "Observation",
            "patient_id": patient_id,
            "filters": {
                "code": CGM_LOINC,
                "limit": 288,  # Last 24 hours of 5-minute readings
            },
        })

        readings = fhir_result.get("resources", [])

        if not readings:
            logger.info("No CGM readings found for patient %s", patient_id)
            return self._build_result(
                status="no_data",
                findings={"message": "No CGM readings in last 24 hours"},
            )

        # 2. Parse glucose values
        glucose_values = []
        for r in readings:
            try:
                value = float(r.get("value", 0))
                ts = r.get("effective_datetime", "")
                if value > 0:
                    glucose_values.append({"value": value, "timestamp": ts})
            except (ValueError, TypeError):
                continue

        if not glucose_values:
            return self._build_result(
                status="parse_error",
                findings={"message": "Could not parse CGM values"},
            )

        values_only = [g["value"] for g in glucose_values]

        # 3. Current glucose (most recent reading)
        current_glucose = values_only[0]

        # 4. Time-in-range statistics
        tir_stats = self._calculate_tir(values_only)

        # 5. Pattern detection
        patterns = self._detect_patterns(glucose_values)

        # 6. LSTM prediction (via ML service)
        prediction = {}
        try:
            prediction = calculate_risk_score.invoke({
                "patient_id": patient_id,
                "condition": "glucose_2hr_prediction",
                "model_type": "lstm",
            })
        except Exception as exc:
            logger.warning("LSTM prediction failed: %s", exc)
            prediction = {"predicted_glucose_2hr": None, "trend": "unknown"}

        # 7. Generate alerts
        alerts = []
        emergency_detected = False

        if current_glucose < HYPO_CRITICAL:
            emergency_detected = True
            alert = self._build_alert(
                severity="EMERGENCY",
                message=f"CRITICAL HYPOGLYCEMIA: Glucose {current_glucose:.1f} mg/dL (< {HYPO_CRITICAL}). Immediate intervention required.",
                patient_id=patient_id,
                details={"current_glucose": current_glucose, "threshold": HYPO_CRITICAL},
            )
            alerts.append(alert)
            # Send immediate notification
            send_notification.invoke({
                "patient_id": patient_id,
                "notification_type": "CRITICAL",
                "message": f"EMERGENCY: Blood glucose critically low at {current_glucose:.1f} mg/dL. Seek immediate medical attention or call 911.",
                "channel": "sms",
            })

        elif current_glucose < HYPO_LEVEL1:
            alert = self._build_alert(
                severity="HIGH",
                message=f"Hypoglycemia detected: Glucose {current_glucose:.1f} mg/dL (< {HYPO_LEVEL1} mg/dL).",
                patient_id=patient_id,
                details={"current_glucose": current_glucose, "threshold": HYPO_LEVEL1},
            )
            alerts.append(alert)

        elif current_glucose > HYPER_CRITICAL:
            emergency_detected = True
            alert = self._build_alert(
                severity="EMERGENCY",
                message=f"CRITICAL HYPERGLYCEMIA: Glucose {current_glucose:.1f} mg/dL (> {HYPER_CRITICAL}). Risk of DKA/HHS.",
                patient_id=patient_id,
                details={"current_glucose": current_glucose, "threshold": HYPER_CRITICAL},
            )
            alerts.append(alert)

        elif current_glucose > HYPER_LEVEL1:
            alert = self._build_alert(
                severity="NORMAL",
                message=f"Hyperglycemia: Glucose {current_glucose:.1f} mg/dL (> {HYPER_LEVEL1} mg/dL).",
                patient_id=patient_id,
                details={"current_glucose": current_glucose},
            )
            alerts.append(alert)

        # Pattern-specific alerts
        for pattern in patterns:
            if pattern["type"] in ("somogyi_effect", "dawn_phenomenon"):
                alerts.append(self._build_alert(
                    severity="NORMAL",
                    message=f"Pattern detected: {pattern['description']}",
                    patient_id=patient_id,
                    details=pattern,
                ))

        # 8. TIR alert if below target
        if tir_stats["tir_percent"] < TIR_TARGET_PERCENT:
            alerts.append(self._build_alert(
                severity="NORMAL",
                message=(
                    f"Time-in-range suboptimal: {tir_stats['tir_percent']:.1f}% "
                    f"(target ≥{TIR_TARGET_PERCENT}%). ADA recommends TIR ≥70% for T2DM patients."
                ),
                patient_id=patient_id,
                details=tir_stats,
            ))

        # 9. LLM-enhanced clinical narrative
        llm_input = (
            f"Patient {patient_id} CGM summary:\n"
            f"  Current glucose: {current_glucose:.1f} mg/dL\n"
            f"  24-hour mean: {tir_stats['mean_glucose']:.1f} mg/dL\n"
            f"  Time-in-range: {tir_stats['tir_percent']:.1f}%\n"
            f"  Time below range: {tir_stats['tbr_percent']:.1f}%\n"
            f"  Time above range: {tir_stats['tar_percent']:.1f}%\n"
            f"  Glucose variability (CV): {tir_stats['cv_percent']:.1f}%\n"
            f"  Patterns: {[p['type'] for p in patterns]}\n"
            f"  2-hour prediction: {prediction}\n"
            f"\n"
            f"Based on this CGM data, provide:\n"
            f"1. Clinical assessment of glucose control quality\n"
            f"2. Most likely contributing factors to poor control (if applicable)\n"
            f"3. Specific evidence-based recommendations (cite ADA 2024 Standards of Care)\n"
            f"4. Safety alerts and urgency level"
        )

        try:
            llm_result = await self.run_agent_chain(input_text=llm_input)
            clinical_narrative = llm_result.get("output", "")
        except Exception as exc:
            logger.warning("LLM narrative generation failed: %s", exc)
            clinical_narrative = "LLM narrative unavailable."

        return self._build_result(
            status="completed",
            findings={
                "current_glucose_mgdl": current_glucose,
                "readings_analyzed": len(glucose_values),
                "tir_stats": tir_stats,
                "patterns_detected": patterns,
                "prediction_2hr": prediction,
                "clinical_narrative": clinical_narrative,
            },
            alerts=alerts,
            recommendations=self._generate_recommendations(
                current_glucose=current_glucose,
                tir_stats=tir_stats,
                patterns=patterns,
            ),
            emergency_detected=emergency_detected,
        )

    # ── Pattern detection ──────────────────────────────────────────────────

    def _calculate_tir(self, values: List[float]) -> Dict[str, float]:
        """Calculate ADA-standard time-in-range metrics."""
        if not values:
            return {
                "tir_percent": 0.0,
                "tbr_percent": 0.0,
                "tar_percent": 0.0,
                "mean_glucose": 0.0,
                "cv_percent": 0.0,
                "estimated_hba1c": 0.0,
            }

        n = len(values)
        tir = sum(1 for v in values if TIR_NORMAL_LOW <= v <= TIR_NORMAL_HIGH)
        tbr = sum(1 for v in values if v < TIR_NORMAL_LOW)
        tar = sum(1 for v in values if v > TIR_NORMAL_HIGH)
        mean_val = sum(values) / n

        # Coefficient of variation (%)
        variance = sum((v - mean_val) ** 2 for v in values) / n
        std_dev = variance ** 0.5
        cv = (std_dev / mean_val * 100) if mean_val > 0 else 0.0

        # Estimated HbA1c using Nathan 2008 formula: HbA1c = (mean_glucose + 46.7) / 28.7
        estimated_hba1c = (mean_val + 46.7) / 28.7

        return {
            "tir_percent": round(tir / n * 100, 1),
            "tbr_percent": round(tbr / n * 100, 1),
            "tar_percent": round(tar / n * 100, 1),
            "mean_glucose": round(mean_val, 1),
            "std_dev": round(std_dev, 1),
            "cv_percent": round(cv, 1),
            "estimated_hba1c": round(estimated_hba1c, 1),
            "sample_count": n,
        }

    def _detect_patterns(self, glucose_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Detect Somogyi effect, dawn phenomenon, and other glucose patterns."""
        patterns = []
        values = [g["value"] for g in glucose_data]

        if len(values) < 12:
            return patterns

        # Dawn phenomenon: glucose rises in early morning (4-8 AM) without prior hypo
        # Simplified: check for rise in positions 48-96 of a 288-reading dataset
        # In production this would parse timestamps properly
        dawn_window = values[48:96] if len(values) >= 96 else []
        if dawn_window and len(dawn_window) >= 2:
            dawn_rise = dawn_window[-1] - dawn_window[0]
            if dawn_rise > 30 and min(dawn_window) >= HYPO_LEVEL1:
                patterns.append({
                    "type": "dawn_phenomenon",
                    "description": f"Dawn phenomenon detected: glucose rose {dawn_rise:.1f} mg/dL in early morning hours without preceding hypoglycemia.",
                    "glucose_rise_mgdl": round(dawn_rise, 1),
                    "recommendation": "Consider basal insulin dose adjustment or evening snack modification.",
                })

        # Somogyi effect: rebound hyperglycemia following nocturnal hypoglycemia
        nocturnal = values[24:72] if len(values) >= 72 else []
        if nocturnal:
            min_nocturnal = min(nocturnal)
            if min_nocturnal < HYPO_LEVEL1:
                post_hypo_idx = nocturnal.index(min_nocturnal)
                post_values = nocturnal[post_hypo_idx:post_hypo_idx + 12]
                if post_values and max(post_values) > HYPER_LEVEL1:
                    patterns.append({
                        "type": "somogyi_effect",
                        "description": f"Somogyi effect suspected: nocturnal hypoglycemia ({min_nocturnal:.1f} mg/dL) followed by rebound hyperglycemia.",
                        "nadir_glucose": round(min_nocturnal, 1),
                        "rebound_glucose": round(max(post_values), 1),
                        "recommendation": "Reduce evening insulin dose; add bedtime snack. Confirm with continuous monitoring.",
                    })

        # Glucose variability spike
        if len(values) >= 12:
            rolling_diffs = [abs(values[i] - values[i-1]) for i in range(1, min(12, len(values)))]
            max_diff = max(rolling_diffs)
            if max_diff > 50:
                patterns.append({
                    "type": "high_variability",
                    "description": f"High glucose variability detected: max 5-minute change of {max_diff:.1f} mg/dL.",
                    "max_delta_mgdl": round(max_diff, 1),
                    "recommendation": "Review meal timing, portion sizes, and insulin-to-carb ratio.",
                })

        return patterns

    def _generate_recommendations(
        self,
        current_glucose: float,
        tir_stats: Dict[str, float],
        patterns: List[Dict[str, Any]],
    ) -> List[str]:
        """Generate evidence-based clinical recommendations."""
        recs = []

        if current_glucose < HYPO_LEVEL1:
            recs.append("IMMEDIATE: Consume 15g fast-acting carbohydrates (Rule of 15). Recheck glucose in 15 minutes. (ADA 2024)")
        elif current_glucose > HYPER_CRITICAL:
            recs.append("URGENT: Check ketones. Consider emergency insulin correction. Seek immediate medical attention if ketones positive.")

        if tir_stats.get("tir_percent", 100) < TIR_TARGET_PERCENT:
            recs.append(f"Glycemic optimization needed: TIR {tir_stats['tir_percent']:.1f}% (target ≥70%). Review medication regimen with endocrinologist.")

        if tir_stats.get("cv_percent", 0) > 36:
            recs.append("High glucose variability (CV >36%): Review meal consistency, carbohydrate counting accuracy, and insulin timing.")

        estimated_a1c = tir_stats.get("estimated_hba1c", 0)
        if estimated_a1c > 8.0:
            recs.append(f"Estimated HbA1c {estimated_a1c:.1f}%: Consider medication intensification per ADA Standards of Care.")

        for p in patterns:
            if "recommendation" in p:
                recs.append(p["recommendation"])

        return recs
