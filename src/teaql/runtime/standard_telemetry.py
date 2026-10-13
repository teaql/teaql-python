"""Optional isolated SDK. This module is loaded only after explicit enablement."""
import threading
from time import monotonic, time_ns
from opentelemetry import context as otel_context, trace
from opentelemetry._logs import LogRecord, SeverityNumber
from opentelemetry.metrics import NoOpMeterProvider
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.sampling import ALWAYS_ON
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk._logs import LoggerProvider
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from .telemetry_http import HttpExporter, record_count, export_result
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
from .telemetry import RuntimeOperation, runtime_error_category
from .telemetry_startup import TelemetryConfiguration, ENABLED, SERVICE, ENDPOINT, notice
from .telemetry_queue import ExportQueue, AdmissionBatchProcessor


class _SafeExporter:
    def __init__(self, delegate, pipeline, signal, queue=None):
        self.delegate, self.pipeline, self.signal, self.queue = delegate, pipeline, signal, queue

    def __getattr__(self, name):
        return getattr(self.delegate, name)

    def export(self, batch, *args, **kwargs):
        result_type = export_result(self.signal)
        ticket = self.queue.begin_export(batch) if self.queue is not None else None
        if self.queue is not None and ticket is None:
            return result_type.SUCCESS  # Retired SDK deque entries cannot re-export.
        try:
            count = record_count(batch, self.signal)
        except Exception:
            count = 0
        try:
            result = self.delegate.export(batch, *args, **kwargs)
        except Exception:
            result = result_type.FAILURE
        failed = getattr(result, 'name', '') == 'FAILURE'
        if ticket is not None:
            ticket(failed)
        elif failed:
            try:
                self.pipeline._lost(self.signal, count)
            except Exception:
                notice('TeaQL telemetry: export loss accounting incomplete; business outcome unchanged.')
        return result


