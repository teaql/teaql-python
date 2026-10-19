from dataclasses import dataclass, field, replace
from datetime import datetime
from enum import Enum, auto
from typing import List, Dict, Any, Optional, Protocol, Union, AsyncIterator
from copy import deepcopy

from teaql.core.query import SelectQuery
from teaql.core.request_intent import QueryIntent, require_intent
from teaql.core.request_tree import QueryOperation, _RequestOwner, _owner_for, _retain_owner
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


_BIND_REQUEST = object()


class QueryRequest:
    __slots__ = ('query', 'trace_chain', '__intent', '__origin_entity',
                 '_log_intent_source', '_log_intent_queries', '_relation_assembly', '__owner')
    _UNSET = object()

    def __init__(self, query: SelectQuery, trace_chain=None, _comment=_UNSET, _purpose=_UNSET,
                 *, _origin_entity=None, _binding=None):
        comment = getattr(query, 'comment_text', None) if _comment is self._UNSET else _comment
        purpose = getattr(query, 'purpose_text', None) if _purpose is self._UNSET else _purpose
        self.__intent = QueryIntent(comment, purpose)
        previous = _owner_for(query)
        if _binding is not None:
            if (not isinstance(_binding, tuple) or len(_binding) != 2
                    or _binding[0] is not _BIND_REQUEST or not isinstance(_binding[1], _RequestOwner)):
                raise ValueError('QUERY_REQUEST_OWNERSHIP_INVALID: request binding is runtime-owned')
            self.__owner = _binding[1]
        elif previous is not None and previous.intent == self.__intent:
            self.__owner = previous
        else:
            self.__owner = _RequestOwner(None, query.entity, self.__intent.comment, self.__intent)
        self.__origin_entity = (_origin_entity if _origin_entity is not None else
            self.parent_request.origin_entity if self.parent_request is not None else self.request_name)
        self.query = deepcopy(query)
        self.query.comment_text = self.intent.comment
        self.query.purpose_text = self.intent.purpose
        self.trace_chain = deepcopy(trace_chain) if trace_chain is not None else list(deepcopy(self.__owner.source))
        self.__owner = replace(self.__owner, source=tuple(deepcopy(self.trace_chain)))
        _retain_owner(self.query, self.__owner)

    @property
    def parent_request(self):
        return self.__owner.parent

    @property
    def _invocation_identity(self):
        return self.__owner.invocation

    @property
    def root_request(self):
        root = self
        while root.parent_request is not None:
            root = root.parent_request
        return root

    @property
    def request_name(self):
        return self.__owner.name

    @property
    def local_comment(self):
        return self.__owner.comment

    @property
    def operation(self):
        return self.__owner.operation

    @property
    def business_trace_chain(self):
        comments, current = [], self
        while current is not None:
            comments.append(TraceNode(kind='comment', name=current.request_name,
                                      comment=current.local_comment))
            current = current.parent_request
        return (TraceNode(kind='purpose', name=self.root_request.request_name,
                          comment=self._purpose), *reversed(comments))

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
        require_intent(self.local_comment, 'comment', 'query')
        if any(not isinstance(node, TraceNode) for node in self.trace_chain):
            raise TypeError('QueryRequest trace must contain typed TraceNode values')

    def with_query(self, query: SelectQuery) -> 'QueryRequest':
        previous = _owner_for(query)
        if previous is not None and previous.invocation is not self.__owner.invocation:
            raise ValueError('QUERY_SCOPE_OWNER_MISMATCH: replacement belongs to another query invocation')
        result = QueryRequest(query, self.trace_chain, self._comment, self._purpose,
                              _origin_entity=self.origin_entity, _binding=(_BIND_REQUEST, self.__owner))
        if hasattr(self, '_log_intent_source'):
            result._log_intent_source = deepcopy(self._log_intent_source)
        # Derived work may drop a relation/projection whose private values are
        # still mentioned by the originating intent. Retain owned source graphs
        # solely for compiler classification, never on Context or log payloads.
        result._log_intent_queries = (*deepcopy(getattr(self, '_log_intent_queries', ())),
                                      deepcopy(self.query))
        if hasattr(self, '_relation_assembly'):
            result._relation_assembly = self._relation_assembly
        return result

    def _child(self, query, comment, operation=None, relation=None):
        owner = _RequestOwner(self, query.entity, require_intent(comment, 'comment', 'query'),
                              self.intent, operation)
        traces = deepcopy(self.trace_chain)
        if relation is not None:
            traces.append(TraceNode(kind='relation', name=relation,
                                    comment=f'{self.query.entity}.{relation}'))
        result = QueryRequest(query, traces, self._comment, self._purpose,
                              _origin_entity=self.origin_entity, _binding=(_BIND_REQUEST, owner))
        if hasattr(self, '_log_intent_source'):
            result._log_intent_source = self._log_intent_source
        result._log_intent_queries = (*getattr(self, '_log_intent_queries', ()), self.query)
        return result

    def derive_operation(self, query, operation: QueryOperation, relation=None):
        if not isinstance(operation, QueryOperation):
            raise ValueError('QUERY_OPERATION_INVALID: a typed generated descriptor is required')
        return self._child(query, operation.comment(), operation, relation)

    def derive_helper(self, query, comment):
        return self._child(query, comment)

    def for_count(self, alias=None, operation=None):
        """Derive exact-count execution without losing the caller's named result."""
        if alias is not None and not isinstance(alias, str):
            raise ValueError('QUERY_COUNT_ALIAS_INVALID: alias must be a string')
        if operation is not None and operation.alias is not None and operation.alias != alias:
            raise ValueError('QUERY_OPERATION_ALIAS_MISMATCH: count descriptor and result alias differ')
        return self.derive_operation(self.query.for_exact_count('__teaql_total' if alias is None else alias),
            operation or QueryOperation('named-count', alias=alias))

    def derive_child(self, query, relation=None):
        comment = getattr(query, 'comment_text', None)
        return self._child(query, 'load ' + query.entity if comment is None else comment, relation=relation)

    def derive(self, query, relation, operation=None):
        parent = self.derive_operation(self.query, operation or QueryOperation('relation-select', relation=relation))
        return parent.derive_child(query, relation)

    def derive_aggregate(self, query, relation, operation):
        """Anonymous aggregate work executes its operation, not a value load."""
        facet = self.parent_request
        if facet is not None and facet.operation is not None and facet.operation.kind == 'facet':
            branch = facet.derive_helper(query, 'aggregate ' + facet.operation.relation)
        else:
            branch = self.derive_operation(query, operation)
        branch.trace_chain = [*deepcopy(self.trace_chain), TraceNode(
            kind='relation', name=relation, comment=f'{self.query.entity}.{relation}')]
        branch.__owner = replace(branch.__owner, source=tuple(deepcopy(branch.trace_chain)))
        _retain_owner(branch.query, branch.__owner)
        branch._log_intent_queries = (*getattr(self, '_log_intent_queries', ()), self.query)
        if hasattr(self, '_log_intent_source'):
            branch._log_intent_source = self._log_intent_source
        return branch if query.comment_text is None else branch.derive_child(query)

    def with_log_intent(self, source, assembly=None):
        self._log_intent_source = source
        self._relation_assembly = assembly
        return self

    def comment(self, text: str) -> 'QueryRequest':
        result = self.with_query(self.query)
        require_intent(text, 'comment', 'query')
        if result.parent_request is None:
            result.__intent = QueryIntent(text, self._purpose)
        result.__owner = _RequestOwner(result.parent_request, result.request_name, text,
                                      result.intent, result.operation)
        _retain_owner(result.query, result.__owner)
        result.query.comment_text = result.intent.comment
        return result

    def purpose(self, text: str) -> 'QueryRequest':
        if self.parent_request is not None and text != self._purpose:
            raise ValueError('QUERY_ROOT_PURPOSE_IMMUTABLE: derived requests retain the root purpose')
        result = self.with_query(self.query)
        result.__intent = QueryIntent(self._comment, text)
        result.__owner = _RequestOwner(result.parent_request, result.request_name, result.local_comment,
                                      result.intent, result.operation)
        _retain_owner(result.query, result.__owner)
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
    # Legacy trace_chain is the physical route. This separate business chain is
    # projected as SqlLogEntry.trace_chain; SqlLogEntry.trace_path stays physical.
    request_trace_chain: tuple[TraceNode, ...] = field(default_factory=tuple)
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
    # Logical mutation summaries own ordered physical children. Batch summaries
    # retain per-item grouping; leaves are empty and never point to a summary.
    statements: tuple['ExecutionMetadata', ...] = field(default_factory=tuple)


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
