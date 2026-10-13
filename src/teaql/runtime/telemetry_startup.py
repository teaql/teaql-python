"""SDK-neutral process configuration; importing this file imports no SDK."""
from dataclasses import dataclass
import os
import re
import sys
import threading
from urllib.parse import urlsplit

ENABLED = 'TEAQL_TELEMETRY_ENABLED'
SERVICE = 'TEAQL_TELEMETRY_SERVICE_NAME'
ENDPOINT = 'TEAQL_TELEMETRY_OTLP_ENDPOINT'
HINTS = f'{ENABLED}=true {SERVICE}=<application-name> {ENDPOINT}=<collector-url>'


def notice(message):
    try:
        print(message, file=sys.stderr)
    except Exception:
        pass


@dataclass(frozen=True)
class TelemetryConfiguration:
    enabled: bool = False
    service: str = ''
    endpoint: str = ''
    error: str = ''

    @classmethod
    def read(cls, environment):
        flag = environment.get(ENABLED, '').strip().lower()
        if flag in ('', 'false'):
            return cls()
        if flag != 'true':
            return cls(error='invalid-enable')
        service = environment.get(SERVICE, '').strip()
        if not re.fullmatch(r'[a-zA-Z0-9_.-]{1,120}', service):
            return cls(error='invalid-service')
        endpoint = environment.get(ENDPOINT, '')
        try:
            uri = urlsplit(endpoint)
            _ = uri.port
            if uri.scheme not in ('http', 'https') or not uri.hostname or uri.username is not None or uri.password is not None or '?' in endpoint or '#' in endpoint or any(c.isspace() for c in endpoint):
                return cls(error='invalid-endpoint')
        except ValueError:
            return cls(error='invalid-endpoint')
        return cls(True, service, endpoint.rstrip('/'))

    @property
    def message(self):
        if self.error:
            return f'TeaQL telemetry: disabled; configuration={self.error}. {HINTS}'
        if not self.enabled:
            return f'TeaQL telemetry: supported, disabled. Enable full masked diagnostics with {HINTS}'
        return f'TeaQL telemetry: starting standard module; full recording, masked SQL; {ENABLED}=true {SERVICE}={self.service} {ENDPOINT}={self.endpoint}'


_lock = threading.Lock()
_pipelines = {}
_announced = set()


def default_telemetry(environment=None):
    from .telemetry import NOOP_RUNTIME_TELEMETRY
    config = TelemetryConfiguration.read(os.environ if environment is None else environment)
    with _lock:
        if config.message not in _announced:
            _announced.add(config.message)
            notice(config.message)
        if not config.enabled:
            return NOOP_RUNTIME_TELEMETRY
        key = (config.service, config.endpoint)
        pipeline = _pipelines.get(key)
        if pipeline is not None and not pipeline.closed:
            return pipeline
        try:
            from .standard_telemetry import StandardTelemetry
        except ImportError:
            notice('TeaQL telemetry: standard module unavailable; install teaql[telemetry]. ' + HINTS)
            return NOOP_RUNTIME_TELEMETRY
        completed = threading.Event()
        result = []
        abandoned = threading.Event()
        handshake = threading.Lock()
        def build():
            try:
                candidate = StandardTelemetry(config)
                with handshake:
                    cleanup = abandoned.is_set()
                    if not cleanup:
                        result.append(candidate)
                if cleanup:
                    candidate.shutdown()
            except Exception:
                pass
            finally:
                completed.set()
        threading.Thread(target=build, daemon=True).start()
        completed.wait(5)
        with handshake:
            failed = not result
            if failed:
                abandoned.set()
        if failed:
            notice('TeaQL telemetry: initialization failed; business continues without export.')
            return NOOP_RUNTIME_TELEMETRY
        _pipelines[key] = result[0]
        notice('TeaQL telemetry: enabled; full recording, traces, metrics, logs and masked SQL.')
        return result[0]
