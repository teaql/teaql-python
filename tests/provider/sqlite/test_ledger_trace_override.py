"""Explicit native ledger input, not a generated automatic-writer assertion."""
from copy import deepcopy
from types import SimpleNamespace

import aiosqlite
import pytest

from test_trace_chain import fixture
from teaql.core.entity import EntityKey, EntityRoot
from teaql.core.mutation import UpdateCommand


def scalar(value):
    return getattr(value, 'val', value)


def lineage(nodes):
    return [(node.name or node.entity_type, node.entity_id, node.comment) for node in nodes]


@pytest.mark.asyncio
@pytest.mark.parametrize('logging', [False, True])
@pytest.mark.parametrize('empty', [False, True])
async def test_native_ledger_preference_reaches_sql_and_committed_audit(
        tmp_path, monkeypatch, logging, empty):
    monkeypatch.delenv('TEAQL_ALLOW_SENSITIVE_PLAINTEXT_LOGS', raising=False)
    context, service, transport, diagnostics = await fixture(tmp_path)
    context.insert_resource('dataService', service)
    if not logging:
        context.disable_sql_log()
    context.entity('Payment').audit_mask_fields(['name'])
    service.schema_provider.get_entity('Payment').audit_mask_fields(['name'])
    secret = 'OVERRIDEPRIVATEPAYMENT'
    reason = 'apply ' + secret
    ledger = EntityRoot()
    keys = [EntityKey(entity, 1) for entity in ('CustomerOrder', 'Payment', 'Shipment')]
    names = ['changed root', secret, 'changed shipment']
    commands, results, events, phases = [], [], [], []
    begin = transport.begin_sql

    async def observed_begin():
        tx = await begin()
        phases.append('begin')
        commit = tx.commit_sql

        async def observed_commit():
            await commit()
            phases.append('commit')
        tx.commit_sql = observed_commit
        return tx

    monkeypatch.setattr(transport, 'begin_sql', observed_begin)

    def audit(_context, event):
        assert phases[-1] == 'commit'
        events.append(event)
    context.with_app_audit_event_sink(SimpleNamespace(on_safe_event=audit))

    async def work(graph):
        root = graph.scope(keys[0])
        # A native caller supplies the complete chain using real scope recovery.
        # No observer inserts expected frames into requests or execution results.
        supplied = graph.scope(keys[1], root, 'review ' + secret).recover()
        before = deepcopy(supplied)
        ledger.set_trace_chain(keys[1], () if empty else supplied)
        ledger.set_trace_chain(keys[2], ())
        scope = [root, graph.scope(keys[1], root, 'fallback charge'), root]
        updates = [UpdateCommand.new(key.entity, key.id).expected_version(1).value('name', name)
                   for key, name in zip(keys, names)]
        for command in updates:
            graph.context.preflight_mutation(command)
        for key, command, local in zip(keys, updates, scope):
            request = graph.request(command, local, ledger, key)
            commands.append((key, deepcopy(request.mutation_lineage)))
            results.append(await graph.transaction.mutate(graph.context, request))
            assert not events
        assert supplied == before
        assert ledger.trace_chain(keys[1]) == (() if empty else before)

    await context.execute_graph_save(work, comment=reason)
    root_node = ('CustomerOrder', 1, reason)
    local_reason = 'fallback charge' if empty else 'review ' + secret
    expected = [[root_node], [root_node, ('Payment', 1, local_reason)], [root_node]]
    assert phases == ['begin', 'commit']
    assert [key for key, _ in commands] == keys
    assert [lineage(nodes) for _, nodes in commands] == expected
    assert len(transport.writes) == len(transport.reads) == len(results) == len(events) == 3
    for index, result in enumerate(results):
        assert scalar(result.persisted_record['name']) == names[index]
        assert scalar(result.persisted_record['version']) == 2
        assert result.affected_rows == 1
        assert lineage(result.metadata.mutation_lineage) == expected[index]
        assert len(result.metadata.statements) == 2
        for read, metadata in enumerate(result.metadata.statements):
            compiled = (transport.reads if read else transport.writes)[index]
            assert metadata.parameterized_sql == compiled.sql
            assert metadata.parameters == compiled.params
            assert metadata.comment == reason
            assert metadata.execution_outcome == 'success'
            assert lineage(metadata.mutation_lineage) == expected[index]
            assert metadata.result_count == 1 if read else metadata.affected_rows == 1
            assert [node.kind for node in metadata.trace_chain] == [
                'operation', 'request' if read else 'entity', 'provider', 'sql']
            assert metadata.trace_chain[0].name == 'CustomerOrder'
    safe = [[(kind, identity, comment.replace(secret, '[REDACTED]'))
             for kind, identity, comment in nodes] for nodes in expected]
    assert [(event.entity, scalar(event.entity_id)) for event in events] == [(key.entity, key.id) for key in keys]
    assert [lineage(event.trace_chain) for event in events] == safe
    assert secret not in repr(events)
    assert len(diagnostics) == (6 if logging else 0)
    if logging:
        assert [lineage(entry.mutation_lineage) for entry in diagnostics] == [nodes for nodes in safe for _ in range(2)]
        assert secret not in repr(diagnostics)
    async with aiosqlite.connect(transport.db_path) as db:
        for key, name in zip(keys, names):
            row = await (await db.execute(
                f'SELECT name, version FROM {key.entity.lower()}_data WHERE id = ?', (key.id,))).fetchone()
            assert row == (name, 2)

    # Native ownership is explicit; this does not claim generated auto-cleanup.
    ledger.clear_committed()
    assert ledger.trace_chain(keys[1]) == ()
    later_reason = 'independent mention ' + secret

    async def later(graph):
        command = UpdateCommand.new('Payment', 1).expected_version(2).value('name', 'next value')
        graph.context.preflight_mutation(command)
        request = graph.request(command, graph.scope(keys[1]), ledger, keys[1])
        result = await graph.transaction.mutate(graph.context, request)
        assert lineage(result.metadata.mutation_lineage) == [('Payment', 1, later_reason)]
        assert scalar(result.persisted_record['version']) == 3
    await context.execute_graph_save(later, comment=later_reason)
    assert phases == ['begin', 'commit', 'begin', 'commit']
    assert len(events) == 4
    assert lineage(events[-1].trace_chain) == [('Payment', 1, later_reason)]
    assert len(transport.writes) == len(transport.reads) == 4
    if logging:
        assert len(diagnostics) == 8
        assert all(entry.comment == later_reason for entry in diagnostics[-2:])
