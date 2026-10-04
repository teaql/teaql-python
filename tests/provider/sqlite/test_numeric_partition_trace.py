"""Native numeric grouping/window evidence, not generated aggregation acceptance."""
from copy import deepcopy
import json
from types import SimpleNamespace

import aiosqlite
import pytest

from test_trace_chain import RecordingTransport
from teaql.core.expr import Expr, begin_with
from teaql.core.meta import EntityDescriptor, PropertyDescriptor, RelationDescriptor
from teaql.core.query import SelectQuery
from teaql.core.value import DataType
from teaql.data_service import QueryRequest
from teaql.provider.sqlite import SimpleSchemaProvider
from teaql.provider.sqlite.dialect import SqliteDialect
from teaql.runtime import RuntimeModule
from teaql.runtime.context import SqlLogOptions
from teaql.sql.executor import SqlDataServiceExecutor


OPERANDS = ('%NUMERIC_FIRST_', '%NUMERIC_SECOND_')


async def numeric_fixture(tmp_path, monkeypatch, logging):
    monkeypatch.delenv('TEAQL_ALLOW_SENSITIVE_PLAINTEXT_LOGS', raising=False)
    module, schema = RuntimeModule.new(), SimpleSchemaProvider()
    for name, fields in (
            ('NumericRoot', ()), ('NumericParent', ('root_id',)),
            ('NumericItem', ('parent_id', 'bucket', 'private_name', 'public_name'))):
        descriptor = EntityDescriptor(name).table_name(name.lower())
        descriptor.property(PropertyDescriptor('id', DataType.I64).is_id().log_policy('plain'))
        descriptor.property(PropertyDescriptor('version', DataType.I64).is_version().log_policy('plain'))
        for field in fields:
            descriptor.property(PropertyDescriptor(field,
                DataType.Text if field.endswith('_name') else DataType.I64).log_policy('plain'))
        descriptor.audit_mask_fields(['private_name'] if name == 'NumericItem' else [])
        if name == 'NumericRoot':
            descriptor.relation(RelationDescriptor('parents', 'NumericParent')
                                .local('id').foreign('root_id').many())
        elif name == 'NumericParent':
            descriptor.relation(RelationDescriptor('items', 'NumericItem')
                                .local('id').foreign('parent_id').many())
        module.entity(descriptor)
        schema.register_entity(descriptor)
    context = module.into_context()
    entries, raw = [], []
    context.set_diagnostic_sql_log_sink(SimpleNamespace(write=entries.append))
    if not logging:
        context.with_sql_log_options(SqlLogOptions.disabled())
    record = context._record_metadata_log

    def observe(metadata, **kwargs):
        raw.append(deepcopy(metadata))
        return record(metadata, **kwargs)

    monkeypatch.setattr(context, '_record_metadata_log', observe)
    transport = RecordingTransport(str(tmp_path / 'numeric.sqlite'))
    service = SqlDataServiceExecutor(SqliteDialect(), transport, schema)
    async with aiosqlite.connect(transport.db_path) as db:
        await db.execute('CREATE TABLE numericroot (id INTEGER PRIMARY KEY, version INTEGER)')
        await db.execute('CREATE TABLE numericparent '
                         '(id INTEGER PRIMARY KEY, version INTEGER, root_id INTEGER)')
        await db.execute('CREATE TABLE numericitem (id INTEGER PRIMARY KEY, version INTEGER, '
                         'parent_id INTEGER, bucket INTEGER, private_name TEXT, public_name TEXT)')
        await db.execute('INSERT INTO numericroot VALUES (1, 1)')
        await db.executemany('INSERT INTO numericparent VALUES (?, 1, 1)', [(1,), (2,), (3,)])
        for index, operand in enumerate(OPERANDS):
            rows = [(identity + index * 100, 1, parent, bucket,
                     operand + str(identity), operand + str(identity))
                    for identity, parent, bucket in (
                        (11, 1, 10), (12, 1, 10), (13, 1, 20),
                        (21, 2, 10), (22, 2, 30), (23, 2, 30))]
            await db.executemany('INSERT INTO numericitem VALUES (?, ?, ?, ?, ?, ?)', rows)
        await db.commit()
    return context, service, transport, entries, raw


def assert_path(nodes, root, relations):
    assert [node.kind for node in nodes] == [
        'operation', 'request', *['relation'] * len(relations), 'provider', 'sql']
    assert [node.name for node in nodes] == [root, root, *relations, 'sqlite', 'select']
    assert not any(node.kind == 'relation' and node.name in ('bucket', 'n', 'parent_id')
                   for node in nodes)


def assert_observations(request, before, transport, entries, raw, logging, field, operand,
                        root, routes, counts, expected_params):
    assert request.query == before and request.query.trace_chain == []
    assert len(transport.reads) == len(raw) == len(routes)
    assert [item.result_count for item in raw] == counts
    assert [[value.val for value in query.params] for query in transport.reads] == expected_params
    assert [item.parameters for item in raw] == [list(query.params) for query in transport.reads]
    assert all((item.comment, item.purpose) == (request.intent.comment, request.intent.purpose)
               for item in raw)
    for item, relations in zip(raw, routes):
        assert_path(item.trace_chain, root, relations)
    assert len(entries) == (len(raw) if logging else 0)
    for entry, relations in zip(entries, routes):
        assert_path(entry.trace_path, root, relations)
        if field == 'private_name':
            assert operand not in repr(entry)
            assert entry.comment == request.intent.comment.replace(operand, '[REDACTED]')
            assert entry.purpose == request.intent.purpose.replace(operand, '[REDACTED]')
        else:
            assert entry.comment == request.intent.comment and entry.purpose == request.intent.purpose
    print('NUMERIC_OBSERVATION ' + json.dumps({
        'root': root, 'logging': logging, 'field': field, 'routes': routes, 'counts': counts,
        'sql': [query.sql for query in transport.reads], 'parameters': expected_params,
        'safeIntent': [(entry.comment, entry.purpose) for entry in entries],
    }))


