"""Actual SQLite relation plans must inherit intent redactions, not SQL binds."""
from types import SimpleNamespace

import aiosqlite
import pytest

from teaql.core.expr import Expr
from teaql.core.meta import EntityDescriptor, PropertyDescriptor, RelationDescriptor
from teaql.core.query import SelectQuery, RelationAggregate
from teaql.core.value import DataType
from teaql.data_service import QueryRequest
from teaql.provider.sqlite import SimpleSchemaProvider
from teaql.provider.sqlite.dialect import SqliteDialect
from teaql.provider.sqlite.transport import SqliteTransport
from teaql.runtime import RuntimeModule
from teaql.runtime.context import TextDiagnosticSqlLogSink
from teaql.runtime.log_privacy import PLAINTEXT_ENV, PLAINTEXT_ACK, sql_log_projection
from teaql.sql.executor import SqlDataServiceExecutor, TransportError


class CaptureTransport(SqliteTransport):
    def __init__(self, path):
        super().__init__(path)
        self.reads = []
        self.failing_table = None
        self.failure = RuntimeError('DRIVER-CANARY')

    async def fetch_all_sql(self, compiled):
        self.reads.append(compiled)
        if self.failing_table and self.failing_table in compiled.sql:
            raise self.failure
        return await super().fetch_all_sql(compiled)


class CaptureExecutor(SqlDataServiceExecutor):
    def __init__(self, transport, provider):
        super().__init__(SqliteDialect(), transport, provider)
        self.dispatched = []

    async def query(self, context, request):
        self.dispatched.append(request.query.entity)
        return await super().query(context, request)


