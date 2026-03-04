"""
LangGraph state definitions for InHealth patient monitoring pipeline.
"""

from __future__ import annotations

import operator
from typing import Annotated, Any, Dict, List, Optional

from langchain_core.messages import BaseMessage
from typing_extensions import TypedDict


class PatientMonitoringState(TypedDict):
    """
    Central state passed between all LangGraph nodes throughout the
    5-tier patient monitoring pipeline.
    """

    # ── Identity ──────────────────────────────────────────────────────────────
    patient_id: str
    tenant_id: str

    # ── Conversation history (append-only via operator.add) ───────────────────
    messages: Annotated[List[BaseMessage], operator.add]

    # ── Tier 1 — Monitoring ───────────────────────────────────────────────────
    monitoring_results: Dict[str, Any]
    """
    Keyed by agent name, e.g.:
    {
        "glucose": {"value": 85, "trend": "stable", "alerts": []},
        "cardiac": {"hr": 72, "bp": "120/80", "alerts": []},
        ...
    }
    """

    # ── Tier 2 — Diagnostics ──────────────────────────────────────────────────
    diagnostic_results: Dict[str, Any]
    """
    {
        "ecg": {"rhythm": "NSR", "findings": [], "critical": False},
        "labs": {"hba1c": 7.2, "egfr": 62, "critical_values": []},
        ...
    }
    """

    # ── Tier 3 — Risk ─────────────────────────────────────────────────────────
    risk_scores: Dict[str, Any]
    """
    {
        "hospitalization_7d": {"score": 0.23, "level": "MEDIUM", "drivers": [...]},
        "comorbidity_index": 4,
        "sdoh_risk": 0.45,
        ...
    }
    """

    # ── Tier 4 — Interventions ────────────────────────────────────────────────
    interventions: List[Dict[str, Any]]
    """
    List of recommended interventions from Tier 4 agents:
    [
        {"type": "medication", "recommendation": {...}, "requires_hitl": True},
        {"type": "lifestyle", "recommendation": {...}, "requires_hitl": False},
    ]
    """

    # ── Tier 5 — Actions ──────────────────────────────────────────────────────
    actions_taken: List[Dict[str, Any]]
    """
    Actions confirmed and executed:
    [
        {"type": "notification_sent", "channel": "sms", "patient_id": "..."},
        {"type": "appointment_scheduled", "date": "...", "provider": "..."},
    ]
    """

    # ── Alerts ────────────────────────────────────────────────────────────────
    alerts: List[Dict[str, Any]]
    """
    Aggregated alerts from all tiers:
    [
        {"severity": "CRITICAL", "source": "glucose_agent", "message": "...", "timestamp": "..."},
    ]
    """

    # ── Control flow ──────────────────────────────────────────────────────────
    emergency_detected: bool
    current_tier: str          # "tier1" | "tier2" | "tier3" | "tier4" | "tier5" | "complete"
    iteration: int             # Loop counter for continuous monitoring cycles

    # ── Error handling ────────────────────────────────────────────────────────
    error: Optional[str]

    # ── Human-in-the-loop ─────────────────────────────────────────────────────
    hitl_required: bool
    hitl_decision: Optional[str]   # "approve" | "modify" | "reject"
    hitl_notes: Optional[str]

    # ── Output ────────────────────────────────────────────────────────────────
    final_report: Optional[Dict[str, Any]]
    """
    Structured summary generated after completing all tiers:
    {
        "generated_at": "ISO-8601",
        "patient_id": "...",
        "summary": "...",
        "risk_level": "MEDIUM",
        "key_findings": [...],
        "recommendations": [...],
        "actions_taken": [...],
    }
    """


class ResearchState(TypedDict):
    """State for the independent research pipeline."""

    query: str
    condition: Optional[str]
    patient_id: Optional[str]
    tenant_id: str

    literature_results: List[Dict[str, Any]]
    synthesis: Optional[Dict[str, Any]]
    qa_answer: Optional[Dict[str, Any]]
    trial_matches: List[Dict[str, Any]]
    guideline_gaps: List[Dict[str, Any]]

    messages: Annotated[List[BaseMessage], operator.add]
    error: Optional[str]


class HITLState(TypedDict):
    """Snapshot stored when a graph execution is paused for human approval."""

    thread_id: str
    patient_id: str
    tenant_id: str
    intervention: Dict[str, Any]
    notified_physician_id: Optional[str]
    pending_since: str          # ISO-8601 timestamp
    decision: Optional[str]     # "approve" | "modify" | "reject"
    notes: Optional[str]
    resolved_at: Optional[str]