async def independent(context, service, entries, logging):
    reason = 'independent ' + ' and '.join(OPERANDS)
    result = await service.query(context, QueryRequest(SelectQuery('NumericRoot').project('id').limit(1),
        _comment=reason, _purpose='no numeric query provenance'))
    assert [row['id'] for row in result.rows] == [1]
    assert_path(result.metadata.trace_chain, 'NumericRoot', [])
    if logging:
        assert entries[-1].comment == reason
        assert entries[-1].purpose == 'no numeric query provenance'


@pytest.mark.asyncio
@pytest.mark.parametrize('logging', [False, True])
@pytest.mark.parametrize('field', ['private_name', 'public_name'])
@pytest.mark.parametrize('shape', ['group', 'window', 'grouped-window'])
async def test_root_numeric_grouping_and_partition_keep_real_sql_semantics(
        tmp_path, monkeypatch, logging, field, shape):
    context, service, transport, entries, raw = await numeric_fixture(tmp_path, monkeypatch, logging)
    for index, operand in enumerate(OPERANDS):
        entries.clear(); raw.clear(); transport.reads.clear()
        minimum = 15 if index == 0 else 25
        query = SelectQuery('NumericItem').filter(begin_with(field, operand))
        if shape == 'window':
            query.project('id', 'parent_id', 'bucket').partition_by_field('bucket').order_asc('id').limit(1)
        else:
            query.group_by('parent_id', 'bucket').count('n').having(Expr.gte('bucket', minimum))
            query.order_desc('bucket').limit(10 if shape == 'group' else 1)
            if shape == 'grouped-window':
                query.partition_by_field('parent_id')
        request = QueryRequest(query, _comment='inspect ' + operand, _purpose='justify ' + operand)
        before = deepcopy(request.query)
        result = await service.query(context, request)
        if shape == 'window':
            assert sorted((row['id'], row['parent_id'], row['bucket']) for row in result.rows) == [
                (11 + index * 100, 1, 10), (13 + index * 100, 1, 20), (22 + index * 100, 2, 30)]
        else:
            expected = [(1, 20, 1), (2, 30, 2)] if index == 0 else [(2, 30, 2)]
            assert sorted((row['parent_id'], row['bucket'], row['n']) for row in result.rows) == expected
        sql = transport.reads[0].sql
        assert ('ROW_NUMBER()' in sql) == (shape != 'group')
        assert ('GROUP BY' in sql and 'HAVING' in sql) == (shape != 'window')
        assert transport.reads[0].parameter_log_policies == [
            'masked' if field == 'private_name' else 'plain', *(['plain'] if shape != 'window' else [])]
        assert_observations(request, before, transport, entries, raw, logging, field, operand,
            'NumericItem', [[]], [len(result.rows)], [[operand + '%'] + ([] if shape == 'window' else [minimum])])
        await independent(context, service, entries, logging)


@pytest.mark.asyncio
@pytest.mark.parametrize('logging', [False, True])
@pytest.mark.parametrize('field', ['private_name', 'public_name'])
@pytest.mark.parametrize('plan', ['window', 'probe'])
async def test_loaded_grouped_relation_keeps_ancestors_membership_and_future_privacy(
        tmp_path, monkeypatch, logging, field, plan):
    context, service, transport, entries, raw = await numeric_fixture(tmp_path, monkeypatch, logging)
    for index, operand in enumerate(OPERANDS):
        entries.clear(); raw.clear(); transport.reads.clear()
        minimum = 15 if index == 0 else 25
        child = (SelectQuery('NumericItem').filter(begin_with(field, operand))
                 .group_by('parent_id', 'bucket').count('n').having(Expr.gte('bucket', minimum))
                 .order_desc('bucket').limit(1).top_n_probe_parent_threshold(0 if plan == 'window' else 10))
        parents = (SelectQuery('NumericParent').project('id').order_asc('id').limit(3)
                   .top_n_probe_parent_threshold(0).relation_query('items', child))
        query = SelectQuery('NumericRoot').project('id').limit(1).relation_query('parents', parents)
        request = QueryRequest(query, _comment='inspect future ' + operand, _purpose='justify future ' + operand)
        before = deepcopy(request.query)
        result = await service.query(context, request)
        assert len(result.rows) == 1
        loaded = result.rows[0]['parents']
        assert [parent['id'] for parent in loaded] == [1, 2, 3]
        assert {parent['id']: [(row['parent_id'], row['bucket'], row['n']) for row in parent['items']]
                for parent in loaded} == {
                    1: [(1, 20, 1)] if index == 0 else [], 2: [(2, 30, 2)], 3: []}
        assert all('__teaql_partition_rank' not in row for parent in loaded for row in parent['items'])
        child_reads = transport.reads[2:]
        assert all('GROUP BY' in item.sql and 'HAVING' in item.sql for item in child_reads)
        assert all(('ROW_NUMBER()' in item.sql) == (plan == 'window') for item in child_reads)
        expected_params = [[], [1]] + (
            [[operand + '%', 1, 2, 3, minimum]] if plan == 'window' else
            [[operand + '%', parent, minimum] for parent in (1, 2, 3)])
        counts = [1, 3] + ([2 if index == 0 else 1] if plan == 'window' else [1 if index == 0 else 0, 1, 0])
        assert_observations(request, before, transport, entries, raw, logging, field, operand,
            'NumericRoot', [[], ['parents']] + [['parents', 'items']] * len(child_reads), counts, expected_params)
        await independent(context, service, entries, logging)
