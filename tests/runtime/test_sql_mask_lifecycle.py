import asyncio
from types import SimpleNamespace

import pytest

from teaql.core.expr import Expr
from teaql.core.meta import EntityDescriptor, PropertyDescriptor
from teaql.core.mutation import InsertCommand, UpdateCommand, DeleteCommand, MutationRequest, TraceNode
from teaql.core.query import SelectQuery
from teaql.core.value import DataType, Value
from teaql.data_service import QueryRequest
from teaql.provider.sqlite import SimpleSchemaProvider
from teaql.provider.sqlite.dialect import SqliteDialect
from teaql.runtime import RuntimeModule
from teaql.runtime.context import TextDiagnosticSqlLogSink
from teaql.runtime.log_privacy import PLAINTEXT_ENV, PLAINTEXT_ACK
from teaql.sql.executor import (SqlDataServiceExecutor, SqlTransport, TransportError,
                               SqlTransactionTransport, SqlTransactionTransportTx)


class FaultTransport(SqlTransport):
    def __init__(self, batches=0, failure=None):
        self.batches, self.failure = batches, failure
        self.closed = False
        self.params = []

    async def fetch_all_sql(self, query):
        self.params = query.params
        if self.failure:
            raise self.failure
        return []

    async def execute_sql(self, query):
        self.params = query.params
        if self.failure:
            raise self.failure
        return 0, None

    async def stream_sql(self, query, chunk_size):
        self.params = query.params
        try:
            for _ in range(self.batches):
                yield [{'display_name': 'Riverside'}]
            if self.failure:
                raise self.failure
        finally:
            self.closed = True


class DomainStatementExecutor(SqlDataServiceExecutor):
    # Isolate domain-statement failures from unrelated ID-space initialization.
    async def next_id(self, entity):
        return 1

    async def ensure_id_floor(self, entity, floor):
        pass


@pytest.fixture
def fixture(monkeypatch):
    monkeypatch.delenv(PLAINTEXT_ENV, raising=False)
    entity = EntityDescriptor('Customer').table_name('customer_data')
    entity.property(PropertyDescriptor('id', DataType.I64).is_id())
    entity.property(PropertyDescriptor('version', DataType.I64).is_version())
    for field in ['display_name', 'public_address', 'password_hash']:
        entity.property(PropertyDescriptor(field, DataType.Text).log_policy('plain'))
    entity.audit_mask_fields(['display_name', 'password_hash'])
    provider = SimpleSchemaProvider()
    provider.register_entity(entity)
    context = RuntimeModule.new().entity(entity).into_context()
    output, entries = [], []
    sink = TextDiagnosticSqlLogSink(output.append)
    def capture(entry):
        entries.append(entry)
        sink.write(entry)
    context.set_diagnostic_sql_log_sink(SimpleNamespace(write=capture))
    return context, provider, output, entries


def request():
    query = (SelectQuery('Customer').filter(Expr.eq('display_name', 'Riverside'))
             .and_filter(Expr.eq('public_address', '1 Runtime Road'))
             .and_filter(Expr.eq('password_hash', 'PASSWORD-CANARY')).limit(5))
    return QueryRequest(query).comment('what: inspect customers').purpose('why: lifecycle test')


@pytest.mark.asyncio
async def test_old_generated_query_request_keeps_query_intent(fixture):
    context, provider, output, entries = fixture
    query = (SelectQuery('Customer').filter(Expr.eq('display_name', 'Riverside'))
             .limit(5).comment('what: old generated request')
             .purpose('why: preserve diagnostic intent'))
    request = QueryRequest(query)
    assert request._comment == 'what: old generated request'
    assert request._purpose == 'why: preserve diagnostic intent'
    assert QueryRequest(query, _comment='explicit what', _purpose='explicit why')._comment == 'explicit what'
    assert QueryRequest(query, _comment='explicit what', _purpose='explicit why')._purpose == 'explicit why'

    executor = DomainStatementExecutor(SqliteDialect(), FaultTransport(), provider)
    await executor.query(context, request)
    assert entries[0].comment == 'what: old generated request'
    assert entries[0].purpose == 'why: preserve diagnostic intent'
    assert 'what: old generated request' in output[0]
    assert 'why: preserve diagnostic intent' in output[0]


