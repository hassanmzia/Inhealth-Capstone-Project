"""
Human-in-the-loop (HITL) handlers for InHealth AI Agent System.

Flow:
  1. interrupt_for_approval()  — called by LangGraph node, pauses execution,
                                  stores snapshot, notifies physician.
  2. process_hitl_response()   — called by physician via API / WebSocket,
                                  updates stored snapshot, resumes graph.
  3. HITLDecision model        — Pydantic model for the physician's decision.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import redis.asyncio as aioredis
from pydantic import BaseModel, Field

from orchestrator.state import HITLState, PatientMonitoringState

logger = logging.getLogger("inhealth.hitl")

# Redis key prefix for pending HITL requests
_HITL_KEY_PREFIX = "hitl:pending:"
_HITL_TTL_SECONDS = 60 * 60 * 4  # 4-hour TTL; requests expire if ignored


# ---------------------------------------------------------------------------
# Pydantic model
# ---------------------------------------------------------------------------

class HITLDecision(BaseModel):
    """Physician decision on a HITL intervention approval request."""

    thread_id: str = Field(..., description="LangGraph thread_id to resume")
    decision: str = Field(
        ...,
        description="approve | modify | reject",
        pattern="^(approve|modify|reject)$",
    )
    notes: Optional[str] = Field(None, description="Physician notes / modifications")
    modified_intervention: Optional[Dict[str, Any]] = Field(
        None, description="Modified intervention payload if decision == modify"
    )
    physician_id: str = Field(..., description="Physician user ID making the decision")


# ---------------------------------------------------------------------------
# Redis helper
# ---------------------------------------------------------------------------

async def _get_redis() -> Optional[aioredis.Redis]:
    """Return a Redis client; returns None if Redis is unavailable."""
    try:
        url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        client = await aioredis.from_url(url, decode_responses=True)
        await client.ping()
        return client
    except Exception as exc:
        logger.warning("HITL: Redis unavailable (%s); using in-memory fallback", exc)
        return None


# In-memory fallback for environments without Redis
_memory_store: Dict[str, Dict[str, Any]] = {}


async def _store_hitl_state(thread_id: str, state: Dict[str, Any]) -> None:
    redis = await _get_redis()
    key = f"{_HITL_KEY_PREFIX}{thread_id}"
    serialized = json.dumps(state, default=str)
    if redis:
        await redis.setex(key, _HITL_TTL_SECONDS, serialized)
        await redis.aclose()
    else:
        _memory_store[key] = state


async def _retrieve_hitl_state(thread_id: str) -> Optional[Dict[str, Any]]:
    redis = await _get_redis()
    key = f"{_HITL_KEY_PREFIX}{thread_id}"
    if redis:
        raw = await redis.get(key)
        await redis.aclose()
        if raw:
            return json.loads(raw)
        return None
    return _memory_store.get(key)


async def _delete_hitl_state(thread_id: str) -> None:
    redis = await _get_redis()
    key = f"{_HITL_KEY_PREFIX}{thread_id}"
    if redis:
        await redis.delete(key)
        await redis.aclose()
    else:
        _memory_store.pop(key, None)


# ---------------------------------------------------------------------------
# Notification helper (stub; replaced by physician_notify_agent in production)
# ---------------------------------------------------------------------------

async def _notify_physician(
    physician_id: Optional[str],
    patient_id: str,
    thread_id: str,
    intervention: Dict[str, Any],
) -> None:
    """
    Send a real-time push notification to the responsible physician.
    In production this calls the physician_notify_agent via A2A message bus.
    """
    redis = await _get_redis()
    if redis:
        channel = f"physician:{physician_id or 'on_call'}:notifications"
        payload = json.dumps(
            {
                "event": "hitl_approval_required",
                "thread_id": thread_id,
                "patient_id": patient_id,
                "intervention": intervention,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
        try:
            await redis.publish(channel, payload)
            logger.info("HITL notification published to %s", channel)
        except Exception as exc:
            logger.warning("Failed to publish HITL notification: %s", exc)
        finally:
            await redis.aclose()
    else:
        logger.info(
            "HITL [in-memory]: approval required — patient=%s thread=%s",
            patient_id,
            thread_id,
        )


# ---------------------------------------------------------------------------
# Core HITL handlers
# ---------------------------------------------------------------------------

async def interrupt_for_approval(
    state: PatientMonitoringState,
    thread_id: str,
    intervention: Dict[str, Any],
    physician_id: Optional[str] = None,
) -> PatientMonitoringState:
    """
    Pause graph execution for physician approval.

    This function:
      1. Creates a HITLState snapshot.
      2. Persists it to Redis (with TTL) so the API can retrieve it.
      3. Sends a push notification to the physician.
      4. Returns the mutated state with hitl_required=True.

    In a LangGraph graph this node is expected to be followed by a
    conditional edge that loops until hitl_decision is populated.
    """
    hitl_state: HITLState = {
        "thread_id": thread_id,
        "patient_id": state["patient_id"],
        "tenant_id": state["tenant_id"],
        "intervention": intervention,
        "notified_physician_id": physician_id,
        "pending_since": datetime.now(timezone.utc).isoformat(),
        "decision": None,
        "notes": None,
        "resolved_at": None,
    }

    await _store_hitl_state(thread_id, hitl_state)

    await _notify_physician(
        physician_id=physician_id,
        patient_id=state["patient_id"],
        thread_id=thread_id,
        intervention=intervention,
    )

    logger.info(
        "HITL interrupt — patient=%s thread=%s intervention_type=%s",
        state["patient_id"],
        thread_id,
        intervention.get("type", "unknown"),
    )

    updated_state = dict(state)
    updated_state["hitl_required"] = True
    updated_state["hitl_decision"] = None
    return updated_state  # type: ignore[return-value]


async def process_hitl_response(decision: HITLDecision) -> Dict[str, Any]:
    """
    Called by the API endpoint when the physician submits their decision.

    Retrieves the persisted HITLState, records the decision, and returns
    a dict that can be merged into the PatientMonitoringState to resume
    graph execution.
    """
    hitl_state = await _retrieve_hitl_state(decision.thread_id)
    if hitl_state is None:
        raise ValueError(
            f"HITL request not found or expired: thread_id={decision.thread_id}"
        )

    hitl_state["decision"] = decision.decision
    hitl_state["notes"] = decision.notes
    hitl_state["resolved_at"] = datetime.now(timezone.utc).isoformat()
    hitl_state["physician_id"] = decision.physician_id

    # Persist updated state (for audit trail)
    await _store_hitl_state(decision.thread_id, hitl_state)

    logger.info(
        "HITL decision recorded — thread=%s decision=%s physician=%s",
        decision.thread_id,
        decision.decision,
        decision.physician_id,
    )

    # Build the state patch to resume the LangGraph graph
    state_patch = {
        "hitl_required": False,
        "hitl_decision": decision.decision,
        "hitl_notes": decision.notes,
    }

    # If modified, inject the modified intervention
    if decision.decision == "modify" and decision.modified_intervention:
        state_patch["interventions"] = [decision.modified_intervention]

    # Cleanup after short delay (keep for audit; delete after 24 h in production)
    # await _delete_hitl_state(decision.thread_id)

    return {
        "thread_id": decision.thread_id,
        "state_patch": state_patch,
        "hitl_state": hitl_state,
    }


async def get_pending_hitl_requests(tenant_id: Optional[str] = None) -> list:
    """
    Return all pending HITL requests (optionally filtered by tenant).
    Used by the physician dashboard API.
    """
    redis = await _get_redis()
    pending = []

    if redis:
        try:
            cursor = 0
            while True:
                cursor, keys = await redis.scan(
                    cursor=cursor, match=f"{_HITL_KEY_PREFIX}*", count=100
                )
                for key in keys:
                    raw = await redis.get(key)
                    if raw:
                        record = json.loads(raw)
                        if record.get("decision") is None:
                            if tenant_id is None or record.get("tenant_id") == tenant_id:
                                pending.append(record)
                if cursor == 0:
                    break
        finally:
            await redis.aclose()
    else:
        for record in _memory_store.values():
            if record.get("decision") is None:
                if tenant_id is None or record.get("tenant_id") == tenant_id:
                    pending.append(record)

    return pending
