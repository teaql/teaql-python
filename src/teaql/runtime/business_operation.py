"""Explicit single-database business operations, initially qualified on SQLite.

Graphs keep independent ledgers. Only saves made through the context passed to
the registered handler participate in this operation's one database transaction.
"""

from __future__ import annotations

import asyncio
from copy import copy
from dataclasses import dataclass
import hashlib
from inspect import isawaitable
import json
from types import MappingProxyType
from typing import Callable, Mapping

from teaql.core.request_intent import MutationIntent
from .graph_session import GraphCommittedError, GraphMutationSession
from .i18n import CheckException


class BusinessOperationError(RuntimeError):
    def __init__(self, code, message, *, outcome="not_started"):
        self.code = code
        self.outcome = outcome
        super().__init__(message)


class BusinessOperationCommitUnknown(BusinessOperationError):
    def __init__(self):
        super().__init__(
            "OPERATION_COMMIT_UNKNOWN",
            "Commit outcome is unknown; recover using the original idempotency key",
            outcome="unknown",
        )


def _json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False)


@dataclass(frozen=True)
class BusinessOperation:
    """Trusted registration, not a descriptor supplied by a remote caller.

    ``parameters`` is the complete, scalar-only v1 business input schema. Every
    field participates in the fingerprint. Authorization is mandatory and runs
    on every invocation, including replay. Successful results must be JSON data.
    """

    name: str
    version: str
    root_type: str
    parameters: Mapping[str, type]
    authorize: Callable
    prepare: Callable
    handler: Callable
    validate: Callable

    def __post_init__(self):
        for value in (self.name, self.version, self.root_type):
            if not isinstance(value, str) or not value.strip() or len(value) > 128:
                raise ValueError("operation name, version and root type are required (max 128)")
        schema = dict(self.parameters)
        if (not schema or any(not isinstance(key, str) or not key or
                              kind not in (str, int, bool) for key, kind in schema.items())):
            raise ValueError("v1 parameters require named str, int or bool fields")
        if not all(callable(value) for value in (self.authorize, self.prepare, self.handler, self.validate)):
            raise TypeError("authorization, preparation, handler and invariant validator are required")
        object.__setattr__(self, "parameters", MappingProxyType(schema))

    async def execute(self, context, *, key: str, parameters: Mapping, comment: str):
        intent = MutationIntent(comment)
        if not isinstance(key, str) or not key.strip() or len(key) > 256:
            raise BusinessOperationError("OPERATION_INPUT_INVALID", "idempotency key required (max 256)")
        if (not isinstance(parameters, Mapping) or set(parameters) != set(self.parameters)
                or any(type(parameters[name]) is not kind for name, kind in self.parameters.items())):
            raise BusinessOperationError("OPERATION_INPUT_INVALID", "parameters must match the complete registered schema")
        # Values are scalars; freeze caller input before the first await.
        params = MappingProxyType(dict(parameters))
        root = context.require_active_root(self.root_type)
        if type(root.id) is not int or root.id <= 0:
            raise BusinessOperationError("OPERATION_SCOPE_INVALID", "active root must have a valid identity")
        if context._graph_session is not None or context._business_operation is not None:
            raise BusinessOperationError("OPERATION_NESTING_UNSUPPORTED", "business operations cannot nest")
        guard = context._graph_save_guard.get()
        if guard is not None and guard['active']:
            raise BusinessOperationError("OPERATION_NESTING_UNSUPPORTED", "an explicit operation cannot enter an active graph")
        permission = self.authorize(context, params)
        if isawaitable(permission):
            permission = await permission
        if permission is not True:
            raise BusinessOperationError("OPERATION_DENIED", "business operation authorization denied")
        fingerprint = hashlib.sha256(_json({"version": self.version, "parameters": dict(params)}).encode()).hexdigest()
        scope = _json([root.entity, root.id])
        provider = context.require_resource("dataService")
        begin = getattr(provider, "begin_business_operation", None)
        if not callable(begin):
            raise BusinessOperationError("OPERATION_UNSUPPORTED", "provider does not support business operations")
        async with context._graph_save_lock:
            transaction = await begin(context)
            session = _BusinessOperationSession(context, transaction)
            guard = {'active': True}
            token = context._graph_save_guard.set(guard)
            try:
                stored = await transaction.lookup_business_result(scope, self.name, key)
                if stored is not None:
                    if stored["fingerprint"] != fingerprint:
                        raise BusinessOperationError("IDEMPOTENCY_CONFLICT", "same key has different business parameters or operation version")
                    # A replay has no writes. End its read transaction before return.
                    replay = json.loads(stored["result"])
                    await transaction.rollback(session.context)
                    return replay
                before = await self.prepare(session.context, params)
                result = await self.handler(session.context, params)
                session.require_active()
                if session.failed:
                    raise BusinessOperationError("OPERATION_ROLLBACK_ONLY", "a participating graph failed; the operation cannot commit")
                if await self.validate(session.context, params, before, result) is not True:
                    raise BusinessOperationError("OPERATION_INVARIANT_FAILED", "registered business postconditions rejected the operation")
                session.require_active()
                if session.failed:
                    raise BusinessOperationError("OPERATION_ROLLBACK_ONLY", "validation cannot hide a failed graph")
                encoded = _json(result)
                await transaction.store_business_result(scope, self.name, key, fingerprint, encoded,
                                                       context.user_identifier())
                try:
                    await transaction.commit(session.context)
                except BaseException as error:
                    # A provider exception does not prove COMMIT did not happen.
                    raise BusinessOperationCommitUnknown() from error
            except BaseException as error:
                rollback_failed = False
                recovery_failures = []
                try:
                    await transaction.rollback(session.context)
                except BaseException:
                    rollback_failed = True
                for graph in reversed(session.graphs):
                    recovery_failures.extend(await graph.rolled_back())
                if isinstance(error, BusinessOperationError) and error.outcome != "unknown":
                    error.outcome = "unknown" if rollback_failed else "rolled_back"
                if isinstance(error, BusinessOperationError):
                    error.state_recovery_failures = tuple(recovery_failures)
                if isinstance(error, Exception) and not isinstance(error, BusinessOperationError):
                    failure = BusinessOperationError(
                        "OPERATION_EXECUTION_FAILED", str(error),
                        outcome="unknown" if rollback_failed else "rolled_back",
                    )
                    failure.state_recovery_failures = tuple(recovery_failures)
                    raise failure from error
                raise
            else:
                failures = []
                for graph in session.graphs:
                    try:
                        await graph.committed()
                    except GraphCommittedError as error:
                        failures.extend(error.failures)
                if failures:
                    raise GraphCommittedError(failures)
                # Detach the response as well as persisting its original snapshot.
                return json.loads(encoded)
            finally:
                session.close()
                guard['active'] = False
                context._graph_save_guard.reset(token)