@pytest.mark.asyncio
@pytest.mark.parametrize('shape', ['batch', 'probe', 'window', 'aggregate', 'nested', 'nested-aggregate'])
@pytest.mark.parametrize('debug', [False, True])
@pytest.mark.parametrize('failure', [False, True])
async def test_derived_relation_intent(tmp_path, monkeypatch, shape, debug, failure):
    monkeypatch.delenv(PLAINTEXT_ENV, raising=False)
    provider = SimpleSchemaProvider()
    module = RuntimeModule.new()
    for name, fields in [('Customer', ['name', 'password']),
                         ('Order', ['customer_id', 'name']), ('Line', ['order_id'])]:
        entity = EntityDescriptor(name).table_name(name.lower() + '_data')
        entity.property(PropertyDescriptor('id', DataType.I64).is_id().log_policy('plain'))
        entity.property(PropertyDescriptor('version', DataType.I64).is_version().log_policy('plain'))
        for field in fields:
            entity.property(PropertyDescriptor(field, DataType.I64 if field.endswith('_id')
                                               else DataType.Text).log_policy('plain'))
        entity.audit_mask_fields(['name'])
        if name == 'Customer':
            entity.relation(RelationDescriptor('orders', 'Order').foreign('customer_id').many())
        elif name == 'Order':
            entity.relation(RelationDescriptor('lines', 'Line').foreign('order_id').many())
        provider.register_entity(entity)
        module.entity(entity)
    path = str(tmp_path / 'relations.db')
    async with aiosqlite.connect(path) as db:
        await db.executescript('''
            CREATE TABLE customer_data(id INTEGER PRIMARY KEY, version INTEGER, name TEXT, password TEXT);
            CREATE TABLE order_data(id INTEGER PRIMARY KEY, version INTEGER, customer_id INTEGER, name TEXT);
            CREATE TABLE line_data(id INTEGER PRIMARY KEY, version INTEGER, order_id INTEGER);
        ''')
        await db.execute('INSERT INTO customer_data VALUES (1,1,?,?)', ('Riverside', 'PASSWORD-CANARY'))
        await db.execute('INSERT INTO order_data VALUES (1,1,1,?)', ('Lakeside',))
        await db.execute('INSERT INTO line_data VALUES (1,1,1)')
        await db.commit()
    transport = CaptureTransport(path)
    service = CaptureExecutor(transport, provider)
    context = module.into_context()
    logs, output = [], []
    sink = TextDiagnosticSqlLogSink(output.append)
    def capture(entry):
        logs.append(entry)
        sink.write(entry)
    context.set_diagnostic_sql_log_sink(SimpleNamespace(write=capture))
    if debug:
        monkeypatch.setenv(PLAINTEXT_ENV, PLAINTEXT_ACK)
    if failure:
        transport.failing_table = 'line_data' if shape in ('nested', 'nested-aggregate') else 'order_data'
    query = (SelectQuery('Customer').project('id', 'name')
             .filter(Expr.eq('name', 'Riverside')).and_filter(Expr.eq('password', 'PASSWORD-CANARY')).limit(1))
    child = SelectQuery('Order').project('id', 'name')
    if shape == 'probe':
        child.limit(1).top_n_probe_parent_threshold(32)
    if shape == 'window':
        child.limit(1).top_n_probe_parent_threshold(0)
    if shape == 'nested':
        child.filter(Expr.eq('name', 'Lakeside')).relation_query('lines', SelectQuery('Line').project('id').limit(2))
    if shape == 'nested-aggregate':
        child.filter(Expr.eq('name', 'Lakeside'))
        child.relation_aggregates.append(RelationAggregate('lines', 'line_count', SelectQuery('Line').count('n'), True))
    if shape == 'aggregate':
        query.relation_aggregates.append(RelationAggregate('orders', 'record_count', SelectQuery('Order').count('n'), True))
    elif shape == 'batch':
        query.relation('orders')
    else:
        query.relation_query('orders', child)
    request = (QueryRequest(query, _comment='what: runtime regression fixture', _purpose='why: verify runtime behavior').comment('what: load Riverside PASSWORD-CANARY Lakeside graph')
               .purpose('why: verify inherited intent'))
    if failure:
        with pytest.raises(TransportError) as caught:
            await service.query(context, request)
        assert caught.value.error is transport.failure
    else:
        result = await service.query(context, request)
        assert len(result.rows) == 1
        if shape == 'aggregate':
            assert result.rows[0]['record_count'] == 1
        elif shape == 'batch':
            # A relation without a nested projection loads only its linking key.
            assert result.rows[0]['orders'] == [{'customer_id': 1}]
        else:
            assert result.rows[0]['orders'][0]['id'] == 1
            if shape == 'nested':
                assert result.rows[0]['orders'][0]['lines'][0]['id'] == 1
            if shape == 'nested-aggregate':
                assert result.rows[0]['orders'][0]['line_count'] == 1
    assert service.dispatched == (['Customer', 'Order', 'Line'] if shape in ('nested', 'nested-aggregate') else ['Customer', 'Order'])
    assert len(logs) == len(service.dispatched)
    entry = logs[-1]
    assert entry.execution_outcome == ('failure' if failure else 'success')
    assert entry.comment.startswith('what: load')
    assert entry.purpose == 'why: verify inherited intent'
    assert ('Riverside' in entry.comment) == debug
    assert 'PASSWORD-CANARY' not in repr(logs) + '\n'.join(output) + repr(context.sql_logs())
    if not debug:
        assert 'Riverside' not in repr(logs) + '\n'.join(output)
        if shape in ('nested', 'nested-aggregate'):
            assert 'Lakeside' not in entry.comment
            assert 'Lakeside' not in repr(logs) + '\n'.join(output) + repr(context.sql_logs())
    if shape == 'nested-aggregate':
        assert [(node.kind, node.name) for node in entry.trace_path] == [
            ('operation', 'Customer'), ('request', 'Customer'), ('relation', 'orders'),
            ('relation', 'lines'), ('provider', 'sqlite'), ('sql', 'select')]
    assert len(entry.params) == len(transport.reads[-1].params)
    assert 'PASSWORD-CANARY' in [v.val for v in transport.reads[0].params]
    if shape == 'batch':
        assert ' IN (' in entry.sql
    elif shape == 'window':
        assert 'ROW_NUMBER() OVER' in entry.sql
    elif shape == 'probe':
        assert ' IN (' not in entry.sql and 'ROW_NUMBER' not in entry.sql
    monkeypatch.delenv(PLAINTEXT_ENV, raising=False)
    assert 'Riverside' not in repr(sql_log_projection(entry))
    transport.failing_table = None
    await service.query(context, QueryRequest(SelectQuery('Customer').limit(1), _comment='what: runtime regression fixture', _purpose='why: verify runtime behavior')
                        .comment('what: independent Riverside').purpose('why: source isolation'))
    assert logs[-1].comment == 'what: independent Riverside'
