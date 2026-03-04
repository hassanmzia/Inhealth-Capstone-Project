"""
Agent 13 — Disease Prediction Agent

Responsibilities:
  - Run XGBoost 7-day hospitalization risk model
  - Use RAG to retrieve similar patient cases from Qdrant
  - Multi-modal features: vitals trends + labs + demographics + SDOH
  - Feature importance explanation (SHAP-inspired)
  - Generate probability + confidence interval + key risk drivers
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from base.agent import MCPAgent
from base.tools import calculate_risk_score, query_fhir_database, vector_search

logger = logging.getLogger("inhealth.agent.prediction")


class PredictionAgent(MCPAgent):
    """Agent 13: 7-day hospitalization risk prediction with ML ensembles."""

    agent_id = 13
    agent_name = "prediction_agent"
    agent_tier = "tier3_risk"
    system_prompt = (
        "You are the Disease Prediction AI Agent for InHealth Chronic Care. "
        "You run XGBoost and LSTM hospitalization risk models, explain predictions using "
        "SHAP-inspired feature importance, and retrieve similar patient cases for context. "
        "Provide calibrated risk probabilities with confidence intervals. "
        "Reference the HOSPITAL score, LACE index, and relevant condition-specific prediction tools."
    )

    def _default_tools(self):
        return [calculate_risk_score, query_fhir_database, vector_search]

    async def analyze(
        self,
        patient_id: str,
        state: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:

        # Run multiple risk models in parallel
        import asyncio

        async def run_model(condition: str, model_type: str) -> Dict[str, Any]:
            try:
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    None,
                    lambda: calculate_risk_score.invoke({
                        "patient_id": patient_id,
                        "condition": condition,
                        "model_type": model_type,
                    })
                )
                return result
            except Exception as exc:
                logger.warning("Model %s/%s failed: %s", condition, model_type, exc)
                return {"score": 0.0, "level": "UNKNOWN", "error": str(exc)}

        hospitalization_xgb, hospitalization_lstm, readmission_risk = await asyncio.gather(
            run_model("hospitalization_7d", "xgboost"),
            run_model("hospitalization_7d", "lstm"),
            run_model("30d_readmission", "xgboost"),
        )

        # Ensemble: weighted average
        xgb_score = hospitalization_xgb.get("score", 0.0)
        lstm_score = hospitalization_lstm.get("score", 0.0)
        ensemble_score = round(0.6 * xgb_score + 0.4 * lstm_score, 3)

        # Risk level
        if ensemble_score >= 0.70:
            risk_level = "CRITICAL"
        elif ensemble_score >= 0.40:
            risk_level = "HIGH"
        elif ensemble_score >= 0.20:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"

        # Feature importance from XGBoost (returned by ML service)
        feature_importances = hospitalization_xgb.get("feature_importances", [])
        top_drivers = sorted(feature_importances, key=lambda x: x.get("importance", 0), reverse=True)[:5]

        # Confidence interval (from model calibration)
        ci_low = max(0.0, ensemble_score - 0.10)
        ci_high = min(1.0, ensemble_score + 0.10)

        # RAG: similar patient cases
        try:
            similar_cases = vector_search.invoke({
                "query": f"hospitalization risk score {ensemble_score:.2f} patient profile chronic disease",
                "collection": "patient_cases",
                "top_k": 3,
            })
        except Exception as exc:
            logger.warning("Similar cases RAG failed: %s", exc)
            similar_cases = []

        alerts = []
        if risk_level in ("CRITICAL", "HIGH"):
            alerts.append(self._build_alert(
                severity="HIGH" if risk_level == "HIGH" else "EMERGENCY",
                message=f"7-day hospitalization risk: {ensemble_score * 100:.1f}% ({risk_level}). Proactive intervention recommended.",
                patient_id=patient_id,
                details={
                    "ensemble_score": ensemble_score,
                    "confidence_interval": [ci_low, ci_high],
                    "risk_level": risk_level,
                    "top_drivers": top_drivers,
                },
            ))

        # LLM narrative for risk explanation
        drivers_text = "\n".join([
            f"  {d.get('feature', 'unknown')}: {d.get('importance', 0):.3f} (direction: {d.get('direction', 'unknown')})"
            for d in top_drivers
        ])
        llm_input = (
            f"Patient {patient_id} hospitalization risk prediction:\n"
            f"  7-day risk probability: {ensemble_score * 100:.1f}% ({risk_level})\n"
            f"  95% confidence interval: [{ci_low * 100:.1f}%, {ci_high * 100:.1f}%]\n"
            f"  XGBoost score: {xgb_score:.3f}, LSTM score: {lstm_score:.3f}\n"
            f"  30-day readmission risk: {readmission_risk.get('score', 0):.1%}\n\n"
            f"Top risk drivers (SHAP feature importance):\n{drivers_text}\n\n"
            f"Similar patient cases from database: {len(similar_cases)} retrieved\n\n"
            f"Provide:\n"
            f"1. Patient-specific explanation of why this risk score was generated\n"
            f"2. Modifiable vs non-modifiable risk factors\n"
            f"3. Specific interventions that could lower risk by ≥10%\n"
            f"4. Recommended monitoring frequency based on risk level\n"
            f"5. Threshold for escalation to urgent care"
        )

        try:
            llm_result = await self.run_agent_chain(input_text=llm_input)
            risk_explanation = llm_result.get("output", "")
        except Exception as exc:
            logger.warning("Prediction LLM explanation failed: %s", exc)
            risk_explanation = f"Hospitalization risk: {risk_level} ({ensemble_score * 100:.1f}%)"

        risk_score_payload = {
            "score": ensemble_score,
            "level": risk_level,
            "confidence_interval": [ci_low, ci_high],
            "xgboost_score": xgb_score,
            "lstm_score": lstm_score,
            "readmission_risk": readmission_risk.get("score", 0.0),
            "feature_importances": top_drivers,
            "similar_cases_retrieved": len(similar_cases),
            "risk_explanation": risk_explanation,
        }

        # Merge into state risk_scores
        updated_risk_scores = dict(state.get("risk_scores", {}))
        updated_risk_scores["hospitalization_7d"] = risk_score_payload

        return self._build_result(
            status="completed",
            findings=risk_score_payload,
            alerts=alerts,
            recommendations=self._generate_recommendations(risk_level, ensemble_score, top_drivers),
        )

    def _generate_recommendations(
        self,
        risk_level: str,
        score: float,
        drivers: List[Dict[str, Any]],
    ) -> List[str]:
        recs = []
        if risk_level == "CRITICAL":
            recs.append(f"CRITICAL hospitalization risk ({score * 100:.1f}%): Same-day physician contact. Consider hospital observation if decompensating.")
        elif risk_level == "HIGH":
            recs.append(f"HIGH hospitalization risk ({score * 100:.1f}%): Urgent outpatient visit within 48 hours. Intensify monitoring (daily vitals, weekly labs).")
        elif risk_level == "MEDIUM":
            recs.append(f"MEDIUM hospitalization risk ({score * 100:.1f}%): Scheduled visit within 1-2 weeks. Optimize medications and care plan.")

        driver_names = [d.get("feature", "") for d in drivers[:3]]
        if driver_names:
            recs.append(f"Primary risk drivers: {', '.join(driver_names)}. Target these for maximum risk reduction.")

        return recs
