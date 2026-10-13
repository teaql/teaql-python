"""Lazy typed stream ownership and delivered-row accounting for generated Q."""
import asyncio
from contextvars import ContextVar

from .telemetry import RuntimeOperation, start_runtime_operation


_active_stream = ContextVar('teaql_typed_stream_execution', default=None)


def stream_observation(context, service, request):
    active = _active_stream.get()
    if active is None:
        return None
    owner, task = active
    if (owner.context is context and owner.service is service
            and owner.request._invocation_identity is request._invocation_identity
            and task is asyncio.current_task()):
        return owner
    return None


def execute_typed_stream(context, request, hydrate, chunk_size):
    request.validate()
    if type(chunk_size) is not int or chunk_size <= 0:
        raise ValueError('chunk_size must be positive')
    service = context.require_resource('dataService')
    return TypedStream(context, service, request.with_query(request.query), hydrate, chunk_size)


class TypedStream:
    def __init__(self, context, service, request, hydrate, chunk_size):
        self.context, self.service, self.request = context, service, request
        self.hydrate, self.chunk_size = hydrate, chunk_size
        self.cursor = self.scope = None
        self.scopes = []
        self.rows = iter(())
        self.delivered = 0
        self.closed = False
        self.busy = False

    def __aiter__(self):
        return self

    def bind_scope(self, scope):
        self.scopes.append(scope)

    def _activate(self):
        if self.scope is None:
            self.scope = start_runtime_operation(self.context.runtime_telemetry(), RuntimeOperation(
                'query', self.request.query.entity + '.stream', {'teaql.entity.type': self.request.query.entity}))
            self.scopes.append(self.scope)
        else:
            for scope in self.scopes:
                scope.activate()
        return _active_stream.set((self, asyncio.current_task()))

    def _deactivate(self, token):
        for scope in reversed(self.scopes):
            scope.deactivate()
        _active_stream.reset(token)

    async def _close_cursor(self):
        if self.cursor is not None:
            cursor, self.cursor = self.cursor, None
            close = getattr(cursor, 'aclose', None)
            if close is not None:
                await close()

    async def __anext__(self):
        if self.closed:
            raise StopAsyncIteration
        if self.busy:
            raise RuntimeError('stream already has an active poll or close')
        self.busy = True
        token = self._activate()
        try:
            if self.cursor is None:
                self.cursor = self.service.query_stream(self.context, self.request, self.chunk_size)
            while True:
                raw = next(self.rows, None)
                if raw is not None:
                    value = self.hydrate(raw)
                    self.delivered += 1
                    return value
                chunk = await anext(self.cursor)
                self.rows = iter(chunk.rows)
        except StopAsyncIteration:
            self.closed = True
            try:
                await self._close_cursor()
            except BaseException as error:
                self.scope.failure(error)
                raise
            self.scope.success({'teaql.result.cardinality': self.delivered})
            raise
        except BaseException as error:
            self.closed = True
            try:
                await self._close_cursor()
            except BaseException:
                pass  # Preserve the original source/hydration/cancellation error.
            if isinstance(error, asyncio.CancelledError):
                self.scope.cancelled({'teaql.result.cardinality': self.delivered})
            else:
                self.scope.failure(error)
            raise
        finally:
            self._deactivate(token)
            self.busy = False

    async def aclose(self):
        if self.closed:
            return
        if self.busy:
            raise RuntimeError('stream already has an active poll or close')
        self.closed = True
        if self.scope is None:
            return  # Unpolled streams create no SDK span, SQL or driver cursor.
        self.busy = True
        token = self._activate()
        try:
            await self._close_cursor()
            self.scope.cancelled({'teaql.result.cardinality': self.delivered})
        except BaseException as error:
            self.scope.failure(error)
            raise
        finally:
            self._deactivate(token)
            self.busy = False
