"""Real exporter response and SDK metric-object accounting counterexamples."""
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import threading
import logging
import time
import pytest
from opentelemetry.sdk.trace.export import SpanExportResult
from opentelemetry.sdk.metrics.export import MetricExportResult
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from teaql.runtime.telemetry_http import HttpExporter
from teaql.runtime.standard_telemetry import _SafeExporter


def one_span():
    memory = InMemorySpanExporter()
    provider = TracerProvider(shutdown_on_exit=False)
    provider.add_span_processor(SimpleSpanProcessor(memory))
    span = provider.get_tracer('response-test').start_span('native response fixture')
    span.end()
    result = memory.get_finished_spans()
    provider.shutdown()
    return result


def test_invalid_protobuf_is_not_full_acceptance():
    with receiver(b'\xff' * 8) as endpoint:
        exporter = HttpExporter(endpoint + '/v1/traces', 'traces')
        try:
            assert exporter.export(one_span()) == SpanExportResult.FAILURE
        finally:
            exporter.shutdown()


@contextmanager
def receiver(body, status=200, content_type='application/x-protobuf', behavior=None):
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            self.rfile.read(int(self.headers['Content-Length']))
            if behavior:
                behavior(self)
                return
            self.send_response(status, 'PRIVATE-REMOTE-REASON')
            self.send_header('Content-Type', content_type)
            self.send_header('X-Private', 'PRIVATE-REMOTE-HEADER')
            self.end_headers()
            self.wfile.write(body)
        def log_message(self, *args):
            pass
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    server.daemon_threads = True
    server.handle_error = lambda *args: None
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        yield f'http://127.0.0.1:{server.server_port}'
    finally:
        server.shutdown()
        server.server_close()


def test_failed_metric_batch_counts_metric_data_objects_not_one_batch():
    from types import SimpleNamespace
    batch = SimpleNamespace(resource_metrics=[SimpleNamespace(scope_metrics=[
        SimpleNamespace(metrics=[object(), object(), object()]), SimpleNamespace(metrics=[object(), object()])])])
    class Exporter:
        def export(self, batch):
            return MetricExportResult.FAILURE
    class Pipeline:
        def __init__(self):
            self.lost = []
        def _lost(self, signal, count):
            self.lost.append((signal, count))
    pipeline = Pipeline()
    assert _SafeExporter(Exporter(), pipeline, 'metrics').export(batch) == MetricExportResult.FAILURE
    assert pipeline.lost == [('metrics', 5)]


def acknowledgement(rejected, message='PRIVATE-REMOTE-BODY'):
    from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import ExportTraceServiceResponse
    response = ExportTraceServiceResponse()
    response.partial_success.rejected_spans = rejected
    response.partial_success.error_message = message
    return response.SerializeToString()


@pytest.mark.parametrize('body,reason,rejected', [
    (acknowledgement(1), 'partial_success', 1),
    (acknowledgement(0), 'warning', 0),
    (b'', None, 0), (b'\x0a\x00', None, 0),
])
def test_official_ack_reports_fixed_semantics_without_raw_text(body, reason, rejected, caplog, capsys, monkeypatch):
    import http.client
    monkeypatch.setattr(http.client.HTTPConnection, 'debuglevel', 1)
    reports = []
    with caplog.at_level(logging.DEBUG), receiver(body) as endpoint:
        exporter = HttpExporter(endpoint + '/v1/traces', 'traces', lambda *args: reports.append(args))
        try:
            assert exporter.export(one_span()) == SpanExportResult.SUCCESS
            assert reports == ([('traces', rejected, reason)] if reason else [])
        finally:
            exporter.shutdown()
    captured = capsys.readouterr()
    text = caplog.text + captured.out + captured.err
    assert 'PRIVATE-REMOTE-' not in text
    assert http.client.HTTPConnection.debuglevel == 1, 'customer debug settings unchanged'


@pytest.mark.parametrize('body,content_type', [
    (acknowledgement(-1), 'application/x-protobuf'),
    (acknowledgement(2), 'application/x-protobuf'),
    (b'\x08\x01', 'application/x-protobuf'),
    (b'\x0a\x03\x0a\x01\x01', 'application/x-protobuf'),
    (b'\x0a\x03\x12\x01\xff', 'application/x-protobuf'),
    (b'\x95\x03\x00', 'application/x-protobuf'),
    (b'\x93\x03' * 150 + b'\x94\x03' * 150, 'application/x-protobuf'),
    (b'X' * (4 * 1024 * 1024 + 1), 'application/x-protobuf'),
    (b'\x0a\x00', 'text/plain'),
])
def test_invalid_acknowledgement_is_failure_with_fixed_counter(body, content_type):
    reports = []
    with receiver(body, content_type=content_type) as endpoint:
        exporter = HttpExporter(endpoint + '/v1/traces', 'traces', lambda *args: reports.append(args))
        try:
            assert exporter.export(one_span()) == SpanExportResult.FAILURE
            assert reports == [('traces', 0, 'invalid_response')]
        finally:
            exporter.shutdown()


@pytest.mark.parametrize('phase', ['headers', 'body'])
def test_whole_attempt_deadline_bounds_slow_headers_or_trickle_body(phase):
    def slow(handler):
        if phase == 'body':
            handler.send_response(200)
            handler.send_header('Content-Type', 'application/x-protobuf')
            handler.end_headers()
        for _ in range(8):
            time.sleep(0.15)
            if phase == 'body':
                handler.wfile.write(b'\x00')
                handler.wfile.flush()
    with receiver(b'', behavior=slow) as endpoint:
        exporter = HttpExporter(endpoint + '/v1/traces', 'traces')
        started = time.monotonic()
        try:
            assert exporter.export(one_span(), timeout_millis=300) == SpanExportResult.FAILURE
            assert time.monotonic() - started < 0.9
        finally:
            exporter.shutdown()


def test_exporter_and_loss_callback_exceptions_are_not_retried_or_leaked(capsys):
    class Broken:
        def export(self, batch):
            raise RuntimeError('PRIVATE-EXPORTER-ERROR')
    class Pipeline:
        calls = 0
        def _lost(self, signal, count):
            self.calls += 1
            raise RuntimeError('PRIVATE-COUNTER-ERROR')
    pipeline = Pipeline()
    assert _SafeExporter(Broken(), pipeline, 'traces').export(one_span()) == SpanExportResult.FAILURE
    assert pipeline.calls == 1
    captured = capsys.readouterr()
    assert 'PRIVATE-' not in captured.out + captured.err
