"""OpenTelemetry wiring (FastAPI + httpx + LLM spans) with optional Langfuse.

Everything is best-effort: if the OTel packages or collector are unavailable the
app still boots, we just log a warning. Enable with ``OTEL_ENABLED=true`` and
point ``OTEL_EXPORTER_OTLP_ENDPOINT`` at Grafana Alloy / Tempo / Grafana Cloud.
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Any, Iterator

from app.core.settings import Settings, get_settings

logger = logging.getLogger(__name__)

_tracer: Any | None = None


def setup_telemetry(app: Any, settings: Settings | None = None) -> None:
    settings = settings or get_settings()
    if not settings.otel_enabled:
        logger.info("OpenTelemetry disabled (OTEL_ENABLED=false)")
        return

    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
    except ImportError as exc:  # pragma: no cover - optional deps
        logger.warning("OpenTelemetry packages missing (%s); tracing disabled", exc)
        return

    resource = Resource.create({"service.name": settings.otel_service_name})
    provider = TracerProvider(resource=resource)
    endpoint = settings.otel_exporter_otlp_endpoint.rstrip("/") + "/v1/traces"
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint)))
    trace.set_tracer_provider(provider)

    FastAPIInstrumentor.instrument_app(app)
    HTTPXClientInstrumentor().instrument()

    global _tracer
    _tracer = trace.get_tracer(settings.otel_service_name)
    logger.info("OpenTelemetry tracing exporting to %s", endpoint)

    if settings.langfuse_enabled:
        _setup_langfuse(settings)


def _setup_langfuse(settings: Settings) -> None:  # pragma: no cover - optional dep
    try:
        from langfuse import Langfuse
    except ImportError:
        logger.warning(
            "LANGFUSE_ENABLED=true but the `langfuse` package is not installed; skipping"
        )
        return
    Langfuse(
        public_key=settings.langfuse_public_key,
        secret_key=settings.langfuse_secret_key,
        host=settings.langfuse_host,
    )
    logger.info("Langfuse tracing enabled (host=%s)", settings.langfuse_host)


@contextmanager
def span(name: str, **attributes: Any) -> Iterator[None]:
    """No-op-safe span helper usable from module services."""
    if _tracer is None:
        yield
        return
    with _tracer.start_as_current_span(name) as current:  # pragma: no cover
        for key, value in attributes.items():
            current.set_attribute(key, value)
        yield
