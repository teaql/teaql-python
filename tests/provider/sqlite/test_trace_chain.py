"""Native SQLite observations; no expected trace frames are supplied to requests."""
from types import SimpleNamespace

import aiosqlite
import pytest

from teaql.core.expr import Expr
from teaql.core.meta import EntityDescriptor, PropertyDescriptor, RelationDescriptor
from teaql.core.mutation import InsertCommand, MutationRequest
from teaql.core.query import SelectQuery
from teaql.core.value import DataType
from teaql.data_service import QueryRequest
from teaql.provider.sqlite import SimpleSchemaProvider
from teaql.provider.sqlite.dialect import SqliteDialect
from teaql.provider.sqlite.transport import SqliteTransport
from teaql.runtime import RuntimeModule
from teaql.sql.executor import SqlDataServiceExecutor, TransportError


class RecordingTransport(SqliteTransport):
    def __init__(self, path):
        super().__init__(path)
        self.reads = []
        self.fail_table = None
        self.failure = RuntimeError('synthetic readback failure')

    async def fetch_all_sql(self, compiled):
        self.reads.append(compiled)
        if self.fail_table and self.fail_table in compiled.sql:
            raise self.failure
        return await super().fetch_all_sql(compiled)

    async def begin_sql(self):
        transaction = await super().begin_sql()
        fetch = transaction.fetch_all_sql

        async def capture(compiled):
            self.reads.append(compiled)
            if self.fail_table and self.fail_table in compiled.sql:
                raise self.failure
            return await fetch(compiled)

        transaction.fetch_all_sql = capture
        return transaction


async def fixture(tmp_path):
    module, schema = RuntimeModule.new(), SimpleSchemaProvider()
    names = ('CustomerOrder', 'Payment', 'PaymentAttempt', 'Shipment')
    for index, name in enumerate(names):
        descriptor = EntityDescriptor(name).table_name(name.lower() + '_data')
        descriptor.property(PropertyDescriptor('id', DataType.I64).is_id())
        descriptor.property(PropertyDescriptor('version', DataType.I64).is_version())
        descriptor.property(PropertyDescriptor('name', DataType.Text))
        if index < 3:
            descriptor.relation(RelationDescriptor('children', names[index + 1])
                                .local('id').foreign('parent_id').many())
        if index:
            descriptor.property(PropertyDescriptor('parent_id', DataType.I64))
        module.entity(descriptor)
        schema.register_entity(descriptor)
    context = module.into_context()
    entries = []
    context.set_diagnostic_sql_log_sink(SimpleNamespace(write=entries.append))
    transport = RecordingTransport(str(tmp_path / 'trace.db'))
    service = SqlDataServiceExecutor(SqliteDialect(), transport, schema)
    # Native provider fixture, not generated-example or bootstrap proof.
    async with aiosqlite.connect(transport.db_path) as database:
        for index, name in enumerate(names):
            tail = ', parent_id INTEGER' if index else ''
            await database.execute(f'CREATE TABLE {name.lower()}_data '
                                   f'(id INTEGER PRIMARY KEY, version INTEGER, name TEXT{tail})')
        await database.commit()
    for index, name in enumerate(names):
        command = InsertCommand.new(name).value('name', name)
        if index:
            command.value('parent_id', 1)
        await service.mutate(context, MutationRequest(command, comment='seed native trace fixture'))
    entries.clear()
    context.clear_sql_logs()
    transport.reads.clear()
    return context, service, transport, entries


def three_levels():
    return (SelectQuery('CustomerOrder').project('id', 'name').limit(1)
            .relation_query('children', SelectQuery('Payment').project('id').limit(1)
                .relation_query('children', SelectQuery('PaymentAttempt').project('id').limit(1)
                    .relation_query('children', SelectQuery('Shipment').project('id').limit(1)))))


