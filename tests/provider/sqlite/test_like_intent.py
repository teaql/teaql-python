"""Exact typed LIKE operands at real SQLite boundaries; never strip wildcards."""
from copy import deepcopy
from dataclasses import asdict, replace

import pytest

from test_trace_chain import fixture
from teaql.core import expr
from teaql.core.mutation import MutationRequest, UpdateCommand
from teaql.core.query import SelectQuery
from teaql.core.value import Value
from teaql.data_service import QueryRequest
from teaql.runtime.context import SqlLogOptions
from teaql.sql.executor import TransportError


OPERATIONS = [
    (expr.contain, '%', '%', False),
    (expr.not_contain, '%', '%', True),
    (expr.begin_with, '', '%', False),
    (expr.not_begin_with, '', '%', True),
    (expr.end_with, '%', '', False),
    (expr.not_end_with, '%', '', True),
]


async def set_name(context, service, transport, entries, entity, value):
    await service.mutate(context, MutationRequest(UpdateCommand.new(entity, 1)
        .expected_version(1).value('name', value), comment='prepare LIKE operand fixture'))
    entries.clear()
    context.clear_sql_logs()
    transport.reads.clear()


def assert_logs(entries, logging, private, operand, root):
    if not logging:
        assert entries == []
        return
    assert entries
    for entry in entries:
        assert entry.trace_path[0].name == root
        assert entry.trace_path[-1].kind == 'sql'
        if private:
            assert operand not in repr(entry), 'original operand leaked to safe SQL evidence'
            assert '[REDACTED]' in entry.comment
            assert '[REDACTED]' in entry.purpose
        else:
            assert operand in entry.comment and operand in entry.purpose


@pytest.mark.asyncio
@pytest.mark.parametrize('operation,prefix,suffix,negated', OPERATIONS,
                         ids=[op[0].__name__ for op in OPERATIONS])
@pytest.mark.parametrize('logging', [False, True])
@pytest.mark.parametrize('private', [False, True])
@pytest.mark.parametrize('transaction', [False, True])
async def test_like_original_operand_at_sqlite_boundaries(
        tmp_path, monkeypatch, operation, prefix, suffix, negated, logging, private, transaction):
    monkeypatch.delenv('TEAQL_ALLOW_SENSITIVE_PLAINTEXT_LOGS', raising=False)
    context, service, transport, entries = await fixture(tmp_path)
    descriptor = service.schema_provider.get_entity('CustomerOrder')
    descriptor.audit_mask_fields(['name'] if private else [])
    descriptor.property_by_name('name').log_policy('plain')
    operand = 'PRIVATE-ROOT-OPERAND'
    await set_name(context, service, transport, entries, 'CustomerOrder', operand)
    if not logging:
        context.with_sql_log_options(SqlLogOptions.disabled())
    comment, purpose = 'inspect ' + operand, 'justify ' + operand
    policies = []
    context.with_request_policy(lambda query: policies.append(deepcopy(query)) or query)
    tx = await service.begin(context) if transaction else None
    execution = tx or service
    try:
        for count in [False, True]:
            query = SelectQuery('CustomerOrder').filter(operation('name', operand)).limit(2)
            query = query.count('n') if count else query.project('id')
            request = QueryRequest(query, _comment=comment, _purpose=purpose)
            before = deepcopy(request.query)
            result = await execution.query(context, context.prepare_query_request(request))
            assert (result.rows[0]['n'] if count else len(result.rows)) == (0 if negated else 1)
            assert request.query == before
            assert (request.intent.comment, request.intent.purpose) == (comment, purpose)
            assert policies[-1].filter_expr == query.filter_expr
            assert policies[-1].comment_text == comment and policies[-1].purpose_text == purpose
            assert [value.val for value in transport.reads[-1].params] == [prefix + operand + suffix]
            assert transport.reads[-1].parameter_log_policies == ['masked' if private else 'plain']
        assert_logs(entries, logging, private, operand, 'CustomerOrder')
        assert len(transport.reads) == 2
        # An independent invocation on the same Context must not retain this secret.
        await execution.query(context, QueryRequest(SelectQuery('CustomerOrder').project('id').limit(1),
            _comment=comment, _purpose=purpose))
        if logging:
            assert entries[-1].comment == comment and entries[-1].purpose == purpose
    finally:
        if tx:
            await tx.rollback(context)


