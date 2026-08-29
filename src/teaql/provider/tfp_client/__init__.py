from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Awaitable, Callable, Dict, Mapping, Optional

import httpx

from teaql.core.expr import (
    AndExpr, BinaryExpr, BinaryOp, ColumnExpr, Expr, OrExpr, ValueExpr,
)
from teaql.core.list import SmartList
from teaql.core.mutation import (
    DeleteCommand, InsertCommand, RecoverCommand, UpdateCommand,
)
from teaql.core.query import SelectQuery, SortDirection
from teaql.core.value import Value
from teaql.data_service import (
    DataService, DataServiceCapabilities, DataServiceOperation, ExecutionMetadata,
    MutationRequest, MutationResult, QueryRequest, QueryResult,
)
from teaql.runtime.telemetry import (
    NOOP_RUNTIME_TELEMETRY, RuntimeOperation, RuntimeTelemetry,
    inject_runtime_context, observe_runtime_operation,
)

HeaderProvider = Callable[[], Mapping[str, str] | Awaitable[Mapping[str, str]]]


class TfpError(RuntimeError):
    def __init__(self, code: str, message: str, status: Optional[int] = None):
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message
        self.status = status


@dataclass
class FederalQuery:
    entity: str
    filter_condition: Optional[Dict[str, Any]] = None
    limit: Optional[int] = None
    offset: Optional[int] = None
    order_items: list[Dict[str, str]] = field(default_factory=list)
    select_items: list[str] = field(default_factory=list)
    group_by_items: list[str] = field(default_factory=list)
    aggregate_items: list[Dict[str, str]] = field(default_factory=list)
    comment: Optional[str] = None
    purpose: Optional[str] = None


@dataclass
class FederalMutation:
    entity: str
    action: str
    payload: Dict[str, Any]
    comment: str
    id: Any = None
    expected_version: Optional[int] = None


