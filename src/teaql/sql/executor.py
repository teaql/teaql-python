from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, AsyncIterator
from copy import deepcopy
from datetime import datetime
import asyncio
import hashlib
import logging
import time
import threading
from array import array
from dataclasses import fields, is_dataclass, replace
from enum import Enum
from teaql.data_service import (
    DataServiceExecutor, QueryExecutor, MutationExecutor,
    DataServiceCapabilities, QueryRequest, QueryResult,
    MutationRequest, MutationResult, ExecutionMetadata,
    DataServiceOperation, StreamChunk
)
from teaql.core.mutation import (
    InsertCommand, UpdateCommand, DeleteCommand, RecoverCommand, TraceNode
)
from .types import CompiledQuery, SqlCompileError
from .dialect import SqlDialect
from teaql.core.expr import (
    AndExpr, BetweenExpr, BinaryExpr, BinaryOp, FunctionExpr, IsNotNullExpr,
    IsNullExpr, NotExpr, OrExpr, SubQueryExpr, ColumnExpr, ValueExpr,
)
from teaql.core.query import Aggregate, AggregateFunction, SelectQuery
from teaql.core.value import Value
from teaql.core.trace import canonical_sql_trace_path, physical_readback_path, trace_name
from teaql.runtime.telemetry import RuntimeOperation, observe_runtime_operation, start_runtime_operation
from teaql.runtime.context import RetainedIdSet

_id_set_build_locks = {}
_id_set_build_locks_guard = threading.RLock()


class _QueryWithLogIntent(QueryRequest):
    """Invocation-local compiler plumbing, excluded from dataclass/wire fields."""
    def __init__(self, query, trace_chain, comment, purpose, source, origin_entity=None, assembly=None):
        super().__init__(query, trace_chain, comment, purpose, _origin_entity=origin_entity)
        self._log_intent_source = source
        self._relation_assembly = assembly


class _RelationAssembly:
    """One derived load owns scalar keys; never attach them to result records."""
    def __init__(self, field):
        self.field = field
        self.keys = {}

    def capture(self, rows):
        self.keys = {id(row): row.get(self.field) for row in rows}

    def key(self, row):
        # Hydration mutates these same row dictionaries. Reordering (ID-set
        # paging) is fine, but a replacement must not silently drop membership.
        return self.keys[id(row)]


def _intent_bindings(compiled, request):
    # Resolve each source's policy before flattening: credential detection and
    # malformed-policy handling depend on the original statement, not the child.
    from teaql.runtime.log_privacy import _binding_policies
    inherited = getattr(request, '_log_intent_source', None)
    sources = [inherited, compiled] if inherited is not None else [compiled]
    return CompiledQuery('', [deepcopy(value) for source in sources for value in source.params],
                         parameter_log_policies=[policy for source in sources
                                                 for policy in _binding_policies(source)],
                         sql_origin='generated')


class _NoopContextManager:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

def _canonical_id_set_value(value):
    if isinstance(value, Value):
        return ("Value", str(value._type_hint), _canonical_id_set_value(value.val))
    if isinstance(value, Enum):
        return (type(value).__name__, value.name)
    if is_dataclass(value):
        return (type(value).__name__, tuple(
            (item.name, _canonical_id_set_value(getattr(value, item.name)))
            for item in fields(value)))
    if isinstance(value, dict):
        return tuple(sorted((str(key), _canonical_id_set_value(item)) for key, item in value.items()))
    if isinstance(value, (list, tuple)):
        return tuple(_canonical_id_set_value(item) for item in value)
    if isinstance(value, (str, int, float, bool, type(None))):
        return value
    return (type(value).__name__, str(value))

class SqlTransport(ABC):
    @abstractmethod
    async def fetch_all_sql(self, query: CompiledQuery) -> List[Dict[str, Any]]:
        pass
        
    @abstractmethod
    async def execute_sql(self, query: CompiledQuery) -> int:
        pass

    async def stream_sql(self, query: CompiledQuery, chunk_size: int) -> AsyncIterator[List[Dict[str, Any]]]:
        raise NotImplementedError("streaming query is not supported by this transport")

class SqlTransaction(ABC):
    @abstractmethod
    async def commit_sql(self) -> None:
        pass
        
    @abstractmethod
    async def rollback_sql(self) -> None:
        pass

class SqlTransactionTransport(SqlTransport):
    @abstractmethod
    async def begin_sql(self) -> 'SqlTransactionTransportTx':
        pass

class SqlTransactionTransportTx(SqlTransport, SqlTransaction):
    pass

class SqlExecutorError(Exception):
    pass

class CompileError(SqlExecutorError):
    def __init__(self, error: SqlCompileError):
        super().__init__(f"SQL compile error: {error}")
        self.error = error

class TransportError(SqlExecutorError):
    def __init__(self, error: Exception):
        super().__init__(f"Transport error: {error}")
        self.error = error

class SchemaProvider(ABC):
    @abstractmethod
    def get_entity(self, name: str) -> Optional[Any]:
        pass

