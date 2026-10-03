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
        self.streams = []
        self.fail_table = None
        self.failure = RuntimeError('synthetic readback failure')

    async def fetch_all_sql(self, compiled):
        self.reads.append(compiled)
        if self.fail_table and self.fail_table in compiled.sql:
            raise self.failure
        return await super().fetch_all_sql(compiled)

    async def stream_sql(self, compiled, chunk_size):
        self.streams.append(compiled)
        async for chunk in super().stream_sql(compiled, chunk_size):
            yield chunk

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
@pytest.mark.parametrize('with_context', [False, True])
async def test_successful_readback_retains_ordered_physical_metadata(tmp_path, with_context):
    from teaql.data_service import DataServiceOperation
    context, service, transport, entries = await fixture(tmp_path)
    request = MutationRequest(
        InsertCommand.new('Payment').value('name', 'new payment').value('parent_id', 1),
        comment='persist payment and verify its authoritative snapshot')
    result = await service.mutate(context if with_context else None, request)
    assert result.affected_rows == result.metadata.affected_rows == 1
    assert result.metadata.operation == DataServiceOperation.Insert
    assert result.persisted_record['name'] == 'new payment'
    assert len(result.metadata.statements) == 2
    write, read = result.metadata.statements
    assert write.operation == DataServiceOperation.Insert
    assert read.operation == DataServiceOperation.Query
    assert write.statements == read.statements == ()
    assert write.affected_rows == 1 and read.affected_rows is None
    assert read.result_count == 1 and read.execution_outcome == 'success'
    assert read.comment == write.comment == request.comment()
    assert read.audit_reason == write.audit_reason == request.comment()
    assert read.mutation_lineage == write.mutation_lineage
    assert read.purpose == 'verify the persisted mutation result'
    assert [node.kind for node in read.trace_chain] == ['operation', 'request', 'provider', 'sql']
    assert [node.name for node in read.trace_chain] == ['Payment', 'Payment', 'sqlite', 'select']
    assert read.trace_chain[0].comment == 'query'
    assert len(entries) == (2 if with_context else 0)
    if with_context:
        assert [entry.execution_outcome for entry in entries] == ['success', 'success']
        assert len(context.sql_logs()) == 2


@pytest.mark.asyncio
async def test_batch_keeps_each_write_readback_pair(tmp_path):
    from teaql.data_service import DataServiceOperation
    context, service, transport, entries = await fixture(tmp_path)
    result = await service.mutate(context, MutationRequest.Batch([
        InsertCommand.new('Payment').value('name', 'batch payment').value('parent_id', 1),
        InsertCommand.new('PaymentAttempt').value('name', 'batch attempt').value('parent_id', 1),
    ], comment='persist atomic payment batch'))
    assert result.affected_rows == result.metadata.affected_rows == 2
    assert result.metadata.operation == DataServiceOperation.Batch
    assert len(result.metadata.statements) == 2
    for item in result.metadata.statements:
        assert item.operation == DataServiceOperation.Insert
        assert [part.operation for part in item.statements] == [
            DataServiceOperation.Insert, DataServiceOperation.Query]
    assert len(entries) == 4


@pytest.mark.asyncio
@pytest.mark.parametrize('mode', ['no-match', 'hard-delete'])
async def test_no_synthetic_readback_when_none_executed(tmp_path, mode):
    from teaql.core.mutation import UpdateCommand, DeleteCommand
    context, service, transport, entries = await fixture(tmp_path)
    command = (UpdateCommand.new('Payment', 99999).expected_version(1).value('name', 'missing')
               if mode == 'no-match' else DeleteCommand.new('Payment', 1).hard_delete())
    result = await service.mutate(context, MutationRequest(command, comment='verify physical work only'))
    assert result.affected_rows == (0 if mode == 'no-match' else 1)
    assert result.persisted_record is None and result.metadata.statements == ()
    assert len(entries) == 1
    assert transport.reads == []