class TeaQLFederalClient:
    """Canonical asynchronous TFP v1 client. It never serializes trusted policy."""

    def __init__(
        self, base_url: str, *, client: Optional[httpx.AsyncClient] = None,
        header_provider: Optional[HeaderProvider] = None,
        runtime_telemetry: Optional[RuntimeTelemetry] = None,
    ):
        self.base_url = base_url.rstrip("/")
        self._client = client or httpx.AsyncClient(base_url=self.base_url)
        self._owns_client = client is None
        self._header_provider = header_provider
        self._telemetry = runtime_telemetry or NOOP_RUNTIME_TELEMETRY

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def execute_query(self, query: FederalQuery) -> SmartList[Dict[str, Any]]:
        payload = _federal_query_payload(query)

        async def send() -> SmartList[Dict[str, Any]]:
            data = await self._post("/query", payload)
            rows = SmartList(data.get("data", []), facets=data.get("facets", {}))
            return rows

        return await observe_runtime_operation(
            self._telemetry,
            RuntimeOperation("tfp", "client.query", {"teaql.tfp.role": "client"}),
            send,
            lambda rows: {"teaql.result.cardinality": len(rows)},
        )

    async def execute_mutation(self, mutation: FederalMutation) -> Dict[str, Any]:
        payload = _federal_mutation_payload(mutation)
        return await observe_runtime_operation(
            self._telemetry,
            RuntimeOperation("tfp", "client.mutation", {"teaql.tfp.role": "client"}),
            lambda: self._post("/mutate", payload),
        )

    async def execute_for_stream(self, *_: Any, **__: Any) -> None:
        raise TfpError(
            "TFP_INVALID_REQUEST",
            "ordinary TFP v1 does not support streaming; use a dedicated protocol",
        )

    async def _headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if self._header_provider is not None:
            supplied = self._header_provider()
            if hasattr(supplied, "__await__"):
                supplied = await supplied  # type: ignore[assignment,misc]
            headers.update(dict(supplied))  # type: ignore[arg-type]
        inject_runtime_context(self._telemetry, headers)
        return headers

    async def _post(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        response = await self._client.post(path, json=payload, headers=await self._headers())
        if response.is_success:
            body = response.json()
            if not isinstance(body, dict):
                raise TfpError("TFP_INVALID_REQUEST", "TFP response must be an object", response.status_code)
            return body
        try:
            error = response.json()
        except ValueError:
            error = {}
        code = error.get("code", "TFP_EXECUTION_FAILED") if isinstance(error, dict) else "TFP_EXECUTION_FAILED"
        message = error.get("message", "TFP request failed") if isinstance(error, dict) else "TFP request failed"
        raise TfpError(str(code), str(message), response.status_code)


class TfpHttpProvider(DataService):
    """DataService adapter so generated Python requests can use a remote TFP endpoint."""

    def __init__(self, base_url: str, **client_options: Any):
        self.federal_client = TeaQLFederalClient(base_url, **client_options)

    @property
    def client(self) -> httpx.AsyncClient:
        """Compatibility access to the underlying HTTP client."""
        return self.federal_client._client

    async def aclose(self) -> None:
        await self.federal_client.aclose()

    def capabilities(self) -> DataServiceCapabilities:
        return DataServiceCapabilities(query=True, mutation=True)

    async def query(self, context: Any, request: QueryRequest) -> QueryResult:
        started_at = datetime.now()
        federal = _query_request(request)
        rows = await self.federal_client.execute_query(federal)
        return QueryResult(
            rows=rows,
            facets=rows.facets,
            metadata=ExecutionMetadata(
                backend="teaql-federal", operation=DataServiceOperation.Query,
                started_at=started_at, ended_at=datetime.now(), result_count=len(rows),
                comment=federal.comment,
            ),
        )

    async def mutate(self, context: Any, request: MutationRequest) -> MutationResult:
        started_at = datetime.now()
        federal = _mutation_request(request)
        data = await self.federal_client.execute_mutation(federal)
        records = data.get("data") or []
        generated = records[0] if records else {}
        affected = int(data.get("affectedRows", 0))
        operation = {
            "Create": DataServiceOperation.Insert,
            "Update": DataServiceOperation.Update,
            "Delete": DataServiceOperation.Delete,
            "Recover": DataServiceOperation.Recover,
        }[federal.action]
        return MutationResult(
            affected_rows=affected, generated_values=generated,
            persisted_record=generated or None,
            metadata=ExecutionMetadata(
                backend="teaql-federal", operation=operation,
                started_at=started_at, ended_at=datetime.now(), affected_rows=affected,
                comment=federal.comment,
            ),
        )


def _federal_query_payload(query: FederalQuery) -> Dict[str, Any]:
    if not query.comment or not query.comment.strip():
        raise TfpError("TFP_INVALID_REQUEST", "commentText is required")
    if not query.purpose or not query.purpose.strip():
        raise TfpError("TFP_POLICY_VIOLATION", "purposeText is required")
    if query.limit is not None and query.limit < 1:
        raise TfpError("TFP_INVALID_REQUEST", "limitValue must be positive")
    if query.offset is not None and query.offset < 0:
        raise TfpError("TFP_INVALID_REQUEST", "offsetValue must not be negative")
    payload: Dict[str, Any] = {
        "entity": query.entity,
        "orderItems": query.order_items,
        "selectItems": query.select_items,
        "groupByItems": query.group_by_items,
        "aggregateItems": query.aggregate_items,
        "commentText": query.comment.strip(),
        "purposeText": query.purpose.strip(),
    }
    if query.filter_condition is not None:
        payload["filterCondition"] = query.filter_condition
    if query.limit is not None:
        payload["limitValue"] = query.limit
    if query.offset is not None:
        payload["offsetValue"] = query.offset
    _reject_trusted_fields(payload)
    return payload


def _federal_mutation_payload(mutation: FederalMutation) -> Dict[str, Any]:
    if mutation.action not in {"Create", "Update", "Delete", "Recover"}:
        raise TfpError("TFP_INVALID_REQUEST", f"unsupported mutation action: {mutation.action}")
    if not mutation.comment or not mutation.comment.strip():
        raise TfpError("TFP_AUDIT_REASON_REQUIRED", "mutation audit reason is required")
    payload: Dict[str, Any] = {
        "entity": mutation.entity, "action": mutation.action,
        "payload": _json_value(mutation.payload), "comment": mutation.comment.strip(),
    }
    if mutation.id is not None:
        payload["id"] = _json_value(mutation.id)
    if mutation.expected_version is not None:
        payload["expectedVersion"] = mutation.expected_version
    _reject_trusted_fields(payload)
    return payload


def _query_request(request: QueryRequest) -> FederalQuery:
    query: SelectQuery = request.query
    unsupported = (
        query.expr_projection or query.having_expr or query.relations or query.raw_sql
        or query.raw_sql_search_criteria or query.dynamic_properties or query.raw_projections
        or query.object_group_bys or query.child_enhancements or query.stream_config
    )
    if unsupported:
        raise TfpError("TFP_INVALID_REQUEST", "query uses features outside canonical TFP v1")
    return FederalQuery(
        entity=query.entity,
        filter_condition=_encode_expr(query.filter_expr) if query.filter_expr else None,
        limit=query.slice.limit if query.slice else None,
        offset=query.slice.offset if query.slice else None,
        order_items=[{"field": item.field_name, "direction": item.direction.name}
                     for item in query.order_by_items if item.expr is None],
        select_items=list(query.projection), group_by_items=list(query.group_by_items),
        aggregate_items=[{"function": item.function.name, "field": item.field, "alias": item.alias}
                         for item in query.aggregates],
        comment=request._comment or query.comment_text,
        purpose=request._purpose,
    )


def _mutation_request(request: MutationRequest) -> FederalMutation:
    cmd = request._data
    comment = request.comment() or ""
    if isinstance(cmd, InsertCommand):
        return FederalMutation(cmd.entity, "Create", _json_value(cmd.values), comment)
    if isinstance(cmd, UpdateCommand):
        return FederalMutation(cmd.entity, "Update", _json_value(cmd.values), comment,
                               _json_value(cmd.id), cmd.expected_version_val)
    if isinstance(cmd, DeleteCommand):
        return FederalMutation(cmd.entity, "Delete", {}, comment,
                               _json_value(cmd.id), cmd.expected_version_val)
    if isinstance(cmd, RecoverCommand):
        return FederalMutation(cmd.entity, "Recover", {}, comment,
                               _json_value(cmd.id), cmd.expected_version_val)
    raise TfpError("TFP_INVALID_REQUEST", "batch mutation is outside canonical TFP v1")


def _encode_expr(expr: Expr) -> Dict[str, Any]:
    if isinstance(expr, AndExpr) or isinstance(expr, OrExpr):
        operator = "$and" if isinstance(expr, AndExpr) else "$or"
        if not expr.exprs:
            raise TfpError("TFP_INVALID_REQUEST", "logical expression requires operands")
        return {operator: [_encode_expr(value) for value in expr.exprs]}
    if not isinstance(expr, BinaryExpr) or not isinstance(expr.left, ColumnExpr) \
            or not isinstance(expr.right, ValueExpr):
        raise TfpError("TFP_INVALID_REQUEST", "unsupported TFP expression")
    value = _json_value(expr.right.value)
    operators = {
        BinaryOp.Eq: "$eq", BinaryOp.Gte: "$gte", BinaryOp.Lte: "$lte",
        BinaryOp.In: "$in",
    }
    if expr.op == BinaryOp.Like and isinstance(value, str) \
            and value.startswith("%") and value.endswith("%"):
        return {expr.left.name: {"$contains": value[1:-1]}}
    operator = operators.get(expr.op)
    if operator is None:
        raise TfpError("TFP_INVALID_REQUEST", f"unsupported predicate operator: {expr.op.name}")
    return {expr.left.name: {operator: value}}


def _json_value(value: Any) -> Any:
    if isinstance(value, Value):
        return value.to_json_value()
    if isinstance(value, dict):
        return {key: _json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    return value


def _reject_trusted_fields(value: Any, path: str = "$") -> None:
    forbidden = {
        "tenant", "tenantId", "merchant", "merchantId", "user", "userId",
        "permissions", "requestPolicy", "purposePolicy", "trustedContext",
        "hardLimit", "hard_limit", "hardLimitValue", "hard_limit_value",
        "continuousPageFetch", "continuous_page_fetch", "continuousPageRuntime",
        "idSetPagination", "id_set_pagination", "paginationWithIdSet",
    }
    if isinstance(value, dict):
        for key, child in value.items():
            if key in forbidden:
                raise TfpError("TFP_FORBIDDEN_FIELD", f"server-owned field at {path}.{key}")
            _reject_trusted_fields(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_trusted_fields(child, f"{path}[{index}]")


__all__ = [
    "FederalMutation", "FederalQuery", "TeaQLFederalClient", "TfpError",
    "TfpHttpProvider",
]