class _BusinessOperationSession:
    def __init__(self, context, transaction):
        self.transaction = transaction
        self.graphs = []
        self.failed = False
        self.active = True
        self.saving = False
        self.owner = asyncio.current_task()
        self.context = copy(context)
        self.context._resources = dict(context._resources)
        self.context._resources['dataService'] = transaction
        self.context._business_operation = self

    def require_active(self):
        if not self.active or asyncio.current_task() is not self.owner:
            raise BusinessOperationError("OPERATION_CONTEXT_INVALID", "operation context is closed or used by another task")

    async def save_graph(self, work, *, comment, prepare=None):
        self.require_active()
        if self.saving or self.failed:
            raise BusinessOperationError("OPERATION_ROLLBACK_ONLY", "operation graph is reentrant or has already failed")
        self.saving = True
        try:
            graph = GraphMutationSession(self.context, self.transaction, MutationIntent(comment))
            self.graphs.append(graph)
            try:
                if prepare is not None:
                    graph._preparing = True
                    try:
                        await prepare(graph)
                    finally:
                        graph._preparing = False
                result = await work(graph)
                graph.context._mutation_policy.ensure_graph_complete()
                return result
            except CheckException as failure:
                failure.refresh_presentation(graph.context.render_checker_graph_results(
                    failure.violations, graph._checker_messages,
                    (graph._checker_messages.model, graph._checker_origin)))
                raise
        except BaseException:
            self.failed = True
            raise
        finally:
            self.saving = False

    def close(self):
        self.active = False
        for graph in self.graphs:
            graph.close()
