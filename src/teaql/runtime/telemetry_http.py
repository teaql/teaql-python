"""Owned finite OTLP HTTP transport using the official protobuf encoders.

The generated flat library owns a `requests` package. The private stdlib HTTP
connections need neither that third-party package nor customer HTTP log settings.
"""
import http.client
import socket
import threading
from time import monotonic
from urllib.parse import urlsplit
from opentelemetry.sdk.metrics.export import MetricExporter, MetricExportResult
from opentelemetry.sdk.trace.export import SpanExportResult
from opentelemetry.sdk._logs.export import LogRecordExportResult
from opentelemetry.exporter.otlp.proto.common.trace_encoder import encode_spans
from opentelemetry.exporter.otlp.proto.common.metrics_encoder import encode_metrics
from opentelemetry.exporter.otlp.proto.common._log_encoder import encode_logs
from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import ExportTraceServiceResponse
from opentelemetry.proto.collector.logs.v1.logs_service_pb2 import ExportLogsServiceResponse
from opentelemetry.proto.collector.metrics.v1.metrics_service_pb2 import ExportMetricsServiceResponse


MAX_RESPONSE_BYTES = 4 * 1024 * 1024


def export_result(signal):
    return {'traces': SpanExportResult, 'metrics': MetricExportResult, 'logs': LogRecordExportResult}[signal]


def record_count(batch, signal):
    if signal != 'metrics':
        return len(batch)
    return sum(len(scope.metrics) for resource in batch.resource_metrics for scope in resource.scope_metrics)


def _varint(data, offset):
    value = 0
    for index in range(10):
        if offset >= len(data):
            raise ValueError('invalid-response')
        byte = data[offset]
        offset += 1
        if index == 9 and byte > 1:
            raise ValueError('invalid-response')
        value |= (byte & 127) << (index * 7)
        if byte < 128:
            return value, offset
    raise ValueError('invalid-response')


def _validate_wire(data, inner=False):
    """Bound the two-level proto3 schema before official decoding.

    Unknown proto2 groups are not part of an OTLP acknowledgement. Reject them
    rather than relying on a decoder's recursive unknown-field skipping.
    """
    offset = 0
    while offset < len(data):
        tag, offset = _varint(data, offset)
        field, wire = tag >> 3, tag & 7
        if not 0 < field < 2**29 or (field == 1 and wire != (0 if inner else 2)) or (inner and field == 2 and wire != 2):
            raise ValueError('invalid-response')
        if wire == 0:
            _, offset = _varint(data, offset)
        elif wire in (1, 5):
            offset += 8 if wire == 1 else 4
        elif wire == 2:
            size, offset = _varint(data, offset)
            end = offset + size
            if end > len(data):
                raise ValueError('invalid-response')
            if field == 1 and not inner:
                _validate_wire(data[offset:end], True)
            elif field == 2 and inner:
                data[offset:end].decode('utf-8', 'strict')
            offset = end
        else:
            raise ValueError('invalid-response')
        if offset > len(data):
            raise ValueError('invalid-response')


def _acknowledgement(data, signal, submitted):
    _validate_wire(data)
    response_type, field = {
        'traces': (ExportTraceServiceResponse, 'rejected_spans'),
        'logs': (ExportLogsServiceResponse, 'rejected_log_records'),
        'metrics': (ExportMetricsServiceResponse, 'rejected_data_points'),
    }[signal]
    response = response_type.FromString(data)
    rejected = getattr(response.partial_success, field)
    if rejected < 0 or rejected > submitted:
        raise ValueError('invalid-response')
    return rejected, ('partial_success' if rejected else 'warning' if response.partial_success.error_message else None)


class _Deadline:
    """Cancel only sockets belonging to this owned HTTP attempt."""
    def __init__(self, seconds):
        self.ends = monotonic() + seconds
        self.lock = threading.Lock()
        self.sockets = []
        self.connection = None
        self.expired = False
        self.timer = threading.Timer(seconds, self.abort)
        self.timer.daemon = True
        self.timer.start()

    def abort(self):
        with self.lock:
            self.expired = True
            if self.connection is not None and self.connection.sock is not None:
                self.sockets.append(self.connection.sock)
            for sock in self.sockets:
                try:
                    sock.shutdown(socket.SHUT_RDWR)
                except (OSError, ValueError):
                    pass

    def attach(self, connection):
        with self.lock:
            self.connection = connection
        self.check()

    def check(self):
        if self.expired or monotonic() >= self.ends:
            raise TimeoutError('export-deadline')

    def close(self):
        self.timer.cancel()


