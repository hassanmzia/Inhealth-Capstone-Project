"""
OpenTelemetry initialization for the FastAPI agents service.

Configures distributed tracing with OTLP export, auto-instruments FastAPI
and httpx outgoing calls, and provides helpers for creating custom spans
around agent execution.

Enhanced with:
- Agent decision event recording
- LLM token/cost span attributes
- Retry and fallback span events
- Tier-aware span naming

Usage — call ``init_telemetry(app)`` during FastAPI lifespan startup.
"""

from __future__ import annotations

import logging
import os
import time
from contextlib import contextmanager
from typing import Any, Dict, List, Optional

logger = logging.getLogger("inhealth.agents.telemetry")

_tracer = None


def init_telemetry(app: Any = None) -> None:
    """Bootstrap the OpenTelemetry SDK for the agents FastAPI service."""

    global _tracer

    otel_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "")
    if not otel_endpoint:
        logger.info("OTEL_EXPORTER_OTLP_ENDPOINT not set — tracing disabled")
        return

    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
            OTLPSpanExporter,
        )
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        resource = Resource.create(
            {
                "service.name": os.getenv(
                    "OTEL_SERVICE_NAME", "inhealth-agents"
                ),
                "service.version": "1.0.0",
                "deployment.environment": os.getenv("ENV", "development"),
            }
        )

        provider = TracerProvider(resource=resource)
        exporter = OTLPSpanExporter(endpoint=otel_endpoint, insecure=True)
        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)

        _tracer = trace.get_tracer("inhealth.agents")

        # Auto-instrument
        if app is not None:
            FastAPIInstrumentor.instrument_app(app)
        HTTPXClientInstrumentor().instrument()

        logger.info(
            "OpenTelemetry initialised — exporting to %s", otel_endpoint
        )

    except ImportError as exc:
        logger.warning(
            "OpenTelemetry packages not installed (tracing disabled): %s", exc
        )
    except Exception as exc:
        logger.error("OpenTelemetry init failed: %s", exc, exc_info=True)


@contextmanager
def agent_span(
    agent_name: str,
    patient_id: str,
    attributes: Optional[Dict[str, Any]] = None,
):
    """
    Context manager that creates an OpenTelemetry span for an agent execution.

    Usage::

        with agent_span("glucose_agent", patient_id="P-123") as span:
            result = await agent.analyze(...)
            span.set_attribute("risk_level", result["level"])
    """
    if _tracer is None:
        # No-op when tracing is disabled
        yield _NoOpSpan()
        return

    with _tracer.start_as_current_span(
        f"agent.{agent_name}",
        attributes={
            "agent.name": agent_name,
            "patient.id": patient_id,
            **(attributes or {}),
        },
    ) as span:
        yield span


@contextmanager
def tier_span(
    tier: str,
    patient_id: str,
    agents: Optional[List[str]] = None,
):
    """
    Context manager for a tier-level span encompassing multiple agent executions.

    Usage::

        with tier_span("tier3_risk", patient_id="P-123", agents=["prediction", "ensemble"]) as span:
            await run_tier3_agents(state)
    """
    if _tracer is None:
        yield _NoOpSpan()
        return

    with _tracer.start_as_current_span(
        f"tier.{tier}",
        attributes={
            "tier.name": tier,
            "patient.id": patient_id,
            "tier.agents": ",".join(agents or []),
        },
    ) as span:
        yield span


@contextmanager
def llm_span(
    agent_name: str,
    model: str,
):
    """
    Context manager for LLM call spans with token/cost tracking.

    Usage::

        with llm_span("ensemble_agent", "claude-sonnet-4-6") as span:
            result = await llm.invoke(prompt)
            span.record_usage(input_tokens=1200, output_tokens=450, cost_usd=0.008)
    """
    if _tracer is None:
        yield _NoOpLLMSpan()
        return

    with _tracer.start_as_current_span(
        f"llm.{agent_name}",
        attributes={
            "llm.model": model,
            "agent.name": agent_name,
        },
    ) as span:
        yield _LLMSpanWrapper(span)


