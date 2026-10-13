import json
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import threading
import pytest
from teaql.runtime.telemetry_startup import TelemetryConfiguration, ENABLED, SERVICE, ENDPOINT


def test_disabled_has_hints_without_importing_sdk():
    script = "from teaql.runtime.context import UserContext; import sys; UserContext(); assert not any(name.startswith('opentelemetry') for name in sys.modules)"
    result = subprocess.run([sys.executable, '-c', script], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    for name in (ENABLED, SERVICE, ENDPOINT):
        assert name in result.stderr


@pytest.mark.parametrize('endpoint', ['http://secret:password@localhost', 'http://localhost?token=secret', 'http://localhost?', 'file:///secret', 'http://localhost/#secret'])
def test_invalid_urls_never_echo(endpoint):
    config = TelemetryConfiguration.read({ENABLED: 'true', SERVICE: 'example', ENDPOINT: endpoint})
    assert not config.enabled and config.error == 'invalid-endpoint'
    assert 'secret' not in config.message


def test_official_sdk_exports_three_signals_with_carried_identity_and_no_global_replacement(monkeypatch):
    from teaql.runtime.standard_telemetry import StandardTelemetry
    from teaql.runtime.telemetry import RuntimeOperation
    from opentelemetry import trace
    from opentelemetry.proto.collector.logs.v1.logs_service_pb2 import ExportLogsServiceRequest
    from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import ExportTraceServiceRequest
    messages = []
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            messages.append((self.path, dict(self.headers), self.rfile.read(int(self.headers['Content-Length']))))
            self.send_response(200); self.send_header('Content-Type', 'application/x-protobuf'); self.end_headers()
        def log_message(self, *args):
            pass
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    monkeypatch.setenv('OTEL_EXPORTER_OTLP_HEADERS', 'Authorization=PRIVATE-CUSTOMER-TOKEN')
    previous = trace.get_tracer_provider()
    pipeline = StandardTelemetry(TelemetryConfiguration(True, 'sdk-test', f'http://127.0.0.1:{server.server_port}'))
    try:
        first = pipeline.start(RuntimeOperation('provider', 'first'))
        first.success()
        second = pipeline.start(RuntimeOperation('provider', 'second'))
        second.success()
        unrelated = pipeline.start(RuntimeOperation('query', 'unrelated'))
        pipeline.record_diagnostic({'teaql.sql.debug': 'SELECT second'}, second.correlation)
        pipeline.record_diagnostic({'teaql.sql.debug': 'SELECT first'}, first.correlation)
        unrelated.success()
        pipeline.flush()
        assert {path for path, _, _ in messages} == {'/v1/traces', '/v1/logs', '/v1/metrics'}
        assert all('Authorization' not in headers for _, headers, _ in messages)
        spans, logs = [], []
        for path, _, data in messages:
            if path == '/v1/traces':
                payload = ExportTraceServiceRequest.FromString(data)
                spans.extend(span for resource in payload.resource_spans for scope in resource.scope_spans for span in scope.spans)
            elif path == '/v1/logs':
                payload = ExportLogsServiceRequest.FromString(data)
                logs.extend(log for resource in payload.resource_logs for scope in resource.scope_logs for log in scope.log_records)
        assert len(spans) == 3
        sql = [log for log in logs if log.body.string_value == 'TeaQL SQL execution']
        assert len(sql) == 2
        for record, identity in zip(sql, [second.correlation, first.correlation]):
            assert int.from_bytes(record.trace_id, 'big') == identity[0]
            assert int.from_bytes(record.span_id, 'big') == identity[1]
        assert trace.get_tracer_provider() is previous
    finally:
        pipeline.shutdown(); server.shutdown(); server.server_close()


def test_runtime_projection_is_masked_when_ordinary_logging_is_disabled(monkeypatch):
    from datetime import datetime
    from teaql.runtime.context import UserContext
    from teaql.data_service import ExecutionMetadata, DataServiceOperation
    from teaql.sql.types import DatabaseKind
    from teaql.core.value import Value
    class Probe:
        def record_diagnostic(self, attributes, correlation):
            self.event = attributes, correlation
    probe = Probe()
    context = UserContext().with_runtime_telemetry(probe)
    context.disable_select_sql_log()
    context.disable_mutation_sql_log()
    monkeypatch.setenv('TEAQL_ALLOW_SENSITIVE_PLAINTEXT_LOGS', 'I_UNDERSTAND_SENSITIVE_DATA_MAY_BE_WRITTEN_TO_DISK')
    metadata = ExecutionMetadata('sqlite', DataServiceOperation.Query, datetime.now(), datetime.now(),
        parameterized_sql='SELECT name FROM sample WHERE name = ?', parameters=[Value.ValText('PRIVATE-VALUE')],
        parameter_log_policies=['masked'], sql_origin='generated', database_kind=DatabaseKind.Sqlite,
        comment='load PRIVATE-VALUE', execution_outcome='success')
    metadata._sql_correlation = (123, 456)
    context.record_metadata_log(metadata)
    assert probe.event[1] == (123, 456)
    assert 'PRIVATE-VALUE' not in json.dumps(probe.event[0])
    assert context.sql_logs() == []
