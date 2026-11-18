import concurrent.futures
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest

from teaql.runtime import RuntimeLogger, RuntimeLoggingError, UserContext
from teaql.runtime.telemetry import RuntimeOperation, observe_runtime_operation


def records(path):
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines()]


def test_default_startup_and_request_context_share_destination(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    for name in ('TEAQL_DOMAIN', 'TEAQL_LOG_ENDPOINT', 'TEAQL_LOG_MAX_SIZE', 'TEAQL_LOG_MAX_FILES'):
        monkeypatch.delenv(name, raising=False)
    first = UserContext.new()
    path = tmp_path / 'logs/teaql.log'
    assert path.exists()
    second = UserContext.new()
    assert first._runtime_logger is second._runtime_logger
    assert [row['event'] for row in records(path)] == ['runtime.start']
    row = records(path)[0]
    assert row['level'] == 'INFO' and row['runtime'] == 'python' and row['log_name'] == 'teaql'
    assert datetime.fromisoformat(row['timestamp'].replace('Z', '+00:00')).utcoffset() == timedelta(0)


@pytest.mark.parametrize('explicit,domain,models,expected', [
    ('application', 'domain', ('model',), 'application'),
    (None, 'domain', ('model',), 'domain'),
    (None, None, ('model',), 'model'),
    (None, None, (), 'teaql'),
    (None, None, ('one', 'two'), 'teaql'),
    ('应用日志', None, (), '应用日志'),
])
def test_name_precedence_and_override(tmp_path, explicit, domain, models, expected):
    environment = {'TEAQL_LOG_ENDPOINT': 'different/custom.log'}
    if domain is not None:
        environment['TEAQL_DOMAIN'] = domain
    logger = RuntimeLogger(explicit, model_names=models, environment=environment, working_directory=tmp_path)
    assert logger.log_name == expected
    assert records(tmp_path / 'different/custom.log')[0]['log_name'] == expected
    assert not (tmp_path / 'logs').exists()


@pytest.mark.parametrize('name', ['', '.', '..', '../private', 'a/b', 'a\\b', 'a\nSECRET',
                                  'x:y', 'tail.', 'tail ', 'CON', 'nul.txt', 'LPT1', 'a?b'])
def test_invalid_filename_segment_fails_without_echo(tmp_path, capsys, name):
    with pytest.raises(RuntimeLoggingError, match='invalid_log_name'):
        RuntimeLogger(name, environment={}, working_directory=tmp_path)
    row = json.loads(capsys.readouterr().err)
    assert row['level'] == 'ERROR' and row['error_code'] == 'invalid_log_name'
    assert 'SECRET' not in json.dumps(row)
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize('suffix,size', [('1', 1), ('2K', 2048), ('2KB', 2048),
                                       ('3m', 3 * 1024 ** 2), ('1GB', 1024 ** 3)])
def test_binary_size_suffixes(tmp_path, suffix, size):
    logger = RuntimeLogger(environment={'TEAQL_LOG_MAX_SIZE': suffix}, working_directory=tmp_path)
    assert logger.max_size == size


@pytest.mark.parametrize('environment', [
    {'TEAQL_LOG_MAX_SIZE': '0'}, {'TEAQL_LOG_MAX_SIZE': '-1'}, {'TEAQL_LOG_MAX_SIZE': 'wat'},
    {'TEAQL_LOG_MAX_FILES': '-1'}, {'TEAQL_LOG_MAX_FILES': '1.5'},
])
def test_invalid_rotation_configuration_fails_startup(tmp_path, environment):
    with pytest.raises(RuntimeLoggingError):
        RuntimeLogger(environment=environment, working_directory=tmp_path)


def test_stdout_is_structured_and_retains_application_name(tmp_path, capsys):
    logger = RuntimeLogger('app', environment={'TEAQL_LOG_ENDPOINT': 'stdout'}, working_directory=tmp_path)
    logger.write('WARN', 'sql.retry', 'Retry scheduled', category='SQL', outcome='retrying')
    output = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    assert [row['level'] for row in output] == ['INFO', 'WARN']
    assert all(row['log_name'] == 'app' for row in output)
    assert not list(tmp_path.iterdir())


def test_size_rotation_utf8_oversized_line_order_and_zero_retention(tmp_path):
    logger = RuntimeLogger('size', environment={'TEAQL_LOG_MAX_SIZE': '400', 'TEAQL_LOG_MAX_FILES': '2'},
                           working_directory=tmp_path)
    logger.write('INFO', 'large', '中' * 300 + '\ninside record')
    path = tmp_path / 'logs/size.log'
    assert path.stat().st_size > 400
    assert len(records(path)) == 1 and records(path)[0]['event'] == 'large'
    logger.write('INFO', 'after', 'After oversized record')
    assert records(path)[0]['event'] == 'after'
    assert records(Path(str(path) + '.1'))[0]['event'] == 'large'
    assert records(Path(str(path) + '.2'))[0]['event'] == 'runtime.start'
    for index in range(10):
        logger.write('INFO', 'many', 'x' * 300, index=index)
    assert not Path(str(path) + '.3').exists()
    no_archives = RuntimeLogger('size', environment={'TEAQL_LOG_MAX_SIZE': '400', 'TEAQL_LOG_MAX_FILES': '0'},
                                working_directory=tmp_path)
    no_archives.write('INFO', 'last', 'x' * 500)
    assert len(records(path)) == 1 and records(path)[0]['event'] == 'last'
    assert not Path(str(path) + '.1').exists() and not Path(str(path) + '.2').exists()


def test_utc_day_change_and_restart_check_existing_file(tmp_path):
    first = RuntimeLogger('day', environment={}, working_directory=tmp_path)
    first.write('INFO', 'before', 'Before rotation')
    path = tmp_path / 'logs/day.log'
    yesterday = (datetime.now(timezone.utc) - timedelta(days=2)).timestamp()
    os.utime(path, (yesterday, yesterday))
    first.write('INFO', 'after', 'After UTC date change')
    assert [row['event'] for row in records(Path(str(path) + '.1'))] == ['runtime.start', 'before']
    assert [row['event'] for row in records(path)] == ['after']
    os.utime(path, (yesterday, yesterday))
    RuntimeLogger('day', environment={}, working_directory=tmp_path)
    assert [row['event'] for row in records(path)] == ['runtime.start']
    assert [row['event'] for row in records(Path(str(path) + '.1'))] == ['after']
    assert [row['event'] for row in records(Path(str(path) + '.2'))] == ['runtime.start', 'before']


def test_regular_utf8_records_rotate_at_whole_line_byte_limit(tmp_path):
    logger = RuntimeLogger(environment={'TEAQL_LOG_MAX_SIZE': '1K', 'TEAQL_LOG_MAX_FILES': '1000'},
                           working_directory=tmp_path)
    for index in range(40):
        assert logger.write('INFO', 'regular', '界' * 30, index=index)
    files = list((tmp_path / 'logs').iterdir())
    assert len(files) > 1
    assert all(0 < file.stat().st_size <= 1024 for file in files)
    output = [row for file in files for row in records(file)]
    assert len(output) == 41
    assert sorted(row['index'] for row in output if row['event'] == 'regular') == list(range(40))


@pytest.mark.asyncio
async def test_rotation_failure_preserves_business_and_foreign_archive_directory(tmp_path, capsys):
    logger = RuntimeLogger(environment={}, working_directory=tmp_path)
    context = UserContext.new(runtime_logger=logger)
    path = tmp_path / 'logs/teaql.log'
    before = path.read_bytes()
    archive = Path(str(path) + '.1')
    archive.mkdir()
    (archive / 'marker').write_text('preserve')
    yesterday = (datetime.now(timezone.utc) - timedelta(days=2)).timestamp()
    os.utime(path, (yesterday, yesterday))
    async def work():
        return 42
    assert await observe_runtime_operation(context.operation_telemetry(), RuntimeOperation('query', 'probe'), work) == 42
    original = OSError('private-original-error')
    async def failure():
        raise original
    with pytest.raises(OSError) as caught:
        await observe_runtime_operation(context.operation_telemetry(), RuntimeOperation('query', 'probe'), failure)
    assert caught.value is original
    assert not logger.write('INFO', 'probe', 'Completed')
    assert path.read_bytes() == before and (archive / 'marker').read_text() == 'preserve'
    errors = [json.loads(line) for line in capsys.readouterr().err.splitlines()]
    assert all(row['level'] == 'ERROR' and row['error_code'] == 'log_write_failed' for row in errors)
    assert len(errors) >= 3


@pytest.mark.asyncio
async def test_native_rule_rejections_are_warnings_and_keep_original_errors(tmp_path):
    from teaql.runtime.i18n import CheckException
    from teaql.runtime.mutation_policy import MutationPolicyError
    from teaql.core.request_intent import RequestIntentError
    logger = RuntimeLogger(environment={}, working_directory=tmp_path)
    context = UserContext.new(runtime_logger=logger)
    for error in (CheckException([]), RequestIntentError('QUERY_PURPOSE_REQUIRED', 'purpose', 'query'),
                  MutationPolicyError('private-policy-value')):
        async def failure():
            raise error
        with pytest.raises(type(error)) as caught:
            await observe_runtime_operation(context.operation_telemetry(), RuntimeOperation('query', 'probe'), failure)
        assert caught.value is error
    output = records(tmp_path / 'logs/teaql.log')
    assert [row['level'] for row in output] == ['INFO', 'WARN', 'WARN', 'WARN']
    assert 'private-policy-value' not in json.dumps(output)


def test_initial_io_failure_is_fatal_and_value_free(tmp_path, capsys):
    parent = tmp_path / 'PATH-CONTAINING-CANARY'
    parent.write_text('not a directory')
    with pytest.raises(RuntimeLoggingError, match='log_destination_unavailable'):
        RuntimeLogger(environment={'TEAQL_LOG_ENDPOINT': str(parent / 'file')})
    output = capsys.readouterr().err
    assert json.loads(output)['level'] == 'ERROR'
    assert 'PATH-CONTAINING-CANARY' not in output


@pytest.mark.asyncio
async def test_post_startup_io_failure_does_not_change_business_result(tmp_path, capsys):
    logger = RuntimeLogger('io', environment={}, working_directory=tmp_path)
    context = UserContext.new(runtime_logger=logger)
    path = tmp_path / 'logs/io.log'
    path.unlink()
    path.mkdir()
    async def work():
        return 42
    result = await observe_runtime_operation(context.operation_telemetry(), RuntimeOperation('query', 'probe'), work)
    assert result == 42 and path.is_dir()
    errors = [json.loads(line) for line in capsys.readouterr().err.splitlines() if line.startswith('{')]
    assert errors[-1]['error_code'] == 'log_write_failed'


@pytest.mark.asyncio
async def test_native_operation_severity_and_failure_redaction(tmp_path):
    logger = RuntimeLogger('operations', environment={}, working_directory=tmp_path)
    context = UserContext.new(runtime_logger=logger)
    async def success():
        return 7
    assert await observe_runtime_operation(context.operation_telemetry(), RuntimeOperation('query', 'probe'), success) == 7
    for error in [ValueError('VALIDATION-CREDENTIAL-CANARY'), OSError('DRIVER-CREDENTIAL-CANARY')]:
        async def failure():
            raise error
        with pytest.raises(type(error)) as caught:
            await observe_runtime_operation(context.operation_telemetry(), RuntimeOperation('provider', 'probe'), failure)
        assert caught.value is error
    output = records(tmp_path / 'logs/operations.log')
    assert [row['level'] for row in output] == ['INFO', 'INFO', 'WARN', 'ERROR']
    assert 'CREDENTIAL-CANARY' not in json.dumps(output)


def test_concurrent_threads_share_rotation_lock(tmp_path):
    loggers = [RuntimeLogger('threads', environment={'TEAQL_LOG_MAX_SIZE': '2K', 'TEAQL_LOG_MAX_FILES': '100'},
                             working_directory=tmp_path) for _ in range(4)]
    def write(index):
        assert loggers[index % 4].write('INFO', 'parallel', '多线程', index=index)
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(write, range(100)))
    output = [row for path in (tmp_path / 'logs').iterdir() if not path.name.endswith('.lock') for row in records(path)]
    assert sorted(row['index'] for row in output if row['event'] == 'parallel') == list(range(100))


