"""Actual SDK queues and owned HTTP, not simulated queue lengths."""
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from teaql.runtime.standard_telemetry import StandardTelemetry
from teaql.runtime.telemetry import RuntimeOperation
from teaql.runtime.telemetry_startup import TelemetryConfiguration
from teaql.runtime.telemetry_http import HttpExporter, export_result


def burst(pipeline, count):
    for _ in range(count):
        pipeline.start(RuntimeOperation('query', 'native queue fixture')).success()


def test_inflight_and_queued_sdk_records_share_one_budget(monkeypatch):
    release = threading.Event()
    entered = {signal: threading.Event() for signal in ('traces', 'logs')}
    def export(self, batch, *args, **kwargs):
        if self.signal in entered:
            entered[self.signal].set()
            release.wait(3)
        return export_result(self.signal).SUCCESS
    monkeypatch.setattr(HttpExporter, 'export', export)
    pipeline = StandardTelemetry(TelemetryConfiguration(True, 'native-quota', 'http://127.0.0.1:1'))
    try:
        burst(pipeline, 128)
        assert all(event.wait(1) for event in entered.values())
        burst(pipeline, 2172)
        health = pipeline.health()
        for signal in ('traces', 'logs'):
            assert health.get('loss_reasons', {}).get(signal, {}).get('queue_overflow', 0) == 252
    finally:
        release.set()
        pipeline.shutdown()


def test_shutdown_settles_actual_never_acknowledged_backlog_before_return():
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            self.rfile.read(int(self.headers['Content-Length']))
            self.connection.settimeout(8)
            try:
                while self.connection.recv(1):
                    pass
            except OSError:
                pass
        def log_message(self, *args):
            pass
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    server.daemon_threads = True
    threading.Thread(target=server.serve_forever, daemon=True).start()
    pipeline = StandardTelemetry(TelemetryConfiguration(True, 'native-backlog', f'http://127.0.0.1:{server.server_port}'))
    try:
        burst(pipeline, 2300)
        started = time.monotonic()
        pipeline.shutdown()
        assert time.monotonic() - started < 6.5
        # The SDK's actual owned workers must terminate, not continue exporting
        # the remaining deque after the public lifecycle method returned.
        trace_processor = pipeline.traces._active_span_processor._span_processors[0]
        log_processor = pipeline.logs._multi_log_record_processor._log_record_processors[0]
        assert not trace_processor._batch_processor._worker_thread.is_alive()
        assert not log_processor._batch_processor._worker_thread.is_alive()
        for signal in ('traces', 'logs'):
            queue = pipeline.health()['queues'][signal]
            assert queue['outstanding'] == queue['exporting'] == 0
            assert queue['admitted'] == queue['completed'] + queue['retired'] == 2048
    finally:
        pipeline.shutdown()
        server.shutdown()
        server.server_close()


def test_closed_and_active_scopes_report_late_once_without_new_spans(monkeypatch):
    monkeypatch.setattr(HttpExporter, 'export', lambda self, batch, *args, **kwargs: export_result(self.signal).SUCCESS)
    pipeline = StandardTelemetry(TelemetryConfiguration(True, 'native-late', 'http://127.0.0.1:1'))
    active = pipeline.start(RuntimeOperation('query', 'active before shutdown'))
    pipeline.shutdown()
    before = pipeline.health()
    active.success()
    active.success()
    late = pipeline.start(RuntimeOperation('query', 'new after shutdown'))
    assert late.correlation is None
    late.success()
    late.failure(RuntimeError('late private error'))
    after = pipeline.health()
    for signal in ('traces', 'logs'):
        assert after['queues'][signal]['post_shutdown'] - before['queues'][signal]['post_shutdown'] == 2
        assert after['queues'][signal]['admitted'] == before['queues'][signal]['admitted']
        assert after['queues'][signal]['outstanding'] == 0
