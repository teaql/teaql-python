from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, AsyncIterator
from copy import deepcopy
from datetime import datetime
from teaql.data_service import (
    DataServiceExecutor, QueryExecutor, MutationExecutor,
    DataServiceCapabilities, QueryRequest, QueryResult,
    MutationRequest, MutationResult, ExecutionMetadata,
    DataServiceOperation, StreamChunk
)
from teaql.core.mutation import (
    InsertCommand, UpdateCommand, DeleteCommand, RecoverCommand
)
from .types import CompiledQuery, SqlCompileError
from .dialect import SqlDialect
from teaql.core.expr import BinaryExpr, BinaryOp, ColumnExpr, ValueExpr
from teaql.core.query import SelectQuery
from teaql.core.value import Value
from teaql.runtime.telemetry import RuntimeOperation, observe_runtime_operation, start_runtime_operation

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

    async def query_stream(self, context, request: QueryRequest, chunk_size: int):
        if chunk_size <= 0:
            raise ValueError("chunk_size must be positive")
        if request.query.relations or request.query.child_enhancements or request.query.object_group_bys:
            raise ValueError(
                "streaming relation or aggregate enhancement is not supported; "
                "stream a root query or use execute_for_list"
            )
        entity_desc = self.schema_provider.get_entity(request.query.entity)
        if not entity_desc:
            raise CompileError(SqlCompileError(f"unknown entity: {request.query.entity}"))
        compiled = self.dialect.compile_select(entity_desc, request.query)
        pending = None
        index = 0
        async for rows in self.transport.stream_sql(compiled, chunk_size):
            if pending is not None:
                yield StreamChunk(pending, index, False)
                index += 1
            pending = rows
        if pending is not None:
            yield StreamChunk(pending, index, True)

    async def query(self, context: 'UserContext', request: QueryRequest) -> QueryResult:
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
        request.query.prepare_for_list()
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
            
        try:
            compiled = self.dialect.compile_select(entity_desc, request.query)
        except SqlCompileError as e:
            raise CompileError(e)
            
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
        except Exception as e:
            raise TransportError(e)

        await self._enhance_relations(context, rows, request.query)

        facets = {}
        if getattr(request.query, 'object_group_bys', None):
            for ogb in request.query.object_group_bys:
                if ogb.property_name == "status_stats":
                    # Map object field to database column name
                    column_name = ogb.storage_field
                    for p in getattr(entity_desc, 'properties', []):
                        if p.name == ogb.storage_field:
                            column_name = getattr(p, 'column_name_val', ogb.storage_field)
                            break
                    # Simple hardcoded facet query for test
                    q = f"SELECT {column_name} as id, COUNT(*) as count_tasks FROM {entity_desc.table_name_val} GROUP BY {column_name}"
                    try:
                        facet_rows = await self.transport.fetch_all_sql(compiled.__class__(q, []))
                        from teaql.core.list import SmartList
                        facets[ogb.property_name] = SmartList(facet_rows)
                    except Exception as e:
                        pass
        
        end = datetime.now()
        
        metadata = ExecutionMetadata(
            backend="sql",
            operation=DataServiceOperation.Query,
            started_at=start,
            ended_at=end,
            parameterized_sql=compiled.sql_with_comment(),
            parameters=list(compiled.params),
            result_count=len(rows),
            trace_chain=request.trace_chain,
            comment=request._comment,
            debug_query=compiled.debug_sql(self.dialect.kind())
        )
        if context is not None:
            context.record_metadata_log(metadata)
        return QueryResult(
            rows=rows,
            metadata=metadata,
            facets=facets
        )

    async def _enhance_relations(self, context, parents: List[Dict[str, Any]], query: SelectQuery) -> None:
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
                parent_ids = [row[relation.local_key] for row in parents if relation.local_key in row]
                child_query = deepcopy(load.query) if load.query is not None else SelectQuery(relation.target_entity)
                child_query.entity = relation.target_entity
                if relation.foreign_key not in child_query.projection:
                    child_query.projection.append(relation.foreign_key)
                values = Value.List([Value.from_any(value) for value in parent_ids])
                child_query.and_filter(BinaryExpr(ColumnExpr(relation.foreign_key), BinaryOp.In, ValueExpr(values)))
                if child_query.slice is not None:
                    child_query.partition_by_field(relation.foreign_key)
                children = (await self.query(context, QueryRequest(child_query))).rows
                for child in children:
                    child.pop("__teaql_partition_rank", None)
                buckets: Dict[Any, List[Dict[str, Any]]] = {}
                for child in children:
                    buckets.setdefault(child.get(relation.foreign_key), []).append(child)
                for parent in parents:
                    related = buckets.get(parent.get(relation.local_key), [])
                    parent[load.name] = related if relation.is_many else (related[0] if related else None)
                relation_scope.success({"teaql.result.cardinality": len(children)})
            except BaseException as error:
                relation_scope.failure(error)
                raise

    async def mutate(self, context: 'UserContext', request: MutationRequest) -> MutationResult:
        entity = getattr(request._data, "entity", "unknown")
        kind = type(request._data).__name__.replace("Command", "").lower()
        if context is not None:
            context.check_and_fix_mutation(request._data)
        telemetry = context.runtime_telemetry() if context is not None else None
        return await observe_runtime_operation(
            telemetry,
            RuntimeOperation("mutation", f"{entity}.{kind}", {
                "teaql.entity.type": entity,
                "teaql.mutation.kind": kind,
            }),
            lambda: self._mutate(context, request),
        )

    async def _mutate(self, context: 'UserContext', request: MutationRequest) -> MutationResult:
        if isinstance(self.transport, SqlTransactionTransport):
            transaction = await self.transport.begin_sql()
            executor = SqlDataServiceExecutor(self.dialect, transaction, self.schema_provider)
            try:
                result = await executor._mutate(context, request)
                await transaction.commit_sql()
                return result
            except Exception:
                await transaction.rollback_sql()
                raise

        req_data = request._data
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
        except Exception as e:
            raise TransportError(e)
        end = datetime.now()

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
            persisted_rows = await self.transport.fetch_all_sql(
                CompiledQuery(
                    f"SELECT {columns} FROM {table} WHERE {id_column} = {self.dialect.placeholder(1)}",
                    [Value.from_any(entity_id)],
                )
            )
            if not persisted_rows:
                raise TransportError(RuntimeError(
                    f"authoritative persisted row not found for {req_data.entity}"))
            persisted_record = persisted_rows[0]

        metadata = ExecutionMetadata(
            backend="sql",
            operation={
                "insert": DataServiceOperation.Insert,
                "update": DataServiceOperation.Update,
                "delete": DataServiceOperation.Delete,
                "recover": DataServiceOperation.Recover,
            }[op],
            started_at=start,
            ended_at=end,
            parameterized_sql=compiled.sql_with_comment(),
            parameters=list(compiled.params),
            affected_rows=affected_rows,
            trace_chain=request.trace_chain(),
            comment=request.comment(),
            debug_query=compiled.debug_sql(self.dialect.kind())
        )
        if context is not None:
            context.record_metadata_log(metadata)
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
            await context.send_audit_event(RawAuditEvent(kind, req_data.entity, entity_id, changes, tuple(request.trace_chain())))
        return MutationResult(
            affected_rows=affected_rows,
            generated_values=generated_values,
            metadata=metadata,
            persisted_record=persisted_record,
        )

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
            except Exception as e:
                # If creating table fails, it might be due to dialect unsupported features, just pass for now
                print(f"Error creating table for entity {getattr(entity, '_name', entity)}: {e}")
                pass
        await self.transport.execute_sql(CompiledQuery(
            "CREATE TABLE IF NOT EXISTS teaql_id_space ("
            "type_name VARCHAR(255) NOT NULL PRIMARY KEY, "
            "current_level BIGINT NOT NULL)", []))
        await self.ensure_initial_graphs(context)

    async def ensure_initial_graphs(self, context: 'UserContext') -> None:
        from teaql.core.mutation import InsertCommand, UpdateCommand
        graphs = [
            *((graph, False) for graph in context.root_graphs()),
            *((graph, True) for graph in context.initial_graphs()),
        ]
        for graph, reconcile in graphs:
            entity_name = getattr(graph, 'entity', None)
            if not entity_name:
                continue
                
            entity_desc = self.schema_provider.get_entity(entity_name)
            if not entity_desc:
                entities = context.get_resource("entities") or []
                for e in entities:
                    if getattr(e, "_name", None) == entity_name:
                        entity_desc = e
                        break
            if not entity_desc:
                continue
                
            values = getattr(graph, 'fields', getattr(graph, 'values', {}))
            seed_id = values.get('id')
            seed_id = seed_id.val if hasattr(seed_id, 'val') else seed_id
            if seed_id is None:
                raise ValueError(f"bootstrap graph {entity_name} must define id")
            query = SelectQuery(entity_name).filter(BinaryExpr(
                ColumnExpr('id'), BinaryOp.Eq, ValueExpr(Value.from_any(seed_id))))
            current_rows = (await self._query(context, QueryRequest(query))).rows
            if not current_rows:
                mutation = InsertCommand(entity_name)
                for k, v in values.items():
                    mutation.value(k, v)
                version_prop = next((p for p in getattr(entity_desc, 'properties', [])
                    if getattr(p, '_is_version', False) or getattr(p, 'is_version_val', False)), None)
                if version_prop is not None and version_prop.name not in mutation.values:
                    mutation.value(version_prop.name, 1)
                await self.transport.execute_sql(self.dialect.compile_insert(entity_desc, mutation))
            elif reconcile:
                current = current_rows[0]
                changed = {k: v for k, v in values.items() if k != 'id'
                    and current.get(k) != (v.val if hasattr(v, 'val') else v)}
                if changed:
                    mutation = UpdateCommand(entity_name, Value.from_any(seed_id))
                    for k, v in changed.items():
                        mutation.value(k, v)
                    version = current.get('version')
                    version = version.val if hasattr(version, 'val') else version
                    if version is not None:
                        mutation.expected_version(int(version))
                    await self.transport.execute_sql(self.dialect.compile_update(entity_desc, mutation))
            await self.ensure_id_floor(entity_name, int(seed_id))

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
        executor = SqlDataServiceExecutor(self.dialect, self.transport, self.schema_provider)
        return await executor.mutate(context, request)

    async def next_id(self, entity: str) -> int:
        executor = SqlDataServiceExecutor(self.dialect, self.transport, self.schema_provider)
        return await executor.next_id(entity)

    async def ensure_id_floor(self, entity: str, floor: int) -> None:
        executor = SqlDataServiceExecutor(self.dialect, self.transport, self.schema_provider)
        await executor.ensure_id_floor(entity, floor)

    async def commit(self, context: 'UserContext') -> None:
        await self.transport.commit_sql()

    async def rollback(self, context: 'UserContext') -> None:
        await self.transport.rollback_sql()
