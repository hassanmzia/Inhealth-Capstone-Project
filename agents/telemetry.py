"""
OpenTelemetry initialization for the FastAPI agents service.

Configures distributed tracing with OTLP export, auto-instruments FastAPI
and httpx outgoing calls, and provides helpers for creating custom spans
around agent execution.

Usage — call ``init_telemetry(app)`` during FastAPI lifespan startup.
"""

from __future__ import annotations

import logging
import os
from contextlib import contextmanager
from typing import Any, Dict, Optional

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


class _NoOpSpan:
    """Minimal stub so callers can call ``span.set_attribute(...)`` safely."""

    def set_attribute(self, key: str, value: Any) -> None:  # noqa: D102
        pass

    def set_status(self, *args: Any, **kwargs: Any) -> None:  # noqa: D102
        pass

    def add_event(self, name: str, attributes: Any = None) -> None:  # noqa: D102
        pass