@pytest.mark.asyncio
async def test_query_log_switch_does_not_remove_physical_readback_result(tmp_path):
    context, service, transport, entries = await fixture(tmp_path)
    context.enable_mutation_sql_log()
    result = await service.mutate(context, MutationRequest(
        InsertCommand.new('Payment').value('name', 'log switch payment').value('parent_id', 1),
        comment='persist despite query log switch'))
    assert len(result.metadata.statements) == 2
    assert len(entries) == 1 and not entries[0].operation.is_select()
    assert len(context.sql_logs()) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize('graph', [False, True])
@pytest.mark.parametrize('failure', [None, 'read-error', 'cancelled'])
async def test_future_child_values_cannot_escape_root_intent(tmp_path, graph, failure):
    import asyncio
    from teaql.core.mutation import UpdateCommand
    from teaql.core.value import Value
    context, service, transport, entries = await fixture(tmp_path)
    context.entity('Payment').audit_mask_fields(['name'])
    service.schema_provider.get_entity('Payment').audit_mask_fields(['name'])
    audits = []
    context.with_app_audit_event_sink(SimpleNamespace(on_safe_event=lambda _, event: audits.append(event)))
    secret, old = 'PRIVATE-FUTURE-CHILD-VALUE', 'PRIVATE-OLD-CHILD-VALUE'
    comment = f'authorize graph containing {secret} replacing {old}'
    root = InsertCommand.new('CustomerOrder').value('name', 'public root')
    child = UpdateCommand.new('Payment', 1).expected_version(1).value('name', secret)
    child.old_values = {'name': Value.from_any(old)}
    async with aiosqlite.connect(transport.db_path) as database:
        await database.execute('UPDATE payment_data SET name=? WHERE id=1', (old,))
        await database.commit()
    if failure:
        transport.fail_table = 'payment_data'
        if failure == 'cancelled':
            transport.failure = asyncio.CancelledError()
    async def execute():
        if graph:
            context.insert_resource('dataService', service)
            async def work(session):
                for command in (root, child):
                    session.context.preflight_mutation(command)
                for command in (root, child):
                    await session.transaction.mutate(session.context, MutationRequest(command, comment=comment))
            await context.execute_graph_save(work, comment=comment)
        else:
            await service.mutate(context, MutationRequest.Batch([root, child], comment=comment))
    if failure:
        with pytest.raises(type(transport.failure)) as caught:
            await execute()
        assert caught.value is transport.failure
    else:
        await execute()
    assert len(entries) == 4 and len(audits) == (0 if failure else 2)
    assert entries[-1].execution_outcome == (
        'cancelled' if failure == 'cancelled' else 'failure' if failure else 'success')
    for value in (secret, old):
        assert value not in repr(entries)
        assert value not in repr(context.sql_logs())
        assert value not in repr(audits)
    async with aiosqlite.connect(transport.db_path) as database:
        row = await (await database.execute('SELECT name, version FROM payment_data WHERE id=1')).fetchone()
        assert row == ((old, 1) if failure else (secret, 2))
    await service.query(context, QueryRequest(SelectQuery('CustomerOrder').limit(1),
        _comment=f'independent {secret} {old}', _purpose='verify privacy does not outlive its invocation'))
    assert secret in entries[-1].comment and old in entries[-1].comment


@pytest.mark.asyncio
async def test_concurrent_native_batches_own_distinct_privacy(tmp_path):
    import asyncio
    context, service, transport, entries = await fixture(tmp_path)
    context.configure_audit_policy('Payment', ['name'])
    secrets = ['FIRST-PRIVATE-PAYMENT', 'SECOND-PRIVATE-PAYMENT']
    groups = ['alpha', 'beta']
    async def save(index):
        own, other = secrets[index], secrets[1 - index]
        return await service.mutate(context, MutationRequest.Batch([
            InsertCommand.new('CustomerOrder').value('name', f'public root {index}'),
            InsertCommand.new('Payment').value('name', own).value('parent_id', 1),
        ], comment=f'group-{groups[index]} protects {own} unrelated {other}'))
    results = await asyncio.gather(save(0), save(1))
    assert all(result.affected_rows == 2 for result in results)
    assert len(entries) == 8
    for index in range(2):
        own_logs = [entry for entry in entries if entry.comment.startswith(f'group-{groups[index]}')]
        assert len(own_logs) == 4
        assert all(secrets[index] not in entry.comment and secrets[1-index] in entry.comment for entry in own_logs)


