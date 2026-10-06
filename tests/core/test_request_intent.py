import pytest
import json
from pathlib import Path
from dataclasses import FrozenInstanceError

from teaql.core import InsertCommand, MutationRequest, SelectQuery, TraceNode
from teaql.data_service import QueryRequest
from teaql.core import QueryIntent, MutationIntent, RequestIntentError

VECTORS = json.loads((Path(__file__).parents[1] / 'fixtures/request-intent-v1.json').read_text())['cases']


@pytest.mark.parametrize('case', VECTORS, ids=lambda case: case['id'])
def test_shared_request_intent_contract(case):
    data = case['input']
    traces = [TraceNode(kind=node['kind'], comment=node['detail']) for node in data.get('trace', [])]

    def build():
        if case['kind'] == 'query':
            return QueryRequest(SelectQuery('Order'), traces,
                _comment=data.get('comment'), _purpose=data.get('purpose'))
        if 'children' in data:
            children = [MutationRequest(InsertCommand('OrderItem'), comment=child['comment'])
                for child in data['children']]
            return MutationRequest.Batch(children, comment=data.get('comment'))
        return MutationRequest(InsertCommand('Order', trace_chain=traces), comment=data.get('comment'))

    if 'error' in case:
        with pytest.raises(RequestIntentError) as caught:
            build()
        assert caught.value.code == case['error']['code']
        assert caught.value.field == case['error']['field']
        assert caught.value.request_kind == case['kind']
    else:
        request = build()
        assert request.intent.comment == case['expected']['comment']
        if case['kind'] == 'query':
            assert request.intent.purpose == case['expected']['purpose']


@pytest.mark.parametrize('codepoint', [*range(9, 14), 0x20, 0x85, 0xA0, 0x1680,
    *range(0x2000, 0x200B), 0x2028, 0x2029, 0x202F, 0x205F, 0x3000])
def test_unicode_white_space_matches_rust(codepoint):
    with pytest.raises(RequestIntentError, match='REQUEST_COMMENT_REQUIRED'):
        MutationIntent(chr(codepoint))
    with pytest.raises(RequestIntentError, match='QUERY_PURPOSE_REQUIRED'):
        QueryIntent('load order', chr(codepoint))


@pytest.mark.parametrize('text', ['\u001c', '\u001d', '\u001e', '\u001f', '\u200b', '\ufeff'])
def test_non_white_space_is_not_silently_reclassified(text):
    assert MutationIntent(text).comment == text


def test_owned_intent_survives_builder_and_route_changes_without_leaking_in_repr():
    query = SelectQuery('Order').comment(' load order ').purpose('render order')
    request = QueryRequest(query)
    query.comment('different request')
    request.query.comment('policy must not rewrite intent')
    assert request.intent.comment == ' load order '
    assert request.with_query(SelectQuery('OrderItem')).intent == request.intent
    with pytest.raises(AttributeError):
        request._comment = ''
    with pytest.raises(FrozenInstanceError):
        request.intent.comment = ''
    command = InsertCommand('Order', trace_chain=[TraceNode(comment='child reason')])
    mutation = MutationRequest(command, comment='submit order')
    command.trace_chain.append(TraceNode(kind='provider', comment=''))
    assert mutation.comment() == 'submit order'
    assert mutation.intent.readback().comment == 'submit order'
    with pytest.raises(AttributeError):
        mutation.comment = 'cannot shadow accessor'
    assert 'submit order' not in repr(mutation.intent)
    assert 'load order' not in repr(request.intent)


def test_query_policy_cannot_replace_root_intent():
    from teaql.runtime import UserContext
    context = UserContext().with_request_policy(lambda _: SelectQuery('Order').comment('rewrite').purpose('rewrite'))
    request = QueryRequest(SelectQuery('Order'), _comment='original comment', _purpose='original purpose')
    prepared = context.prepare_query_request(request)
    assert prepared.intent == request.intent
    assert prepared.query.comment_text == 'original comment'
    assert prepared.query.purpose_text == 'original purpose'


@pytest.mark.asyncio
async def test_graph_root_is_required_before_begin_even_with_a_valid_child():
    from teaql.runtime import UserContext
    calls = []
    async def work():
        calls.append('work')
        return MutationRequest(InsertCommand('OrderItem'), comment='create item')
    class Provider:
        async def begin(self, _):
            calls.append('begin')
            raise AssertionError('provider must not be called')
    context = UserContext().insert_resource('dataService', Provider())
    with pytest.raises(RequestIntentError, match='REQUEST_COMMENT_REQUIRED'):
        await context.execute_graph_save(work, comment='\u0085')
    assert calls == []


@pytest.mark.asyncio
@pytest.mark.parametrize('logging', [False, True])
async def test_direct_provider_gates_before_checker_schema_and_stream(logging):
    from teaql.runtime import UserContext
    from teaql.runtime.context import SqlLogOptions
    from teaql.sql.executor import SqlDataServiceExecutor
    context = UserContext()
    if not logging:
        context.with_sql_log_options(SqlLogOptions.disabled())
    calls = []
    context.check_and_fix_mutation = lambda _: calls.append('checker')
    context.with_request_policy(lambda _: calls.append('policy'))
    provider = object.__new__(SqlDataServiceExecutor)
    provider._sync_generated_schema = lambda _: calls.append('schema')
    query = object.__new__(QueryRequest)
    query.query = SelectQuery('MissingTable')
    mutation = object.__new__(MutationRequest)
    mutation._data = InsertCommand('MissingTable').value('secret', 'PAYLOAD-CANARY')
    def diagnostic(error, kind):
        assert error.code == 'REQUEST_COMMENT_REQUIRED'
        assert error.field == 'comment'
        assert error.request_kind == kind
        assert 'PAYLOAD-CANARY' not in str(error)
    for execute, kind in [(provider.query(context, query), 'query'), (provider.mutate(context, mutation), 'mutation')]:
        with pytest.raises(RequestIntentError) as caught:
            await execute
        diagnostic(caught.value, kind)
    with pytest.raises(RequestIntentError) as caught:
        await context.prepare_query_request(query)
    diagnostic(caught.value, 'query')
    with pytest.raises(RequestIntentError) as caught:
        async for _ in provider.query_stream(context, query, 10):
            raise AssertionError('stream must not open')
    diagnostic(caught.value, 'query')
    assert calls == []


@pytest.mark.parametrize('comment', [None, '', ' \t\r\n', '\u0085', '\u2003'])
def test_query_request_rejects_missing_or_blank_comment(comment):
    with pytest.raises(ValueError, match='REQUEST_COMMENT_REQUIRED'):
        QueryRequest(SelectQuery('Order'), _comment=comment, _purpose='render orders')


@pytest.mark.parametrize('comment', [None, '', ' \t\r\n', '\u0085', '\u2003'])
def test_mutation_request_does_not_infer_comment_from_trace(comment):
    command = InsertCommand('Order', trace_chain=[TraceNode(comment='submit order')])
    with pytest.raises(ValueError, match='REQUEST_COMMENT_REQUIRED'):
        if comment is None:
            MutationRequest(command)
        else:
            MutationRequest(command, comment=comment)
