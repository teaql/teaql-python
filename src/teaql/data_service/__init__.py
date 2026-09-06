from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import List, Dict, Any, Optional, Protocol, Union, AsyncIterator

from teaql.core.query import SelectQuery
from teaql.core.mutation import (
    MutationRequest,
    InsertCommand as CoreInsertCommand,
    UpdateCommand as CoreUpdateCommand,
    DeleteCommand as CoreDeleteCommand,
    RecoverCommand as CoreRecoverCommand,
    TraceNode
)


@dataclass
class DataServiceCapabilities:
    query: bool = False
    mutation: bool = False
    transaction: bool = False
    schema: bool = False
    id_generation: bool = False
    batch_mutation: bool = False
    returning: bool = False


@dataclass
class QueryRequest:
    query: SelectQuery
    trace_chain: List[TraceNode] = field(default_factory=list)
    _comment: Optional[str] = None
    _purpose: Optional[str] = None

    def comment(self, text: str) -> 'QueryRequest':
        if not text:
            raise ValueError("comment cannot be empty")
        self._comment = text
        return self

    def purpose(self, text: str) -> 'QueryRequest':
        if not text:
            raise ValueError("purpose cannot be empty")
        self._purpose = text
        return self


class DataServiceOperation(Enum):
    Query = auto()
    Insert = auto()
    Update = auto()
    Delete = auto()
    Recover = auto()
    Batch = auto()
    Schema = auto()


@dataclass
class ExecutionMetadata:
    backend: str
    operation: DataServiceOperation
    started_at: datetime
    ended_at: datetime
    parameterized_sql: str = ""
    parameters: List[Any] = field(default_factory=list)
    affected_rows: Optional[int] = None
    result_count: Optional[int] = None
    trace_chain: List[TraceNode] = field(default_factory=list)
    comment: Optional[str] = None
    purpose: Optional[str] = None
    audit_reason: Optional[str] = None
    backend_request_id: Optional[str] = None
    debug_query: Optional[str] = None


@dataclass
class QueryResult:
    rows: List[Dict[str, Any]]
    metadata: ExecutionMetadata
    facets: Dict[str, Any] = field(default_factory=dict)

def InsertCommand(cmd):
    return MutationRequest(cmd)

def UpdateCommand(cmd):
    return MutationRequest(cmd)

def DeleteCommand(cmd):
    return MutationRequest(cmd)

def RecoverCommand(cmd):
    return MutationRequest(cmd)



@dataclass
class MutationResult:
    affected_rows: int
    generated_values: Dict[str, Any]
    metadata: ExecutionMetadata
    persisted_record: Optional[Dict[str, Any]] = None


@dataclass
class StreamChunk:
    rows: List[Dict[str, Any]]
    chunk_index: int
    is_last: bool


class DataServiceExecutor(Protocol):
    def capabilities(self) -> DataServiceCapabilities:
        ...


class QueryExecutor(DataServiceExecutor, Protocol):
    async def query(self, context: 'UserContext', request: QueryRequest) -> QueryResult:
        ...


class StreamQueryExecutor(DataServiceExecutor, Protocol):
    def query_stream(self, context: 'UserContext', request: QueryRequest, chunk_size: int) -> AsyncIterator[StreamChunk]:
        ...


class MutationExecutor(DataServiceExecutor, Protocol):
    async def mutate(self, context: 'UserContext', request: MutationRequest) -> MutationResult:
        ...


class Transaction(Protocol):
    async def commit(self) -> None:
        ...

    async def rollback(self) -> None:
        ...


class TransactionExecutor(DataServiceExecutor, Protocol):
    async def begin(self) -> Transaction:
        ...


@dataclass
class _SchemaRequest:
    entity_name: str


@dataclass
class _SchemaResult:
    changed: bool


class _SchemaExecutor(DataServiceExecutor, Protocol):
    async def _ensure_schema_request(self, request: _SchemaRequest) -> _SchemaResult:
        ...


class IdGeneratorExecutor(DataServiceExecutor, Protocol):
    async def next_id(self, entity: str) -> int:
        ...


class DataService(QueryExecutor, MutationExecutor, Protocol):
    pass


def _generated_schema_provider():
    from teaql.provider.sqlite import SimpleSchemaProvider
    return SimpleSchemaProvider()


class SQLiteTeaQLClient:
    """Stable high-level SQLite entry point used by generated workspaces."""
    def __new__(cls, database_url: str):
        from teaql.provider.sqlite import create_sqlite_service
        return create_sqlite_service(database_url, _generated_schema_provider())


class TeaQLClient(SQLiteTeaQLClient):
    """Portable local client backed by the packaged SQLite provider."""
    pass


class PostgreSQLTeaQLClient:
    def __new__(cls, database_url: str):
        from teaql.provider.postgres.dialect import PostgresDialect
        from teaql.provider.postgres.transport import PostgresTransport
        from teaql.sql.executor import SqlDataServiceExecutor
        return SqlDataServiceExecutor(PostgresDialect(), PostgresTransport(database_url),
                                      _generated_schema_provider())


class MySQLTeaQLClient:
    def __new__(cls, database_url: str):
        from teaql.provider.mysql.dialect import MysqlDialect
        from teaql.provider.mysql.transport import MysqlTransport
        from teaql.sql.executor import SqlDataServiceExecutor
        return SqlDataServiceExecutor(MysqlDialect(), MysqlTransport(database_url),
                                      _generated_schema_provider())


__all__ = [
    "DataServiceCapabilities",
    "QueryRequest",
    "DataServiceOperation",
    "ExecutionMetadata",
    "QueryResult",
    "MutationRequest",
    "InsertCommand",
    "UpdateCommand",
    "DeleteCommand",
    "RecoverCommand",
    "MutationResult",
    "StreamChunk",
    "DataServiceExecutor",
    "QueryExecutor",
    "StreamQueryExecutor",
    "MutationExecutor",
    "Transaction",
    "TransactionExecutor",
    "IdGeneratorExecutor",
    "DataService"
    , "TeaQLClient", "SQLiteTeaQLClient", "PostgreSQLTeaQLClient", "MySQLTeaQLClient"
]
