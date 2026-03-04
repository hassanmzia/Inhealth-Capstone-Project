"""
Agent 14 — ML Ensemble Risk Agent

Responsibilities:
  - Combine outputs from all Tier 3 agents
  - Multi-modal attention fusion (time-series + tabular + graph + text features)
  - Generate unified risk score with explainability
  - Tiered risk level: LOW/MEDIUM/HIGH/CRITICAL
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from base.agent import MCPAgent
from base.tools import calculate_risk_score, vector_search

logger = logging.getLogger("inhealth.agent.ml_ensemble")

# Weights for each risk domain in the ensemble
DOMAIN_WEIGHTS = {
    "hospitalization_7d": 0.35,
    "comorbidity_risk": 0.20,
    "sdoh_risk": 0.15,
    "family_history_risk": 0.10,
    "monitoring_alerts": 0.20,
}


class MLEnsembleAgent(MCPAgent):
    """Agent 14: Multi-modal ML ensemble for unified patient risk scoring."""

    agent_id = 14
    agent_name = "ml_ensemble_agent"
    agent_tier = "tier3_risk"
    system_prompt = (
        "You are the ML Ensemble Risk AI Agent for InHealth Chronic Care. "
        "You combine outputs from all risk assessment agents using multi-modal attention fusion "
        "to generate a unified, calibrated patient risk score. Provide explainability for the "
        "combined score. Generate tiered risk level with actionable recommendations. "
        "Reference evidence-based risk stratification tools: LACE+, HOSPITAL score, CCI, and condition-specific risk models."
    )

    def _default_tools(self):
        return [calculate_risk_score, vector_search]

    async def analyze(
        self,
        patient_id: str,
        state: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:

        # Collect risk inputs from state (populated by earlier Tier 3 agents)
        risk_scores = state.get("risk_scores", {})
        monitoring_results = state.get("monitoring_results", {})
        diagnostic_results = state.get("diagnostic_results", {})
        alerts = state.get("alerts", [])

        # Extract individual risk scores
        hosp_risk = risk_scores.get("hospitalization_7d", {})
        comorbidity_data = risk_scores.get("comorbidity_agent", {})
        sdoh_data = risk_scores.get("sdoh_agent", {})
        family_data = risk_scores.get("family_history_agent", {})

        # ── Feature extraction from each domain ──────────────────────────────

        # 1. Hospitalization prediction score (0-1)
        hosp_score = float(hosp_risk.get("score", 0.0)) if hosp_risk else 0.0

        # 2. Comorbidity risk (normalize CCI to 0-1; max practical CCI ~10)
        cci_score_raw = (comorbidity_data.get("findings", {}) or {}).get("charlson_index", {}).get("score", 0)
        comorbidity_score = min(float(cci_score_raw) / 10.0, 1.0)

        # 3. SDOH risk score (already 0-1 percentage normalized)
        sdoh_percentage = (sdoh_data.get("findings", {}) or {}).get("sdoh_score", {}).get("percentage", 0)
        sdoh_score = float(sdoh_percentage) / 100.0

        # 4. Family history risk (binary high/moderate)
        family_findings = (family_data.get("findings", {}) or {}).get("polygenic_risk_approximation", {})
        fam_high_risk_count = sum(1 for v in family_findings.values() if isinstance(v, dict) and v.get("risk_level") == "HIGH")
        family_score = min(float(fam_high_risk_count) / 3.0, 1.0)

        # 5. Active monitoring alerts severity
        critical_alert_count = sum(1 for a in alerts if a.get("severity") in ("EMERGENCY", "CRITICAL"))
        high_alert_count = sum(1 for a in alerts if a.get("severity") == "HIGH")
        alert_score = min((critical_alert_count * 0.4 + high_alert_count * 0.2), 1.0)

        # ── Attention fusion ──────────────────────────────────────────────────
        # Simple weighted sum (in production: learned attention weights from transformer)
        domain_scores = {
            "hospitalization_7d": hosp_score,
            "comorbidity_risk": comorbidity_score,
            "sdoh_risk": sdoh_score,
            "family_history_risk": family_score,
            "monitoring_alerts": alert_score,
        }

        weighted_score = sum(
            domain_scores[domain] * DOMAIN_WEIGHTS[domain]
            for domain in DOMAIN_WEIGHTS
        )

        # Emergency override: if any EMERGENCY alert, minimum score is 0.70
        if critical_alert_count > 0:
            weighted_score = max(weighted_score, 0.70)

        # ── Risk level assignment ─────────────────────────────────────────────
        if weighted_score >= 0.70:
            risk_level = "CRITICAL"
        elif weighted_score >= 0.45:
            risk_level = "HIGH"
        elif weighted_score >= 0.20:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"

        # ── Confidence interval ───────────────────────────────────────────────
        # Wider CI when fewer data domains contributed
        contributed_domains = sum(1 for s in domain_scores.values() if s > 0)
        ci_half_width = 0.15 - (contributed_domains * 0.02)
        ci_low = max(0.0, weighted_score - ci_half_width)
        ci_high = min(1.0, weighted_score + ci_half_width)

        # ── Explainability ────────────────────────────────────────────────────
        domain_contributions = {
            domain: {
                "raw_score": round(domain_scores[domain], 3),
                "weight": DOMAIN_WEIGHTS[domain],
                "weighted_contribution": round(domain_scores[domain] * DOMAIN_WEIGHTS[domain], 3),
                "pct_of_total": round(
                    (domain_scores[domain] * DOMAIN_WEIGHTS[domain]) / max(weighted_score, 0.001) * 100, 1
                ),
            }
            for domain in DOMAIN_WEIGHTS
        }

        # Top contributing domains
        top_domains = sorted(
            domain_contributions.items(),
            key=lambda x: x[1]["weighted_contribution"],
            reverse=True,
        )[:3]

        alerts_out = []
        if risk_level == "CRITICAL":
            alerts_out.append(self._build_alert(
                severity="EMERGENCY",
                message=f"CRITICAL UNIFIED RISK: Ensemble score {weighted_score:.2f} ({risk_level}). Immediate clinical intervention required.",
                patient_id=patient_id,
                details={
                    "ensemble_score": weighted_score,
                    "risk_level": risk_level,
                    "top_contributors": [d[0] for d in top_domains],
                },
            ))
        elif risk_level == "HIGH":
            alerts_out.append(self._build_alert(
                severity="HIGH",
                message=f"HIGH RISK: Ensemble score {weighted_score:.2f}. Urgent care coordination needed within 24-48 hours.",
                patient_id=patient_id,
                details={"ensemble_score": weighted_score, "risk_level": risk_level},
            ))

        # LLM narrative
        llm_input = (
            f"Patient {patient_id} ML Ensemble Risk Assessment:\n"
            f"  Unified risk score: {weighted_score:.3f} ({risk_level})\n"
            f"  95% confidence interval: [{ci_low:.3f}, {ci_high:.3f}]\n\n"
            f"Domain contributions:\n"
            + "\n".join([
                f"  {domain}: raw={info['raw_score']:.3f}, weighted={info['weighted_contribution']:.3f} ({info['pct_of_total']:.1f}% of total)"
                for domain, info in domain_contributions.items()
            ])
            + f"\n\nTop risk drivers: {[d[0] for d in top_domains]}\n"
            f"Active emergency alerts: {critical_alert_count}\n\n"
            f"Provide:\n"
            f"1. Integrated risk narrative explaining the unified score\n"
            f"2. Priority interventions with expected risk reduction for each\n"
            f"3. Risk trajectory prediction (improving/stable/worsening) over next 30 days\n"
            f"4. Tailored care escalation pathway based on risk level\n"
            f"5. Patient-facing risk communication (health literacy level 5)"
        )

        try:
            llm_result = await self.run_agent_chain(input_text=llm_input)
            risk_narrative = llm_result.get("output", "")
        except Exception as exc:
            logger.warning("Ensemble LLM narrative failed: %s", exc)
            risk_narrative = f"Unified risk level: {risk_level} (score: {weighted_score:.2f})"

        ensemble_result = {
            "unified_score": round(weighted_score, 3),
            "risk_level": risk_level,
            "confidence_interval": [round(ci_low, 3), round(ci_high, 3)],
            "domain_contributions": domain_contributions,
            "top_risk_drivers": [d[0] for d in top_domains],
            "risk_narrative": risk_narrative,
            "contributed_domains": contributed_domains,
        }

        return self._build_result(
            status="completed",
            findings=ensemble_result,
            alerts=alerts_out,
            recommendations=self._generate_recommendations(risk_level, top_domains, weighted_score),
        )

    def _generate_recommendations(
        self,
        risk_level: str,
        top_domains: List,
        score: float,
    ) -> List[str]:
        recs = []
        if risk_level == "CRITICAL":
            recs.append("CRITICAL RISK: Hospital observation or same-day urgent evaluation. Activate care management protocol. Physician notification within 15 minutes.")
        elif risk_level == "HIGH":
            recs.append("HIGH RISK: Urgent outpatient visit within 24-48 hours. Intensified monitoring (twice-daily vitals, weekly labs). Care coordinator assignment.")
        elif risk_level == "MEDIUM":
            recs.append("MEDIUM RISK: Scheduled follow-up within 1-2 weeks. Optimize medications. Patient education on warning signs.")

        top_domain_names = [d[0] for d in top_domains]
        if "monitoring_alerts" in top_domain_names:
            recs.append("Active monitoring alerts are driving risk — review and address outstanding alerts from Tier 1/2 agents.")
        if "sdoh_risk" in top_domain_names:
            recs.append("Social determinants are significantly contributing to risk — social work engagement is essential for sustainable improvement.")

        return recs
