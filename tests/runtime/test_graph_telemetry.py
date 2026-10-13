"""The runtime graph parent covers all transaction and completion phases."""
import pytest

from teaql.core.entity import EntityKey
from teaql.runtime import UserContext
from teaql.runtime.audit import MutationAuditKind, RawAuditEvent


class Recorder:
    def __init__(self, events, broken=False):
        self.events, self.broken = events, broken

    def start(self, operation):
        if self.broken:
            raise RuntimeError('optional adapter unavailable')
        self.events.append(('start', operation.name))
        events = self.events
        class Scope:
            def success(self, attributes=None):
                events.append(('success', operation.name))

            def failure(self, error):
                events.append(('failure', operation.name, error))
        return Scope()


@pytest.mark.asyncio
@pytest.mark.parametrize('failure', ['none', 'begin', 'work', 'commit', 'audit', 'cleanup', 'adapter'])
async def test_graph_parent_covers_begin_commit_audit_and_cleanup(failure):
    events, original = [], RuntimeError('private provider failure')
    class Provider:
        async def begin(self, context):
            events.append('begin')
            if failure == 'begin':
                raise original
            return self

        async def commit(self, context):
            events.append('commit')
            if failure == 'commit':
                raise original

        async def rollback(self, context):
            events.append('rollback')

    context = UserContext().insert_resource('dataService', Provider())
    context.with_runtime_telemetry(Recorder(events, failure == 'adapter'))
    class Sink:
        def on_safe_event(self, context, event):
            events.append('audit')
            if failure == 'audit':
                raise original
    context.with_app_audit_event_sink(Sink())
    retained = []
    async def work(graph):
        retained.append(graph)
        events.append('work')
        if failure == 'work':
            raise original
        await graph.context.send_audit_event(RawAuditEvent(MutationAuditKind.CREATED, 'CustomerOrder', 1, ()))
        def cleanup():
            events.append('cleanup')
            if failure == 'cleanup':
                raise original
        graph.after_commit(cleanup)
        return 'saved'

    if failure in ('none', 'adapter'):
        assert await context.execute_graph_save(work, comment='save graph') == 'saved'
    else:
        with pytest.raises(RuntimeError) as caught:
            await context.execute_graph_save(work, comment='save graph')
        if failure in ('audit', 'cleanup'):
            assert caught.value.committed is True
            assert original in caught.value.failures
        else:
            assert caught.value is original
        assert events[-1] == ('failure', 'graph.save', caught.value)
    if failure != 'adapter':
        assert events[0] == ('start', 'graph.save')
        assert sum(event == ('start', 'graph.save') for event in events) == 1
        assert sum(isinstance(event, tuple) and event[:2] in (
            ('success', 'graph.save'), ('failure', 'graph.save')) for event in events) == 1
    if retained:
        with pytest.raises(RuntimeError, match='no longer writable'):
            retained[0].scope(EntityKey('CustomerOrder', 1))
    assert not context._graph_save_lock.locked()
    assert context._graph_save_guard.get() is None
    if failure in ('none', 'audit', 'cleanup', 'adapter'):
        assert 'commit' in events and 'rollback' not in events
        assert events.index('commit') < events.index('audit') < events.index('cleanup')


@pytest.mark.asyncio
async def test_rejected_root_starts_no_span_and_no_transaction():
    events = []
    context = UserContext().with_runtime_telemetry(Recorder(events))
    for comment in (None, '', ' \t'):
        with pytest.raises(ValueError):
            await context.execute_graph_save(lambda graph: None, comment=comment)
    assert events == []
