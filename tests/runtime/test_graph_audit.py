"""Transaction lifecycle assertions, independent of generated library fixtures."""
import pytest

from teaql.runtime import UserContext
from teaql.runtime.audit import MutationAuditKind, RawAuditEvent
from teaql.core.entity import EntityKey


class Provider:
    def __init__(self, events):
        self.events = events

    async def begin(self, context):
        self.events.append('begin')
        return self

    async def commit(self, context):
        self.events.append('commit')

    async def rollback(self, context):
        self.events.append('rollback')


def fixture():
    events = []
    provider = Provider(events)
    context = UserContext().insert_resource('dataService', provider)
    class Sink:
        def on_safe_event(self, context, event):
            events.append('audit')
    context.with_app_audit_event_sink(Sink())
    return context, provider, events


@pytest.mark.asyncio
@pytest.mark.parametrize('failure', [False, True])
async def test_graph_audit_waits_for_commit_and_rollback_discards(failure):
    context, provider, events = fixture()
    async def work(graph):
        await graph.context.send_audit_event(RawAuditEvent(MutationAuditKind.CREATED, 'CustomerOrder', 1, ()))
        assert events == ['begin']
        if failure:
            raise RuntimeError('failed graph')
    if failure:
        with pytest.raises(RuntimeError, match='failed graph'):
            await context.execute_graph_save(work, comment='create order')
        assert events == ['begin', 'rollback']
    else:
        await context.execute_graph_save(work, comment='create order')
        assert events == ['begin', 'commit', 'audit']


@pytest.mark.asyncio
async def test_postcommit_failure_still_attempts_remaining_completion_actions():
    context, provider, events = fixture()
    def broken():
        events.append('broken completion')
        raise RuntimeError('completion unavailable')
    async def work(graph):
        graph.after_commit(broken)
        graph.after_commit(lambda: events.append('ledger clear'))
    with pytest.raises(RuntimeError) as caught:
        await context.execute_graph_save(work, comment='complete order')
    assert getattr(caught.value, 'committed', False) is True
    assert events == ['begin', 'commit', 'broken completion', 'ledger clear']


@pytest.mark.asyncio
async def test_reentrant_root_fails_before_begin_and_explicit_child_uses_one_session():
    context, provider, events = fixture()
    async def root(graph):
        assert context.require_resource('dataService') is provider
        with pytest.raises(RuntimeError, match='re-enter'):
            await context.execute_graph_save(root, comment='another independent root')
        async def spawned():
            with pytest.raises(RuntimeError, match='re-enter'):
                await context.execute_graph_save(root, comment='spawned independent root')
        await __import__('asyncio').create_task(spawned())
        with pytest.raises(RuntimeError, match='explicit session context'):
            context._require_mutation_invocation()
        graph.context._require_mutation_invocation()
        return graph
    graph = await context.execute_graph_save(root, comment='explicit root')
    assert events == ['begin', 'commit']
    with pytest.raises(RuntimeError, match='no longer writable'):
        graph.scope(EntityKey('CustomerOrder', 1))
    with pytest.raises(RuntimeError, match='no longer writable'):
        graph.context._require_mutation_invocation()


@pytest.mark.asyncio
async def test_foreign_scope_rejected_and_next_invocation_can_reuse_context():
    context, provider, events = fixture()
    async def first(graph):
        return graph.scope(EntityKey('CustomerOrder', 1))
    previous = await context.execute_graph_save(first, comment='first graph')
    async def second(graph):
        with pytest.raises(ValueError, match='another invocation'):
            graph.scope(EntityKey('Payment', 1), previous, 'authorize payment')
        return graph.scope(EntityKey('CustomerOrder', 1)).recover()
    nodes = await context.execute_graph_save(second, comment='second graph')
    assert [node.comment for node in nodes] == ['second graph']
    assert events == ['begin', 'commit', 'begin', 'commit']


@pytest.mark.asyncio
async def test_audit_snapshot_is_owned_and_failing_sink_does_not_skip_other_sink_or_cleanup():
    context, provider, events = fixture()
    raw = []
    class Broken:
        def on_event(self, context, event):
            raw.append(event)
            events.append('raw attempt')
            raise RuntimeError('sink failure')
    context._set_standard_audit_sink(Broken())
    async def work(graph):
        from teaql.core.mutation import TraceNode
        source = TraceNode(kind='auditReason', name='CustomerOrder', entity_id=1, comment='create order')
        await graph.context.send_audit_event(RawAuditEvent(
            MutationAuditKind.CREATED, 'CustomerOrder', 1, (), (source,)))
        source.comment = 'changed after queue'
        graph.after_commit(lambda: events.append('ledger clear'))
    with pytest.raises(RuntimeError) as caught:
        await context.execute_graph_save(work, comment='create order')
    assert caught.value.committed is True
    assert raw[0].trace_chain[0].comment == 'create order'
    assert events == ['begin', 'commit', 'raw attempt', 'audit', 'ledger clear']


@pytest.mark.asyncio
async def test_provider_type_error_does_not_retry_transaction_begin():
    context, provider, events = fixture()
    async def broken(context):
        events.append('broken begin')
        raise TypeError('provider implementation error')
    provider.begin = broken
    async def work(graph):
        raise AssertionError('work must not run')
    with pytest.raises(TypeError, match='provider implementation error'):
        await context.execute_graph_save(work, comment='create order')
    assert events == ['broken begin']