@pytest.mark.asyncio
@pytest.mark.parametrize('logging', [False, True])
@pytest.mark.parametrize('transaction', [False, True])
@pytest.mark.parametrize('failure', [False, True])
async def test_like_future_child_masks_first_root_and_failure(
        tmp_path, monkeypatch, logging, transaction, failure):
    monkeypatch.delenv('TEAQL_ALLOW_SENSITIVE_PLAINTEXT_LOGS', raising=False)
    context, service, transport, entries = await fixture(tmp_path)
    service.schema_provider.get_entity('Payment').audit_mask_fields(['name'])
    operand = 'PRIVATE-CHILD-OPERAND'
    await set_name(context, service, transport, entries, 'Payment', operand)
    if not logging:
        context.with_sql_log_options(SqlLogOptions.disabled())
    child = SelectQuery('Payment').project('id', 'parent_id').filter(expr.contain('name', operand)).limit(1)
    query = SelectQuery('CustomerOrder').project('id').limit(1).relation_query('children', child)
    request = QueryRequest(query, _comment='inspect ' + operand, _purpose='justify ' + operand)
    before = deepcopy(request.query)
    tx = await service.begin(context) if transaction else None
    execution = tx or service
    try:
        if failure:
            transport.fail_table = 'payment_data'
            with pytest.raises(TransportError):
                await execution.query(context, request)
        else:
            result = await execution.query(context, request)
            assert len(result.rows[0]['children']) == 1
        assert len(transport.reads) == 2
        assert any(value.val == '%' + operand + '%' for value in transport.reads[1].params)
        assert request.query == before
        assert_logs(entries, logging, True, operand, 'CustomerOrder')
        if logging:
            assert len(entries) == 2
            assert [(n.name, n.comment) for n in entries[-1].trace_path if n.kind == 'relation'] == [
                ('children', 'CustomerOrder.children')]
            assert entries[-1].execution_outcome == ('failure' if failure else 'success')
        transport.fail_table = None
        await execution.query(context, QueryRequest(SelectQuery('CustomerOrder').project('id').limit(1),
            _comment='independent ' + operand, _purpose='no inherited source'))
        if logging:
            assert entries[-1].comment == 'independent ' + operand
    finally:
        if tx:
            await tx.rollback(context)


@pytest.mark.asyncio
@pytest.mark.parametrize('logging', [False, True])
async def test_like_literal_operands_and_raw_patterns_are_not_inferred(tmp_path, monkeypatch, logging):
    monkeypatch.delenv('TEAQL_ALLOW_SENSITIVE_PLAINTEXT_LOGS', raising=False)
    context, service, transport, entries = await fixture(tmp_path)
    service.schema_provider.get_entity('CustomerOrder').audit_mask_fields(['name'])
    operand = '%_\\fragment%'
    await service.mutate(context, MutationRequest(UpdateCommand.new('CustomerOrder', 1)
        .expected_version(1).value('name', operand), comment='prepare literal fixture'))
    entries.clear()
    transport.reads.clear()
    if not logging:
        context.with_sql_log_options(SqlLogOptions.disabled())
    result = await service.query(context, QueryRequest(
        SelectQuery('CustomerOrder').project('id').filter(expr.begin_with('name', operand)).limit(1),
        _comment='inspect ' + operand + ' public fragment', _purpose='justify ' + operand))
    assert len(result.rows) == 1
    assert [value.val for value in transport.reads[-1].params] == [operand + '%']
    assert_logs(entries, logging, True, operand, 'CustomerOrder')
    if logging:
        assert 'public fragment' in entries[-1].comment
    # Raw LIKE accepts a complete pattern. It has no original unwrapped operand.
    pattern = '%fragment%'
    result = await service.query(context, QueryRequest(
        SelectQuery('CustomerOrder').project('id').filter(expr.like('name', pattern)).limit(1),
        _comment='literal fragment; pattern ' + pattern, _purpose='raw pattern ' + pattern))
    assert len(result.rows) == 1
    assert [value.val for value in transport.reads[-1].params] == [pattern]
    if logging:
        assert entries[-1].comment == 'literal fragment; pattern [REDACTED]'
        assert entries[-1].purpose == 'raw pattern [REDACTED]'