def assert_log(fixture, outcome, count=None, debug=False):
    context, _, output, entries = fixture
    assert len(entries) == 1
    assert entries[0].execution_outcome == outcome
    assert entries[0].result_count == count
    text = '\n'.join(output)
    assert f'outcome={outcome}' in text
    assert 'PASSWORD-CANARY' not in text and 'DRIVER-CANARY' not in text
    assert 'PASSWORD-CANARY' not in repr(context.sql_logs())
    if not debug:
        assert 'Riverside' not in text
    assert entries[0].debug_sql


@pytest.mark.asyncio
@pytest.mark.parametrize('operation', ['query', 'insert', 'update', 'delete'])
async def test_failed_statement_logs_and_preserves_error(fixture, operation):
    context, provider, output, entries = fixture
    failure = RuntimeError('DRIVER-CANARY Riverside PASSWORD-CANARY')
    transport = FaultTransport(failure=failure)
    executor = DomainStatementExecutor(SqliteDialect(), transport, provider)
    with pytest.raises(TransportError) as caught:
        if operation == 'query':
            await executor.query(context, request())
        else:
            commands = {
                'insert': InsertCommand('Customer').value('display_name', 'Riverside'),
                'update': UpdateCommand('Customer', Value.I64(1)).expected_version(1).value('display_name', 'Riverside'),
                'delete': DeleteCommand('Customer', Value.I64(1)).expected_version(1),
            }
            cmd = commands[operation]
            cmd.trace_chain = [TraceNode(comment='what: lifecycle mutation')]
            await executor.mutate(context, MutationRequest(cmd))
    assert caught.value.error is failure
    assert_log(fixture, 'failure')
    assert entries[0].affected_rows is None
    if operation == 'query':
        for text in ['Ri*****de', '1 Runtime Road', 'what: inspect customers', 'why: lifecycle test']:
            assert text in output[0]
        assert 'Riverside' in [p.val for p in transport.params]


@pytest.mark.asyncio
@pytest.mark.parametrize('plaintext_debug', [False, True])
async def test_schema_failure_does_not_print_driver_error(fixture, monkeypatch,
                                                          caplog, capsys, plaintext_debug):
    from teaql.runtime._schema_capability import SCHEMA_CAPABILITY

    if plaintext_debug:
        monkeypatch.setenv(PLAINTEXT_ENV, PLAINTEXT_ACK)

    class SchemaFaultTransport(FaultTransport):
        async def execute_sql(self, query):
            if 'CREATE TABLE' in query.sql and 'teaql_id_space' not in query.sql:
                raise RuntimeError('DRIVER-CANARY Riverside PASSWORD-CANARY')
            return 0, None

    context, provider, _, _ = fixture
    executor = SqlDataServiceExecutor(SqliteDialect(), SchemaFaultTransport(), provider)
    await executor._ensure_schema(context, SCHEMA_CAPABILITY)

    printed = capsys.readouterr()
    assert printed.out == printed.err == ''
    assert 'Schema creation failed for entity Customer (RuntimeError)' in caplog.text
    for secret in ('DRIVER-CANARY', 'Riverside', 'PASSWORD-CANARY'):
        assert secret not in caplog.text


@pytest.mark.asyncio
@pytest.mark.parametrize('batches,fail,count', [(3,False,3),(0,False,0),(3,True,2),(1,True,0)])
async def test_stream_completion_and_failure(fixture, batches, fail, count):
    context, provider, output, _ = fixture
    failure = RuntimeError('DRIVER-CANARY Riverside PASSWORD-CANARY') if fail else None
    transport = FaultTransport(batches, failure)
    executor = SqlDataServiceExecutor(SqliteDialect(), transport, provider)
    received = []
    try:
        async for chunk in executor.query_stream(context, request(), 1):
            received.extend(chunk.rows)
    except RuntimeError as error:
        assert error is failure
    else:
        assert not fail
    assert len(received) == count and transport.closed
    assert all(row['display_name'] == 'Riverside' for row in received)
    assert_log(fixture, 'failure' if fail else 'success', count)
    assert '1 Runtime Road' in output[0] and 'Ri*****de' in output[0]