@pytest.mark.asyncio
async def test_inherited_debug_opt_in_keeps_credentials_hidden_and_can_reproject(tmp_path, monkeypatch):
    from teaql.runtime.log_privacy import PLAINTEXT_ENV, PLAINTEXT_ACK, sql_log_projection
    context, service, transport, entries = await fixture(tmp_path)
    descriptor = context.entity('Payment')
    descriptor.audit_mask_fields(['name'])
    descriptor.property(PropertyDescriptor('password_hash', DataType.Text))
    async with aiosqlite.connect(transport.db_path) as database:
        await database.execute('ALTER TABLE payment_data ADD COLUMN password_hash TEXT')
        await database.commit()
    audits = []
    context.with_app_audit_event_sink(SimpleNamespace(on_safe_event=lambda _, event: audits.append(event)))
    business, credential = 'DEBUG-BUSINESS-CANARY', 'CREDENTIAL-NEVER-PUBLIC'
    monkeypatch.setenv(PLAINTEXT_ENV, PLAINTEXT_ACK)
    await service.mutate(context, MutationRequest.Batch([
        InsertCommand.new('CustomerOrder').value('name', 'root'),
        InsertCommand.new('Payment').value('name', business).value('password_hash', credential).value('parent_id', 1),
    ], comment=f'authorize {business} with {credential}'))
    assert len(entries) == 4 and len(audits) == 2
    assert all(business in entry.comment and 'EXPLICIT OPT-IN' in entry.debug_sql for entry in entries)
    assert credential not in repr(entries) + repr(audits)
    monkeypatch.delenv(PLAINTEXT_ENV)
    for entry in entries:
        safe = sql_log_projection(entry)
        assert business not in repr(safe) and credential not in repr(safe)


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
        assert [node.kind for node in entry.trace_path] == [
            'operation', 'request' if operation == 'select' else 'entity', 'provider', 'sql']
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


@pytest.mark.asyncio
@pytest.mark.parametrize('nested', [False, True])
@pytest.mark.parametrize('logging', [False, True])
async def test_loaded_forward_key_remains_usable_by_relation_aggregate(tmp_path, nested, logging):
    from teaql.core.query import RelationAggregate
    from teaql.core.mutation import UpdateCommand
    context, service, transport, entries = await fixture(tmp_path)
    descriptor = service.schema_provider.get_entity('Payment')
    descriptor.relation(RelationDescriptor('parent_id', 'CustomerOrder').local('parent_id').foreign('id'))
    service.schema_provider.get_entity('CustomerOrder').audit_mask_fields(['name'])
    secret = 'PRIVATE-AGGREGATE-PARENT'
    await service.mutate(context, MutationRequest(UpdateCommand.new('CustomerOrder', 1)
        .expected_version(1).value('name', secret), comment='prepare private relation fixture'))
    entries.clear()
    context.clear_sql_logs()
    transport.reads.clear()
    if not logging:
        context.disable_select_sql_log()
    child = (SelectQuery('Payment').project('id', 'parent_id').limit(1)
             .relation_query('parent_id', SelectQuery('CustomerOrder').project('id', 'name').limit(1)))
    child.relation_aggregates.append(RelationAggregate('parent_id', 'parent_count',
        SelectQuery('CustomerOrder').filter(Expr.eq('name', secret)).count('n'), True))
    query = (SelectQuery('CustomerOrder').project('id').limit(1).relation_query('children', child)
             if nested else child)
    result = await service.query(context, QueryRequest(query, _comment='inspect ' + secret,
                                                     _purpose='verify composed aggregate ancestry'))
    row = result.rows[0]['children'][0] if nested else result.rows[0]
    assert row['parent_count'] == 1
    assert row['parent_id']['name'] == secret
    assert len(transport.reads) == (4 if nested else 3)
    if logging:
        assert len(entries) == len(transport.reads)
        assert all(secret not in entry.comment for entry in entries)
        assert all(entry.purpose == 'verify composed aggregate ancestry' for entry in entries)
        expected_root = 'CustomerOrder' if nested else 'Payment'
        assert all(entry.trace_path[0].name == expected_root for entry in entries)
        aggregate = next(entry for entry in entries if 'COUNT(' in entry.sql.upper())
        assert [node.name for node in aggregate.trace_path if node.kind == 'relation'] == (
            ['children', 'parent_id'] if nested else ['parent_id'])
    else:
        assert entries == []