class HttpExporter(MetricExporter):
    def __init__(self, endpoint, signal, on_response=None):
        super().__init__()
        self.endpoint, self.signal = endpoint, signal
        self._lock = threading.Lock()
        self._active = None
        self.closed = False
        self.on_response = on_response

    def _report(self, reason, rejected=0):
        if self.on_response and reason:
            try:
                self.on_response(self.signal, rejected, reason)
            except Exception:
                pass  # Optional diagnostics must not change export/business work.

    def export(self, batch, timeout_millis=None, **kwargs):
        result = export_result(self.signal)
        if self.closed:
            return result.FAILURE
        encoder = {'traces': encode_spans, 'metrics': encode_metrics, 'logs': encode_logs}[self.signal]
        try:
            payload = encoder(batch)
            submitted = (sum(len(getattr(metric, metric.WhichOneof('data')).data_points)
                for resource in payload.resource_metrics for scope in resource.scope_metrics
                for metric in scope.metrics if metric.WhichOneof('data'))
                if self.signal == 'metrics' else len(batch))
            seconds = min(3, timeout_millis / 1000) if timeout_millis is not None else 3
            if seconds <= 0:
                return result.FAILURE
            with self._lock:
                if self.closed or self._active is not None:
                    return result.FAILURE
                attempt = _Attempt(self.endpoint, self.signal, payload.SerializeToString(), submitted, seconds)
                self._active = attempt
            def work():
                try:
                    attempt.run()
                finally:
                    with self._lock:
                        if self._active is attempt:
                            self._active = None
                    attempt.done.set()
            threading.Thread(target=work, daemon=True).start()
            if not attempt.done.wait(seconds):
                attempt.deadline.abort()
                return result.FAILURE
            if attempt.deadline.expired:
                return result.FAILURE
            if attempt.outcome == 'invalid_response':
                self._report('invalid_response')
                return result.FAILURE
            if attempt.outcome == 'failure':
                return result.FAILURE
            self._report(attempt.outcome, attempt.rejected)
            return result.SUCCESS
        except Exception:
            # No driver/endpoint/response text can escape into SDK log handlers.
            return result.FAILURE

    def force_flush(self, timeout_millis=5000):
        return True

    def shutdown(self, timeout_millis=5000, **kwargs):
        with self._lock:
            self.closed = True
            attempt = self._active
        if attempt:
            attempt.deadline.abort()

    def abort(self):
        with self._lock:
            attempt = self._active
        if attempt:
            attempt.deadline.abort()

    def wait_idle(self, timeout):
        with self._lock:
            attempt = self._active
        return attempt is None or attempt.done.wait(timeout)


class _Attempt:
    """At most one private attempt/worker per exporter, no customer HTTP logs."""
    def __init__(self, endpoint, signal, payload, submitted, seconds):
        self.endpoint, self.signal, self.payload = endpoint, signal, payload
        self.submitted, self.seconds = submitted, seconds
        self.done = threading.Event()
        self.deadline = _Deadline(seconds)
        self.outcome, self.rejected = 'failure', 0

    def run(self):
        connection = None
        try:
            uri = urlsplit(self.endpoint)
            connection_type = http.client.HTTPSConnection if uri.scheme == 'https' else http.client.HTTPConnection
            connection = connection_type(uri.hostname, uri.port, timeout=self.seconds)
            connection.set_debuglevel(0)
            self.deadline.attach(connection)
            connection.connect()
            self.deadline.check()
            connection.request('POST', uri.path or '/', self.payload,
                headers={'Content-Type': 'application/x-protobuf', 'Accept-Encoding': 'identity', 'Connection': 'close'})
            response = connection.getresponse()
            self.deadline.check()
            if response.status != 200:
                return
            if (response.getheader('Content-Type', '').split(';')[0].strip().lower() != 'application/x-protobuf'
                    or response.getheader('Content-Encoding', 'identity').lower() != 'identity'):
                self.outcome = 'invalid_response'
                return
            try:
                length = response.getheader('Content-Length')
                if length is not None and (not length.isdecimal() or int(length) > MAX_RESPONSE_BYTES):
                    raise ValueError('invalid-response')
                data = bytearray()
                while True:
                    self.deadline.check()
                    chunk = response.read(16384)
                    if not chunk:
                        break
                    if len(data) + len(chunk) > MAX_RESPONSE_BYTES:
                        raise ValueError('invalid-response')
                    data.extend(chunk)
                self.deadline.check()
                self.rejected, self.outcome = _acknowledgement(bytes(data), self.signal, self.submitted)
            except ValueError:
                self.outcome = 'invalid_response'
        except Exception:
            self.outcome = 'failure'  # Never return/log raw transport exceptions.
        finally:
            if connection:
                connection.close()
            self.deadline.close()
