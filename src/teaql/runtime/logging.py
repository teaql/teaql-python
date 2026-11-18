"""Application-owned structured runtime logging and shared file rotation.

Call ``RuntimeLogger`` once during application composition and pass it to
request contexts. The implicit default is shared by contexts in the process.
Only already-projected diagnostic fields reach this destination.
"""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import stat
import sys
import threading
import time
from time import monotonic as _lock_clock
from typing import Mapping, Sequence
from urllib.parse import unquote, urlsplit


class RuntimeLoggingError(RuntimeError):
    """A value-free failure to initialize a required logging destination."""


_locks_guard = threading.Lock()
_locks: dict[str, threading.RLock] = {}
_default_guard = threading.Lock()
_defaults: dict[tuple, RuntimeLogger] = {}


def _failure(code: str, log_name: str = 'teaql') -> None:
    try:
        print(json.dumps({'timestamp': datetime.now(timezone.utc).isoformat(), 'level': 'ERROR',
                          'log_name': log_name, 'runtime': 'python', 'event': 'logging.failure', 'message': 'Runtime logging failed',
                          'error_code': code}, separators=(',', ':')), file=sys.stderr)
    except Exception:
        pass


def _name(explicit: str | None, models: Sequence[str], environment: Mapping[str, str]) -> str:
    value = explicit if explicit is not None else environment.get('TEAQL_DOMAIN') or (
        models[0] if len(models) == 1 else 'teaql')
    if (not isinstance(value, str) or not value or value in ('.', '..') or value[-1] in ' .'
            or any(ord(c) < 32 or ord(c) == 127 or c in '<>:"/\\|?*' for c in value)
            or re.fullmatch(r'(?i)(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])', value.split('.')[0])):
        raise RuntimeLoggingError('invalid_log_name')
    value.encode('utf-8', errors='strict')
    return value


def _size(value: str) -> int:
    matched = re.fullmatch(r'([0-9]+)\s*(K|KB|M|MB|G|GB)?', value.strip().upper())
    if not matched:
        raise RuntimeLoggingError('invalid_log_max_size')
    multiplier = {'K': 1024, 'KB': 1024, 'M': 1024 ** 2, 'MB': 1024 ** 2,
                  'G': 1024 ** 3, 'GB': 1024 ** 3}.get(matched[2], 1)
    result = int(matched[1]) * multiplier
    if not 0 < result <= 2 ** 63 - 1:
        raise RuntimeLoggingError('invalid_log_max_size')
    return result


_event_fields = frozenset(('timestamp', 'level', 'log_name', 'runtime', 'event', 'message'))
_human_header = re.compile(r'^\d{4}-\d\d-\d\dT\S+(?:Z|\+00:00) \[TeaQL\]\[.*\]\[(INFO|WARN|ERROR)\] .+ runtime=\S+$')


def _human_controls(value: str) -> str:
    # Escape controls even when JSON permits them literally (C1 and Unicode
    # line separators). A payload can never create a header or terminal escape.
    return ''.join('\\u%04x' % ord(c) if ord(c) < 32 or 127 <= ord(c) <= 159
                   or c in '\u2028\u2029' else c for c in value)


def _human_scalar(value: str) -> str:
    return _human_controls(value.replace('\\', '\\\\'))


def _human_record(record) -> str:
    scalar = _human_scalar
    lines = [f"{scalar(record['timestamp'])} [TeaQL][{scalar(record['log_name'])}]"
             f"[{record['level']}] {scalar(record['event'])} runtime={scalar(record['runtime'])}",
             '  ' + scalar(record['message'])]
    for key in sorted(record.keys() - _event_fields):
        value = record[key]
        if key == 'sql' and isinstance(value, str):
            lines.append('  sql:')
            lines.extend('    ' + scalar(line) for line in value.split('\n'))
        else:
            # JSON detail values retain numbers, booleans, null and typed audit
            # identities, rather than calling an arbitrary object's str().
            lines.append('  ' + scalar(key) + '=' + _human_controls(json.dumps(value, ensure_ascii=False, separators=(',', ':'))))
    return '\n'.join(lines) + '\n'


