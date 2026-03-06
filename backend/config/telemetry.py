"""
OpenTelemetry initialization for the Django backend.

Configures distributed tracing with OTLP export, and auto-instruments
Django, psycopg2, and Redis.

Usage — call ``init_telemetry()`` early in Django startup (e.g. in
``config/settings/base.py`` or the ASGI/WSGI entrypoint).
"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger("inhealth.telemetry")


def init_telemetry() -> None:
    """Bootstrap the OpenTelemetry SDK for the Django backend."""

    otel_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "")
    if not otel_endpoint:
        logger.info("OTEL_EXPORTER_OTLP_ENDPOINT not set — tracing disabled")
        return

    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
            OTLPSpanExporter,
        )
        from opentelemetry.instrumentation.django import DjangoInstrumentor
        from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor
        from opentelemetry.instrumentation.redis import RedisInstrumentor
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        resource = Resource.create(
            {
                "service.name": os.getenv("OTEL_SERVICE_NAME", "inhealth-backend"),
                "service.version": "1.0.0",
                "deployment.environment": os.getenv("DJANGO_ENV", "development"),
            }
        )

        provider = TracerProvider(resource=resource)

        exporter = OTLPSpanExporter(endpoint=otel_endpoint, insecure=True)
        provider.add_span_processor(BatchSpanProcessor(exporter))

        trace.set_tracer_provider(provider)

        # Auto-instrument frameworks
        DjangoInstrumentor().instrument()
        Psycopg2Instrumentor().instrument(enable_commenter=True)
        RedisInstrumentor().instrument()

        logger.info(
            "OpenTelemetry initialised — exporting to %s", otel_endpoint
        )

    except ImportError as exc:
        logger.warning(
            "OpenTelemetry packages not installed (tracing disabled): %s", exc
        )
    except Exception as exc:
        logger.error("OpenTelemetry init failed: %s", exc, exc_info=True)
