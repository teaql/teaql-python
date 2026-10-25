"""Invocation-local list execution shared by generated libraries and providers."""
from __future__ import annotations

import asyncio
import math
from contextvars import ContextVar
from copy import deepcopy
from typing import Any, Awaitable, Callable, TypeVar

from teaql.core.list import SmartList
from teaql.core.query import AggregateFunction
from teaql.data_service import QueryRequest
from .telemetry import RuntimeOperation, observe_runtime_operation

T = TypeVar('T')

# This is a task-local execution capability, not a Context-owned query frame or
# mutation ledger. A different service, UserContext, invocation or task does not
# inherit ownership merely because an OTEL span is currently active.
_query_owner: ContextVar[tuple | None] = ContextVar('teaql_query_execution_owner', default=None)


async def observe_query_operation(context, service, request: QueryRequest,
                                  work: Callable[[], Awaitable[T]],
                                  completion: Callable[[T], dict]) -> T:
    request.validate()
    owner = (service, context, request._invocation_identity, asyncio.current_task())
    active = _query_owner.get()
    if active is not None and all(left is right for left, right in zip(active, owner)):
        return await work()
    token = _query_owner.set(owner)
    try:
        telemetry = context.runtime_telemetry() if context is not None else None
        return await observe_runtime_operation(
            telemetry, RuntimeOperation('query', f'{request.root_request.query.entity}.list', {
                'teaql.entity.type': request.root_request.query.entity,
            }), work, completion)
    finally:
        _query_owner.reset(token)


async def execute_typed_list(context, request: QueryRequest, hydrate: Callable[[dict], T],
                             *, count_operation=None, count_alias: str | None = None) -> SmartList[T]:
    """Generated bridge: trusted policy and request snapshot precede this call.

    Do not install SDK spans in generated entities. Count is explicit metadata;
    the provider handles relations/facets and hydration stays inside this root.
    """
    root = request.with_query(request.query)
    service = context.require_resource('dataService')

    async def execute():
        if root.query.group_by_items:
            raise ValueError('grouped projections require a separate projection result boundary')
        total = None
        row_query = root.query
        if count_operation is None:
            row_result = await service.query(context, root)
        else:
            alias = count_alias if count_alias is not None else '__teaql_total'
            query = deepcopy(root.query)
            query.aggregates = [item for item in query.aggregates
                                if not (item.function == AggregateFunction.Count and item.alias == count_alias)]
            row_query = query
            rows_request = root.with_query(query)

            async def count():
                result = await service.query(context, root.for_count(count_alias, count_operation))
                value = result.rows[0].get(alias) if len(result.rows) == 1 else None
                if (isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0
                        or isinstance(value, float) and not math.isfinite(value) or int(value) != value):
                    raise RuntimeError('dataService did not return an exact list count')
                return int(value)

            if root.query.id_set_pagination is not None:
                row_result = await service.query(context, rows_request)
                retained, accuracy = context.id_set_count()
                total = retained if accuracy == 'EXACT' else await count()
            else:
                total = await count()
                row_result = await service.query(context, rows_request)
        aggregations = {count_alias: total} if count_alias is not None else {}
        if row_query.aggregates:
            if len(row_result.rows) != 1:
                raise RuntimeError('dataService did not return one scalar aggregation result')
            values = row_result.rows[0]
            aggregations.update({item.alias: values[item.alias] for item in row_query.aggregates
                                 if item.alias in values})
            rows = ()
        else:
            rows = (hydrate(row) for row in row_result.rows)
        return SmartList(rows, facets=row_result.facets, total_count=total, aggregations=aggregations)

    return await observe_query_operation(context, service, root, execute,
                                         lambda result: {'teaql.result.cardinality': len(result)})