@pytest.mark.asyncio
@pytest.mark.parametrize('logging', [False, True])
async def test_scalar_stream_rejects_relation_aggregate_before_provider(tmp_path, logging):
    from teaql.core.query import RelationAggregate
    context, service, transport, entries = await fixture(tmp_path)
    if not logging:
        context.disable_select_sql_log()
    query = SelectQuery('CustomerOrder').project('id').limit(1)
    query.relation_aggregates.append(RelationAggregate('children', 'child_count', SelectQuery('Payment').count('n'), True))
    stream = service.query_stream(context, QueryRequest(query, _comment='stream child counts',
                                                       _purpose='reject unsupported enhancement'), 1)
    with pytest.raises(ValueError, match='streaming relation or aggregate enhancement is not supported'):
        async for _ in stream:
            pytest.fail('unsupported aggregate stream must not yield incomplete rows')
    assert transport.streams == [] and transport.reads == [] and entries == []


def test_hydrated_relation_key_uses_declared_target_not_assumed_id():
    descriptor = EntityDescriptor('Stock')
    descriptor.relation(RelationDescriptor('sku', 'Product').local('sku').foreign('code'))
    row = {'sku': {'id': 999, 'code': 'SKU-A'}}
    assert SqlDataServiceExecutor._relation_key(row, descriptor, 'sku') == 'SKU-A'
    assert row == {'sku': {'id': 999, 'code': 'SKU-A'}}
    assert SqlDataServiceExecutor._relation_key({'sku': 'SKU-A'}, descriptor, 'sku') == 'SKU-A'


@pytest.mark.asyncio
@pytest.mark.parametrize('remove_in_policy', [False, True])
@pytest.mark.parametrize('fail', [False, True])
async def test_exact_count_retains_privacy_of_removed_relations_without_ambient_state(tmp_path, remove_in_policy, fail):
    context, service, transport, entries = await fixture(tmp_path)
    service.schema_provider.get_entity('CustomerOrder').audit_mask_fields([])
    service.schema_provider.get_entity('CustomerOrder').property_by_name('name').log_policy('plain')
    service.schema_provider.get_entity('Payment').audit_mask_fields(['name'])
    private = 'CHILD-COUNT-PRIVACY-CANARY'
    original = QueryRequest(SelectQuery('CustomerOrder').project('id').limit(1)
        .relation_query('children', SelectQuery('Payment').filter(Expr.eq('name', private)).limit(1)),
        _comment='count graph mentioning ' + private,
        _purpose='inspect total for ' + private)
    if remove_in_policy:
        def discard_relation(query):
            query.relations = []
            return query
        context.with_request_policy(discard_relation)
    prepared = context.prepare_query_request(original)
    counted = prepared.with_query(prepared.query.for_exact_count('__total')).comment(
        original.intent.comment).purpose(original.intent.purpose)
    if fail:
        transport.fail_table = 'customerorder_data'
        with pytest.raises(TransportError) as caught:
            await service.query(context, counted)
        assert caught.value.error is transport.failure
        transport.fail_table = None
    else:
        result = await service.query(context, counted)
        assert result.rows == [{'__total': 1}]
    assert len(transport.reads) == len(entries) == 1
    assert 'COUNT(' in transport.reads[0].sql.upper()
    assert 'payment_data' not in transport.reads[0].sql
    assert entries[0].comment == 'count graph mentioning [REDACTED]'
    assert entries[0].purpose == 'inspect total for [REDACTED]'
    assert entries[0].execution_outcome == ('failure' if fail else 'success')
    assert private not in repr(context.sql_logs())
    assert original.intent.comment.endswith(private) and len(original.query.relations) == 1
    await service.query(context, QueryRequest(SelectQuery('CustomerOrder')
        .filter(Expr.eq('name', private)).limit(1),
        _comment='independent query mentioning ' + private, _purpose='no inherited privacy'))
    assert entries[-1].comment.endswith(private)