class StandardTelemetry:
    def __init__(self, config):
        valid = TelemetryConfiguration.read({ENABLED: 'true', SERVICE: config.service, ENDPOINT: config.endpoint})
        if not valid.enabled:
            raise ValueError('invalid-telemetry-configuration')
        self.closed = False
        self._lock = threading.Lock()
        self._lifecycle_lock = threading.Lock()
        self._flush_jobs = {}
        self.losses = {'traces': 0, 'logs': 0, 'metrics': 0}
        self.loss_reasons = {signal: {reason: 0 for reason in (
            'queue_overflow', 'export_failure', 'shutdown', 'handoff_failure')} for signal in self.losses}
        self.queues = {signal: ExportQueue(signal, 2048, self._queue_loss) for signal in ('traces', 'logs')}
        self.responses = {signal: {'rejected': 0, 'partial_success': 0, 'warning': 0, 'invalid_response': 0}
                          for signal in self.losses}
        resource = Resource({'service.name': valid.service, 'teaql.runtime.language': 'python'})
        sdk_metrics = NoOpMeterProvider()
        self.traces = TracerProvider(resource=resource, sampler=ALWAYS_ON, shutdown_on_exit=False, meter_provider=sdk_metrics)
        self.http = {signal: HttpExporter(valid.endpoint + '/v1/' + signal, signal, self._response)
                     for signal in ('traces', 'logs', 'metrics')}
        trace_processor = BatchSpanProcessor(_SafeExporter(
            self.http['traces'], self, 'traces', self.queues['traces']),
            max_queue_size=2048, max_export_batch_size=128, schedule_delay_millis=1000, export_timeout_millis=5000, meter_provider=sdk_metrics)
        trace_processor._batch_processor = AdmissionBatchProcessor(trace_processor._batch_processor, self.queues['traces'])
        self.traces.add_span_processor(trace_processor)
        reader = PeriodicExportingMetricReader(_SafeExporter(
            self.http['metrics'], self, 'metrics'),
            export_interval_millis=10000, export_timeout_millis=5000)
        self.metrics = MeterProvider(resource=resource, metric_readers=[reader], shutdown_on_exit=False)
        self.logs = LoggerProvider(resource=resource, shutdown_on_exit=False, meter_provider=sdk_metrics)
        log_processor = BatchLogRecordProcessor(_SafeExporter(
            self.http['logs'], self, 'logs', self.queues['logs']),
            max_queue_size=2048, max_export_batch_size=128, schedule_delay_millis=1000, export_timeout_millis=5000, meter_provider=sdk_metrics)
        log_processor._batch_processor = AdmissionBatchProcessor(log_processor._batch_processor, self.queues['logs'])
        self.logs.add_log_record_processor(log_processor)
        self.tracer = self.traces.get_tracer('io.teaql.runtime')
        self.logger = self.logs.get_logger('io.teaql.runtime')
        meter = self.metrics.get_meter('io.teaql.runtime')
        self.duration = meter.create_histogram('teaql.runtime.operation.duration', unit='ms')
        self.operations = meter.create_counter('teaql.runtime.operation.count', unit='{operation}')
        self.lost_counter = meter.create_counter('teaql.telemetry.export.lost', unit='{record}')
        self.rejected_counter = meter.create_counter('teaql.telemetry.export.rejected', unit='{record_or_point}')
        self.response_counter = meter.create_counter('teaql.telemetry.export.response', unit='{response}')
        for signal in self.losses:
            for reason in self.loss_reasons[signal]:
                self.lost_counter.add(0, {'teaql.telemetry.signal': signal, 'teaql.telemetry.reason': reason})
            self.rejected_counter.add(0, {'teaql.telemetry.signal': signal})
            for reason in ('partial_success', 'warning', 'invalid_response'):
                self.response_counter.add(0, {'teaql.telemetry.signal': signal, 'teaql.telemetry.reason': reason})
        self.propagator = TraceContextTextMapPropagator()

    def _lost(self, signal, count):
        self._queue_loss(signal, count, 'export_failure')

    def _queue_loss(self, signal, count, reason):
        with self._lock:
            first = self.loss_reasons[signal][reason] == 0
            self.loss_reasons[signal][reason] += count
            if reason == 'export_failure':
                self.losses[signal] += count
        self.lost_counter.add(count, {'teaql.telemetry.signal': signal, 'teaql.telemetry.reason': reason})
        if first:
            notice(f'TeaQL telemetry: records lost; signal={signal} reason={reason}; business outcome unchanged.')

    def _response(self, signal, rejected, reason):
        with self._lock:
            first = self.responses[signal][reason] == 0
            self.responses[signal][reason] += 1
            self.responses[signal]['rejected'] += rejected
        self.rejected_counter.add(rejected, {'teaql.telemetry.signal': signal})
        self.response_counter.add(1, {'teaql.telemetry.signal': signal, 'teaql.telemetry.reason': reason})
        if first:
            notice(f'TeaQL telemetry: {signal} {reason}; fixed diagnostic counted; business outcome unchanged.')

    def health(self):
        with self._lock:
            snapshot = {'failed_records': dict(self.losses), 'responses': {signal: dict(values) for signal, values in self.responses.items()},
                        'loss_reasons': {signal: dict(values) for signal, values in self.loss_reasons.items()}}
        snapshot['queues'] = {signal: queue.snapshot() for signal, queue in self.queues.items()}
        return snapshot

    def start(self, operation):
        if self.closed:
            return _ClosedScope(self)
        return _Scope(self, operation.safe())

    def inject(self, carrier):
        self.propagator.inject(carrier)

    def emit(self, body, attributes, correlation):
        if not correlation or self.closed:
            return
        span_context = trace.SpanContext(correlation[0], correlation[1], False, trace.TraceFlags.SAMPLED)
        if not span_context.is_valid:
            notice('TeaQL telemetry: SQL correlation unavailable; no replacement span created.')
            return
        context = trace.set_span_in_context(trace.NonRecordingSpan(span_context), otel_context.Context())
        self.logger.emit(LogRecord(timestamp=time_ns(), context=context, severity_number=SeverityNumber.INFO,
                                   severity_text='INFO', body=body, attributes=attributes))

    def record_diagnostic(self, attributes, correlation):
        self.emit('TeaQL SQL execution', attributes, correlation)

    def _lifecycle(self, close):
        started = monotonic()
        if not self._lifecycle_lock.acquire(timeout=6):
            notice('TeaQL telemetry: lifecycle timed out; business outcome unchanged.')
            return
        try:
            if self.closed:
                return
            if close:
                self.closed = True
                for queue in self.queues.values():
                    queue.close()
            self._settle_lifecycle(close, started + 6)
        finally:
            self._lifecycle_lock.release()

    def _settle_lifecycle(self, close, deadline):
        prefixes = {signal: queue.prefix() for signal, queue in self.queues.items()}
        completed = []
        for signal, provider in (('traces', self.traces), ('logs', self.logs)):
            event = self._flush_jobs.get(signal) if not close else None
            if event is not None and not event.is_set():
                completed.append(event)
                continue
            event = threading.Event()
            if not close:
                self._flush_jobs[signal] = event
            completed.append(event)
            def run(provider=provider, event=event):
                try:
                    if close:
                        provider.shutdown()
                    else:
                        provider.force_flush(timeout_millis=5000)
                except Exception:
                    notice('TeaQL telemetry: lifecycle incomplete; business outcome unchanged.')
                finally:
                    event.set()
            threading.Thread(target=run, daemon=True).start()
        drained = all(queue.wait_prefix(prefixes[signal], max(0, deadline - 1 - monotonic()))
                      for signal, queue in self.queues.items())
        if not drained:
            notice('TeaQL telemetry: lifecycle timed out; business outcome unchanged.')
        if close:
            for event in completed:
                event.wait(max(0, deadline - 1 - monotonic()))
        if close and not drained:
            for queue in self.queues.values():
                queue.abort_queued()
            for signal in ('traces', 'logs'):
                self.http[signal].abort()
            for signal in ('traces', 'logs'):
                self.queues[signal].wait_idle(max(0, deadline - .3 - monotonic()))
                self.http[signal].wait_idle(max(0, deadline - .3 - monotonic()))
            for event in completed:
                event.wait(max(0, deadline - .3 - monotonic()))
        # The cumulative metric snapshot follows trace/log acknowledgements.
        # It can therefore report rejection/loss from those exact attempts.
        metric_done = threading.Event()
        def metrics():
            try:
                remaining = max(1, int((deadline - monotonic()) * 1000))
                if close:
                    self.metrics.shutdown(timeout_millis=remaining)
                else:
                    self.metrics.force_flush(timeout_millis=remaining)
            except Exception:
                notice('TeaQL telemetry: lifecycle incomplete; business outcome unchanged.')
            finally:
                metric_done.set()
        threading.Thread(target=metrics, daemon=True).start()
        if not metric_done.wait(max(0, deadline - monotonic())):
            notice('TeaQL telemetry: lifecycle timed out; business outcome unchanged.')
        if close:
            for queue in self.queues.values():
                queue.abort_queued()
            for exporter in self.http.values():
                exporter.shutdown()
                exporter.wait_idle(max(0, deadline - monotonic()))

    def flush(self):
        self._lifecycle(False)

    def shutdown(self):
        self._lifecycle(True)


