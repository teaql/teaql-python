from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import List, Dict, Any, Optional, Protocol, Union, AsyncIterator
from copy import deepcopy

from teaql.core.query import SelectQuery
from teaql.core.request_intent import QueryIntent
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


class QueryRequest:
    __slots__ = ('query', 'trace_chain', '__intent', '__origin_entity',
                 '_log_intent_source', '_log_intent_queries')
    _UNSET = object()

    def __init__(self, query: SelectQuery, trace_chain=None, _comment=_UNSET, _purpose=_UNSET,
                 *, _origin_entity=None):
        comment = getattr(query, 'comment_text', None) if _comment is self._UNSET else _comment
        purpose = getattr(query, 'purpose_text', None) if _purpose is self._UNSET else _purpose
        self.__intent = QueryIntent(comment, purpose)
        self.__origin_entity = query.entity if _origin_entity is None else _origin_entity
        self.query = deepcopy(query)
        self.query.comment_text = self.intent.comment
        self.query.purpose_text = self.intent.purpose
        self.trace_chain = deepcopy(trace_chain) if trace_chain is not None else []

    @property
    def intent(self) -> QueryIntent:
        return self.__intent

    @property
    def origin_entity(self) -> str:
        return self.__origin_entity

    @property
    def _comment(self) -> str:
        return self.intent.comment

    @property
    def _purpose(self) -> str:
        return self.intent.purpose

    def validate(self) -> None:
        intent = getattr(self, '_QueryRequest__intent', None)
        QueryIntent(getattr(intent, 'comment', None), getattr(intent, 'purpose', None))
        if any(not isinstance(node, TraceNode) for node in self.trace_chain):
            raise TypeError('QueryRequest trace must contain typed TraceNode values')

    def with_query(self, query: SelectQuery) -> 'QueryRequest':
        result = QueryRequest(query, self.trace_chain, self._comment, self._purpose,
                              _origin_entity=self.origin_entity)
        if hasattr(self, '_log_intent_source'):
            result._log_intent_source = deepcopy(self._log_intent_source)
        # Derived work may drop a relation/projection whose private values are
        # still mentioned by the originating intent. Retain owned source graphs
        # solely for compiler classification, never on Context or log payloads.
        result._log_intent_queries = (*deepcopy(getattr(self, '_log_intent_queries', ())),
                                      deepcopy(self.query))
        return result

    def comment(self, text: str) -> 'QueryRequest':
        result = self.with_query(self.query)
        result.__intent = QueryIntent(text, self._purpose)
        result.query.comment_text = result.intent.comment
        return result

    def purpose(self, text: str) -> 'QueryRequest':
        result = self.with_query(self.query)
        result.__intent = QueryIntent(self._comment, text)
        result.query.purpose_text = result.intent.purpose
        return result


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
    mutation_lineage: tuple[TraceNode, ...] = field(default_factory=tuple)
    comment: Optional[str] = None
    purpose: Optional[str] = None
    audit_reason: Optional[str] = None
    backend_request_id: Optional[str] = None
    debug_query: Optional[str] = None
    database_kind: Any = None
    parameter_log_policies: Optional[List[str]] = None
    sql_origin: Optional[str] = None
    # Statement/cursor termination only, not transaction commit.
    execution_outcome: Optional[str] = None


@dataclass
class QueryResult:
    rows: List[Dict[str, Any]]
    metadata: ExecutionMetadata
    facets: Dict[str, Any] = field(default_factory=dict)

def InsertCommand(cmd, comment=None):
    return MutationRequest(cmd, comment)

def UpdateCommand(cmd, comment=None):
    return MutationRequest(cmd, comment)

def DeleteCommand(cmd, comment=None):
    return MutationRequest(cmd, comment)

def RecoverCommand(cmd, comment=None):
    return MutationRequest(cmd, comment)



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
