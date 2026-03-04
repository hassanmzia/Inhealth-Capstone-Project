"""
Conditional routing logic for the LangGraph supervisor.

Each router function receives the current PatientMonitoringState and returns
the name of the next node (or END) that LangGraph should route to.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Literal

from langgraph.graph import END

from orchestrator.state import PatientMonitoringState

logger = logging.getLogger("inhealth.router")

# ── Routing literals ──────────────────────────────────────────────────────────
TierOneRoute = Literal["triage_agent", "diagnostic_tier", "risk_tier", END]
TierTwoRoute = Literal["triage_agent", "risk_tier", END]
TierThreeRoute = Literal["intervention_tier", "hitl_checkpoint", END]
TierFourRoute = Literal["action_tier", END]
TierFiveRoute = Literal["monitoring_tier", END]


# ── Severity helpers ──────────────────────────────────────────────────────────

def _has_critical_alert(alerts: List[Dict[str, Any]]) -> bool:
    return any(a.get("severity") in ("CRITICAL", "EMERGENCY") for a in alerts)


def _has_high_alert(alerts: List[Dict[str, Any]]) -> bool:
    return any(a.get("severity") in ("HIGH", "URGENT") for a in alerts)


def _has_critical_findings(diagnostic_results: Dict[str, Any]) -> bool:
    for _, data in diagnostic_results.items():
        if isinstance(data, dict) and data.get("critical"):
            return True
    return False


def _is_high_risk(risk_scores: Dict[str, Any]) -> bool:
    """
    High-risk when any risk model returns HIGH or CRITICAL level,
    or hospitalization probability ≥ 0.40.
    """
    for key, value in risk_scores.items():
        if isinstance(value, dict):
            if value.get("level") in ("HIGH", "CRITICAL"):
                return True
            score = value.get("score", 0.0)
            if isinstance(score, (int, float)) and score >= 0.40:
                return True
    return False


def _hitl_needed(interventions: List[Dict[str, Any]]) -> bool:
    return any(iv.get("requires_hitl", False) for iv in interventions)


# ── Tier 1 → next ─────────────────────────────────────────────────────────────

def route_after_monitoring(state: PatientMonitoringState) -> str:
    """
    After Tier 1 monitoring agents complete:
      - emergency_detected  → triage_agent (bypass diagnostic / risk)
      - any alert present   → diagnostic_tier
      - otherwise           → risk_tier (skip diagnostics for stable patients)
    """
    if state.get("emergency_detected") or _has_critical_alert(state.get("alerts", [])):
        logger.info(
            "[Router] patient=%s  monitoring → TRIAGE (emergency)",
            state.get("patient_id"),
        )
        return "triage_agent"

    if state.get("monitoring_results") and _has_high_alert(state.get("alerts", [])):
        logger.info(
            "[Router] patient=%s  monitoring → DIAGNOSTIC (alerts present)",
            state.get("patient_id"),
        )
        return "diagnostic_tier"

    logger.info(
        "[Router] patient=%s  monitoring → RISK (no immediate alerts)",
        state.get("patient_id"),
    )
    return "risk_tier"


# ── Tier 2 → next ─────────────────────────────────────────────────────────────

def route_after_diagnostic(state: PatientMonitoringState) -> str:
    """
    After Tier 2 diagnostic agents complete:
      - critical finding (STEMI, PE, stroke)  → triage_agent
      - otherwise                              → risk_tier
    """
    if state.get("emergency_detected") or _has_critical_findings(
        state.get("diagnostic_results", {})
    ):
        logger.info(
            "[Router] patient=%s  diagnostic → TRIAGE (critical finding)",
            state.get("patient_id"),
        )
        return "triage_agent"

    logger.info(
        "[Router] patient=%s  diagnostic → RISK",
        state.get("patient_id"),
    )
    return "risk_tier"


# ── Tier 3 → next ─────────────────────────────────────────────────────────────

def route_after_risk(state: PatientMonitoringState) -> str:
    """
    After Tier 3 risk assessment agents complete:
      - high risk + HITL required  → hitl_checkpoint
      - high risk (no HITL)        → intervention_tier
      - low / medium risk          → action_tier (notifications / scheduling only)
    """
    interventions = state.get("interventions", [])
    high_risk = _is_high_risk(state.get("risk_scores", {}))

    if _hitl_needed(interventions):
        logger.info(
            "[Router] patient=%s  risk → HITL_CHECKPOINT",
            state.get("patient_id"),
        )
        return "hitl_checkpoint"

    if high_risk or interventions:
        logger.info(
            "[Router] patient=%s  risk → INTERVENTION (high_risk=%s)",
            state.get("patient_id"),
            high_risk,
        )
        return "intervention_tier"

    logger.info(
        "[Router] patient=%s  risk → ACTION (low risk, no interventions)",
        state.get("patient_id"),
    )
    return "action_tier"


# ── Tier 4 → next ─────────────────────────────────────────────────────────────

def route_after_intervention(state: PatientMonitoringState) -> str:
    """
    After Tier 4 intervention agents complete:
      - always proceed to action_tier for notifications / scheduling / EHR write-back.
    """
    logger.info(
        "[Router] patient=%s  intervention → ACTION",
        state.get("patient_id"),
    )
    return "action_tier"


# ── Tier 5 → next ─────────────────────────────────────────────────────────────

def route_after_action(state: PatientMonitoringState) -> str:
    """
    After Tier 5 action agents complete:
      - emergency_detected → END (one-shot emergency handled; no re-loop)
      - iteration < max    → monitoring_tier (continuous monitoring loop)
      - otherwise          → END
    """
    max_iterations = 3   # Configurable; prevents infinite loops in tests
    iteration = state.get("iteration", 0)

    if state.get("emergency_detected"):
        logger.info(
            "[Router] patient=%s  action → END (post-emergency, iter=%d)",
            state.get("patient_id"),
            iteration,
        )
        return END

    if iteration < max_iterations:
        logger.info(
            "[Router] patient=%s  action → MONITORING (iter=%d/%d)",
            state.get("patient_id"),
            iteration,
            max_iterations,
        )
        return "monitoring_tier"

    logger.info(
        "[Router] patient=%s  action → END (max iterations reached)",
        state.get("patient_id"),
    )
    return END


# ── HITL checkpoint → next ────────────────────────────────────────────────────

def route_after_hitl(state: PatientMonitoringState) -> str:
    """
    After physician makes HITL decision:
      - approve / modify → intervention_tier
      - reject           → action_tier (send patient notification, no prescription)
    """
    decision = state.get("hitl_decision", "reject")

    if decision in ("approve", "modify"):
        logger.info(
            "[Router] patient=%s  hitl → INTERVENTION (decision=%s)",
            state.get("patient_id"),
            decision,
        )
        return "intervention_tier"

    logger.info(
        "[Router] patient=%s  hitl → ACTION (decision=reject)",
        state.get("patient_id"),
    )
    return "action_tier"