@pytest.mark.asyncio
@pytest.mark.parametrize('failure', [False, True])
async def test_three_real_relation_levels_keep_origin_and_qualified_frames(tmp_path, failure):
    context, service, transport, entries = await fixture(tmp_path)
    request = QueryRequest(three_levels(), _comment='load payment execution graph',
                           _purpose='observe business trace without injected frames')
    if failure:
        transport.fail_table = 'shipment_data'
        with pytest.raises(TransportError) as caught:
            await service.query(context, request)
        assert caught.value.error is transport.failure
    else:
        result = await service.query(context, request)
        assert result.rows[0]['children'][0]['children'][0]['children'][0]['id'] == 1
    assert len(transport.reads) == len(entries) == 4
    qualified = ['CustomerOrder.children', 'Payment.children', 'PaymentAttempt.children']
    for depth, entry in enumerate(entries):
        assert entry.comment == request.intent.comment
        assert entry.purpose == request.intent.purpose
        nodes = entry.trace_path
        assert [node.kind for node in nodes] == ['operation', 'request'] + ['relation'] * depth + ['provider', 'sql']
        assert [node.name for node in nodes[:2]] == ['CustomerOrder', 'CustomerOrder']
        assert nodes[0].comment == 'query'
        assert [node.name for node in nodes[2:-2]] == ['children'] * depth
        assert [node.comment for node in nodes[2:-2]] == qualified[:depth]
        assert [(node.name, node.comment) for node in nodes[-2:]] == [('sqlite', ''), ('select', '')]
        assert entry.execution_outcome == ('failure' if failure and depth == 3 else 'success')


@pytest.mark.asyncio
async def test_successful_write_and_failed_readback_have_separate_canonical_paths(tmp_path):
    context, service, transport, entries = await fixture(tmp_path)
    transport.fail_table = 'payment_data'
    command = InsertCommand.new('Payment').value('name', 'pending payment').value('parent_id', 1)
    request = MutationRequest(command, comment='create payment before verifying authoritative row')
    with pytest.raises(RuntimeError) as caught:
        await service.mutate(context, request)
    assert caught.value is transport.failure
    assert len(entries) == 2
    write, read = entries
    assert write.execution_outcome == 'success' and read.execution_outcome == 'failure'
    assert write.audit_reason == read.audit_reason == request.comment()
    for entry, operation in ((write, 'insert'), (read, 'select')):
        assert [node.kind for node in entry.trace_path] == ['operation', 'entity', 'provider', 'sql']
        assert entry.trace_path[0].name == 'Payment'
        assert entry.trace_path[-1].name == operation
    async with aiosqlite.connect(transport.db_path) as database:
        cursor = await database.execute('SELECT COUNT(*) FROM payment_data')
        assert (await cursor.fetchone())[0] == 1  # failed graph transaction rolled back


@pytest.mark.asyncio
async def test_query_trace_source_does_not_override_request_owned_intent(tmp_path):
    context, service, transport, entries = await fixture(tmp_path)
    from teaql.core.mutation import TraceNode
    request = QueryRequest(SelectQuery('CustomerOrder').filter(Expr.eq('id', 1)).limit(1),
        trace_chain=[TraceNode(kind='comment', name='CustomerOrder', comment='untrusted old text'),
                     TraceNode(kind='purpose', name='CustomerOrder', comment='old purpose')],
        _comment='explicit request comment', _purpose='explicit request purpose')
    await service.query(context, request)
    assert entries[0].comment == 'explicit request comment'
    assert entries[0].purpose == 'explicit request purpose'
    assert not {'comment', 'purpose', 'auditReason'}.intersection(node.kind for node in entries[0].trace_path)


@pytest.mark.asyncio
async def test_unexecuted_aggregate_provenance_does_not_modify_query_builders(tmp_path):
    from copy import deepcopy
    from teaql.core.query import RelationAggregate
    context, service, transport, entries = await fixture(tmp_path)
    child = SelectQuery('Payment').count('count').relation_query('children', SelectQuery('PaymentAttempt'))
    parent = SelectQuery('CustomerOrder').project('id').filter(Expr.eq('name', 'missing')).limit(1)
    parent.relation_aggregates.append(RelationAggregate('children', 'child_count', child, True))
    request = QueryRequest(parent, _comment='inspect absent parent', _purpose='test provenance isolation')
    before = deepcopy(request.query)
    result = await service.query(context, request)
    assert result.rows == [] and len(entries) == len(transport.reads) == 1
    assert request.query == before and child.slice is None
    assert child.relations[0].query.slice is None