class _Scope:
    def __init__(self, pipeline, operation):
        self.pipeline, self.operation, self.started = pipeline, operation, monotonic()
        self.span = pipeline.tracer.start_span('teaql.' + operation.family, attributes=operation.attributes)
        state = self.span.get_span_context()
        self.correlation = (state.trace_id, state.span_id)
        self.token = otel_context.attach(trace.set_span_in_context(self.span))
        self.ended = False

    def activate(self):
        if self.token is None and not self.ended:
            self.token = otel_context.attach(trace.set_span_in_context(self.span))

    def deactivate(self):
        if self.token is not None:
            token, self.token = self.token, None
            otel_context.detach(token)

    def cancelled(self, attributes=None):
        for key, value in (attributes or {}).items():
            if key == 'teaql.result.cardinality':
                self.span.set_attribute(key, value)
        self._finish('cancelled', 'cancelled')

    def success(self, attributes=None):
        for key, value in (attributes or {}).items():
            if key in ('teaql.result.cardinality', 'teaql.cache.result'):
                self.span.set_attribute(key, value)
        self._finish('success')

    def failure(self, error):
        self.span.set_attribute('teaql.error.type', type(error).__name__)
        self.span.set_attribute('teaql.error.category', runtime_error_category(error))
        self._finish('failure', runtime_error_category(error))

    def _finish(self, outcome, category=None):
        if self.ended:
            return
        self.ended = True
        try:
            if self.pipeline.closed:
                self.pipeline.queues['logs'].reject_late()
                return
            self.span.set_attribute('teaql.operation.outcome', outcome)
            self.span.set_status(trace.Status(trace.StatusCode.OK if outcome == 'success' else trace.StatusCode.ERROR))
            elapsed = max(0, monotonic() - self.started) * 1000
            tags = {'teaql.operation.family': self.operation.family, 'teaql.operation.outcome': outcome}
            self.pipeline.duration.record(elapsed, tags)
            self.pipeline.operations.add(1, tags)
            values = {**tags, 'teaql.operation.name': self.operation.name, 'teaql.operation.duration_ms': elapsed}
            if category:
                values['teaql.error.category'] = category
            self.pipeline.emit('TeaQL runtime operation completed', values, self.correlation)
        finally:
            self.deactivate()
            self.span.end()


class _ClosedScope:
    correlation = None

    def __init__(self, pipeline):
        self.pipeline, self.ended = pipeline, False

    def success(self, attributes=None):
        if not self.ended:
            self.ended = True
            for queue in self.pipeline.queues.values():
                queue.reject_late()

    def failure(self, error):
        self.success()