@pytest.mark.asyncio
@pytest.mark.parametrize('batches', [1,3])
async def test_explicit_stream_close_releases_inner_generator(fixture, batches):
    context, provider, _, _ = fixture
    transport = FaultTransport(batches)
    stream = SqlDataServiceExecutor(SqliteDialect(), transport, provider).query_stream(context, request(), 1)
    await stream.__anext__()
    await stream.aclose()
    assert transport.closed  # must not wait for GC/event-loop finalization
    assert_log(fixture, 'cancelled', 1)


@pytest.mark.asyncio
async def test_cancelled_stream(fixture):
    context, provider, _, _ = fixture
    failure = asyncio.CancelledError()
    transport = FaultTransport(failure=failure)
    executor = SqlDataServiceExecutor(SqliteDialect(), transport, provider)
    with pytest.raises(asyncio.CancelledError) as caught:
        async for _ in executor.query_stream(context, request(), 1):
            pass
    assert caught.value is failure and transport.closed
    assert_log(fixture, 'cancelled', 0)


@pytest.mark.asyncio
async def test_debug_stream_still_masks_credentials(fixture, monkeypatch):
    monkeypatch.setenv(PLAINTEXT_ENV, PLAINTEXT_ACK)
    context, provider, output, _ = fixture
    executor = SqlDataServiceExecutor(SqliteDialect(), FaultTransport(), provider)
    async for _ in executor.query_stream(context, request(), 1):
        pass
    assert_log(fixture, 'success', 0, debug=True)
    assert 'Riverside' in output[0] and 'DEBUG' in output[0] and 'EXPLICIT OPT-IN' in output[0]


@pytest.mark.asyncio
async def test_disabled_stream_still_executes(fixture):
    context, provider, output, entries = fixture
    context.disable_select_sql_log()
    transport = FaultTransport(2)
    executor = SqlDataServiceExecutor(SqliteDialect(), transport, provider)
    rows = [chunk async for chunk in executor.query_stream(context, request(), 1)]
    assert len(rows) == 2 and transport.closed
    assert not entries and not output and not context.sql_logs()


@pytest.mark.asyncio
@pytest.mark.parametrize('streaming', [False, True])
async def test_broken_sink_cannot_replace_driver_failure(fixture, streaming):
    context, provider, _, _ = fixture
    def broken(entry):
        raise ValueError('diagnostic destination unavailable')
    context.set_diagnostic_sql_log_sink(SimpleNamespace(write=broken))
    failure = RuntimeError('DRIVER-CANARY')
    transport = FaultTransport(failure=failure)
    executor = SqlDataServiceExecutor(SqliteDialect(), transport, provider)
    if streaming:
        with pytest.raises(RuntimeError) as caught:
            async for _ in executor.query_stream(context, request(), 1):
                pass
        assert caught.value is failure and transport.closed
    else:
        with pytest.raises(TransportError) as caught:
            await executor.query(context, request())
        assert caught.value.error is failure
    assert len(context.sql_logs()) == 1


@pytest.mark.asyncio
async def test_broken_sink_cannot_fail_successful_query(fixture):
    context, provider, _, _ = fixture
    attempts = []

    def broken(entry):
        attempts.append(entry)
        raise RuntimeError('DIAGNOSTIC-SINK-CANARY')

    context.set_diagnostic_sql_log_sink(SimpleNamespace(write=broken))
    executor = DomainStatementExecutor(SqliteDialect(), FaultTransport(), provider)
    result = await executor.query(context, request())

    assert result is not None
    assert len(attempts) == 1
    assert len(context.sql_logs()) == 1
    assert 'PASSWORD-CANARY' not in str(context.sql_logs()[0])


@pytest.mark.asyncio
async def test_query_cancellation_preserved(fixture):
    context, provider, _, _ = fixture
    failure = asyncio.CancelledError()
    executor = SqlDataServiceExecutor(SqliteDialect(), FaultTransport(failure=failure), provider)
    with pytest.raises(asyncio.CancelledError) as caught:
        await executor.query(context, request())
    assert caught.value is failure
    assert_log(fixture, 'cancelled')


