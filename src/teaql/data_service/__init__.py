from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import List, Dict, Any, Optional, Protocol, Union

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
    affected_rows: Optional[int] = None
    result_count: Optional[int] = None
    trace_chain: List[TraceNode] = field(default_factory=list)
    comment: Optional[str] = None
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


@dataclass
class StreamChunk:
    rows: List[Dict[str, Any]]
    chunk_index: int
    is_last: bool


class DataServiceExecutor(Protocol):
    def capabilities(self) -> DataServiceCapabilities:
        ...


class QueryExecutor(DataServiceExecutor, Protocol):
    async def query(self, ctx: 'UserContext', request: QueryRequest) -> QueryResult:
        ...


class StreamQueryExecutor(DataServiceExecutor, Protocol):
    async def query_stream(self, request: QueryRequest, chunk_size: int) -> List[StreamChunk]:
        ...


class MutationExecutor(DataServiceExecutor, Protocol):
    async def mutate(self, ctx: 'UserContext', request: MutationRequest) -> MutationResult:
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
class SchemaRequest:
    entity_name: str


@dataclass
class SchemaResult:
    changed: bool


class SchemaExecutor(DataServiceExecutor, Protocol):
    async def ensure_schema(self, request: SchemaRequest) -> SchemaResult:
        ...


class IdGeneratorExecutor(DataServiceExecutor, Protocol):
    async def next_id(self, entity: str) -> int:
        ...


class DataService(QueryExecutor, MutationExecutor, Protocol):
    pass


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
    "SchemaRequest",
    "SchemaResult",
    "SchemaExecutor",
    "IdGeneratorExecutor",
    "DataService"
]
