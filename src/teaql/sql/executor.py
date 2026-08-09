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
            schema=False,
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
        end = datetime.now()
        
        metadata = ExecutionMetadata(
            backend="sql",
            operation=DataServiceOperation.Query,
            started_at=start,
            ended_at=end,
            result_count=len(rows),
            trace_chain=request.trace_chain,
            comment=request._comment,
            debug_query=compiled.sql_with_comment() # Simplification for python
        )
        return QueryResult(rows=rows, metadata=metadata)

    async def mutate(self, ctx: 'UserContext', request: MutationRequest) -> MutationResult:
        req_data = request._data
        if isinstance(req_data, list):
            total_affected = 0
            start = datetime.now()
            for req in req_data:
                res = await self.mutate(ctx, req)
                total_affected += res.affected_rows
            end = datetime.now()
            return MutationResult(
                affected_rows=total_affected,
                generated_values={},
                metadata=ExecutionMetadata(
                    backend="sql",
                    operation=DataServiceOperation.Batch,
                    started_at=start,
                    ended_at=end,
                    affected_rows=total_affected
                )
            )

        entity_name = req_data.entity
        entity_desc = self.schema_provider.get_entity(entity_name)
        if not entity_desc and ctx:
            entities = ctx.get_resource("entities")
            if entities:
                for e in entities:
                    if getattr(e, "_name", None) == entity_name:
                        entity_desc = e
                        break
        if not entity_desc:
            raise CompileError(SqlCompileError(f"unknown entity: {entity_name}"))
            
        try:
            if isinstance(req_data, InsertMutation):
                compiled = self.dialect.compile_insert(entity_desc, req_data)
                op = DataServiceOperation.Insert
            elif isinstance(req_data, UpdateMutation):
                compiled = self.dialect.compile_update(entity_desc, req_data)
                op = DataServiceOperation.Update
            elif isinstance(req_data, DeleteMutation):
                compiled = self.dialect.compile_delete(entity_desc, req_data)
                op = DataServiceOperation.Delete
            elif isinstance(req_data, RecoverMutation):
                compiled = self.dialect.compile_recover(entity_desc, req_data)
                op = DataServiceOperation.Recover
            else:
                raise CompileError(SqlCompileError("unsupported mutation"))
        except SqlCompileError as e:
            raise CompileError(e)

        start = datetime.now()
        try:
            affected_rows = await self.transport.execute_sql(compiled)
        except Exception as e:
            raise TransportError(e)
        end = datetime.now()

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
            generated_values={},
            metadata=metadata
        )
