from __future__ import annotations

from time import monotonic
from typing import Dict, Optional

from opentelemetry.metrics import Meter
from opentelemetry.trace import SpanKind, Status, StatusCode, Tracer

from .telemetry import (
    AttributeValue,
    RuntimeOperation,
    RuntimeTelemetry,
    RuntimeTelemetryScope,
)


class OpenTelemetryRuntimeTelemetry(RuntimeTelemetry):
    """Adapter over application-owned OpenTelemetry tracer and meter providers."""

    def __init__(self, tracer: Tracer, meter: Meter):
        self._tracer = tracer
        self._duration = meter.create_histogram(
            "teaql.runtime.operation.duration", unit="ms",
            description="TeaQL runtime operation duration",
        )
        self._operations = meter.create_counter(
            "teaql.runtime.operation.count", unit="{operation}",
            description="Completed TeaQL runtime operations",
        )

    def start(self, operation: RuntimeOperation) -> RuntimeTelemetryScope:
        span = self._tracer.start_span(
            f"teaql.{operation.family}", kind=SpanKind.INTERNAL,
            attributes=operation.attributes,
        )
        return _OpenTelemetryScope(
            span, operation.family, monotonic(), self._duration, self._operations,
        )


class _OpenTelemetryScope:
    def __init__(self, span, family, started_at, duration, operations):
        self._span = span
        self._family = family
        self._started_at = started_at
        self._duration = duration
        self._operations = operations
        self._ended = False

    def success(self, attributes: Optional[Dict[str, AttributeValue]] = None) -> None:
        if self._ended:
            return
        for key, value in (attributes or {}).items():
            if key in {"teaql.result.cardinality", "teaql.cache.result"}:
                self._span.set_attribute(key, value)
        self._span.set_status(Status(StatusCode.OK))
        self._finish("success")

    def failure(self, error: BaseException) -> None:
        if self._ended:
            return
        self._span.set_attribute("teaql.error.type", type(error).__name__)
        self._span.set_status(Status(StatusCode.ERROR))
        self._finish("failure")

    def _finish(self, outcome: str) -> None:
        self._ended = True
        dimensions = {
            "teaql.operation.family": self._family,
            "teaql.operation.outcome": outcome,
        }
        self._duration.record(max(0.0, (monotonic() - self._started_at) * 1000), dimensions)
        self._operations.add(1, dimensions)
        self._span.end()