def test_native_processes_append_across_two_starts_and_concurrent_rotation(tmp_path):
    script = """from teaql.runtime import RuntimeLogger
import sys
logger=RuntimeLogger('processes',environment={'TEAQL_LOG_MAX_SIZE':'2K','TEAQL_LOG_MAX_FILES':'100'})
for index in range(30):
    assert logger.write('INFO','process.record','原生并发',worker=int(sys.argv[1]),index=index)
"""
    environment = {name: os.environ[name] for name in ('PATH', 'HOME', 'LANG', 'LC_ALL', 'TZ') if name in os.environ}
    environment.update(PYTHONDONTWRITEBYTECODE='1', PYTHONPATH=str(Path(__file__).resolve().parents[2] / 'src'))
    children = []
    try:
        for worker in range(4):
            children.append(subprocess.Popen([sys.executable, '-B', '-c', script, str(worker)], cwd=tmp_path,
                                              env=environment, stdout=subprocess.PIPE, stderr=subprocess.PIPE))
        for child in children:
            _, error = child.communicate(timeout=30)
            assert child.returncode == 0, error.decode()
        # A subsequent native start must append to the same active destination.
        subprocess.run([sys.executable, '-B', '-c', script, '4'], cwd=tmp_path, env=environment,
                       check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
    finally:
        for child in children:
            if child.poll() is None:
                child.kill()
            child.wait()
    output = [row for path in (tmp_path / 'logs').iterdir() if not path.name.endswith('.lock') for row in records(path)]
    assert sum(row['event'] == 'runtime.start' for row in output) == 5
    assert sorted((row['worker'], row['index']) for row in output if row['event'] == 'process.record') == [
        (worker, index) for worker in range(5) for index in range(30)]


@pytest.mark.asyncio
async def test_default_sql_and_audit_file_projects_before_serialization(monkeypatch, tmp_path):
    from teaql.runtime.audit import RawAuditEvent, MutationAuditKind, AuditFieldChange
    monkeypatch.delenv('TEAQL_ALLOW_SENSITIVE_PLAINTEXT_LOGS', raising=False)
    logger = RuntimeLogger(environment={}, working_directory=tmp_path)
    context = UserContext.new(runtime_logger=logger)
    secret = 'UNIQUE-LOG-PASSWORD-CANARY'
    metadata = SimpleNamespace(operation='update', parameters=[secret],
        parameterized_sql='UPDATE customer SET password = ?', debug_query=secret,
        comment='change ' + secret, execution_outcome='failure', affected_rows=1)
    context.record_metadata_log(metadata)
    event = RawAuditEvent(MutationAuditKind.UPDATED, 'Customer', 42,
        (AuditFieldChange('password', 'OLD-PASSWORD-CANARY', secret),),
        ('change target 42 ' + secret,))
    await context.send_audit_event(event)
    path = tmp_path / 'logs/teaql.log'
    output = records(path)
    assert any(row.get('category') == 'SQL' and row['level'] == 'ERROR' for row in output)
    audit = next(row for row in output if row.get('category') == 'AUDIT')
    assert audit['level'] == 'INFO' and audit['entity_id'] == '42'
    text = path.read_text()
    assert secret not in text and 'OLD-PASSWORD-CANARY' not in text
    assert metadata.parameters == [secret] and event.entity_id == 42
    assert event.changes[0].new_value == secret


def test_default_sql_file_keeps_available_trace_correlation(tmp_path):
    logger = RuntimeLogger(environment={}, working_directory=tmp_path)
    context = UserContext.new(runtime_logger=logger)
    trace_id = '0123456789abcdef0123456789abcdef'
    context.record_metadata_log(SimpleNamespace(operation='select', parameters=[],
        parameterized_sql='SELECT id FROM customer', debug_query='SELECT id FROM customer',
        execution_outcome='success', _sql_correlation=SimpleNamespace(trace_id=trace_id)))
    record = next(row for row in records(tmp_path / 'logs/teaql.log') if row.get('category') == 'SQL')
    assert record['trace_id'] == trace_id
