import asyncio
from types import SimpleNamespace

import pytest

from teaql.core.query import SelectQuery
from teaql.core.request_tree import QueryOperation
from teaql.data_service import QueryRequest
from teaql.runtime import UserContext
from teaql.runtime.query_list import execute_typed_list, observe_query_operation, _query_owner


class Probe:
    def __init__(self):
        self.events = []

    def start(self, operation):
        self.events.append(('start', operation.name))
        events = self.events

        class Scope:
            def success(self, values):
                events.append(('success', values['teaql.result.cardinality']))

            def failure(self, error):
                events.append(('failure', error))

        return Scope()


class Service:
    def __init__(self):
        self.queries = []
        self.callback = None
        self.failure = None
        self.count = 3

    async def query(self, context, request):
        async def execute():
            self.queries.append(request)
            if self.callback:
                await self.callback(context, request)
            if self.failure:
                raise self.failure
            if request.query.aggregates:
                return SimpleNamespace(rows=[{'totalOrders': self.count}], facets={})
            return SimpleNamespace(rows=[{'id': 2, 'version': 1}], facets={'statusCounts': []})

        return await observe_query_operation(context, self, request, execute,
                                             lambda result: {'teaql.result.cardinality': len(result.rows)})


def setup(counted=True):
    probe, service = Probe(), Service()
    context = UserContext().with_runtime_telemetry(probe).insert_resource('dataService', service)
    query = SelectQuery('Order').limit(1).comment('load orders').purpose('render order list')
    if counted:
        query.count_field('id', 'totalOrders')
    return context, service, probe, QueryRequest(query)


async def typed(context, request, counted=True, hydrate=lambda row: row['id']):
    return await execute_typed_list(context, request, hydrate,
        count_operation=QueryOperation('named-count', 'count_as', 'totalOrders') if counted else None,
        count_alias='totalOrders' if counted else None)


@pytest.mark.asyncio
@pytest.mark.parametrize('counted', [False, True])
async def test_one_root_covers_optional_count_facets_and_hydration(counted):
    context, service, probe, root = setup(counted)

    def hydrate(row):
        assert probe.events == [('start', 'Order.list')], 'root ended before typed hydration'
        return row['id']

    result = await typed(context, root, counted, hydrate)
    assert list(result) == [2] and result.facets == {'statusCounts': []}
    assert len(service.queries) == (2 if counted else 1)
    assert result.aggregations == ({'totalOrders': 3} if counted else {})
    assert probe.events == [('start', 'Order.list'), ('success', 1)]
    assert _query_owner.get() is None


@pytest.mark.asyncio
@pytest.mark.parametrize('phase', ['count', 'rows', 'hydrate'])
async def test_failure_preserves_original_error_closes_root_and_restores_ownership(phase):
    context, service, probe, root = setup(phase != 'rows')
    original = ValueError('PRIVATE-QUERY-FAILURE')
    if phase != 'hydrate':
        service.failure = original

    def hydrate(row):
        raise original

    with pytest.raises(ValueError) as caught:
        await typed(context, root, phase != 'rows', hydrate)
    assert caught.value is original
    assert probe.events == [('start', 'Order.list'), ('failure', original)]
    assert _query_owner.get() is None
    assert len(service.queries) == (2 if phase == 'hydrate' else 1)


@pytest.mark.asyncio
async def test_independent_nested_request_and_different_service_keep_their_own_root():
    context, service, probe, root = setup()
    other = Service()

    async def nested(ctx, request):
        if not request.query.aggregates:
            return
        independent = QueryRequest(SelectQuery('Status').limit(1).comment('load status').purpose('inspect status'))
        await service.query(ctx, independent)
        await other.query(ctx, request.with_query(request.query))

    service.callback = nested
    await typed(context, root)
    assert [value for phase, value in probe.events if phase == 'start'] == ['Order.list', 'Status.list', 'Order.list']
    assert _query_owner.get() is None


@pytest.mark.asyncio
async def test_same_context_concurrent_lists_have_separate_task_ownership():
    context, service, probe, root = setup()
    arrivals, release = 0, asyncio.Event()

    async def barrier(ctx, request):
        nonlocal arrivals
        if request.query.aggregates:
            arrivals += 1
            if arrivals == 2:
                release.set()
            await asyncio.wait_for(release.wait(), 2)

    service.callback = barrier
    result = await asyncio.wait_for(asyncio.gather(typed(context, root), typed(context, root)), 3)
    assert [list(rows) for rows in result] == [[2], [2]]
    assert [value for phase, value in probe.events if phase == 'start'] == ['Order.list', 'Order.list']
    assert len([event for event in probe.events if event == ('success', 1)]) == 2
    assert len(service.queries) == 4 and _query_owner.get() is None


@pytest.mark.asyncio
async def test_child_task_does_not_silently_inherit_parent_invocation_ownership():
    context, service, probe, root = setup(False)

    async def execute():
        return await asyncio.create_task(service.query(context, root.with_query(root.query)))

    await observe_query_operation(context, service, root, execute,
                                  lambda result: {'teaql.result.cardinality': len(result.rows)})
    assert len([event for event in probe.events if event[0] == 'start']) == 2
    assert _query_owner.get() is None


@pytest.mark.asyncio
async def test_cancellation_is_preserved_and_next_query_is_independent():
    context, service, probe, root = setup()
    original = asyncio.CancelledError()
    service.failure = original
    with pytest.raises(asyncio.CancelledError) as caught:
        await typed(context, root)
    assert caught.value is original and _query_owner.get() is None
    service.failure = None
    await typed(context, root)
    assert probe.events == [('start', 'Order.list'), ('failure', original), ('start', 'Order.list'), ('success', 1)]


@pytest.mark.asyncio
@pytest.mark.parametrize('value', [-1, 1.5, float('nan'), float('inf'), True, '3'])
async def test_invalid_count_does_not_invent_row_result(value):
    context, service, probe, root = setup()
    service.count = value
    with pytest.raises(RuntimeError, match='exact list count'):
        await typed(context, root)
    assert len(service.queries) == 1 and probe.events[-1][0] == 'failure'
    assert _query_owner.get() is None


@pytest.mark.asyncio
async def test_adapter_faults_do_not_replace_results_or_failures():
    context, service, _, root = setup()

    class Broken:
        def start(self, operation):
            raise RuntimeError('PRIVATE-ADAPTER-FAILURE')

    context.with_runtime_telemetry(Broken())
    assert list(await typed(context, root)) == [2]
    original = ValueError('PRIVATE-QUERY-FAILURE')
    service.failure = original
    with pytest.raises(ValueError) as caught:
        await typed(context, root)
    assert caught.value is original and _query_owner.get() is None
