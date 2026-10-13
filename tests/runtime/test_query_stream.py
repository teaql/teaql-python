import asyncio
from contextvars import ContextVar
from types import SimpleNamespace
import pytest

from teaql.core.query import SelectQuery
from teaql.data_service import QueryRequest
from teaql.runtime import UserContext
from teaql.runtime.query_stream import execute_typed_stream


active = ContextVar('test_stream_active', default=None)


class Recorder:
    def __init__(self):
        self.events = []
    def start(self, operation):
        events = self.events
        events.append(('start', operation.name))
        class Scope:
            token = active.set(operation.name)
            def activate(self):
                if self.token is None:
                    self.token = active.set(operation.name)
            def deactivate(self):
                if self.token is not None:
                    token, self.token = self.token, None
                    active.reset(token)
            def success(self, attributes=None):
                events.append(('success', operation.name, attributes))
                self.deactivate()
            def cancelled(self, attributes=None):
                events.append(('cancelled', operation.name, attributes))
                self.deactivate()
            def failure(self, error):
                events.append(('failure', operation.name, error))
                self.deactivate()
        return Scope()


class Cursor:
    def __init__(self):
        self.closed = self.polled = 0
    def __aiter__(self):
        return self
    async def __anext__(self):
        assert active.get() == 'School.stream'
        self.polled += 1
        if self.polled > 1:
            raise StopAsyncIteration
        return SimpleNamespace(rows=[{'id': 1}, {'id': 2}])
    async def aclose(self):
        assert active.get() == 'School.stream'
        self.closed += 1


def fixture(cursor=None, hydrate=lambda row: row):
    telemetry = Recorder()
    cursor = cursor or Cursor()
    class Service:
        calls = 0
        def query_stream(self, context, request, chunk_size):
            self.calls += 1
            return cursor
    service = Service()
    context = UserContext().with_runtime_telemetry(telemetry).insert_resource('dataService', service)
    request = QueryRequest(SelectQuery('School'), _comment='bounded stream', _purpose='test ownership')
    return execute_typed_stream(context, request, hydrate, 2), telemetry, cursor, service


@pytest.mark.asyncio
async def test_lazy_close_and_poll_scoped_activation():
    stream, telemetry, cursor, service = fixture()
    assert telemetry.events == [] and service.calls == 0
    await stream.aclose()
    assert telemetry.events == [] and service.calls == 0 and cursor.closed == 0
    stream, telemetry, cursor, service = fixture()
    assert (await anext(stream))['id'] == 1
    assert active.get() is None
    assert [row async for row in stream] == [{'id': 2}]
    assert active.get() is None and cursor.closed == 1
    assert telemetry.events[-1] == ('success', 'School.stream', {'teaql.result.cardinality': 2})


@pytest.mark.asyncio
async def test_early_close_counts_delivered_not_prefetched_and_is_once_only():
    stream, telemetry, cursor, service = fixture()
    await anext(stream)
    await stream.aclose()
    await stream.aclose()
    assert cursor.closed == 1 and active.get() is None
    assert telemetry.events[-1] == ('cancelled', 'School.stream', {'teaql.result.cardinality': 1})


@pytest.mark.asyncio
async def test_hydration_failure_is_original_and_closes_cursor():
    original = RuntimeError('private hydration error')
    def hydrate(row):
        raise original
    stream, telemetry, cursor, service = fixture(hydrate=hydrate)
    with pytest.raises(RuntimeError) as caught:
        await anext(stream)
    assert caught.value is original and cursor.closed == 1 and active.get() is None
    assert telemetry.events[-1] == ('failure', 'School.stream', original)


@pytest.mark.asyncio
async def test_cleanup_failure_after_exhaustion_fails_root_and_restores_owner():
    original = RuntimeError('private cleanup error')
    class Broken(Cursor):
        async def aclose(self):
            raise original
    stream, telemetry, cursor, service = fixture(cursor=Broken())
    with pytest.raises(RuntimeError) as caught:
        [row async for row in stream]
    assert caught.value is original and active.get() is None
    assert telemetry.events[-1] == ('failure', 'School.stream', original)


@pytest.mark.asyncio
async def test_cancelled_poll_closes_cursor_and_preserves_cancellation():
    entered = asyncio.Event()
    class Waiting(Cursor):
        async def __anext__(self):
            entered.set()
            await asyncio.Event().wait()
    stream, telemetry, cursor, service = fixture(cursor=Waiting())
    task = asyncio.create_task(anext(stream))
    await entered.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert cursor.closed == 1 and active.get() is None
    assert telemetry.events[-1] == ('cancelled', 'School.stream', {'teaql.result.cardinality': 0})
