"""Optional OpenTelemetry tracing setup.

Enable by setting OTEL_ENABLED=true and installing the otel group:

    poetry install --with otel

Then configure the exporter via OTEL_ENDPOINT (default: http://localhost:4317).
See docs/observability.md for a local Jaeger quickstart.
"""

from __future__ import annotations

import structlog

log = structlog.get_logger()


def setup_otel(service_name: str, endpoint: str) -> None:
    """Initialise OpenTelemetry tracing with an OTLP gRPC exporter.

    All imports are lazy so this module can be safely imported even when the
    otel poetry group is not installed — provided setup_otel() is never called.
    If packages are missing, a warning is logged and the function returns without
    crashing the application.
    """
    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
            OTLPSpanExporter,
        )
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.sdk.resources import SERVICE_NAME, Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
    except ImportError:
        log.warning(
            "otel_packages_not_installed",
            hint="Install with: poetry install --with otel",
        )
        return

    provider = TracerProvider(
        resource=Resource.create({SERVICE_NAME: service_name}),
    )
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint)))
    trace.set_tracer_provider(provider)
    FastAPIInstrumentor().instrument()

    try:
        from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

        HTTPXClientInstrumentor().instrument()
    except ImportError:
        pass

    log.info("otel_initialized", service_name=service_name, endpoint=endpoint)
