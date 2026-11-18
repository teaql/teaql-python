"""Native acceptance of the two presentations, including whole-event files."""
import concurrent.futures
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from teaql.runtime import RuntimeLogger, RuntimeLoggingError, UserContext
from teaql.runtime.telemetry import RuntimeOperation, observe_runtime_operation


HEADER = re.compile(r'^(\S+) \[TeaQL\]\[(.*)\]\[(INFO|WARN|ERROR)\] (.*) runtime=(\S+)$')


def scalar(text):
    return re.sub(r'\\(\\|u[0-9a-fA-F]{4})',
                  lambda match: '\\' if match[1] == '\\' else chr(int(match[1][1:], 16)), text)


def events(text, presentation):
    if presentation == 'json':
        # JSONL separates on LF, not on Unicode characters permitted in JSON strings.
        return [json.loads(line) for line in text.split('\n')[:-1]]
    output = []
    sql = None
    for line in text.split('\n')[:-1]:
        header = HEADER.fullmatch(line)
        if header:
            timestamp, name, level, event, runtime = header.groups()
            assert datetime.fromisoformat(timestamp.replace('Z', '+00:00')).utcoffset() == timedelta(0)
            output.append(dict(timestamp=timestamp, log_name=scalar(name), level=level,
                               event=scalar(event), runtime=scalar(runtime)))
            sql = None
        else:
            assert output and line.startswith('  '), 'unindented human continuation: ' + repr(line)
            row = output[-1]
            if 'message' not in row:
                row['message'] = scalar(line[2:])
            elif line == '  sql:':
                row['sql'] = ''
                sql = []
            elif line.startswith('    ') and sql is not None:
                sql.append(scalar(line[4:]))
                row['sql'] = '\n'.join(sql)
            else:
                key, value = line[2:].split('=', 1)
                row[scalar(key)] = json.loads(value)
                sql = None
        assert not any(ord(c) < 32 or 127 <= ord(c) <= 159 or c in '\u2028\u2029' for c in line)
    assert text.endswith('\n') and all('message' in row for row in output)
    return output


def read(path, presentation):
    return events(path.read_text(encoding='utf-8'), presentation)


@pytest.mark.parametrize('presentation', ['json', 'human'])
@pytest.mark.parametrize('explicit,domain,models,name', [
    ('application', 'domain', ['model'], 'application'),
    (None, 'domain', ['model'], 'domain'), (None, None, ['model'], 'model'),
    (None, None, [], 'teaql'), (None, None, ['one', 'two'], 'teaql'),
])
def test_selection_paths_precedence_frozen_contexts_and_two_starts(tmp_path, presentation, explicit, domain, models, name):
    env = {'TEAQL_LOG_FORMAT': presentation}
    if domain:
        env['TEAQL_DOMAIN'] = domain
    logger = RuntimeLogger(explicit, model_names=models, environment=env, working_directory=tmp_path)
    context = UserContext.new(runtime_logger=logger)
    env['TEAQL_LOG_FORMAT'] = 'human' if presentation == 'json' else 'json'
    env['TEAQL_DOMAIN'] = 'changed'
    assert context._runtime_logger is logger
    assert logger.log_format == presentation and logger.log_name == name
    assert logger.write('INFO', 'frozen', 'Configuration is startup-owned')
    RuntimeLogger(name, log_format=presentation, environment={}, working_directory=tmp_path)
    path = tmp_path / ('logs/' + name + '.log')
    assert [row['event'] for row in read(path, presentation)] == ['runtime.start', 'frozen', 'runtime.start']
    override = RuntimeLogger(name, log_format=presentation,
        environment={'TEAQL_LOG_ENDPOINT': 'other/custom.log', 'TEAQL_LOG_FORMAT': 'invalid-unused'}, working_directory=tmp_path)
    assert override.log_format == presentation
    assert read(tmp_path / 'other/custom.log', presentation)[0]['log_name'] == name


def test_default_is_json(tmp_path):
    logger = RuntimeLogger(environment={}, working_directory=tmp_path)
    assert logger.log_format == 'json'
    assert read(logger.path, 'json')[0]['event'] == 'runtime.start'


@pytest.mark.parametrize('presentation', ['json', 'human'])
def test_logging_does_not_consume_the_business_cache_clock(tmp_path, presentation):
    context = UserContext.new(runtime_logger=RuntimeLogger(log_format=presentation, environment={}, working_directory=tmp_path))
    with patch('teaql.runtime.context.time.monotonic', side_effect=[100.0, 101.0]):
        context.put_to_local_cache('ttl', 'temporary', 1)
        assert context.get_from_local_cache('ttl') is None