@pytest.mark.asyncio
@pytest.mark.parametrize('logging', [False, True])
@pytest.mark.parametrize('rewrite', ['operator', 'pattern', 'replace'])
async def test_like_rewritten_ast_does_not_retain_stale_original(tmp_path, monkeypatch, logging, rewrite):
    monkeypatch.delenv('TEAQL_ALLOW_SENSITIVE_PLAINTEXT_LOGS', raising=False)
    context, service, transport, entries = await fixture(tmp_path)
    service.schema_provider.get_entity('CustomerOrder').audit_mask_fields(['name'])
    original = 'STALE-ORIGINAL-OPERAND'
    condition = expr.contain('name', original)
    assert set(asdict(condition.right)) == {'value'}, 'private provenance became a wire field'
    assert condition.right == expr.ValueExpr(Value.Text('%' + original + '%'))
    assert deepcopy(condition.right) == condition.right
    if rewrite == 'operator':
        condition.op = expr.BinaryOp.Eq
        pattern = '%' + original + '%'
    elif rewrite == 'pattern':
        pattern = '%CURRENT-PATTERN%'
        condition.right.value = Value.Text(pattern)
    else:
        pattern = '%REPLACEMENT-PATTERN%'
        condition.right = replace(condition.right, value=Value.Text(pattern))
        assert condition.right == replace(expr.ValueExpr(Value.Text('old')), value=Value.Text(pattern))
        assert not hasattr(condition.right, '_like_operand')
    if not logging:
        context.with_sql_log_options(SqlLogOptions.disabled())
    comment = 'old ' + original + ' current ' + pattern
    request = QueryRequest(SelectQuery('CustomerOrder').project('id').filter(condition).limit(1),
        _comment=comment, _purpose='do not infer a rewritten operand')
    result = await service.query(context, request)
    assert result.rows == []
    assert [value.val for value in transport.reads[-1].params] == [pattern]
    if logging:
        assert entries[-1].comment == 'old ' + original + ' current [REDACTED]'
    else:
        assert entries == []


@pytest.mark.asyncio
@pytest.mark.parametrize('policy', ['masked', 'credential'])
async def test_like_stream_debug_opt_in_and_revocation(tmp_path, monkeypatch, policy):
    from teaql.runtime.log_privacy import PLAINTEXT_ENV, PLAINTEXT_ACK
    monkeypatch.delenv(PLAINTEXT_ENV, raising=False)
    context, service, transport, entries = await fixture(tmp_path)
    descriptor = service.schema_provider.get_entity('CustomerOrder')
    descriptor.audit_mask_fields([])
    descriptor.property_by_name('name').log_policy(policy)
    operand = 'PRIVATE-STREAM-OPERAND'
    await set_name(context, service, transport, entries, 'CustomerOrder', operand)
    request = QueryRequest(SelectQuery('CustomerOrder').project('id')
        .filter(expr.contain('name', operand)).limit(1),
        _comment='inspect ' + operand, _purpose='justify ' + operand)
    for mode in ['safe', 'debug', 'revoked']:
        if mode == 'debug':
            monkeypatch.setenv(PLAINTEXT_ENV, PLAINTEXT_ACK)
        else:
            monkeypatch.delenv(PLAINTEXT_ENV, raising=False)
        entries.clear()
        chunks = [chunk async for chunk in service.query_stream(context, request, 1)]
        assert sum(len(chunk.rows) for chunk in chunks) == 1
        assert [value.val for value in transport.streams[-1].params] == ['%' + operand + '%']
        assert len(entries) == 1
        private = mode != 'debug' or policy == 'credential'
        assert_logs(entries, True, private, operand, 'CustomerOrder')
        if not private:
            assert 'DEBUG PLAINTEXT' in entries[0].debug_sql
        assert request.intent.comment == 'inspect ' + operand