class SqlDataServiceExecutor(QueryExecutor, MutationExecutor):
    MAX_ID_ALLOCATION_ATTEMPTS = 100

    def __init__(self, dialect: SqlDialect, transport: SqlTransport, schema_provider: SchemaProvider):
        self.dialect = dialect
        self.transport = transport
        self.schema_provider = schema_provider

    def _backend_name(self) -> str:
        kind = self.dialect.kind()
        name = getattr(kind, 'name', str(kind)).lower()
        return 'postgres' if name == 'postgresql' else name

    def _query_intent_bindings(self, compiled, request):
        """Capture declared descendant bindings before any physical parent log.

        Compile copies only for policy provenance: no SQL, list preparation,
        query-builder mutation or Context-owned redaction state.
        """
        from teaql.runtime.log_privacy import _binding_policies
        source = _intent_bindings(compiled, request)
        pending = [(request.query, request.query.entity)]
        for original in getattr(request, '_log_intent_queries', ()):
            descriptor = self.schema_provider.get_entity(original.entity)
            if descriptor is None:
                continue
            candidate = deepcopy(original)
            self._resolve_subquery_entities(candidate.filter_expr)
            bindings = self.dialect.compile_select(descriptor, candidate)
            source.params.extend(deepcopy(bindings.params))
            source.parameter_log_policies.extend(_binding_policies(bindings))
            pending.append((original, original.entity))
        visited = set()
        while pending:
            query, entity = pending.pop()
            key = (id(query), entity)
            if key in visited:
                continue
            visited.add(key)
            descriptor = self.schema_provider.get_entity(entity)
            children = []
            for relation in query.relations:
                model = descriptor.relation_by_name(relation.name) if descriptor else None
                if relation.query is not None and model is not None:
                    children.append((relation.query, model.target_entity))
            for aggregate in query.relation_aggregates:
                model = descriptor.relation_by_name(aggregate.relation_name) if descriptor else None
                if model is not None:
                    children.append((aggregate.query, model.target_entity))
            for facet in query.facets:
                children.append((facet.query, facet.query.entity))
            for child, entity in children:
                if (id(child), entity) in visited:
                    continue
                child_descriptor = self.schema_provider.get_entity(entity)
                if child_descriptor is None:
                    continue  # execution still owns missing-schema diagnostics
                candidate = deepcopy(child)
                candidate.entity = entity
                self._resolve_subquery_entities(candidate.filter_expr)
                bindings = self.dialect.compile_select(child_descriptor, candidate)
                source.params.extend(deepcopy(bindings.params))
                source.parameter_log_policies.extend(_binding_policies(bindings))
                pending.append((child, entity))
        return source

    def _sync_generated_schema(self, context: 'UserContext') -> None:
        register = getattr(self.schema_provider, "register_entity", None)
        if callable(register) and context is not None:
            for entity in context.all_entities():
                register(entity)

    async def close(self) -> None:
        close = getattr(self.transport, "close", None)
        if callable(close):
            result = close()
            if hasattr(result, "__await__"):
                await result

    def _resolve_subquery_entities(self, expr) -> None:
        if expr is None:
            return
        if isinstance(expr, SubQueryExpr):
            if isinstance(expr.entity, str):
                descriptor = self.schema_provider.get_entity(expr.entity)
                if descriptor is None:
                    raise CompileError(SqlCompileError(
                        f"unknown subquery entity: {expr.entity}"))
                expr.entity = descriptor
            self._resolve_subquery_entities(getattr(expr.query, "filter_expr", None))
            return
        if isinstance(expr, (AndExpr, OrExpr)):
            for child in expr.exprs:
                self._resolve_subquery_entities(child)
            return
        if isinstance(expr, BinaryExpr):
            self._resolve_subquery_entities(expr.left)
            self._resolve_subquery_entities(expr.right)
            return
        if isinstance(expr, BetweenExpr):
            self._resolve_subquery_entities(expr.expr)
            self._resolve_subquery_entities(expr.lower)
            self._resolve_subquery_entities(expr.upper)
            return
        if isinstance(expr, (IsNullExpr, IsNotNullExpr, NotExpr)):
            self._resolve_subquery_entities(expr.expr)
            return
        if isinstance(expr, FunctionExpr):
            for child in expr.args:
                self._resolve_subquery_entities(child)

    def capabilities(self) -> DataServiceCapabilities:
        return DataServiceCapabilities(
            query=True,
            mutation=True,
            transaction=False, # Could be determined from transport
            schema=True,
            id_generation=True,
            batch_mutation=True,
            returning=False
        )

    def _record_statement(self, context, request, compiled, started_at, operation,
                          outcome, result_count=None, affected_rows=None, intent_privacy=None):
        """Project through context; never attach driver exceptions to diagnostics."""
        query = operation == DataServiceOperation.Query
        entity = request.query.entity if query else request._data.entity
        comment = request._comment if query else getattr(request, 'comment', None)
        if not query and callable(comment):
            comment = comment()
        provider = self._backend_name()
        sql_operation = 'select' if query else operation.name.lower()
        if query:
            trace_source = [TraceNode(kind='comment', name=request.origin_entity, comment=comment),
                            TraceNode(kind='purpose', name=request.origin_entity, comment=request._purpose),
                            *request.trace_chain]
        else:
            chain = [*request.mutation_lineage, *request.trace_chain()]
            root = next((trace_name(node) for node in chain if trace_name(node).strip()), entity)
            target_id = getattr(request._data, 'id', None)
            if target_id is None:
                target_id = getattr(request._data, 'values', {}).get('id')
            target_id = getattr(target_id, 'val', target_id)
            trace_source = [TraceNode(kind='auditReason', name=root, comment=comment),
                            *chain, TraceNode(kind='entity', name=entity, entity_id=target_id)]
        metadata = ExecutionMetadata(
            backend=provider, operation=operation, started_at=started_at,
            ended_at=datetime.now(), execution_outcome=outcome,
            parameterized_sql=compiled.sql, parameters=list(compiled.params),
            parameter_log_policies=compiled.parameter_log_policies,
            sql_origin=compiled.sql_origin, database_kind=self.dialect.kind(), debug_query='',
            result_count=result_count, affected_rows=affected_rows,
            comment=comment, purpose=request._purpose if query else None,
            audit_reason=None if query else comment,
            trace_chain=canonical_sql_trace_path(trace_source, provider, sql_operation),
            mutation_lineage=() if query else request.mutation_lineage,
        )
        if context is not None:
            try:
                source = getattr(request, '_log_intent_source', None) if query else None
                target_id = None
                if not query:
                    target_id = getattr(request._data, 'id', None)
                    if target_id is None:
                        descriptor = self.schema_provider.get_entity(entity)
                        id_property = next((prop for prop in descriptor.properties
                            if getattr(prop, '_is_id', False) or getattr(prop, 'is_id_val', False)), None)
                        if id_property is not None:
                            target_id = getattr(request._data, 'values', {}).get(id_property.name)
                if source is None and target_id is None and intent_privacy is None:
                    context.record_metadata_log(metadata)
                else:
                    context._record_metadata_log(metadata, intent_source=source,
                        intent_values=() if target_id is None else (target_id,),
                        intent_privacy=intent_privacy)
            except Exception:
                # A broken diagnostic destination must not replace an in-flight
                # driver failure, cancellation or generator close.
                if outcome == 'success':
                    raise
        return metadata

    def query_stream(self, context, request: QueryRequest, chunk_size: int):
        """Own the request at cursor creation; opening the driver stays lazy."""
        request.validate()
        if chunk_size <= 0:
            raise ValueError("chunk_size must be positive")
        owned = request.with_query(request.query)
        return self._query_stream(context, owned, chunk_size)

    async def _query_stream(self, context, request: QueryRequest, chunk_size: int):
        if (request.query.relations or request.query.relation_aggregates or request.query.child_enhancements
                or request.query.object_group_bys or request.query.facets):
            raise ValueError(
                "streaming relation or aggregate enhancement is not supported; "
                "stream a root query or use execute_for_list"
            )
        entity_desc = self.schema_provider.get_entity(request.query.entity)
        if not entity_desc:
            raise CompileError(SqlCompileError(f"unknown entity: {request.query.entity}"))
        self._resolve_subquery_entities(request.query.filter_expr)
        compiled = self.dialect.compile_select(entity_desc, request.query)
        request._log_intent_source = self._query_intent_bindings(compiled, request)
        pending = None
        index = 0
        delivered = 0
        started_at = datetime.now()
        outcome = 'cancelled'
        stream = self.transport.stream_sql(compiled, chunk_size)
        try:
            async for rows in stream:
                if pending is not None:
                    delivered += len(pending)
                    yield StreamChunk(pending, index, False)
                    index += 1
                pending = rows
            if pending is not None:
                delivered += len(pending)
                yield StreamChunk(pending, index, True)
            outcome = 'success'
        except (asyncio.CancelledError, GeneratorExit):
            outcome = 'cancelled'
            raise
        except BaseException:
            outcome = 'failure'
            raise
        finally:
            try:
                close = getattr(stream, 'aclose', None)
                if close is not None:
                    await close()
            except BaseException:
                if outcome == 'success':
                    outcome = 'failure'
                    raise
                # Preserve the error/close already being propagated.
            finally:
                self._record_statement(context, request, compiled, started_at,
                                       DataServiceOperation.Query, outcome, result_count=delivered)

    async def query(self, context: 'UserContext', request: QueryRequest) -> QueryResult:
        request.validate()
        telemetry = context.runtime_telemetry() if context is not None else None
        return await observe_runtime_operation(
            telemetry,
            RuntimeOperation("query", f"{request.query.entity}.list", {
                "teaql.entity.type": request.query.entity,
            }),
            lambda: self._query(context, request),
            lambda result: {"teaql.result.cardinality": len(result.rows)},
        )

    async def _query(self, context: 'UserContext', request: QueryRequest) -> QueryResult:
        request.validate()
        assembly = getattr(request, '_relation_assembly', None)
        request = request.with_query(request.query)
        self._sync_generated_schema(context)
        request.query.prepare_for_list()
        execution_query, retained_order, retained_empty = await self._prepare_id_set_page(context, request.query)
        if retained_empty:
            now = datetime.now()
            provider = self._backend_name()
            metadata = ExecutionMetadata(
                backend=provider, operation=DataServiceOperation.Query,
                started_at=now, ended_at=now, result_count=0,
                trace_chain=canonical_sql_trace_path(
                    [TraceNode(kind='comment', name=request.origin_entity, comment=request._comment),
                     *request.trace_chain], provider, 'select'),
                comment=request._comment, purpose=request._purpose,
            )
            if context is not None:
                context.record_metadata_log(metadata)
            return QueryResult(rows=[], metadata=metadata)
        source = getattr(request, '_log_intent_source', None)
        request = (_QueryWithLogIntent(execution_query, request.trace_chain, request._comment,
                                      request._purpose, source, request.origin_entity) if source is not None else
                   request.with_query(execution_query))
        entity_desc = self.schema_provider.get_entity(request.query.entity)
        if not entity_desc and context:
            entities = context.get_resource("entities")
            if entities:
                for e in entities:
                    if getattr(e, "_name", None) == request.query.entity:
                        entity_desc = e
                        break
        if not entity_desc:
            raise CompileError(SqlCompileError(f"unknown entity: {request.query.entity}"))
        self._resolve_subquery_entities(request.query.filter_expr)
            
        try:
            compiled = self.dialect.compile_select(entity_desc, request.query)
        except SqlCompileError as e:
            raise CompileError(e)

        source = self._query_intent_bindings(compiled, request)
        request._log_intent_source = source
            
        start = datetime.now()
        try:
            telemetry = context.runtime_telemetry() if context is not None else None
            rows = await observe_runtime_operation(
                telemetry,
                RuntimeOperation("provider", f"{self.dialect.kind()}.query", {
                    "teaql.provider.kind": str(self.dialect.kind()),
                    "teaql.provider.operation": "query",
                }),
                lambda: self.transport.fetch_all_sql(compiled),
            )
        except BaseException as e:
            self._record_statement(context, request, compiled, start, DataServiceOperation.Query,
                                   'cancelled' if isinstance(e, asyncio.CancelledError) else 'failure')
            if isinstance(e, Exception):
                raise TransportError(e) from e
            raise
        metadata = self._record_statement(context, request, compiled, start,
                                          DataServiceOperation.Query, 'success', result_count=len(rows))

        if assembly is not None:
            assembly.capture(rows)
        # All local identities are captured before aggregate aliases or sibling
        # hydration can replace record fields.
        parent_keys = {relation.local_key: [row.get(relation.local_key) for row in rows]
                       for load in request.query.relations
                       if (relation := entity_desc.relation_by_name(load.name)) is not None}
        # Forward hydration may replace a scalar membership key with an object.
        # Compute related aggregates while those keys still identify their rows.
        await self._enhance_relation_aggregates(context, rows, request, source)
        await self._enhance_relations(context, rows, request, source, parent_keys)
        if retained_order:
            by_id = {int(row["id"]): row for row in rows if row.get("id") is not None}
            rows = [by_id[entity_id] for entity_id in retained_order if entity_id in by_id]

        facets = await self._query_facets(context, request, entity_desc)
        return QueryResult(rows=rows, metadata=metadata, facets=facets)

    async def _query_facets(self, context, request, entity_desc):
        """Count the current membership, then traverse each owned Facet selection."""
        from teaql.core.list import SmartList
        facets = {}
        for facet in getattr(request.query, 'facets', []):
            relation = entity_desc.relation_by_name(facet.relation_name)
            # Legacy numeric partitions still work, but only model metadata can
            # identify a relationship or add a logical traversal to the trace.
            member_field = relation.local_key if relation else facet.relation_name
            target_field = relation.foreign_key if relation else 'id'
            if relation and relation.target_entity != facet.query.entity:
                raise CompileError(SqlCompileError(
                    f'facet target differs from relation: {request.query.entity}.{facet.relation_name}'))
            membership_query = deepcopy(request.query)
            membership_query.facets = []
            membership_query.relations = []
            membership_query.relation_aggregates = []
            membership_query.child_enhancements = []
            membership_query.object_group_bys = []
            membership_query.dynamic_properties = []
            membership_query.raw_projections = []
            membership_query.order_by_items = []
            membership_query.slice = None
            membership_query.partition_by = None
            membership_query.projection = []
            membership_query.expr_projection = []
            membership_query.aggregates = [Aggregate(
                AggregateFunction.Count, "id", "__teaql_facet_count")]
            membership_query.group_by_items = [member_field]
            membership_result = await self._query(context, request.with_query(membership_query))
            member_property = entity_desc.property_by_name(member_field)
            member_column = member_property.column_name_val if member_property else member_field
            counts = {
                str(row[member_column]): int(row["__teaql_facet_count"])
                for row in membership_result.rows
                if row.get(member_column) is not None
            }

            nested_query = deepcopy(facet.query)
            count_aliases = [
                aggregate.alias for aggregate in nested_query.aggregates
                if aggregate.function == AggregateFunction.Count
            ]
            nested_query.aggregates = []
            nested_query.group_by_items = []
            nested_request = request.with_query(nested_query)
            if relation:
                nested_request.trace_chain.append(TraceNode(
                    kind='relation', name=facet.relation_name,
                    comment=f'{request.query.entity}.{facet.relation_name}'))
            nested_result = await self._query(context, nested_request)
            facet_rows = []
            for row in nested_result.rows:
                count = counts.get(str(row.get(target_field)), 0)
                if not facet.include_all_facets and count == 0:
                    continue
                decorated = dict(row)
                for alias in count_aliases or ["count"]:
                    decorated[alias] = count
                facet_rows.append(decorated)
            facets[facet.name] = SmartList(facet_rows, facets=nested_result.facets)
        return facets

    async def _prepare_id_set_page(self, context, query: SelectQuery):
        options = getattr(query, "id_set_pagination", None)
        if context is None or options is None:
            if context is not None:
                context.observe_id_set("ID_SET_DISABLED")
            return query, [], False
        if (query.slice is None or not query.slice.limit or query.partition_by is not None or
                query.aggregates or query.group_by_items or query.raw_sql is not None):
            context.observe_id_set("ID_SET_FALLBACK_UNSUPPORTED_SHAPE")
            return query, [], False
        if any(order.expr is not None or not order.field_name for order in query.order_by_items):
            context.observe_id_set("ID_SET_FALLBACK_NON_DETERMINISTIC_ORDER")
            return query, [], False

        stable = deepcopy(query)
        if not any(order.field_name == "id" for order in stable.order_by_items):
            stable.order_asc("id")
        query_key = self._id_set_query_key(context, stable, options.namespace)
        store = context.id_set_store()
        try:
            retained = store.get(query_key)
        except Exception:
            context.observe_id_set("ID_SET_FALLBACK_STORE_UNAVAILABLE")
            return query, [], False

        plan = "ID_SET_HIT"
        if retained is None:
            loop = asyncio.get_running_loop()
            lock_key = (id(loop), query_key)
            with _id_set_build_locks_guard:
                lock = _id_set_build_locks.setdefault(lock_key, asyncio.Lock())
            async with lock:
                try:
                    retained = store.get(query_key)
                except Exception:
                    context.observe_id_set("ID_SET_FALLBACK_STORE_UNAVAILABLE")
                    return query, [], False
                if retained is None:
                    id_query = deepcopy(stable)
                    id_query.projection = ["id"]
                    id_query.expr_projection = []
                    id_query.relations = []
                    id_query.relation_aggregates = []
                    id_query.child_enhancements = []
                    id_query.facets = []
                    id_query.slice = None
                    id_query.limit(options.max_ids + 1)
                    id_query.id_set_pagination = None
                    id_result = await self._query(context, QueryRequest(id_query))
                    try:
                        ids = array("Q", (int(row["id"]) for row in id_result.rows))
                    except (KeyError, TypeError, ValueError, OverflowError):
                        context.observe_id_set("ID_SET_FALLBACK_UNSUPPORTED_SHAPE")
                        return query, [], False
                    if len(ids) > options.max_ids:
                        context.observe_id_set("ID_SET_FALLBACK_LIMIT_EXCEEDED", "LOWER_BOUND", len(ids))
                        return query, [], False
                    retained = RetainedIdSet(query_key, ids, time.time() + options.ttl_seconds)
                    try:
                        store.put(retained)
                    except Exception:
                        context.observe_id_set("ID_SET_FALLBACK_STORE_UNAVAILABLE")
                        return query, [], False
                    plan = "ID_SET_BUILD"
            with _id_set_build_locks_guard:
                if not lock.locked():
                    _id_set_build_locks.pop(lock_key, None)

        context.observe_id_set(plan, "EXACT", len(retained.ids))
        start = query.slice.offset
        if start >= len(retained.ids):
            return query, [], True
        end = min(start + query.slice.limit, len(retained.ids))
        page_ids = list(retained.ids[start:end])
        page = deepcopy(query)
        page.slice = None
        page.id_set_pagination = None
        page.and_filter(BinaryExpr(
            ColumnExpr("id"), BinaryOp.In,
            ValueExpr(Value.List([Value.from_any(entity_id) for entity_id in page_ids]))))
        return page, page_ids, False

    @staticmethod
    def _id_set_query_key(context, query: SelectQuery, namespace: str) -> str:
        normalized = deepcopy(query)
        normalized.slice = None
        normalized.projection = []
        normalized.expr_projection = []
        normalized.relations = []
        normalized.relation_aggregates = []
        normalized.comment_text = None
        normalized.trace_chain = []
        normalized.id_set_pagination = None
        scope = (namespace, context.user_identifier(), id(context.get_resource("db")),
                 id(context.get_resource("request_policy")),
                 _canonical_id_set_value(context.get_resource("active_root")),
                 _canonical_id_set_value(normalized))
        return "teaql:id-set:v1:" + hashlib.sha256(repr(scope).encode("utf-8")).hexdigest()

    async def _enhance_relations(self, context, parents: List[Dict[str, Any]], request: QueryRequest,
                                 intent_source, parent_keys) -> None:
        query = request.query
        if not parents or not query.relations:
            return
        parent_desc = self.schema_provider.get_entity(query.entity)
        if parent_desc is None:
            raise CompileError(SqlCompileError(f"unknown entity: {query.entity}"))
        for load in query.relations:
            telemetry = context.runtime_telemetry() if context is not None else None
            relation_scope = start_runtime_operation(telemetry, RuntimeOperation(
                "relation_load", f"{query.entity}.{load.name}", {
                    "teaql.entity.type": query.entity,
                    "teaql.relation.name": load.name,
                },
            ))
            try:
                relation = parent_desc.relation_by_name(load.name)
                if relation is None:
                    raise CompileError(SqlCompileError(f"missing relation: {query.entity}.{load.name}"))
                local_keys = parent_keys[relation.local_key]
                parent_ids = [key for key in local_keys if key is not None]
                child_query = deepcopy(load.query) if load.query is not None else SelectQuery(relation.target_entity)
                child_query.entity = relation.target_entity
                # A batched relation SELECT can serve several parents, but its
                # Facet counts belong to each parent's full filtered membership.
                # Preserve the finite selection tree while deferring that work
                # until scalar parent keys have been used to assemble the rows.
                relation_facets = child_query.facets if relation.is_many else []
                if relation_facets:
                    child_query.facets = []
                if relation.foreign_key not in child_query.projection:
                    child_query.projection.append(relation.foreign_key)
                limited = child_query.slice is not None and child_query.slice.limit is not None
                if limited and not any(order.field_name == "id" for order in child_query.order_by_items):
                    child_query.order_asc("id")
                threshold = child_query.top_n_probe_threshold_value
                provider_policy = self.dialect.relation_top_n_policy()
                use_probes = limited and (
                    provider_policy == "always_probe" and threshold is None
                    or threshold is not None and threshold > 0 and len(parent_ids) <= threshold
                )
                child_trace = [*request.trace_chain, TraceNode(
                    kind="relation", name=load.name,
                    comment=f"{query.entity}.{load.name}")]
                if not parent_ids:
                    # Missing/NULL local keys have no relation membership.
                    # Do not compile IN [] or accidentally load orphan rows.
                    children, child_keys = [], []
                    selected_plan, probe_count = "empty", 0
                elif use_probes:
                    children = []
                    child_keys = []
                    for parent_id in parent_ids:
                        probe = deepcopy(child_query)
                        probe.partition_by = None
                        probe.and_filter(BinaryExpr(
                            ColumnExpr(relation.foreign_key), BinaryOp.Eq,
                            ValueExpr(Value.from_any(parent_id))))
                        assembly = _RelationAssembly(relation.foreign_key)
                        loaded = (await self.query(context, _QueryWithLogIntent(
                            probe, child_trace, request._comment, request._purpose, intent_source,
                            request.origin_entity, assembly))).rows
                        children.extend(loaded)
                        child_keys.extend(assembly.key(row) for row in loaded)
                    selected_plan = "bounded_probes"
                    probe_count = len(parent_ids)
                else:
                    values = Value.List([Value.from_any(value) for value in parent_ids])
                    child_query.and_filter(BinaryExpr(
                        ColumnExpr(relation.foreign_key), BinaryOp.In, ValueExpr(values)))
                    if limited:
                        child_query.partition_by_field(relation.foreign_key)
                    assembly = _RelationAssembly(relation.foreign_key)
                    children = (await self.query(context, _QueryWithLogIntent(
                        child_query, child_trace, request._comment, request._purpose, intent_source,
                        request.origin_entity, assembly))).rows
                    child_keys = [assembly.key(row) for row in children]
                    selected_plan = "window" if limited else "batch"
                    probe_count = 0
                for child in children:
                    child.pop("__teaql_partition_rank", None)
                buckets: Dict[Any, List[Dict[str, Any]]] = {}
                for key, child in zip(child_keys, children):
                    buckets.setdefault(key, []).append(child)
                for key, parent in zip(local_keys, parents):
                    related = buckets.get(key, [])
                    if relation_facets:
                        from teaql.core.list import SmartList
                        per_parent = deepcopy(child_query)
                        per_parent.facets = deepcopy(relation_facets)
                        per_parent.and_filter(BinaryExpr(
                            ColumnExpr(relation.foreign_key), BinaryOp.Eq,
                            ValueExpr(Value.from_any(key))))
                        facet_request = _QueryWithLogIntent(
                            per_parent, child_trace, request._comment, request._purpose,
                            intent_source, request.origin_entity)
                        child_desc = self.schema_provider.get_entity(relation.target_entity)
                        related = SmartList(related, facets=await self._query_facets(
                            context, facet_request, child_desc))
                    parent[load.name] = related if relation.is_many else (related[0] if related else None)
                relation_scope.success({
                    "teaql.result.cardinality": len(children),
                    "teaql.relation.parent_count": len(parent_ids),
                    "teaql.relation.per_parent_limit": (
                        child_query.slice.limit if limited else 0),
                    "teaql.relation.configured_probe_threshold": (
                        threshold if threshold is not None else -1),
                    "teaql.relation.selected_plan": selected_plan,
                    "teaql.relation.probe_count": probe_count,
                })
            except BaseException as error:
                relation_scope.failure(error)
                raise

    async def _enhance_relation_aggregates(self, context, parents: List[Dict[str, Any]], request: QueryRequest,
                                          intent_source=None) -> None:
        query = request.query
        if not parents or not query.relation_aggregates:
            return
        parent_desc = self.schema_provider.get_entity(query.entity)
        if parent_desc is None:
            raise CompileError(SqlCompileError(f"unknown entity: {query.entity}"))
        for aggregate in query.relation_aggregates:
            relation = parent_desc.relation_by_name(aggregate.relation_name)
            if relation is None:
                raise CompileError(SqlCompileError(
                    f"missing relation: {query.entity}.{aggregate.relation_name}"))
            parent_ids = [row[relation.local_key] for row in parents if relation.local_key in row]
            if not parent_ids:
                self._attach_empty_relation_aggregate(parents, aggregate, aggregate.query)
                continue
            child_query = deepcopy(aggregate.query)
            child_query.entity = relation.target_entity
            child_query.projection = []
            child_query.expr_projection = []
            child_query.order_by_items = []
            child_query.slice = None
            child_query.relations = []
            child_query.relation_aggregates = []
            if not child_query.aggregates:
                child_query.aggregates = [Aggregate(
                    AggregateFunction.Count, "id", aggregate.alias)]
            if relation.foreign_key not in child_query.group_by_items:
                child_query.group_by_items.append(relation.foreign_key)
            values = Value.List([Value.from_any(value) for value in parent_ids])
            child_query.and_filter(BinaryExpr(
                ColumnExpr(relation.foreign_key), BinaryOp.In, ValueExpr(values)))
            child_trace = [*request.trace_chain, TraceNode(
                kind="relation", name=aggregate.relation_name,
                comment=f"{query.entity}.{aggregate.relation_name}")]
            rows = (await self.query(context, _QueryWithLogIntent(
                child_query, child_trace, request._comment, request._purpose, intent_source,
                request.origin_entity))).rows
            child_desc = self.schema_provider.get_entity(relation.target_entity)
            foreign_property = child_desc.property_by_name(relation.foreign_key) if child_desc else None
            if foreign_property and foreign_property.column_name_val != relation.foreign_key:
                for row in rows:
                    if foreign_property.column_name_val in row:
                        row[relation.foreign_key] = row[foreign_property.column_name_val]
            buckets = {row[relation.foreign_key]: row for row in rows
                       if relation.foreign_key in row}
            for parent in parents:
                row = buckets.get(parent.get(relation.local_key))
                if row is None:
                    parent[aggregate.alias] = self._empty_aggregate_value(aggregate.query)
                elif aggregate.single_result:
                    inner_alias = (child_query.aggregates[0].alias
                                   if child_query.aggregates else aggregate.alias)
                    parent[aggregate.alias] = row.get(inner_alias)
                else:
                    parent[aggregate.alias] = {
                        key: value for key, value in row.items()
                        if key != relation.foreign_key
                    }

    @staticmethod
    def _empty_aggregate_value(query: SelectQuery):
        if not query.aggregates or query.aggregates[0].function == AggregateFunction.Count:
            return 0
        return None

    def _attach_empty_relation_aggregate(self, parents, aggregate, query):
        value = self._empty_aggregate_value(query) if aggregate.single_result else {}
        for parent in parents:
            parent[aggregate.alias] = value

    async def mutate(self, context: 'UserContext', request: MutationRequest) -> MutationResult:
        request.validate()
        if context is not None:
            context._require_mutation_invocation()
        self._sync_generated_schema(context)
        entity = getattr(request._data, "entity", "unknown")
        kind = type(request._data).__name__.replace("Command", "").lower()
        if context is not None:
            def check(data):
                if isinstance(data, MutationRequest):
                    check(data._data)
                elif isinstance(data, list):
                    for child in data:
                        check(child)
                elif not context.consume_mutation_checked(data):
                    context.check_and_fix_mutation(data)
            check(request._data)
        telemetry = context.runtime_telemetry() if context is not None else None
        scope = (
            context.mutation_policy_execution(request)
            if context is not None
            else _NoopContextManager()
        )
        with scope:
            from teaql.runtime.log_privacy import _MutationIntentPrivacy
            def descriptor(name):
                return self.schema_provider.get_entity(name) or (context.entity(name) if context else None)
            privacy = _MutationIntentPrivacy.capture(request, descriptor)
            session = getattr(context, '_graph_session', None)
            if session is not None:
                privacy = session._intent_privacy.merge(privacy)
            return await observe_runtime_operation(
                telemetry,
                RuntimeOperation("mutation", f"{entity}.{kind}", {
                    "teaql.entity.type": entity,
                    "teaql.mutation.kind": kind,
                }),
                lambda: self._mutate(context, request, privacy),
            )

    async def _mutate(self, context: 'UserContext', request: MutationRequest, privacy=None) -> MutationResult:
        request.validate()
        if isinstance(self.transport, SqlTransactionTransport):
            transaction = await self.transport.begin_sql()
            executor = SqlDataServiceExecutor(self.dialect, transaction, self.schema_provider)
            from teaql.runtime.audit import _CommittedAuditJournal
            journal = _CommittedAuditJournal(context) if context is not None else None
            try:
                result = await executor._mutate(journal.context if journal else context, request, privacy)
                await transaction.commit_sql()
            except BaseException:
                if journal:
                    journal.discard()
                # CancelledError is not an Exception. Release the transaction
                # on cancellation too, without replacing the original failure.
                try:
                    await transaction.rollback_sql()
                except BaseException:
                    pass
                raise
            else:
                if journal:
                    await journal.committed()
                return result

        req_data = request._data
        if isinstance(req_data, list):
            start = datetime.now()
            results = []
            for child in req_data:
                child_request = (child.with_root_intent(request.intent)
                    if isinstance(child, MutationRequest) else
                    MutationRequest(child, comment=request.intent.comment))
                results.append(await self._mutate(context, child_request, privacy))
            affected = sum(result.affected_rows for result in results)
            return MutationResult(affected, {}, ExecutionMetadata(
                backend=self._backend_name(), operation=DataServiceOperation.Batch,
                started_at=start, ended_at=datetime.now(), affected_rows=affected,
                comment=request.intent.comment, audit_reason=request.intent.comment,
                statements=tuple(result.metadata for result in results)))
        entity_desc = self.schema_provider.get_entity(req_data.entity)
        if not entity_desc and context:
            entities = context.get_resource("entities")
            if entities:
                for e in entities:
                    if getattr(e, "_name", None) == req_data.entity:
                        entity_desc = e
                        break
        if not entity_desc:
            raise CompileError(SqlCompileError(f"unknown entity: {req_data.entity}"))

        id_prop = next(
            (
                p for p in getattr(entity_desc, 'properties', [])
                if getattr(p, '_is_id', False) or getattr(p, 'is_id_val', False)
            ),
            None,
        )
        if isinstance(req_data, InsertCommand) and id_prop is not None:
            if id_prop.name not in req_data.values:
                req_data.values[id_prop.name] = Value.from_any(
                    await self.next_id(req_data.entity)
                )
            else:
                await self.ensure_id_floor(
                    req_data.entity, int(req_data.values[id_prop.name].val))
            version_prop = next((
                prop for prop in getattr(entity_desc, "properties", [])
                if getattr(prop, "_is_version", False)
            ), None)
            if version_prop is not None and version_prop.name not in req_data.values:
                req_data.values[version_prop.name] = Value.from_any(1)

        if not request.mutation_lineage:
            target_id = getattr(req_data, 'id', None)
            if target_id is None and id_prop is not None:
                target_id = getattr(req_data, 'values', {}).get(id_prop.name)
            request = request.with_mutation_lineage((TraceNode(
                kind='auditReason', name=req_data.entity, entity_type=req_data.entity,
                entity_id=getattr(target_id, 'val', target_id), comment=request.comment()),))
            
        try:
            if isinstance(req_data, InsertCommand):
                op = "insert"
                compiled = self.dialect.compile_insert(entity_desc, req_data)
            elif isinstance(req_data, UpdateCommand):
                op = "update"
                compiled = self.dialect.compile_update(entity_desc, req_data)
            elif isinstance(req_data, DeleteCommand):
                op = "delete"
                compiled = self.dialect.compile_delete(entity_desc, req_data)
            elif isinstance(req_data, RecoverCommand):
                op = "recover"
                compiled = self.dialect.compile_recover(entity_desc, req_data)
            else:
                raise CompileError(SqlCompileError(f"unsupported mutation type: {type(req_data)}"))
        except SqlCompileError as e:
            raise CompileError(e)

        start = datetime.now()
        last_insert_id = None
        operation = {'insert': DataServiceOperation.Insert, 'update': DataServiceOperation.Update,
                     'delete': DataServiceOperation.Delete, 'recover': DataServiceOperation.Recover}[op]
        try:
            telemetry = context.runtime_telemetry() if context is not None else None
            affected_rows, last_insert_id = await observe_runtime_operation(
                telemetry,
                RuntimeOperation("provider", f"{self.dialect.kind()}.mutation", {
                    "teaql.provider.kind": str(self.dialect.kind()),
                    "teaql.provider.operation": op,
                }),
                lambda: self.transport.execute_sql(compiled),
            )
        except BaseException as e:
            self._record_statement(context, request, compiled, start, operation,
                                   'cancelled' if isinstance(e, asyncio.CancelledError) else 'failure',
                                   intent_privacy=privacy)
            if isinstance(e, Exception):
                raise TransportError(e) from e
            raise
        metadata = self._record_statement(context, request, compiled, start, operation,
                                          'success', affected_rows=affected_rows, intent_privacy=privacy)

        generated_values = {}
        if op == "insert" and last_insert_id:
            # Assumes the first ID column
            id_prop = next((
                p for p in getattr(entity_desc, 'properties', [])
                if getattr(p, '_is_id', False) or getattr(p, 'is_id_val', False)
            ), None)
            if id_prop:
                generated_values[id_prop.name] = Value.val_u64(last_insert_id)

        id_prop = next(
            (
                p for p in getattr(entity_desc, 'properties', [])
                if getattr(p, '_is_id', False) or getattr(p, 'is_id_val', False)
            ),
            None,
        )
        persisted_record = None
        entity_id = generated_values.get(getattr(id_prop, 'name', 'id')) if id_prop else None
        if entity_id is None:
            entity_id = getattr(req_data, 'id', None)
        if entity_id is None and id_prop is not None:
            entity_id = getattr(req_data, 'values', {}).get(id_prop.name)
        physically_deleted = isinstance(req_data, DeleteCommand) and not req_data.soft_delete
        if affected_rows > 0 and not physically_deleted and id_prop is not None and entity_id is not None:
            columns = ", ".join(
                self.dialect.quote_ident(p.column_name_val)
                if p.column_name_val == p.name
                else (
                    f"{self.dialect.quote_ident(p.column_name_val)} AS "
                    f"{self.dialect.quote_ident(p.name)}"
                )
                for p in entity_desc.properties
            )
            table = self.dialect.quote_ident(entity_desc.table_name_val)
            id_column = self.dialect.quote_ident(id_prop.column_name_val)
            readback = CompiledQuery(
                f"SELECT {columns} FROM {table} WHERE {id_column} = {self.dialect.placeholder(1)}",
                [Value.from_any(entity_id)],
                parameter_log_policies=[self.dialect.field_log_policy(entity_desc, id_prop.name)],
                sql_origin='generated',
            )
            read_start = datetime.now()
            persisted_rows = None
            try:
                persisted_rows = await self.transport.fetch_all_sql(readback)
                if len(persisted_rows) != 1:
                    raise TransportError(RuntimeError(
                        f"expected one authoritative persisted row for {req_data.entity}, got {len(persisted_rows)}"))
            except BaseException as error:
                self._record_readback(context, readback, compiled, metadata, read_start,
                                      persisted_rows, error, privacy)
                raise
            persisted_record = persisted_rows[0]
            read_metadata = self._record_readback(context, readback, compiled, metadata,
                                                  read_start, persisted_rows, None, privacy)
            metadata = replace(metadata, statements=(metadata, read_metadata))

        if affected_rows > 0 and context is not None:
            from teaql.runtime.audit import AuditFieldChange, MutationAuditKind, RawAuditEvent
            if isinstance(req_data, InsertCommand):
                kind = MutationAuditKind.CREATED
                entity_id = generated_values.get("id", req_data.values.get("id"))
                changes = tuple(AuditFieldChange(name, None, value) for name, value in req_data.values.items())
            elif isinstance(req_data, UpdateCommand):
                kind = MutationAuditKind.UPDATED
                entity_id = req_data.id
                old_values = req_data.old_values or {}
                changes = tuple(AuditFieldChange(name, old_values.get(name), value) for name, value in req_data.values.items())
            elif isinstance(req_data, DeleteCommand):
                kind = MutationAuditKind.DELETED
                entity_id = req_data.id
                changes = ()
            else:
                kind = MutationAuditKind.RECOVERED
                entity_id = req_data.id
                changes = ()
            await context.send_audit_event(RawAuditEvent(
                kind,
                req_data.entity,
                entity_id,
                changes,
                request.mutation_lineage,
                context.user_identifier(),
                context.get_resource("bootstrapCategory"),
                context.current_mutation_governance(),
                _intent_privacy=privacy,
            ))
        return MutationResult(
            affected_rows=affected_rows,
            generated_values=generated_values,
            metadata=metadata,
            persisted_record=persisted_record,
        )

    def _record_readback(self, context, readback, source, write_metadata, started_at, rows, error, privacy=None):
        # A driver returning zero/multiple rows succeeded as SQL; validation of
        # the authoritative snapshot is a separate business failure.
        outcome = ('success' if rows is not None else 'cancelled'
                   if isinstance(error, asyncio.CancelledError) else 'failure')
        metadata = replace(write_metadata, operation=DataServiceOperation.Query,
            purpose='verify the persisted mutation result',
            started_at=started_at, ended_at=datetime.now(), execution_outcome=outcome,
            parameterized_sql=readback.sql, parameters=list(readback.params),
            parameter_log_policies=readback.parameter_log_policies, sql_origin=readback.sql_origin,
            affected_rows=None, result_count=len(rows) if rows is not None else None,
            trace_chain=physical_readback_path(write_metadata.trace_chain))
        if context is None:
            return metadata
        try:
            context._record_metadata_log(metadata, intent_source=source,
                intent_values=tuple(readback.params[:1]), intent_privacy=privacy)
        except BaseException:
            # An in-flight readback error must survive a diagnostic sink failure.
            pass
        return metadata

    async def next_id(self, entity: str) -> int:
        await self.transport.execute_sql(CompiledQuery(
            "CREATE TABLE IF NOT EXISTS teaql_id_space ("
            "type_name VARCHAR(255) NOT NULL PRIMARY KEY, "
            "current_level BIGINT NOT NULL)", []))
        first = self.dialect.placeholder(1)
        second = self.dialect.placeholder(2)
        third = self.dialect.placeholder(3)
        for attempt in range(1, self.MAX_ID_ALLOCATION_ATTEMPTS + 1):
            rows = await self.transport.fetch_all_sql(CompiledQuery(
                f"SELECT current_level FROM teaql_id_space WHERE type_name = {first}",
                [Value.from_any(entity)]))
            if not rows:
                try:
                    changed, _ = await self.transport.execute_sql(CompiledQuery(
                        f"INSERT INTO teaql_id_space(type_name, current_level) "
                        f"VALUES ({first}, 1)", [Value.from_any(entity)]))
                    if changed == 1:
                        return 1
                    raise RuntimeError(
                        f"ID space insert for {entity} changed {changed} rows")
                except Exception:
                    winner = await self.transport.fetch_all_sql(CompiledQuery(
                        f"SELECT current_level FROM teaql_id_space WHERE type_name = {first}",
                        [Value.from_any(entity)]))
                    if not winner:
                        raise
                    continue
            current = int(rows[0]["current_level"])
            if current >= 2**63 - 1:
                raise RuntimeError(f"ID space overflow for {entity}")
            next_value = current + 1
            changed, _ = await self.transport.execute_sql(CompiledQuery(
                "UPDATE teaql_id_space SET current_level = " + first
                + " WHERE type_name = " + second + " AND current_level = " + third,
                [Value.from_any(next_value), Value.from_any(entity), Value.from_any(current)]))
            if changed == 1:
                return next_value
            if changed != 0:
                raise RuntimeError(
                    f"ID space update for {entity} changed {changed} rows on attempt {attempt}")
        raise RuntimeError(
            f"Unable to allocate ID for {entity} after "
            f"{self.MAX_ID_ALLOCATION_ATTEMPTS} optimistic-lock attempts")

    async def ensure_id_floor(self, entity: str, floor: int) -> None:
        if floor < 0 or floor >= 2**63:
            raise ValueError(f"Invalid ID space floor {floor} for {entity}")
        await self.transport.execute_sql(CompiledQuery(
            "CREATE TABLE IF NOT EXISTS teaql_id_space ("
            "type_name VARCHAR(255) NOT NULL PRIMARY KEY, "
            "current_level BIGINT NOT NULL)", []))
        placeholders = [self.dialect.placeholder(index) for index in (1, 2, 3)]
        for attempt in range(1, self.MAX_ID_ALLOCATION_ATTEMPTS + 1):
            rows = await self.transport.fetch_all_sql(CompiledQuery(
                f"SELECT current_level FROM teaql_id_space WHERE type_name = {placeholders[0]}",
                [Value.from_any(entity)]))
            if not rows:
                try:
                    changed, _ = await self.transport.execute_sql(CompiledQuery(
                        "INSERT INTO teaql_id_space(type_name, current_level) VALUES ("
                        f"{placeholders[0]}, {placeholders[1]})",
                        [Value.from_any(entity), Value.from_any(floor)]))
                    if changed == 1:
                        return
                except Exception:
                    winner = await self.transport.fetch_all_sql(CompiledQuery(
                        f"SELECT current_level FROM teaql_id_space WHERE type_name = {placeholders[0]}",
                        [Value.from_any(entity)]))
                    if not winner:
                        raise
                continue
            current = int(rows[0]["current_level"])
            if current >= floor:
                return
            changed, _ = await self.transport.execute_sql(CompiledQuery(
                f"UPDATE teaql_id_space SET current_level = {placeholders[0]} "
                f"WHERE type_name = {placeholders[1]} AND current_level = {placeholders[2]}",
                [Value.from_any(floor), Value.from_any(entity), Value.from_any(current)]))
            if changed == 1:
                return
            if changed != 0:
                raise RuntimeError(
                    f"ID space floor update for {entity} changed {changed} rows "
                    f"on attempt {attempt}")
        raise RuntimeError(
            f"Unable to synchronize ID space floor for {entity} after "
            f"{self.MAX_ID_ALLOCATION_ATTEMPTS} optimistic-lock attempts")

    async def _ensure_schema(self, context: 'UserContext', capability: object) -> None:
        from teaql.runtime._schema_capability import SCHEMA_CAPABILITY
        if capability is not SCHEMA_CAPABILITY:
            raise PermissionError("Ensure Schema is available only through UserContext.ensure_schema()")
        self._sync_generated_schema(context)
        enable_soundex = getattr(self.transport, "enable_soundex", None)
        if callable(enable_soundex):
            await enable_soundex()
        entities = context.all_entities()
        if not entities:
            entities = context.get_resource("entities") or []
        for entity in entities:
            try:
                # Create table
                create_sql = self.dialect.compile_create_table(entity)
                await self.transport.execute_sql(CompiledQuery(create_sql, []))
                
                # Add columns if needed
                # For simplicity in this naive python port, we'll try to add all columns and ignore errors
                for prop in getattr(entity, 'properties', []):
                    try:
                        add_sql = self.dialect.compile_add_column(entity, prop)
                        await self.transport.execute_sql(CompiledQuery(add_sql, []))
                    except Exception:
                        pass
                        
                # Create indexes
                try:
                    indexes = self.dialect.schema_indexes_sqls(entity)
                    for idx_sql in indexes:
                        await self.transport.execute_sql(CompiledQuery(idx_sql, []))
                except Exception:
                    pass
            except Exception as error:
                # Preserve the existing best-effort schema behavior, but never
                # forward driver exception text to an uncontrolled log sink.
                logging.getLogger("teaql.sql").warning(
                    "Schema creation failed for entity %s (%s)",
                    getattr(entity, '_name', type(entity).__name__),
                    type(error).__name__,
                )
        await self.transport.execute_sql(CompiledQuery(
            "CREATE TABLE IF NOT EXISTS teaql_id_space ("
            "type_name VARCHAR(255) NOT NULL PRIMARY KEY, "
            "current_level BIGINT NOT NULL)", []))
        await self.transport.execute_sql(CompiledQuery(
            "CREATE TABLE IF NOT EXISTS teaql_business_id_space ("
            "scope_key VARCHAR(512) NOT NULL PRIMARY KEY, "
            "current_value BIGINT NOT NULL, "
            "version BIGINT NOT NULL, "
            "updated_at BIGINT NOT NULL)", []))

    async def begin(self, context: 'UserContext') -> 'teaql.data_service.Transaction':
        if not isinstance(self.transport, SqlTransactionTransport):
            raise Exception("Transport does not support transactions")
        tx = await self.transport.begin_sql()
        return SqlDataServiceTransaction(self.dialect, tx, self.schema_provider)