@pytest.mark.parametrize('value', ['', 'debug', 'JSON', 'human\nFORMAT-SECRET'])
@pytest.mark.parametrize('setting', ['app', 'environment'])
def test_invalid_format_fails_without_echo(tmp_path, capsys, value, setting):
    with pytest.raises(RuntimeLoggingError, match='invalid_log_format'):
        RuntimeLogger(log_format=value if setting == 'app' else None,
            environment={'TEAQL_LOG_FORMAT': value} if setting == 'environment' else {}, working_directory=tmp_path)
    failure = json.loads(capsys.readouterr().err)
    assert failure['level'] == 'ERROR' and failure['error_code'] == 'invalid_log_format'
    assert 'FORMAT-SECRET' not in json.dumps(failure) and not list(tmp_path.iterdir())


@pytest.mark.parametrize('presentation', ['json', 'human'])
@pytest.mark.parametrize('endpoint', ['stdout', 'stderr'])
def test_streams_share_projected_typed_events(tmp_path, capsys, presentation, endpoint):
    logger = RuntimeLogger('应用', log_format=presentation,
        environment={'TEAQL_LOG_ENDPOINT': endpoint}, working_directory=tmp_path)
    fields = dict(category='AUDIT', trace_id='0123456789abcdef0123456789abcdef', outcome='retrying',
        error_code='connection_timeout', entity_id=42, changes=[{'field': 'password', 'value': '***'}],
        elapsed_us=12, result_count=0, omission_reason=None, sql='SELECT id\nFROM customer\n\x1b[31m\r\u0085\u2028header',
        trace_chain=['root', 'child'], enabled=True)
    message = 'Readable "SQL" \\u001b\nFORGED HEADER\x1b\r\u0085\u2029'
    assert logger.write('WARN', 'unknown.kind', message, **fields)
    capture = capsys.readouterr()
    rows = events(capture.out if endpoint == 'stdout' else capture.err, presentation)
    assert [row['level'] for row in rows] == ['INFO', 'WARN']
    assert rows[1] | {'timestamp': None} == dict(timestamp=None, level='WARN', log_name='应用',
        runtime='python', event='unknown.kind', message=message, **fields)
    assert not list(tmp_path.iterdir())


@pytest.mark.asyncio
@pytest.mark.parametrize('presentation', ['json', 'human'])
async def test_native_outcomes_and_projection_precede_rendering(monkeypatch, tmp_path, presentation):
    from teaql.runtime.audit import RawAuditEvent, MutationAuditKind, AuditFieldChange
    from teaql.runtime.mutation_policy import MutationPolicyError
    from teaql.runtime.log_privacy import PLAINTEXT_ACK
    logger = RuntimeLogger(log_format=presentation, environment={}, working_directory=tmp_path)
    context = UserContext.new(runtime_logger=logger)
    async def success():
        return 42
    assert await observe_runtime_operation(context.operation_telemetry(), RuntimeOperation('query', 'probe'), success) == 42
    for error in (MutationPolicyError('PRIVATE-POLICY-CANARY'), OSError('PRIVATE-DRIVER-CANARY')):
        async def failure():
            raise error
        with pytest.raises(type(error)) as caught:
            await observe_runtime_operation(context.operation_telemetry(), RuntimeOperation('query', 'probe'), failure)
        assert caught.value is error
    for ack in ('', 'true', PLAINTEXT_ACK):
        monkeypatch.setenv('TEAQL_ALLOW_SENSITIVE_PLAINTEXT_LOGS', ack)
        secret = 'PASSWORD-RENDER-CANARY'
        metadata = SimpleNamespace(operation='update', parameters=[secret],
            parameterized_sql='UPDATE customer SET password = ?', debug_query=secret,
            comment='change ' + secret, execution_outcome='failure', affected_rows=1,
            _sql_correlation=SimpleNamespace(trace_id='0123456789abcdef0123456789abcdef'))
        context.record_metadata_log(metadata)
        audit = RawAuditEvent(MutationAuditKind.UPDATED, 'Customer', 42,
            (AuditFieldChange('password', 'OLD-PASSWORD-CANARY', secret),), ('change ' + secret,))
        await context.send_audit_event(audit)
        assert metadata.parameters == [secret] and audit.entity_id == 42 and audit.changes[0].new_value == secret
    text = logger.path.read_text()
    assert 'CANARY' not in text
    rows = events(text, presentation)
    assert [row['level'] for row in rows[:4]] == ['INFO', 'INFO', 'WARN', 'ERROR']
    sql = [row for row in rows if row.get('category') == 'SQL']
    audits = [row for row in rows if row['event'].startswith('audit.')]
    assert len(sql) == 3 and all(row['trace_id'] == '0123456789abcdef0123456789abcdef' for row in sql)
    assert len(audits) == 3 and all(row['entity_id'] == '42' for row in audits)