@pytest.mark.asyncio
async def test_consumer_athrow_closes_stream(fixture):
    context, provider, _, _ = fixture
    transport = FaultTransport(3)
    stream = SqlDataServiceExecutor(SqliteDialect(), transport, provider).query_stream(context, request(), 1)
    await stream.__anext__()
    failure = RuntimeError('consumer failure')
    with pytest.raises(RuntimeError) as caught:
        await stream.athrow(failure)
    assert caught.value is failure and transport.closed
    assert_log(fixture, 'failure', 1)


@pytest.mark.asyncio
async def test_cancelled_mutation_rolls_back_transaction(fixture):
    context, provider, _, _ = fixture
    failure = asyncio.CancelledError()
    class Transaction(FaultTransport, SqlTransactionTransportTx):
        committed = False
        rolled_back = False
        async def commit_sql(self):
            self.committed = True
        async def rollback_sql(self):
            self.rolled_back = True
    tx = Transaction(failure=failure)
    class Transport(FaultTransport, SqlTransactionTransport):
        async def begin_sql(self):
            return tx
    executor = SqlDataServiceExecutor(SqliteDialect(), Transport(), provider)
    cmd = DeleteCommand('Customer', Value.I64(1)).expected_version(1)
    cmd.trace_chain = [TraceNode(comment='what: cancel mutation')]
    with pytest.raises(asyncio.CancelledError) as caught:
        await executor.mutate(context, MutationRequest(cmd))
    assert caught.value is failure
    assert tx.rolled_back and not tx.committed
    assert_log(fixture, 'cancelled')


@pytest.mark.asyncio
async def test_generated_mutation_string_comment_is_preserved(fixture):
    context, provider, _, entries = fixture
    executor = DomainStatementExecutor(SqliteDialect(), FaultTransport(), provider)
    command = InsertCommand('Customer').value('display_name', 'Riverside')
    mutation = MutationRequest(command)
    mutation.comment = 'what: generated audited save'
    await executor.mutate(context, mutation)
    assert entries[0].comment == mutation.comment
    assert entries[0].audit_reason == mutation.comment
    assert_log(fixture, 'success')


class ReadbackTransaction(FaultTransport, SqlTransactionTransportTx):
    def __init__(self, rows=None, failure=None):
        super().__init__(failure=failure)
        self.rows = rows or []
        self.writes = self.reads = self.commits = self.rollbacks = 0

    async def execute_sql(self, query):
        self.params = query.params
        self.writes += 1
        return 1, None

    async def fetch_all_sql(self, query):
        self.reads += 1
        if self.failure:
            raise self.failure
        return self.rows

    async def commit_sql(self):
        self.commits += 1

    async def rollback_sql(self):
        self.rollbacks += 1


def readback_request():
    command = (UpdateCommand('Customer', Value.I64(1)).expected_version(1)
               .value('display_name', 'Riverside').value('password_hash', 'PASSWORD-CANARY'))
    command.trace_chain = [TraceNode(comment='what: update Riverside PASSWORD-CANARY')]
    return MutationRequest(command)


@pytest.mark.asyncio
@pytest.mark.parametrize('explicit', [False, True])
@pytest.mark.parametrize('mode', ['error', 'cancelled', 'empty', 'multiple', 'success'])
async def test_readback_independent_diagnostic(fixture, explicit, mode):
    from dataclasses import asdict
    context, provider, output, entries = fixture
    failure = (asyncio.CancelledError() if mode == 'cancelled'
               else RuntimeError('DRIVER-CANARY') if mode == 'error' else None)
    row = {'id': 1, 'version': 2, 'display_name': 'Riverside'}
    rows = [row] * (2 if mode == 'multiple' else 1 if mode == 'success' else 0)
    tx = ReadbackTransaction(rows, failure)
    class Transport(FaultTransport, SqlTransactionTransport):
        async def begin_sql(self):
            return tx
    executor = SqlDataServiceExecutor(SqliteDialect(), Transport(), provider)
    target = await executor.begin(context) if explicit else executor
    if mode == 'success':
        result = await target.mutate(context, readback_request())
        assert result.persisted_record['display_name'] == 'Riverside'
        if explicit:
            assert tx.commits == 0
            await target.commit(context)
        assert tx.commits == 1 and tx.rollbacks == 0
        assert len(entries) == 1
    else:
        with pytest.raises(BaseException) as caught:
            await target.mutate(context, readback_request())
        if failure:
            assert caught.value is failure
        else:
            assert isinstance(caught.value, TransportError)
        if explicit:
            assert tx.rollbacks == 0
            await target.rollback(context)
        assert tx.rollbacks == 1 and tx.commits == 0
        assert len(entries) == 2
        read = entries[1]
        assert read.execution_outcome == ('cancelled' if mode == 'cancelled' else 'failure' if mode == 'error' else 'success')
        assert read.result_count == (None if failure else len(rows))
        assert read.affected_rows is None
        assert read.audit_reason and 'what: update' in read.audit_reason
        assert 'SELECT' in read.debug_sql
    assert entries[0].execution_outcome == 'success' and entries[0].affected_rows == 1
    assert tx.writes == tx.reads == 1
    assert 'Riverside' in [value.val for value in tx.params]
    for secret in ['Riverside', 'PASSWORD-CANARY', 'DRIVER-CANARY']:
        assert secret not in repr([asdict(entry) for entry in entries])
        assert secret not in '\n'.join(output)


