from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import InMemoryMetricReader
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from teaql.runtime.opentelemetry import OpenTelemetryRuntimeTelemetry
from teaql.runtime.telemetry import RuntimeOperation, start_runtime_operation


def test_exports_safe_spans_and_metrics_through_official_sdk():
    span_exporter = InMemorySpanExporter()
    tracer_provider = TracerProvider()
    tracer_provider.add_span_processor(SimpleSpanProcessor(span_exporter))
    metric_reader = InMemoryMetricReader()
    meter_provider = MeterProvider(metric_readers=[metric_reader])
    telemetry = OpenTelemetryRuntimeTelemetry(
        tracer_provider.get_tracer("io.teaql.runtime"),
        meter_provider.get_meter("io.teaql.runtime"),
    )

    scope = start_runtime_operation(telemetry, RuntimeOperation(
        "query", "School.list", {
            "teaql.entity.type": "School",
            "teaql.entity.id": 42,
        },
    ))
    child = start_runtime_operation(telemetry, RuntimeOperation(
        "provider", "sqlite.query", {
            "teaql.provider.kind": "sqlite",
            "teaql.provider.operation": "query",
        },
    ))
    child.success()
    scope.success({"teaql.result.cardinality": 1})

    spans = span_exporter.get_finished_spans()
    assert len(spans) == 2
    query_span = next(span for span in spans if span.name == "teaql.query")
    provider_span = next(span for span in spans if span.name == "teaql.provider")
    assert query_span.attributes["teaql.entity.type"] == "School"
    assert "teaql.entity.id" not in query_span.attributes
    assert query_span.attributes["teaql.result.cardinality"] == 1
    assert provider_span.parent.span_id == query_span.context.span_id
    metric_names = {
        metric.name
        for scope_metrics in metric_reader.get_metrics_data().resource_metrics[0].scope_metrics
        for metric in scope_metrics.metrics
    }
    assert metric_names >= {
        "teaql.runtime.operation.duration",
        "teaql.runtime.operation.count",
    }

    tracer_provider.shutdown()
    meter_provider.shutdown()