@pytest.mark.parametrize('presentation', ['json', 'human'])
def test_positive_archive_limit_keeps_numeric_newest_order(tmp_path, presentation):
    logger = RuntimeLogger(log_format=presentation,
        environment={'TEAQL_LOG_MAX_SIZE': '256', 'TEAQL_LOG_MAX_FILES': '2'}, working_directory=tmp_path)
    for sequence in range(5):
        assert logger.write('INFO', 'retention', '界' * 200, sequence=sequence, sql='SELECT\n' + str(sequence))
    for suffix, expected in [('', 4), ('.1', 3), ('.2', 2)]:
        rows = read(Path(str(logger.path) + suffix), presentation)
        assert len(rows) == 1 and rows[0]['sequence'] == expected
        assert rows[0]['sql'] == 'SELECT\n' + str(expected)
    assert sorted(p.name for p in logger.path.parent.iterdir()) == ['teaql.log', 'teaql.log.1', 'teaql.log.2']


@pytest.mark.parametrize('presentation', ['json', 'human'])
@pytest.mark.parametrize('override', [False, True])
def test_utf8_whole_events_day_restart_retention_and_oversize(tmp_path, presentation, override):
    env = {'TEAQL_LOG_MAX_SIZE': '1K', 'TEAQL_LOG_MAX_FILES': '100'}
    if override:
        env['TEAQL_LOG_ENDPOINT'] = 'override/custom.log'
    logger = RuntimeLogger(log_format=presentation, environment=env, working_directory=tmp_path)
    for index in range(40):
        assert logger.write('INFO', 'regular', '界' * 25, index=index, sql='SELECT id\nFROM customer')
    paths = list(logger.path.parent.iterdir())
    assert len(paths) > 1 and all(0 < p.stat().st_size <= 1024 for p in paths)
    rows = [row for p in paths for row in read(p, presentation)]
    assert sorted(row['index'] for row in rows if row['event'] == 'regular') == list(range(40))
    assert all(row['sql'] == 'SELECT id\nFROM customer' for row in rows if row['event'] == 'regular')
    assert logger.write('WARN', 'oversize', 'whole', sql='界' * 2000 + '\nNEXT LINE')
    oversized = logger.path.read_bytes()
    assert len(oversized) > 1024 and [r['event'] for r in read(logger.path, presentation)] == ['oversize']
    assert logger.write('INFO', 'after', 'next')
    assert Path(str(logger.path) + '.1').read_bytes() == oversized
    yesterday = (datetime.now(timezone.utc) - timedelta(days=2)).timestamp()
    os.utime(logger.path, (yesterday, yesterday))
    assert logger.write('INFO', 'day', 'UTC rotation')
    assert [r['event'] for r in read(Path(str(logger.path) + '.1'), presentation)] == ['after']
    os.utime(logger.path, (yesterday, yesterday))
    restarted = RuntimeLogger(log_format=presentation, environment=env, working_directory=tmp_path)
    assert [r['event'] for r in read(restarted.path, presentation)] == ['runtime.start']
    assert [r['event'] for r in read(Path(str(logger.path) + '.1'), presentation)] == ['day']
    zero = RuntimeLogger(log_format=presentation, environment={**env, 'TEAQL_LOG_MAX_FILES': '0'}, working_directory=tmp_path)
    assert zero.write('INFO', 'last', '界' * 2000)
    assert list(zero.path.parent.iterdir()) == [zero.path]
    assert [r['event'] for r in read(zero.path, presentation)] == ['last']


@pytest.mark.parametrize('presentation', ['json', 'human'])
def test_threads_keep_multiline_blocks_whole(tmp_path, presentation):
    loggers = [RuntimeLogger(log_format=presentation,
        environment={'TEAQL_LOG_MAX_SIZE': '2K', 'TEAQL_LOG_MAX_FILES': '100'}, working_directory=tmp_path) for _ in range(4)]
    def write(index):
        assert loggers[index % 4].write('INFO', 'parallel', '多线程', index=index, sql='SELECT\n' + str(index))
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(write, range(100)))
    rows = [row for p in loggers[0].path.parent.iterdir() for row in read(p, presentation)]
    assert sorted(row['index'] for row in rows if row['event'] == 'parallel') == list(range(100))
    assert all(row['sql'] == 'SELECT\n' + str(row['index']) for row in rows if row['event'] == 'parallel')


