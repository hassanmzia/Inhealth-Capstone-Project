"""
LangGraph StateGraph supervisor for InHealth 5-tier patient monitoring pipeline.

Architecture
------------
  Tier 1 (parallel)  → Tier 2 (parallel) → Tier 3 (parallel) → HITL? → Tier 4 → Tier 5
                                                ↑                                     |
                                                └──────── continuous loop ────────────┘

All LLM calls are traced via Langfuse callback.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional, Type

from langchain_core.language_models import BaseChatModel
from langfuse.callback import CallbackHandler as LangfuseCallbackHandler
from langgraph.graph import END, StateGraph
from langgraph.graph.graph import CompiledGraph

from orchestrator.router import (
    route_after_action,
    route_after_diagnostic,
    route_after_hitl,
    route_after_intervention,
    route_after_monitoring,
    route_after_risk,
)
from orchestrator.state import PatientMonitoringState

logger = logging.getLogger("inhealth.supervisor")


# ─────────────────────────────────────────────────────────────────────────────
# LLM factory
# ─────────────────────────────────────────────────────────────────────────────

def _build_llm(langfuse_handler: Optional[LangfuseCallbackHandler] = None) -> BaseChatModel:
    """
    Attempt LLM providers in order:
      1. Ollama (local Llama 3.2) — preferred for cost/latency
      2. OpenAI GPT-4o           — cloud fallback
      3. Anthropic Claude 3      — secondary fallback
    """
    callbacks = [langfuse_handler] if langfuse_handler else []

    # 1. Ollama
    try:
        from langchain_community.chat_models import ChatOllama  # type: ignore

        return ChatOllama(
            model=os.getenv("OLLAMA_MODEL", "llama3.2"),
            base_url=os.getenv("OLLAMA_BASE_URL", "http://ollama:11434"),
            callbacks=callbacks,
        )
    except Exception as exc:
        logger.warning("Ollama unavailable (%s); trying OpenAI", exc)

    # 2. OpenAI
    openai_key = os.getenv("OPENAI_API_KEY", "")
    if openai_key:
        try:
            from langchain_openai import ChatOpenAI  # type: ignore

            return ChatOpenAI(
                model=os.getenv("OPENAI_MODEL", "gpt-4o"),
                api_key=openai_key,
                callbacks=callbacks,
            )
        except Exception as exc:
            logger.warning("OpenAI unavailable (%s); trying Anthropic", exc)

    # 3. Anthropic
    anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")
    if anthropic_key:
        try:
            from langchain_anthropic import ChatAnthropic  # type: ignore

            return ChatAnthropic(
                model=os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022"),
                api_key=anthropic_key,
                callbacks=callbacks,
            )
        except Exception as exc:
            logger.error("All LLM providers failed: %s", exc)

    raise RuntimeError(
        "No LLM provider available. Configure OLLAMA_BASE_URL, OPENAI_API_KEY, "
        "or ANTHROPIC_API_KEY."
    )


# ─────────────────────────────────────────────────────────────────────────────
# Agent registry  (name → module path)
# ─────────────────────────────────────────────────────────────────────────────

AGENT_REGISTRY: Dict[str, str] = {
    # Tier 1
    "glucose_agent": "tier1_monitoring.glucose_agent.GlucoseAgent",
    "cardiac_agent": "tier1_monitoring.cardiac_agent.CardiacAgent",
    "activity_agent": "tier1_monitoring.activity_agent.ActivityAgent",
    "temperature_agent": "tier1_monitoring.temperature_agent.TemperatureAgent",
    # Tier 2
    "ecg_agent": "tier2_diagnostic.ecg_agent.ECGAgent",
    "kidney_agent": "tier2_diagnostic.kidney_agent.KidneyAgent",
    "imaging_agent": "tier2_diagnostic.imaging_agent.ImagingAgent",
    "lab_agent": "tier2_diagnostic.lab_agent.LabAgent",
    # Tier 3
    "comorbidity_agent": "tier3_risk.comorbidity_agent.ComorbidityAgent",
    "prediction_agent": "tier3_risk.prediction_agent.PredictionAgent",
    "family_history_agent": "tier3_risk.family_history_agent.FamilyHistoryAgent",
    "sdoh_agent": "tier3_risk.sdoh_agent.SDOHAgent",
    "ml_ensemble_agent": "tier3_risk.ml_ensemble_agent.MLEnsembleAgent",
    # Tier 4
    "coaching_agent": "tier4_intervention.coaching_agent.CoachingAgent",
    "prescription_agent": "tier4_intervention.prescription_agent.PrescriptionAgent",
    "contraindication_agent": "tier4_intervention.contraindication_agent.ContraindicationAgent",
    "triage_agent": "tier4_intervention.triage_agent.TriageAgent",
    # Tier 5
    "physician_notify_agent": "tier5_action.physician_notify_agent.PhysicianNotifyAgent",
    "patient_notify_agent": "tier5_action.patient_notify_agent.PatientNotifyAgent",
    "scheduling_agent": "tier5_action.scheduling_agent.SchedulingAgent",
    "ehr_integration_agent": "tier5_action.ehr_integration_agent.EHRIntegrationAgent",
    "billing_agent": "tier5_action.billing_agent.BillingAgent",
}


def _import_agent_class(dotted_path: str) -> type:
    module_path, class_name = dotted_path.rsplit(".", 1)
    import importlib

    module = importlib.import_module(module_path)
    return getattr(module, class_name)


def get_agent_by_name(
    agent_name: str,
    langfuse_handler: Optional[LangfuseCallbackHandler] = None,
) -> Optional[Any]:
    """Instantiate an agent by its registered name."""
    dotted_path = AGENT_REGISTRY.get(agent_name)
    if dotted_path is None:
        return None
    try:
        cls = _import_agent_class(dotted_path)
        llm = _build_llm(langfuse_handler)
        return cls(llm=llm, langfuse_handler=langfuse_handler)
    except Exception as exc:
        logger.error("Failed to instantiate agent '%s': %s", agent_name, exc, exc_info=True)
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Tier node wrappers
# ─────────────────────────────────────────────────────────────────────────────

def _make_tier_node(
    agent_names: List[str],
    tier_result_key: str,
    langfuse_handler: Optional[LangfuseCallbackHandler],
    llm: BaseChatModel,
):
    """
    Return an async LangGraph node function that runs multiple agents in
    parallel (asyncio.gather) and merges their results into state.
    """
    import asyncio
    from base.memory import AgentMemoryManager

    async def tier_node(state: PatientMonitoringState) -> PatientMonitoringState:
        memory_mgr = AgentMemoryManager()
        results: Dict[str, Any] = {}
        new_alerts: List[Dict[str, Any]] = []

        async def run_one(name: str):
            dotted_path = AGENT_REGISTRY.get(name)
            if dotted_path is None:
                logger.warning("Agent '%s' not in registry; skipping", name)
                return
            try:
                cls = _import_agent_class(dotted_path)
                agent_instance = cls(
                    llm=llm,
                    langfuse_handler=langfuse_handler,
                    memory=memory_mgr.get_memory(
                        agent_name=name,
                        patient_id=state["patient_id"],
                    ),
                )
                result = await agent_instance.execute(
                    patient_id=state["patient_id"],
                    state=state,
                    context={},
                )
                results[name] = result
                for alert in result.get("alerts", []):
                    new_alerts.append(alert)
                # Check for emergency flag
                if result.get("emergency_detected"):
                    state["emergency_detected"] = True  # type: ignore[index]
            except Exception as exc:
                logger.error("Agent '%s' failed: %s", name, exc, exc_info=True)
                results[name] = {"error": str(exc), "status": "failed"}

        await asyncio.gather(*[run_one(n) for n in agent_names])

        # Merge tier results into state
        updated: Dict[str, Any] = dict(state)
        existing = dict(updated.get(tier_result_key, {}))
        existing.update(results)
        updated[tier_result_key] = existing
        updated["alerts"] = list(state.get("alerts", [])) + new_alerts
        updated["iteration"] = state.get("iteration", 0) + (
            1 if tier_result_key == "actions_taken" else 0
        )
        return updated  # type: ignore[return-value]

    tier_node.__name__ = f"{tier_result_key}_node"
    return tier_node


# ─────────────────────────────────────────────────────────────────────────────
# HITL checkpoint node
# ─────────────────────────────────────────────────────────────────────────────

async def _hitl_checkpoint_node(state: PatientMonitoringState) -> PatientMonitoringState:
    """
    Pause the graph for physician approval.
    In production this uses LangGraph's interrupt() to truly suspend;
    here we persist state to Redis and poll until resolved.
    """
    import asyncio
    import uuid

    from orchestrator.hitl import interrupt_for_approval, _retrieve_hitl_state

    thread_id = str(uuid.uuid4())
    interventions = state.get("interventions", [])
    hitl_intervention = next(
        (iv for iv in interventions if iv.get("requires_hitl")), {}
    )

    updated_state = await interrupt_for_approval(
        state=state,
        thread_id=thread_id,
        intervention=hitl_intervention,
    )

    # Poll Redis until physician responds (max 5 min for automated testing)
    max_wait_seconds = int(os.getenv("HITL_TIMEOUT_SECONDS", "300"))
    poll_interval = 5
    waited = 0
    while waited < max_wait_seconds:
        await asyncio.sleep(poll_interval)
        waited += poll_interval
        hitl_state = await _retrieve_hitl_state(thread_id)
        if hitl_state and hitl_state.get("decision"):
            updated_state["hitl_decision"] = hitl_state["decision"]  # type: ignore[index]
            updated_state["hitl_required"] = False  # type: ignore[index]
            logger.info(
                "HITL resolved — thread=%s decision=%s",
                thread_id,
                hitl_state["decision"],
            )
            break
    else:
        # Timeout → auto-reject for safety
        logger.warning(
            "HITL timeout (%ds) — auto-rejecting thread=%s",
            max_wait_seconds,
            thread_id,
        )
        updated_state["hitl_decision"] = "reject"  # type: ignore[index]
        updated_state["hitl_required"] = False  # type: ignore[index]

    return updated_state  # type: ignore[return-value]


# ─────────────────────────────────────────────────────────────────────────────
# Final report node
# ─────────────────────────────────────────────────────────────────────────────

async def _generate_final_report_node(state: PatientMonitoringState) -> PatientMonitoringState:
    """
    Synthesize all tier results into a structured final report.
    Uses the LLM to produce a human-readable clinical summary.
    """
    from datetime import datetime, timezone

    alerts = state.get("alerts", [])
    risk_scores = state.get("risk_scores", {})

    # Determine overall risk level
    levels = [v.get("level", "LOW") for v in risk_scores.values() if isinstance(v, dict)]
    overall_risk = "LOW"
    for level in ("CRITICAL", "HIGH", "MEDIUM"):
        if level in levels:
            overall_risk = level
            break

    final_report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "patient_id": state["patient_id"],
        "tenant_id": state["tenant_id"],
        "overall_risk_level": overall_risk,
        "emergency_detected": state.get("emergency_detected", False),
        "alert_count": len(alerts),
        "critical_alerts": [a for a in alerts if a.get("severity") in ("CRITICAL", "EMERGENCY")],
        "monitoring_summary": state.get("monitoring_results", {}),
        "diagnostic_summary": state.get("diagnostic_results", {}),
        "risk_summary": risk_scores,
        "interventions": state.get("interventions", []),
        "actions_taken": state.get("actions_taken", []),
        "iterations_completed": state.get("iteration", 0),
    }

    updated = dict(state)
    updated["final_report"] = final_report
    updated["current_tier"] = "complete"
    return updated  # type: ignore[return-value]


# ─────────────────────────────────────────────────────────────────────────────
# Graph builder
# ─────────────────────────────────────────────────────────────────────────────

def build_supervisor_graph(
    langfuse_handler: Optional[LangfuseCallbackHandler] = None,
) -> CompiledGraph:
    """
    Compile and return the LangGraph StateGraph for the full 5-tier pipeline.
    """
    llm = _build_llm(langfuse_handler)

    # Tier node functions
    monitoring_node = _make_tier_node(
        agent_names=["glucose_agent", "cardiac_agent", "activity_agent", "temperature_agent"],
        tier_result_key="monitoring_results",
        langfuse_handler=langfuse_handler,
        llm=llm,
    )
    diagnostic_node = _make_tier_node(
        agent_names=["ecg_agent", "kidney_agent", "imaging_agent", "lab_agent"],
        tier_result_key="diagnostic_results",
        langfuse_handler=langfuse_handler,
        llm=llm,
    )
    risk_node = _make_tier_node(
        agent_names=[
            "comorbidity_agent",
            "prediction_agent",
            "family_history_agent",
            "sdoh_agent",
            "ml_ensemble_agent",
        ],
        tier_result_key="risk_scores",
        langfuse_handler=langfuse_handler,
        llm=llm,
    )
    intervention_node = _make_tier_node(
        agent_names=["coaching_agent", "prescription_agent", "contraindication_agent"],
        tier_result_key="interventions",
        langfuse_handler=langfuse_handler,
        llm=llm,
    )
    action_node = _make_tier_node(
        agent_names=[
            "physician_notify_agent",
            "patient_notify_agent",
            "scheduling_agent",
            "ehr_integration_agent",
            "billing_agent",
        ],
        tier_result_key="actions_taken",
        langfuse_handler=langfuse_handler,
        llm=llm,
    )

    # Triage node (single agent)
    async def triage_node(state: PatientMonitoringState) -> PatientMonitoringState:
        from tier4_intervention.triage_agent import TriageAgent
        from base.memory import AgentMemoryManager

        memory_mgr = AgentMemoryManager()
        agent = TriageAgent(
            llm=llm,
            langfuse_handler=langfuse_handler,
            memory=memory_mgr.get_memory("triage_agent", state["patient_id"]),
        )
        result = await agent.execute(
            patient_id=state["patient_id"],
            state=state,
            context={"emergency": True},
        )
        updated = dict(state)
        existing_actions = list(updated.get("actions_taken", []))
        existing_actions.append(result)
        updated["actions_taken"] = existing_actions
        return updated  # type: ignore[return-value]

    # Build the StateGraph
    graph = StateGraph(PatientMonitoringState)

    # Add nodes
    graph.add_node("monitoring_tier", monitoring_node)
    graph.add_node("diagnostic_tier", diagnostic_node)
    graph.add_node("risk_tier", risk_node)
    graph.add_node("intervention_tier", intervention_node)
    graph.add_node("action_tier", action_node)
    graph.add_node("triage_agent", triage_node)
    graph.add_node("hitl_checkpoint", _hitl_checkpoint_node)
    graph.add_node("final_report", _generate_final_report_node)

    # Set entry point
    graph.set_entry_point("monitoring_tier")

    # Conditional edges
    graph.add_conditional_edges(
        "monitoring_tier",
        route_after_monitoring,
        {
            "triage_agent": "triage_agent",
            "diagnostic_tier": "diagnostic_tier",
            "risk_tier": "risk_tier",
        },
    )

    graph.add_conditional_edges(
        "diagnostic_tier",
        route_after_diagnostic,
        {
            "triage_agent": "triage_agent",
            "risk_tier": "risk_tier",
        },
    )

    graph.add_conditional_edges(
        "risk_tier",
        route_after_risk,
        {
            "intervention_tier": "intervention_tier",
            "hitl_checkpoint": "hitl_checkpoint",
            "action_tier": "action_tier",
        },
    )

    graph.add_conditional_edges(
        "hitl_checkpoint",
        route_after_hitl,
        {
            "intervention_tier": "intervention_tier",
            "action_tier": "action_tier",
        },
    )

    graph.add_conditional_edges(
        "intervention_tier",
        route_after_intervention,
        {"action_tier": "action_tier"},
    )

    graph.add_conditional_edges(
        "action_tier",
        route_after_action,
        {
            "monitoring_tier": "monitoring_tier",
            END: "final_report",
        },
    )

    # Triage always → final_report
    graph.add_edge("triage_agent", "final_report")
    graph.add_edge("final_report", END)

    compiled = graph.compile()
    logger.info("LangGraph supervisor compiled with %d nodes", len(graph.nodes))
    return compiled