class _LLMSpanWrapper:
    """Wrapper that adds LLM-specific methods to an OTel span."""

    def __init__(self, span):
        self._span = span

    def record_usage(
        self,
        input_tokens: int = 0,
        output_tokens: int = 0,
        cost_usd: float = 0.0,
        latency_ms: int = 0,
    ):
        self._span.set_attribute("llm.input_tokens", input_tokens)
        self._span.set_attribute("llm.output_tokens", output_tokens)
        self._span.set_attribute("llm.total_tokens", input_tokens + output_tokens)
        self._span.set_attribute("llm.cost_usd", cost_usd)
        if latency_ms:
            self._span.set_attribute("llm.latency_ms", latency_ms)

    def set_attribute(self, key: str, value: Any) -> None:
        self._span.set_attribute(key, value)

    def add_event(self, name: str, attributes: Any = None) -> None:
        self._span.add_event(name, attributes=attributes)

    def set_status(self, *args, **kwargs):
        self._span.set_status(*args, **kwargs)


class _NoOpLLMSpan:
    """No-op LLM span stub."""

    def record_usage(self, **kwargs):
        pass

    def set_attribute(self, key: str, value: Any) -> None:
        pass

    def add_event(self, name: str, attributes: Any = None) -> None:
        pass

    def set_status(self, *args, **kwargs):
        pass


# ── Decision Event Helpers ───────────────────────────────────────────


def record_decision_event(
    span,
    agent_name: str,
    decision: str,
    confidence: float = 0.0,
    rationale: str = "",
    risk_level: str = "",
    requires_hitl: bool = False,
):
    """Record an agent decision as a span event."""
    span.add_event(
        f"decision.{agent_name}",
        attributes={
            "agent.decision": decision[:200],
            "agent.confidence": confidence,
            "agent.rationale": rationale[:500],
            "agent.risk_level": risk_level,
            "agent.requires_hitl": requires_hitl,
        },
    )


def record_retry_event(
    span,
    agent_name: str,
    attempt: int,
    max_attempts: int,
    error: str,
    backoff_seconds: float,
):
    """Record a retry attempt as a span event."""
    span.add_event(
        f"retry.{agent_name}",
        attributes={
            "retry.attempt": attempt,
            "retry.max_attempts": max_attempts,
            "retry.error": error[:200],
            "retry.backoff_seconds": backoff_seconds,
        },
    )
    logger.warning(
        "Retry: agent=%s attempt=%d/%d backoff=%.1fs",
        agent_name, attempt, max_attempts, backoff_seconds,
    )


def record_fallback_event(
    span,
    agent_name: str,
    primary_model: str,
    fallback_model: str,
    reason: str,
):
    """Record a model fallback as a span event."""
    span.add_event(
        f"fallback.{agent_name}",
        attributes={
            "fallback.primary_model": primary_model,
            "fallback.model": fallback_model,
            "fallback.reason": reason[:200],
        },
    )
    logger.warning(
        "Fallback: agent=%s %s → %s reason=%s",
        agent_name, primary_model, fallback_model, reason[:100],
    )


def record_safety_flag_event(
    span,
    agent_name: str,
    flag_type: str,
    details: str = "",
):
    """Record a safety flag as a span event."""
    span.add_event(
        f"safety_flag.{agent_name}",
        attributes={
            "safety.flag_type": flag_type,
            "safety.details": details[:200],
        },
    )


# ── No-Op Span ───────────────────────────────────────────────────────


class _NoOpSpan:
    """Minimal stub so callers can call ``span.set_attribute(...)`` safely."""

    def set_attribute(self, key: str, value: Any) -> None:  # noqa: D102
        pass

    def set_status(self, *args: Any, **kwargs: Any) -> None:  # noqa: D102
        pass

    def add_event(self, name: str, attributes: Any = None) -> None:  # noqa: D102
        pass