@pytest.mark.asyncio
@pytest.mark.parametrize('mode', ['debug', 'disabled', 'broken-sink'])
async def test_readback_sink_and_debug_boundaries(fixture, monkeypatch, mode):
    from dataclasses import replace
    from teaql.runtime.log_privacy import sql_log_projection
    context, provider, output, entries = fixture
    if mode == 'debug':
        monkeypatch.setenv(PLAINTEXT_ENV, PLAINTEXT_ACK)
    if mode == 'disabled':
        context.disable_sql_log()
    if mode == 'broken-sink':
        def broken(entry):
            if 'SELECT' in entry.sql:
                raise ValueError('SINK-FAILURE')
        context.set_diagnostic_sql_log_sink(SimpleNamespace(write=broken))
    failure = RuntimeError('DRIVER-CANARY')
    tx = ReadbackTransaction(failure=failure)
    executor = SqlDataServiceExecutor(SqliteDialect(), tx, provider)
    with pytest.raises(RuntimeError) as caught:
        await executor.mutate(context, readback_request())
    assert caught.value is failure
    if mode == 'disabled':
        assert not entries and not context.sql_logs()
    else:
        assert len(context.sql_logs()) == 2
    if mode == 'debug':
        assert all('Riverside' in entry.audit_reason for entry in entries)
        assert all('EXPLICIT OPT-IN' in entry.debug_sql for entry in entries)
        assert 'PASSWORD-CANARY' not in repr(context.sql_logs())
        monkeypatch.delenv(PLAINTEXT_ENV)
        for entry in entries:
            safe = sql_log_projection(entry)
            assert 'what: update' in safe.audit_reason
            assert 'Riverside' not in repr(safe)
            assert 'Riverside' not in repr(sql_log_projection(replace(entry)))
            entry.audit_reason += ' modified by sink'
            assert 'Riverside' not in repr(sql_log_projection(entry))


@pytest.mark.asyncio
async def test_partial_transaction_keeps_prior_write_and_stops_after_readback(fixture):
    context, provider, _, entries = fixture
    tx = ReadbackTransaction(rows=[{'id':1, 'version':2, 'display_name':'Riverside'}])
    class Transport(FaultTransport, SqlTransactionTransport):
        async def begin_sql(self):
            return tx
    context.insert_resource('dataService', SqlDataServiceExecutor(SqliteDialect(), Transport(), provider))
    failure = RuntimeError('SECOND-READBACK-FAILURE')
    async def work():
        service = context.require_resource('dataService')
        await service.mutate(context, readback_request())
        tx.failure = failure
        await service.mutate(context, readback_request())
        await service.mutate(context, readback_request())
    with pytest.raises(RuntimeError) as caught:
        await context.execute_graph_save(work)
    assert caught.value is failure
    assert [entry.execution_outcome for entry in entries] == ['success','success','failure']
    assert tx.writes == tx.reads == 2 and tx.rollbacks == 1 and tx.commits == 0
    assert 'Riverside' not in repr(context.sql_logs())