@pytest.mark.asyncio
@pytest.mark.parametrize('rollback', [False, True])
async def test_explicit_transaction_audit_waits_for_commit_and_rollback_discards(tmp_path, rollback):
    context, service, transport, entries = await fixture(tmp_path)
    audits = []
    context.with_app_audit_event_sink(SimpleNamespace(on_safe_event=lambda context, event: audits.append(event)))
    transaction = await service.begin(context)
    command = InsertCommand.new('Payment').value('name', 'new payment').value('parent_id', 1)
    await transaction.mutate(context, MutationRequest(command, comment='authorize transaction payment'))
    assert audits == []
    if rollback:
        await transaction.rollback(context)
    else:
        await transaction.commit(context)
        assert len(audits) == 1
        assert audits[0].trace_chain[0].comment == 'authorize transaction payment'
        assert audits[0].trace_chain[0].entity_id == 2
    async with aiosqlite.connect(transport.db_path) as database:
        cursor = await database.execute('SELECT COUNT(*) FROM payment_data')
        assert (await cursor.fetchone())[0] == (1 if rollback else 2)
    assert context._audit_journal is None


@pytest.mark.asyncio
async def test_automatic_batch_readback_failure_discards_prior_successful_audits(tmp_path):
    context, service, transport, entries = await fixture(tmp_path)
    audits = []
    context.with_app_audit_event_sink(SimpleNamespace(on_safe_event=lambda context, event: audits.append(event)))
    transport.fail_table = 'paymentattempt_data'
    first = InsertCommand.new('Payment').value('name', 'first payment').value('parent_id', 1)
    second = InsertCommand.new('PaymentAttempt').value('name', 'second attempt').value('parent_id', 1)
    batch = MutationRequest.Batch([first, second], comment='authorize atomic payment batch')
    with pytest.raises(RuntimeError) as caught:
        await service.mutate(context, batch)
    assert caught.value is transport.failure
    assert audits == []
    assert [entry.execution_outcome for entry in entries] == ['success', 'success', 'success', 'failure']
    assert [entry.trace_path[-1].name for entry in entries] == ['insert', 'select', 'insert', 'select']
    async with aiosqlite.connect(transport.db_path) as database:
        for table in ('payment_data', 'paymentattempt_data'):
            cursor = await database.execute(f'SELECT COUNT(*) FROM {table}')
            assert (await cursor.fetchone())[0] == 1
    assert context._audit_journal is None


@pytest.mark.asyncio
async def test_automatic_transaction_sink_failure_reports_committed_and_does_not_rollback(tmp_path):
    context, service, transport, entries = await fixture(tmp_path)
    calls = []
    def unavailable(context, event):
        calls.append(event)
        raise RuntimeError('postcommit audit unavailable')
    context.with_app_audit_event_sink(SimpleNamespace(on_safe_event=unavailable))
    command = InsertCommand.new('Payment').value('name', 'committed payment').value('parent_id', 1)
    with pytest.raises(RuntimeError) as caught:
        await service.mutate(context, MutationRequest(command, comment='create committed payment'))
    assert caught.value.committed is True and len(calls) == 1
    async with aiosqlite.connect(transport.db_path) as database:
        cursor = await database.execute('SELECT COUNT(*) FROM payment_data')
        assert (await cursor.fetchone())[0] == 2