class RuntimeLogger:
    """A startup-initialized destination, independent of optional OTel SDKs.

    ``model_names`` contains names known by the application at initialization;
    it is never inferred from a request or an entity type.
    """

    def __init__(self, log_name: str | None = None, *, model_names: Sequence[str] = (),
                 environment: Mapping[str, str] | None = None, working_directory=None,
                 log_format: str | None = None):
        environment = os.environ if environment is None else environment
        try:
            self.log_name = _name(log_name, model_names, environment)
            self.log_format = log_format if log_format is not None else environment.get('TEAQL_LOG_FORMAT', 'json')
            if self.log_format not in ('json', 'human'):
                raise RuntimeLoggingError('invalid_log_format')
            self.max_size = _size(environment.get('TEAQL_LOG_MAX_SIZE', '50M'))
            files = environment.get('TEAQL_LOG_MAX_FILES', '7')
            if not re.fullmatch(r'[0-9]+', files) or int(files) > 2 ** 31 - 1:
                raise RuntimeLoggingError('invalid_log_max_files')
            self.max_files = int(files)
            self.stream = None
            endpoint = environment.get('TEAQL_LOG_ENDPOINT') or './logs/' + self.log_name + '.log'
            if endpoint in ('stdout', '-', 'stderr'):
                self.stream = 'stderr' if endpoint == 'stderr' else 'stdout'
                self.path = None
                self._lock = threading.RLock()
            else:
                if endpoint.startswith('file:'):
                    url = urlsplit(endpoint)
                    if url.netloc not in ('', 'localhost') or url.query or url.fragment:
                        raise RuntimeLoggingError('invalid_log_endpoint')
                    endpoint = unquote(url.path)
                elif '://' in endpoint:
                    raise RuntimeLoggingError('invalid_log_endpoint')
                if not endpoint:
                    raise RuntimeLoggingError('invalid_log_endpoint')
                base = Path.cwd() if working_directory is None else Path(working_directory)
                self.path = (base / endpoint).resolve()
                self._lock_path = self.path.with_name(self.path.name + '.lock')
                with _locks_guard:
                    self._lock = _locks.setdefault(str(self.path), threading.RLock())
            self._emit(self._record('INFO', 'runtime.start', 'TeaQL runtime started'))
        except Exception as error:
            code = str(error) if isinstance(error, RuntimeLoggingError) else 'log_destination_unavailable'
            _failure(code, getattr(self, 'log_name', 'teaql'))
            raise RuntimeLoggingError(code) from None

    def _record(self, level: str, event: str, message: str, fields=None):
        record = dict(fields or {})
        record.update(timestamp=datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z'),
                      level=level, log_name=self.log_name, runtime='python', event=event, message=message)
        return record

    def write(self, level: str, event: str, message: str, **safe_fields) -> bool:
        if level not in ('INFO', 'WARN', 'ERROR'):
            raise ValueError('invalid_log_level')
        try:
            self._emit(self._record(level, event, message, safe_fields))
            return True
        except Exception:
            _failure('log_write_failed', self.log_name)
            return False

    @contextmanager
    def _destination_lock(self):
        # Exclusive creation coordinates threads and independent processes on
        # every supported server platform, including other TeaQL runtimes.
        # Never remove a lock owned by another writer.
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            # Logging's lock timeout has its own clock reference. A business
            # cache's clock adapter/mock must not be consumed by diagnostics.
            deadline = _lock_clock() + 30
            while True:
                try:
                    descriptor = os.open(self._lock_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                    break
                except FileExistsError:
                    if _lock_clock() >= deadline:
                        raise OSError('log_destination_locked') from None
                    time.sleep(0.005)
            try:
                yield
            finally:
                try:
                    os.close(descriptor)
                finally:
                    self._lock_path.unlink()

    def _archives(self):
        prefix = self.path.name + '.'
        for file in self.path.parent.iterdir():
            suffix = file.name.removeprefix(prefix) if file.name.startswith(prefix) else ''
            if re.fullmatch(r'[1-9][0-9]*', suffix):
                # Numeric archive names are owned regular files. A directory
                # or symlink at that name is an I/O failure, never movable data.
                if not stat.S_ISREG(file.lstat().st_mode):
                    raise OSError('log_archive_not_file')
                yield int(suffix), file

    def _rotate(self):
        for number, file in sorted(self._archives(), reverse=True):
            if number >= self.max_files:
                file.unlink()
            else:
                file.replace(self.path.with_name(self.path.name + '.' + str(number + 1)))
        if self.max_files:
            self.path.replace(self.path.with_name(self.path.name + '.1'))
        else:
            self.path.unlink()

    def _emit(self, record):
        encoded = json.dumps(record, ensure_ascii=False, separators=(',', ':'), allow_nan=False)
        # Normalize through the same JSON event in both modes. Neither renderer
        # gets execution bindings or unprojected audit/error values.
        text = encoded + '\n' if self.log_format == 'json' else _human_record(json.loads(encoded))
        data = text.encode('utf-8')
        if self.stream:
            with self._lock:
                target = sys.stderr if self.stream == 'stderr' else sys.stdout
                target.write(data.decode('utf-8'))
                target.flush()
            return
        with self._destination_lock():
            # Check before retention/rotation so an incompatible append leaves
            # both the existing active file and its archives untouched.
            self._check_presentation()
            for number, archive in self._archives():
                if number > self.max_files:
                    archive.unlink()
            try:
                current = self.path.stat()
            except FileNotFoundError:
                current = None
            if current is not None:
                if not stat.S_ISREG(current.st_mode):
                    raise OSError('log_destination_not_file')
                day = datetime.fromtimestamp(current.st_mtime, timezone.utc).date()
                if current.st_size and (current.st_size + len(data) > self.max_size
                                        or day != datetime.now(timezone.utc).date()):
                    self._rotate()
            # Reopen under the shared lock: another writer may have rotated
            # since this logger's preceding append.
            descriptor = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
            with os.fdopen(descriptor, 'ab', buffering=0) as output:
                offset = 0
                while offset < len(data):
                    count = output.write(data[offset:])
                    if not count:
                        raise OSError('incomplete_log_write')
                    offset += count

    def _check_presentation(self):
        try:
            current = self.path.stat()
        except FileNotFoundError:
            return
        if not stat.S_ISREG(current.st_mode):
            raise OSError('log_destination_not_file')
        if not current.st_size:
            return
        with self.path.open('r', encoding='utf-8', errors='strict') as stream:
            first = stream.readline()
        if not first.endswith('\n'):
            raise OSError('incompatible_log_format')
        first = first[:-1]
        if self.log_format == 'human' and _human_header.fullmatch(first):
            return
        if self.log_format == 'json':
            try:
                event = json.loads(first)
                if (isinstance(event, dict) and _event_fields <= event.keys()
                        and all(isinstance(event[k], str) for k in _event_fields)
                        and event['level'] in ('INFO', 'WARN', 'ERROR')):
                    return
            except (ValueError, TypeError):
                pass
        raise OSError('incompatible_log_format')


def default_runtime_logger() -> RuntimeLogger:
    # Read only logging configuration; no credentials or other environment
    # values are copied into this application-owned resource.
    names = ('TEAQL_DOMAIN', 'TEAQL_LOG_ENDPOINT', 'TEAQL_LOG_MAX_SIZE', 'TEAQL_LOG_MAX_FILES', 'TEAQL_LOG_FORMAT')
    environment = {name: os.environ[name] for name in names if name in os.environ}
    key = (str(Path.cwd().resolve()), *[environment.get(name) for name in names])
    with _default_guard:
        if key not in _defaults:
            _defaults[key] = RuntimeLogger(environment=environment)
        return _defaults[key]


def telemetry_for_context(context):
    """Keep compatibility with lightweight application context adapters."""
    if context is None:
        return None
    local = getattr(context, 'operation_telemetry', None)
    return local() if callable(local) else context.runtime_telemetry()


class RuntimeLogTelemetry:
    """Local operation logging alongside the independently owned OTel adapter."""

    def __init__(self, delegate, logger: RuntimeLogger):
        self._delegate = delegate
        self._logger = logger

    def __getattr__(self, name):
        return getattr(self._delegate, name)

    def start(self, operation):
        from .telemetry import NOOP_RUNTIME_TELEMETRY
        try:
            delegate = self._delegate.start(operation)
        except BaseException:
            delegate = NOOP_RUNTIME_TELEMETRY.start(operation)
        return _LoggedScope(delegate, operation, self._logger)


class _LoggedScope:
    def __init__(self, delegate, operation, logger):
        self._delegate, self._operation, self._logger = delegate, operation, logger
        self._ended = False

    def __getattr__(self, name):
        return getattr(self._delegate, name)

    def _finish(self, outcome, error=None):
        if self._ended:
            return False
        self._ended = True
        try:
            fields = {'category': self._operation.family.upper(), 'operation': self._operation.name, 'outcome': outcome}
            level = 'INFO'
            if error is not None:
                from .telemetry import runtime_error_category
                from .i18n import CheckException
                from .mutation_policy import MutationPolicyError
                from teaql.core.request_intent import RequestIntentError
                category = ('validation' if isinstance(error, (CheckException, RequestIntentError))
                            else 'authorization' if isinstance(error, MutationPolicyError)
                            else runtime_error_category(error))
                fields['error_code'] = category
                level = 'WARN' if category in ('validation', 'authorization', 'conflict') else 'ERROR'
            correlation = getattr(self._delegate, 'correlation', None)
            trace_id = getattr(correlation, 'trace_id', None)
            if trace_id:
                fields['trace_id'] = trace_id
            self._logger.write(level, 'operation.' + outcome, 'TeaQL operation ' + outcome, **fields)
        except Exception:
            _failure('log_write_failed')
        return True

    def success(self, attributes=None):
        if self._finish('success'):
            self._delegate.success(attributes)

    def failure(self, error):
        if self._finish('failure', error):
            self._delegate.failure(error)

    def cancelled(self, attributes=None):
        import asyncio
        if self._finish('cancelled', asyncio.CancelledError()):
            callback = getattr(self._delegate, 'cancelled', None)
            if callback:
                callback(attributes)
            else:
                self._delegate.failure(asyncio.CancelledError())