class SqlDataServiceTransaction(QueryExecutor, MutationExecutor):
    def __init__(self, dialect: SqlDialect, transport: SqlTransactionTransportTx, schema_provider: SchemaProvider):
        self.dialect = dialect
        self.transport = transport
        self.schema_provider = schema_provider
        self._audit_journal = None
        self._audit_owner = None
        self._completed = False

    def capabilities(self) -> DataServiceCapabilities:
        return DataServiceCapabilities(
            query=True,
            mutation=True,
            transaction=False,
            schema=True,
            id_generation=True,
            batch_mutation=True,
            returning=False
        )

    async def query(self, context: 'UserContext', request: QueryRequest) -> QueryResult:
        executor = SqlDataServiceExecutor(self.dialect, self.transport, self.schema_provider)
        return await executor.query(context, request)

    async def mutate(self, context: 'UserContext', request: MutationRequest) -> MutationResult:
        request.validate()
        if self._completed:
            raise RuntimeError('SQL transaction is already completed')
        if context is not None:
            context._require_mutation_invocation()
            if context._graph_session is None:
                if self._audit_journal is None:
                    from teaql.runtime.audit import _CommittedAuditJournal
                    self._audit_journal = _CommittedAuditJournal(context)
                    self._audit_owner = context
                    self._audit_journal.context._mutation_policy = context._mutation_policy.for_invocation()
                    self._audit_journal.context._checked_mutations = set()
                elif self._audit_owner is not context:
                    raise RuntimeError('SQL transaction audit owner cannot change')
                context = self._audit_journal.context
        executor = SqlDataServiceExecutor(self.dialect, self.transport, self.schema_provider)
        return await executor.mutate(context, request)

    async def next_id(self, entity: str) -> int:
        executor = SqlDataServiceExecutor(self.dialect, self.transport, self.schema_provider)
        return await executor.next_id(entity)

    async def ensure_id_floor(self, entity: str, floor: int) -> None:
        executor = SqlDataServiceExecutor(self.dialect, self.transport, self.schema_provider)
        await executor.ensure_id_floor(entity, floor)

    async def commit(self, context: 'UserContext') -> None:
        if self._completed:
            raise RuntimeError('SQL transaction is already completed')
        await self.transport.commit_sql()
        self._completed = True
        if self._audit_journal:
            await self._audit_journal.committed()

    async def rollback(self, context: 'UserContext') -> None:
        if self._audit_journal:
            self._audit_journal.discard()
        self._completed = True
        await self.transport.rollback_sql()
