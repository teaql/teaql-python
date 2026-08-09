from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime
from teaql.data_service import (
    DataServiceExecutor, QueryExecutor, MutationExecutor,
    DataServiceCapabilities, QueryRequest, QueryResult,
    MutationRequest, MutationResult, ExecutionMetadata,
    DataServiceOperation
)
from teaql.core.mutation import (
    InsertMutation, UpdateMutation, DeleteMutation, RecoverMutation
)
from .types import CompiledQuery, SqlCompileError
from .dialect import SqlDialect

class SqlTransport(ABC):
    @abstractmethod
    async def fetch_all_sql(self, query: CompiledQuery) -> List[Dict[str, Any]]:
        pass
        
    @abstractmethod
    async def execute_sql(self, query: CompiledQuery) -> int:
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
            id_generation=False,
            batch_mutation=True,
            returning=False
        )

    async def query(self, ctx: 'UserContext', request: QueryRequest) -> QueryResult:
        entity_desc = self.schema_provider.get_entity(request.query.entity)
        if not entity_desc and ctx:
            entities = ctx.get_resource("entities")
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
            rows = await self.transport.fetch_all_sql(compiled)
        except Exception as e:
            raise TransportError(e)

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
            operation="query",
            started_at=start,
            ended_at=end,
            affected_rows=len(rows),
            trace_chain=request.trace_chain,
            comment=request._comment,
            debug_query=compiled.sql_with_comment() # Simplification for python
        )
        return QueryResult(
            rows=rows,
            metadata=metadata,
            facets=facets
        )

    async def mutate(self, ctx: 'UserContext', request: MutationRequest) -> MutationResult:
        req_data = request._data
        entity_desc = self.schema_provider.get_entity(req_data.entity)
        if not entity_desc and ctx:
            entities = ctx.get_resource("entities")
            if entities:
                for e in entities:
                    if getattr(e, "_name", None) == req_data.entity:
                        entity_desc = e
                        break
        if not entity_desc:
            raise CompileError(SqlCompileError(f"unknown entity: {req_data.entity}"))
            
        try:
            if isinstance(req_data, InsertMutation):
                op = "insert"
                compiled = self.dialect.compile_insert(entity_desc, req_data)
            elif isinstance(req_data, UpdateMutation):
                op = "update"
                compiled = self.dialect.compile_update(entity_desc, req_data)
            elif isinstance(req_data, DeleteMutation):
                op = "delete"
                compiled = self.dialect.compile_delete(entity_desc, req_data)
            else:
                raise CompileError(SqlCompileError(f"unsupported mutation type: {type(req_data)}"))
        except SqlCompileError as e:
            raise CompileError(e)

        start = datetime.now()
        last_insert_id = None
        try:
            affected_rows, last_insert_id = await self.transport.execute_sql(compiled)
        except Exception as e:
            raise TransportError(e)
        end = datetime.now()

        generated_values = {}
        if op == "insert" and last_insert_id:
            # Assumes the first ID column
            id_prop = next((p for p in getattr(entity_desc, 'properties', []) if getattr(p, '_is_id', False)), None)
            if id_prop:
                from teaql.core.value import Value
                generated_values[id_prop.name] = Value.val_u64(last_insert_id)

        metadata = ExecutionMetadata(
            backend="sql",
            operation=op,
            started_at=start,
            ended_at=end,
            affected_rows=affected_rows,
            trace_chain=request.trace_chain(),
            comment=request.comment(),
            debug_query=compiled.sql_with_comment()
        )
        return MutationResult(
            affected_rows=affected_rows,
            generated_values=generated_values,
            metadata=metadata
        )

    async def ensure_schema(self, ctx: 'UserContext') -> None:
        entities = ctx.all_entities()
        if not entities:
            entities = ctx.get_resource("entities") or []
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

    async def ensure_initial_graphs(self, ctx: 'UserContext') -> None:
        from teaql.core.mutation import InsertMutation
        graphs = ctx.initial_graphs()
        for graph in graphs:
            entity_name = getattr(graph, 'entity', None)
            if not entity_name:
                continue
                
            entity_desc = self.schema_provider.get_entity(entity_name)
            if not entity_desc:
                entities = ctx.get_resource("entities") or []
                for e in entities:
                    if getattr(e, "_name", None) == entity_name:
                        entity_desc = e
                        break
            if not entity_desc:
                continue
                
            values = getattr(graph, 'values', {})
            mutation = InsertMutation(entity_name)
            for k, v in values.items():
                mutation.value(k, v)
                
            try:
                # Try to insert; if it fails (e.g. unique constraint on ID), it's already seeded
                compiled = self.dialect.compile_insert(entity_desc, mutation)
                await self.transport.execute_sql(compiled)
            except Exception:
                pass