@pytest.mark.parametrize('presentation', ['json', 'human'])
def test_processes_and_subsequent_start_keep_blocks_whole(tmp_path, presentation):
    script = """from teaql.runtime import RuntimeLogger
import sys
logger=RuntimeLogger(log_format=sys.argv[2],environment={'TEAQL_LOG_MAX_SIZE':'2K','TEAQL_LOG_MAX_FILES':'100'})
for index in range(30):
 assert logger.write('INFO','process.record','原生并发',worker=int(sys.argv[1]),index=index,sql='SELECT\\n'+str(index))
"""
    env = {key: os.environ[key] for key in ('PATH', 'LANG', 'LC_ALL', 'TZ') if key in os.environ}
    env.update(PYTHONDONTWRITEBYTECODE='1', PYTHONPATH=str(Path(__file__).resolve().parents[2] / 'src'))
    children = []
    try:
        for worker in range(4):
            children.append(subprocess.Popen([sys.executable, '-B', '-c', script, str(worker), presentation],
                cwd=tmp_path, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE))
        for child in children:
            _, error = child.communicate(timeout=30)
            assert child.returncode == 0, error.decode()
        subprocess.run([sys.executable, '-B', '-c', script, '4', presentation], cwd=tmp_path,
            env=env, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
    finally:
        for child in children:
            if child.poll() is None:
                child.kill()
            child.wait()
    rows = [row for p in (tmp_path / 'logs').iterdir() for row in read(p, presentation)]
    assert sum(row['event'] == 'runtime.start' for row in rows) == 5
    assert sorted((r['worker'], r['index']) for r in rows if r['event'] == 'process.record') == [
        (worker, index) for worker in range(5) for index in range(30)]
    assert all(r['sql'] == 'SELECT\n' + str(r['index']) for r in rows if r['event'] == 'process.record')


@pytest.mark.asyncio
@pytest.mark.parametrize('presentation', ['json', 'human'])
async def test_mixed_format_and_io_failures_preserve_files_and_business(tmp_path, capsys, presentation):
    logger = RuntimeLogger(log_format=presentation, environment={}, working_directory=tmp_path)
    other = 'human' if presentation == 'json' else 'json'
    archive = Path(str(logger.path) + '.10')
    archive.write_bytes(b'preserve archived bytes')
    before = {p.name: p.read_bytes() for p in logger.path.parent.iterdir()}
    with pytest.raises(RuntimeLoggingError):
        RuntimeLogger(log_format=other, environment={'TEAQL_LOG_MAX_SIZE': '1', 'TEAQL_LOG_MAX_FILES': '0'}, working_directory=tmp_path)
    assert {p.name: p.read_bytes() for p in logger.path.parent.iterdir()} == before
    replacement = RuntimeLogger(log_format=other, environment={}, working_directory=tmp_path / 'replacement')
    logger.path.write_bytes(replacement.path.read_bytes())
    before = {p.name: p.read_bytes() for p in logger.path.parent.iterdir()}
    context = UserContext.new(runtime_logger=logger)
    async def success():
        return 42
    assert await observe_runtime_operation(context.operation_telemetry(), RuntimeOperation('query', 'probe'), success) == 42
    original = OSError('SECRET-BUSINESS-ERROR')
    async def failure():
        raise original
    with pytest.raises(OSError) as caught:
        await observe_runtime_operation(context.operation_telemetry(), RuntimeOperation('query', 'probe'), failure)
    assert caught.value is original
    assert {p.name: p.read_bytes() for p in logger.path.parent.iterdir()} == before
    logger.path.unlink()
    logger.path.mkdir()
    assert not logger.write('ERROR', 'later', 'later I/O failure')
    blocked = tmp_path / 'SECRET-PATH'
    blocked.write_text('file')
    with pytest.raises(RuntimeLoggingError):
        RuntimeLogger(log_format=presentation, environment={'TEAQL_LOG_ENDPOINT': str(blocked / 'file')})
    failures = capsys.readouterr().err
    assert 'SECRET' not in failures and all(json.loads(line)['level'] == 'ERROR' for line in failures.splitlines())
