import copy
import json
import os
import re
import tempfile
import hashlib
import time
import asyncio
from datetime import date, datetime
from decimal import Decimal
from urllib.parse import parse_qs, unquote, urlparse
from dataclasses import dataclass
from typing import Any, Callable, Dict, Generic, Iterable, Optional, TypeVar
from teaql.runtime import SqlLogOperation, _SCHEMA_INVOCATION

TPage = TypeVar("TPage")

class SmartList(list[TPage], Generic[TPage]):
    def __init__(self, data: Iterable[TPage] = (), facets: Optional[Dict[str, Any]] = None,
                 total_count: Optional[int] = None):
        super().__init__(data)
        self.facets = facets or {}
        self.total_count = len(self) if total_count is None else total_count

    @property
    def data(self) -> "SmartList[TPage]":
        return self

    def facet(self, name: str) -> Any:
        return self.facets.get(name)

    def map(self, mapper: Callable[[TPage], Any]) -> "SmartList[Any]":
        return SmartList((mapper(item) for item in self), self.facets, self.total_count)

    def filter(self, predicate: Callable[[TPage], bool]) -> "SmartList[TPage]":
        return SmartList((item for item in self if predicate(item)), self.facets, self.total_count)

    def first(self) -> Optional[TPage]:
        return self[0] if self else None

    def last(self) -> Optional[TPage]:
        return self[-1] if self else None

@dataclass(frozen=True)
class TeaQLPage(Generic[TPage]):
    data: SmartList[TPage]
    total_count: int
    offset: int
    limit: int

ENTITY_SCHEMAS = {
"Platform": {
    "table": "platform_data",
    "columns": {"id": "integer", "name": "text", "base_url": "text", "create_time": "datetime", "update_time": "datetime", "version": "integer"},
    "required": {"id": True, "name": True, "base_url": True, "create_time": True, "update_time": True, "version": True},
    "relations": {**{}, **{"school_type_list": {"target_entity": "SchoolType", "local_key": "id", "foreign_key": "platform", "many": True}, "school_list": {"target_entity": "School", "local_key": "id", "foreign_key": "platform", "many": True}}},
},
"SchoolType": {
    "table": "school_type_data",
    "columns": {"platform": "integer", "id": "integer", "name": "text", "code": "text", "display_order": "decimal", "version": "integer"},
    "required": {"platform": True, "id": True, "name": True, "code": True, "display_order": True, "version": True},
    "relations": {**{"platform": {"target_entity": "Platform", "local_key": "platform", "foreign_key": "id", "many": False}}, **{"school_list": {"target_entity": "School", "local_key": "id", "foreign_key": "school_type", "many": True}}},
},
"School": {
    "table": "school_data",
    "columns": {"id": "integer", "platform": "integer", "school_type": "integer", "name": "text", "address": "text", "established_date": "date", "student_capacity": "integer", "active": "bool", "create_time": "datetime", "update_time": "datetime", "version": "integer"},
    "required": {"id": True, "platform": True, "school_type": True, "name": True, "address": True, "established_date": True, "student_capacity": True, "active": True, "create_time": True, "update_time": True, "version": True},
    "relations": {**{"platform": {"target_entity": "Platform", "local_key": "platform", "foreign_key": "id", "many": False}, "school_type": {"target_entity": "SchoolType", "local_key": "school_type", "foreign_key": "id", "many": False}}, **{}},
}
}

class Value:
    @staticmethod
    def Text(val): return val
    @staticmethod
    def I64(val): return val
    @staticmethod
    def F64(val): return val
    @staticmethod
    def Decimal(val): return val
    @staticmethod
    def Date(val): return val
    @staticmethod
    def DateTime(val): return val
    @staticmethod
    def Bool(val): return val
    @staticmethod
    def JSON(val): return val
    @staticmethod
    def Object(val): return val
    @staticmethod
    def from_any(val): return val

class SelectQuery:
    def __init__(self, entity):
        self.entity = entity
        self._comment = None
        self._purpose = None
        self._trace_path = []
        self._limit = None
        self._offset = None
        self._order_by = []
        self._group_by = []
        self._aggregates = []
        self._filters = []
        self._projection = []
        self._relations = []
        self._relation_aggregates = []
        self._facets = []
        self._partition_by = None
        self._top_n_probe_parent_threshold = None
        self._continuous_page_fetch_options = None
        self.id_set_pagination = None

    def comment(self, c): self._comment = c
    def purpose(self, p): self._purpose = p
    def limit(self, n):
        if not isinstance(n, int) or isinstance(n, bool) or n < 1:
            raise ValueError("QUERY_INVALID_LIMIT: limit must be a positive integer")
        if n > 10_000: raise ValueError("QUERY_HARD_LIMIT_EXCEEDED: limit exceeds 10000")
        self._limit = n
        return self
    def offset(self, n):
        if not isinstance(n, int) or isinstance(n, bool) or n < 0:
            raise ValueError("QUERY_INVALID_OFFSET: offset must be a non-negative integer")
        self._offset = n
        return self
    def order_by(self, f, d): self._order_by.append((f, d))
    def group_by(self, f): self._group_by.append(f)
    def count_field(self, f, n): self._aggregates.append(("count", f, n))
    def aggregate(self, func, field, ret_name): self._aggregates.append((func, field, ret_name))
    def and_filter(self, expr): self._filters.append(expr)
    def project(self, *fields):
        for field in fields:
            if field not in self._projection: self._projection.append(field)
        return self
    def relation_query(self, name, query): self._relations.append({"name": name, "query": query})
    def top_n_probe_parent_threshold(self, threshold):
        if not isinstance(threshold, int) or isinstance(threshold, bool) or threshold < 0:
            raise ValueError("Top-N probe parent threshold must not be negative")
        self._top_n_probe_parent_threshold = threshold
        return self
    def relation_aggregate(self, relation_name, alias, query, single_result=True):
        self._relation_aggregates.append({
            "relation_name": relation_name, "alias": alias,
            "query": query, "single_result": single_result})
        return self
    def facet_by(self, name, relation_name, query, include_all_facets=True):
        self._facets.append({
            "name": name, "relation_name": relation_name, "query": query,
            "include_all_facets": include_all_facets})
        return self
    def for_exact_count(self, alias="__teaql_total"):
        query = copy.deepcopy(self)
        query._projection = []
        query._relations = []
        query._facets = []
        query._order_by = []
        query._offset = None
        query._limit = None
        query._group_by = []
        query._aggregates = [("count", "id", alias)]
        return query
    def optimize_for_continuous_page_fetch(self):
        return self.optimize_for_continuous_page_fetch_with("default", 600)
    def optimize_for_continuous_page_fetch_with(self, namespace, ttl_seconds):
        if not namespace or not namespace.strip(): raise ValueError("continuous page namespace must not be empty")
        if ttl_seconds <= 0: raise ValueError("continuous page ttl_seconds must be positive")
        self._continuous_page_fetch_options = {"namespace": namespace, "ttl_seconds": ttl_seconds}
        return self
    def optimize_pagination_with_id_set(self):
        return self.optimize_pagination_with_id_set_config("default", 600, 3_000_000)
    def optimize_pagination_with_id_set_config(self, namespace, ttl_seconds, max_ids):
        if not namespace or not namespace.strip(): raise ValueError("ID set pagination namespace must not be empty")
        if ttl_seconds <= 0: raise ValueError("ID set pagination ttl_seconds must be positive")
        if max_ids <= 0: raise ValueError("ID set pagination max_ids must be positive")
        self.id_set_pagination = {"namespace": namespace, "ttl_seconds": ttl_seconds, "max_ids": max_ids}
        return self

class QueryRequest:
    def __init__(self, query):
        self.query = query

async def _execute_facets(service, context, outer_query):
    facets = {}
    for facet in getattr(outer_query, "_facets", []):
        membership = copy.deepcopy(outer_query)
        membership._facets = []
        membership._relations = []
        membership._order_by = []
        membership._offset = None
        membership._limit = None
        membership._projection = []
        membership._aggregates = [("count", "id", "__teaql_facet_count")]
        membership._group_by = [facet["relation_name"]]
        membership_rows = (await service.query(context, QueryRequest(membership))).rows
        counts = {str(row[facet["relation_name"]]): int(row["__teaql_facet_count"])
                  for row in membership_rows if row.get(facet["relation_name"]) is not None}

        nested = copy.deepcopy(facet["query"])
        nested._facets = []
        aliases = [alias for function, _field, alias in nested._aggregates
                   if function.lower() == "count"] or ["count"]
        nested._aggregates = []
        nested._group_by = []
        nested_rows = (await service.query(context, QueryRequest(nested))).rows
        decorated = []
        for row in nested_rows:
            count = counts.get(str(row.get("id")), 0)
            if not facet["include_all_facets"] and count == 0: continue
            copy_row = dict(row)
            for alias in aliases: copy_row[alias] = count
            decorated.append(copy_row)
        facets[facet["name"]] = SmartList(decorated)
    return facets

class MutationRequest:
    def __init__(self, cmd):
        self.cmd = cmd
        self.comment = None

class InsertCommand:
    def __init__(self, entity, payload):
        self.entity = entity
        self.payload = payload

class UpdateCommand:
    def __init__(self, entity, pk, expected_version=None):
        self.entity = entity
        self.pk = pk
        self.expected_version = expected_version
        self.values = {}

    def value(self, k, v):
        self.values[k] = v

class DeleteCommand:
    def __init__(self, entity, pk, expected_version=None):
        self.entity = entity
        self.pk = pk
        self.expected_version = expected_version

def eq(a, b): return {"type": "eq", "field": a, "value": b}
def ne(a, b): return {"type": "ne", "field": a, "value": b}
def contain(a, b): return {"type": "contain", "field": a, "value": b}
def not_contain(a, b): return {"type": "not_contain", "field": a, "value": b}
def begin_with(a, b): return {"type": "begin_with", "field": a, "value": b}
def not_begin_with(a, b): return {"type": "not_begin_with", "field": a, "value": b}
def end_with(a, b): return {"type": "end_with", "field": a, "value": b}
def not_end_with(a, b): return {"type": "not_end_with", "field": a, "value": b}
def sound_like(a, b): return {"type": "sound_like", "field": a, "value": b}
def one_of(a, values): return {"type": "in", "field": a, "value": list(values)}
def in_list(a, values): return one_of(a, values)
def not_in_list(a, values): return {"type": "not_in", "field": a, "value": list(values)}
def gte(a, b): return {"type": "gte", "field": a, "value": b}
def lte(a, b): return {"type": "lte", "field": a, "value": b}
def gt(a, b): return {"type": "gt", "field": a, "value": b}
def lt(a, b): return {"type": "lt", "field": a, "value": b}
def column(a): return a
def value(a): return a
def between(a, lower, upper): return {"type": "between", "field": a, "value": [lower, upper]}
def is_null(a): return {"type": "is_null", "field": a}
def is_not_null(a): return {"type": "is_not_null", "field": a}
def in_subquery(left, entity, query):
    return {"type": "in_subquery", "field": left, "entity": entity, "query": query}
def not_in_subquery(left, entity, query):
    return {"type": "not_in_subquery", "field": left, "entity": entity, "query": query}

def _soundex(value):
    text = "".join(ch for ch in str(value or "").upper() if "A" <= ch <= "Z")
    if not text: return "?000"
    groups = {**dict.fromkeys("BFPV", "1"), **dict.fromkeys("CGJKQSXZ", "2"),
              **dict.fromkeys("DT", "3"), "L": "4", **dict.fromkeys("MN", "5"), "R": "6"}
    result, previous = text[0], groups.get(text[0], "")
    for char in text[1:]:
        code = groups.get(char, "")
        if code and code != previous: result += code
        previous = code
        if len(result) == 4: break
    return (result + "000")[:4]

def _prepare_continuous_page(context, original):
    query = copy.deepcopy(original)
    options = getattr(query, "_continuous_page_fetch_options", None)
    if options is None or context is None or not hasattr(context, "continuous_page_cursor"):
        return query, None
    if query._limit is None or query._limit <= 0 or len(query._order_by) != 1 or query._order_by[0][0] != "id":
        context.observe_continuous_page("OFFSET_FALLBACK:UNSUPPORTED_QUERY_SHAPE")
        return query, None
    normalized = copy.deepcopy(query)
    normalized._offset = 0
    normalized._comment = None
    normalized._purpose = None
    normalized._continuous_page_fetch_options = None
    owner = context.get_resource("user_identifier") or ""
    digest = hashlib.sha256(
        f'{options["namespace"]}|{owner}|{vars(normalized)!r}'.encode("utf-8")
    ).hexdigest()
    query_key = f"teaql:continuous-page:v1:{digest}"
    execution = {"query_key": query_key, "offset": query._offset or 0, "limit": query._limit,
                 "direction": query._order_by[0][1].lower(), "ttl": options["ttl_seconds"], "optimized": False}
    if execution["offset"] == 0:
        context.observe_continuous_page("OFFSET_FALLBACK:FIRST_PAGE")
        return query, execution
    cursor = context.continuous_page_cursor(query_key, execution["offset"])
    if cursor is None:
        context.observe_continuous_page("OFFSET_FALLBACK:CACHE_MISS")
        return query, execution
    query._filters.append((lt if execution["direction"] == "desc" else gt)("id", cursor["boundary"]))
    query._offset = 0
    execution["optimized"] = True
    execution["cursor_id"] = cursor["cursor_id"]
    context.observe_continuous_page("CURSOR_SEEK", cursor["cursor_id"])
    return query, execution

def _register_continuous_page(context, execution, rows):
    if execution is None or len(rows) != execution["limit"] or not rows or "id" not in rows[-1]: return
    cursor_id = f"cpg_{time.time_ns():x}"
    next_offset = execution["offset"] + len(rows)
    context.put_continuous_page_cursor(execution["query_key"], next_offset, {
        "cursor_id": cursor_id, "boundary": rows[-1]["id"], "expires_at": time.time() + execution["ttl"]
    })
    if execution["optimized"]: context.observe_continuous_page("CURSOR_SEEK", execution["cursor_id"])

class MutationResult(dict):
    def __init__(self, values, persisted_record=None):
        super().__init__(values)
        self.persisted_record = persisted_record


class TeaQLClient:
    def __init__(self, storage_path=None):
        self.storage_path = storage_path
        self._data = {}
        self._next_ids = {}
        self._graph_snapshot = None
        self._load()

    async def begin(self, context):
        if self._graph_snapshot is not None:
            raise RuntimeError("A graph transaction is already active on this data service")
        self._graph_snapshot = (copy.deepcopy(self._data), copy.deepcopy(self._next_ids))
        return self

    async def commit(self, context):
        if self._graph_snapshot is None:
            raise RuntimeError("No graph transaction is active")
        self._persist()
        self._graph_snapshot = None

    async def rollback(self, context):
        if self._graph_snapshot is None:
            raise RuntimeError("No graph transaction is active")
        self._data, self._next_ids = self._graph_snapshot
        self._graph_snapshot = None
        self._persist()

    def _load(self):
        if not self.storage_path or not os.path.exists(self.storage_path):
            return
        with open(self.storage_path, "r", encoding="utf-8") as stream:
            state = json.load(stream)
        self._data = state.get("data", {})
        self._next_ids = state.get("next_ids", {})

    def _persist(self):
        if not self.storage_path:
            return
        parent = os.path.dirname(os.path.abspath(self.storage_path))
        os.makedirs(parent, exist_ok=True)
        fd, temporary_path = tempfile.mkstemp(prefix=".teaql-", suffix=".json", dir=parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                json.dump({"data": self._data, "next_ids": self._next_ids}, stream)
            os.replace(temporary_path, self.storage_path)
        finally:
            if os.path.exists(temporary_path):
                os.unlink(temporary_path)

    def _next_id(self, entity):
        value = int(self._next_ids.get(entity, 1))
        self._next_ids[entity] = value + 1
        return value

    async def mutate(self, context, req):
        command = req.cmd
        if not context.consume_mutation_checked(command):
            context.check_and_fix_mutation(command)
        table = self._data.setdefault(command.entity, {})
        if hasattr(command, "payload"):
            record = copy.deepcopy(command.payload)
            record_id = record.get("id") or self._next_id(command.entity)
            record["id"] = record_id
            record["version"] = int(record.get("version") or 0) + 1
            table[str(record_id)] = record
            if self._graph_snapshot is None:
                self._persist()
            result = MutationResult(
                {"success": True, "id": record_id, "version": record["version"]},
                copy.deepcopy(record))
            await context.emit_mutation_audit(req, result)
            return result
        if hasattr(command, "values"):
            record_id = command.pk
            key = str(record_id)
            if key not in table:
                raise KeyError(f"{command.entity}({record_id}) does not exist")
            record = table[key]
            if command.expected_version is not None and record.get("version") != command.expected_version:
                raise RuntimeError(
                    f"Optimistic lock failed for {command.entity}({record_id}): "
                    f"expected version {command.expected_version}"
                )
            record.update(copy.deepcopy(command.values))
            record["version"] = int(record.get("version") or 0) + 1
            if self._graph_snapshot is None:
                self._persist()
            result = MutationResult(
                {"success": True, "id": record_id, "version": record["version"]},
                copy.deepcopy(record))
            await context.emit_mutation_audit(req, result)
            return result
        if hasattr(command, "pk"):
            record_id = command.pk
            if str(record_id) not in table:
                raise KeyError(f"{command.entity}({record_id}) does not exist")
            if command.expected_version is not None and table[str(record_id)].get("version") != command.expected_version:
                raise RuntimeError(
                    f"Optimistic lock failed for {command.entity}({record_id}): "
                    f"expected version {command.expected_version}"
                )
            current_version = int(table[str(record_id)].get("version") or 0)
            table[str(record_id)]["version"] = -(current_version + 1)
            if self._graph_snapshot is None:
                self._persist()
            persisted = copy.deepcopy(table[str(record_id)])
            result = MutationResult({
                "success": True, "id": record_id,
                "version": persisted["version"], "deleted": True,
            }, persisted)
            await context.emit_mutation_audit(req, result)
            return result
        raise TypeError(f"Unsupported mutation command: {type(command).__name__}")

    async def query(self, context, req):
        query, continuous = _prepare_continuous_page(context, req.query)
        rows = [copy.deepcopy(row) for row in self._data.get(query.entity, {}).values()]
        for expression in query._filters:
            if expression.get("type") in ("in_subquery", "not_in_subquery"):
                child_result = await self.query(context, QueryRequest(expression["query"]))
                projected = expression["query"]._projection
                projected_field = projected[0] if projected else "id"
                child_values = {row.get(projected_field) for row in child_result.rows}
                if expression.get("type") == "in_subquery":
                    rows = [row for row in rows if row.get(expression["field"]) in child_values]
                else:
                    rows = [row for row in rows if row.get(expression["field"]) not in child_values]
            elif expression.get("type") == "eq":
                rows = [row for row in rows if row.get(expression["field"]) == expression["value"]]
            elif expression.get("type") == "contain":
                rows = [row for row in rows if expression["value"] in str(row.get(expression["field"], ""))]
            elif expression.get("type") == "not_contain":
                rows = [row for row in rows if expression["value"] not in str(row.get(expression["field"], ""))]
            elif expression.get("type") == "begin_with":
                rows = [row for row in rows if str(row.get(expression["field"], "")).startswith(str(expression["value"]))]
            elif expression.get("type") == "not_begin_with":
                rows = [row for row in rows if not str(row.get(expression["field"], "")).startswith(str(expression["value"]))]
            elif expression.get("type") == "end_with":
                rows = [row for row in rows if str(row.get(expression["field"], "")).endswith(str(expression["value"]))]
            elif expression.get("type") == "not_end_with":
                rows = [row for row in rows if not str(row.get(expression["field"], "")).endswith(str(expression["value"]))]
            elif expression.get("type") == "sound_like":
                rows = [row for row in rows if _soundex(row.get(expression["field"])) == _soundex(expression["value"])]
            elif expression.get("type") == "in":
                rows = [row for row in rows if row.get(expression["field"]) in expression["value"]]
            elif expression.get("type") == "not_in":
                rows = [row for row in rows if row.get(expression["field"]) not in expression["value"]]
            elif expression.get("type") == "ne":
                rows = [row for row in rows if row.get(expression["field"]) != expression["value"]]
            elif expression.get("type") == "between":
                rows = [row for row in rows if expression["value"][0] <= row.get(expression["field"]) <= expression["value"][1]]
            elif expression.get("type") == "is_null":
                rows = [row for row in rows if row.get(expression["field"]) is None]
            elif expression.get("type") == "is_not_null":
                rows = [row for row in rows if row.get(expression["field"]) is not None]
            elif expression.get("type") == "gte":
                rows = [row for row in rows if row.get(expression["field"]) >= expression["value"]]
            elif expression.get("type") == "lte":
                rows = [row for row in rows if row.get(expression["field"]) <= expression["value"]]
            elif expression.get("type") == "gt":
                rows = [row for row in rows if row.get(expression["field"]) > expression["value"]]
            elif expression.get("type") == "lt":
                rows = [row for row in rows if row.get(expression["field"]) < expression["value"]]
        if query._aggregates:
            if query._group_by:
                grouped = {}
                for row in rows:
                    key = tuple(row.get(field) for field in query._group_by)
                    grouped.setdefault(key, []).append(row)
                aggregate_rows = []
                for key, group_rows in grouped.items():
                    values = dict(zip(query._group_by, key))
                    for function, _field, alias in query._aggregates:
                        if function.lower() != "count": raise ValueError(f"Unsupported local aggregate: {function}")
                        values[alias] = len(group_rows)
                    aggregate_rows.append(values)
                return type('QueryResult', (object,), {'rows': aggregate_rows, 'facets': {}})
            values = {}
            for function, _field, alias in query._aggregates:
                if function.lower() != "count": raise ValueError(f"Unsupported local aggregate: {function}")
                values[alias] = len(rows)
            return type('QueryResult', (object,), {'rows': [values], 'facets': {}})
        for field, direction in reversed(query._order_by):
            rows.sort(key=lambda row: (row.get(field) is None, row.get(field)), reverse=direction.lower() == "desc")
        start = query._offset or 0
        end = None if query._limit is None else start + query._limit
        result_rows = rows[start:end]
        _register_continuous_page(context, continuous, result_rows)
        facets = await _execute_facets(self, context, query)
        return type('QueryResult', (object,), {'rows': result_rows, 'facets': facets})

    async def close(self):
        pass


class _Transaction:
    def __init__(self, connection):
        self.connection = connection

    async def __aenter__(self):
        await self.connection.begin()
        return self.connection

    async def __aexit__(self, exc_type, exc, traceback):
        if exc_type is None:
            await self.connection.commit()
        else:
            await self.connection.rollback()


class _NoopTransaction:
    async def __aenter__(self): return self
    async def __aexit__(self, exc_type, exc, traceback): return False


class _AsyncSqlGraphTransaction:
    def __init__(self, client, connection):
        self.client, self.connection = client, connection

    async def mutate(self, context, request):
        return await self.client.mutate(context, request)

    async def query(self, context, request):
        return await self.client.query(context, request)

    async def commit(self, context):
        try:
            await self.connection.commit()
        finally:
            await self.connection.close()
            self.client._graph_connection = None

    async def rollback(self, context):
        try:
            await self.connection.rollback()
        finally:
            await self.connection.close()
            self.client._graph_connection = None


class _PostgreSQLConnection:
    def __init__(self, raw):
        self.raw = raw
        self.current_transaction = None

    def transaction(self): return _Transaction(self)
    async def begin(self):
        self.current_transaction = self.raw.transaction()
        await self.current_transaction.start()
    async def commit(self):
        await self.current_transaction.commit()
        self.current_transaction = None
    async def rollback(self):
        await self.current_transaction.rollback()
        self.current_transaction = None
    async def execute(self, sql, *params):
        status = await self.raw.execute(sql, *params)
        try: return int(status.rsplit(" ", 1)[-1])
        except ValueError: return -1
    async def fetch_all(self, sql, *params):
        return [dict(row) for row in await self.raw.fetch(sql, *params)]
    async def fetch_one(self, sql, *params):
        row = await self.raw.fetchrow(sql, *params)
        return None if row is None else dict(row)
    async def fetch_value(self, sql, *params):
        return await self.raw.fetchval(sql, *params)
    async def close(self): await self.raw.close()


class _SQLiteConnection:
    def __init__(self, raw): self.raw = raw
    def transaction(self): return _Transaction(self)
    async def begin(self): await self.raw.execute("BEGIN")
    async def commit(self): await self.raw.commit()
    async def rollback(self): await self.raw.rollback()
    async def execute(self, sql, *params):
        cursor = await self.raw.execute(sql, params)
        affected = cursor.rowcount
        await cursor.close()
        return affected
    async def fetch_all(self, sql, *params):
        cursor = await self.raw.execute(sql, params)
        rows = [dict(row) for row in await cursor.fetchall()]
        await cursor.close()
        return rows
    async def fetch_one(self, sql, *params):
        cursor = await self.raw.execute(sql, params)
        row = await cursor.fetchone()
        await cursor.close()
        return None if row is None else dict(row)
    async def fetch_value(self, sql, *params):
        row = await self.fetch_one(sql, *params)
        return None if row is None else next(iter(row.values()))
    async def close(self): await self.raw.close()


class _MySQLConnection:
    def __init__(self, raw): self.raw = raw
    def transaction(self): return _Transaction(self)
    async def begin(self): await self.raw.begin()
    async def commit(self): await self.raw.commit()
    async def rollback(self): await self.raw.rollback()
    async def execute(self, sql, *params):
        async with self.raw.cursor() as cursor:
            await cursor.execute(sql, params)
            return cursor.rowcount
    async def fetch_all(self, sql, *params):
        async with self.raw.cursor() as cursor:
            await cursor.execute(sql, params)
            return list(await cursor.fetchall())
    async def fetch_one(self, sql, *params):
        async with self.raw.cursor() as cursor:
            await cursor.execute(sql, params)
            return await cursor.fetchone()
    async def fetch_value(self, sql, *params):
        row = await self.fetch_one(sql, *params)
        return None if row is None else next(iter(row.values()))
    async def close(self): self.raw.close()


class AsyncSqlTeaQLClient:
    """Shared async SQL persistence for PostgreSQL, MySQL, and SQLite."""

    database_kind = None
    identifier_quote = '"'
    _identifier_pattern = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
    _type_maps = {
        "postgres": {
            "bool": "BOOLEAN", "integer": "BIGINT", "float": "DOUBLE PRECISION",
            "decimal": "NUMERIC", "date": "DATE", "datetime": "TIMESTAMPTZ",
            "json": "JSONB", "text": "TEXT",
        },
        "mysql": {
            "bool": "BOOLEAN", "integer": "BIGINT", "float": "DOUBLE",
            "decimal": "DECIMAL(38, 10)", "date": "DATE", "datetime": "DATETIME(6)",
            "json": "JSON", "text": "TEXT",
        },
        "sqlite": {
            "bool": "INTEGER", "integer": "INTEGER", "float": "REAL",
            "decimal": "NUMERIC", "date": "TEXT", "datetime": "TEXT",
            "json": "TEXT", "text": "TEXT",
        },
    }

    def __init__(self, database_url):
        if not database_url:
            raise ValueError("database_url is required")
        self.database_url = database_url
        self._graph_connection = None

    async def begin(self, context):
        if self._graph_connection is not None:
            raise RuntimeError("A graph transaction is already active on this data service")
        connection = await self._connect()
        await connection.begin()
        self._graph_connection = connection
        return _AsyncSqlGraphTransaction(self, connection)

    @staticmethod
    def _table_name(entity):
        schema = ENTITY_SCHEMAS.get(entity)
        if schema is not None:
            return schema["table"]
        snake = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", entity)
        snake = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", snake).lower()
        return f"{snake}_data"

    def _identifier(self, value):
        if not self._identifier_pattern.fullmatch(value):
            raise ValueError(f"Unsafe SQL identifier: {value!r}")
        quote = self.identifier_quote
        return f"{quote}{value}{quote}"

    def _placeholder(self, index):
        if self.database_kind == "postgres": return f"${index}"
        if self.database_kind == "mysql": return "%s"
        return "?"

    def _normalize(self, value):
        value = getattr(value, "id", value)
        if isinstance(value, (dict, list)):
            return json.dumps(value)
        if self.database_kind == "sqlite" and isinstance(value, Decimal):
            return str(value)
        if self.database_kind == "sqlite" and isinstance(value, (date, datetime)):
            return value.isoformat()
        return value

    @staticmethod
    def _logical_type(value):
        value = getattr(value, "id", value)
        if isinstance(value, bool): return "bool"
        if isinstance(value, int): return "integer"
        if isinstance(value, float): return "float"
        if isinstance(value, Decimal): return "decimal"
        if isinstance(value, datetime): return "datetime"
        if isinstance(value, date): return "date"
        if isinstance(value, (dict, list)): return "json"
        return "text"

    def _column_type(self, logical_type):
        return self._type_maps[self.database_kind].get(logical_type, "BIGINT")

    async def _column_exists(self, connection, table, field):
        if self.database_kind == "postgres":
            value = await connection.fetch_value(
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_schema = current_schema() AND table_name = $1 AND column_name = $2",
                table, field,
            )
            return value is not None
        if self.database_kind == "mysql":
            value = await connection.fetch_value(
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_schema = DATABASE() AND table_name = %s AND column_name = %s",
                table, field,
            )
            return value is not None
        rows = await connection.fetch_all(f"PRAGMA table_info({self._identifier(table)})")
        return any(row["name"] == field for row in rows)

    async def _ensure_table(self, connection, entity, values=None):
        table = self._table_name(entity)
        quoted_table = self._identifier(table)
        await connection.execute(
            f"CREATE TABLE IF NOT EXISTS {quoted_table} ("
            f"{self._identifier('id')} BIGINT PRIMARY KEY, "
            f"{self._identifier('version')} BIGINT NOT NULL)"
        )
        columns = dict(ENTITY_SCHEMAS.get(entity, {}).get("columns", {}))
        required = dict(ENTITY_SCHEMAS.get(entity, {}).get("required", {}))
        for field, value in (values or {}).items():
            columns.setdefault(field, self._logical_type(value))
        for field, logical_type in columns.items():
            if field in ("id", "version") or await self._column_exists(connection, table, field):
                continue
            await connection.execute(
                f"ALTER TABLE {quoted_table} ADD COLUMN {self._identifier(field)} "
                f"{self._column_type(logical_type)}"
                f"{' NOT NULL' if required.get(field, False) else ''}"
            )
        return table

    async def _ensure_schema(self, context, invocation):
        if invocation is not _SCHEMA_INVOCATION:
            raise PermissionError("Ensure Schema must be invoked through UserContext.ensure_schema()")
        owns_connection = self._graph_connection is None
        connection = await self._connect() if owns_connection else self._graph_connection
        try:
            async with (connection.transaction() if owns_connection else _NoopTransaction()):
                for entity in ENTITY_SCHEMAS:
                    await self._ensure_table(connection, entity)
                if context is not None:
                    roots = context.get_resource("root_graphs") or ()
                    constants = context.get_resource("initial_graphs") or ()
                    for graph, reconcile in (tuple((g, False) for g in roots)
                                             + tuple((g, True) for g in constants)):
                        table = await self._ensure_table(connection, graph.entity, graph.fields)
                        seed_id = int(graph.fields["id"])
                        existing = await connection.fetch_one(
                            f"SELECT * FROM {self._identifier(table)} WHERE {self._identifier('id')} = {self._placeholder(1)}",
                            seed_id)
                        if existing is None:
                            record = dict(graph.fields)
                            record["version"] = int(record.get("version") or 1)
                            fields = list(record)
                            await connection.execute(
                                f"INSERT INTO {self._identifier(table)} ({', '.join(self._identifier(f) for f in fields)}) VALUES ({', '.join(self._placeholder(i) for i in range(1, len(fields)+1))})",
                                *(self._normalize(record[f]) for f in fields))
                        elif reconcile:
                            existing = dict(existing)
                            changed = {k: v for k, v in graph.fields.items()
                                       if k != "id" and existing.get(k) != self._normalize(v)}
                            if changed:
                                fields = list(changed)
                                next_index = len(fields) + 1
                                await connection.execute(
                                    f"UPDATE {self._identifier(table)} SET {', '.join(self._identifier(f) + ' = ' + self._placeholder(i) for i, f in enumerate(fields, 1))}, {self._identifier('version')} = {self._identifier('version')} + 1 WHERE {self._identifier('id')} = {self._placeholder(next_index)}",
                                    *(self._normalize(changed[f]) for f in fields), seed_id)
                        await self._ensure_id_floor(connection, graph.entity, seed_id)
        finally:
            if owns_connection:
                await connection.close()

    async def _next_id(self, connection, entity):
        await connection.execute(
            "CREATE TABLE IF NOT EXISTS teaql_id_space ("
            "type_name VARCHAR(255) PRIMARY KEY, current_level BIGINT NOT NULL)"
        )
        for attempt in range(1, 101):
            current = await connection.fetch_value(
                "SELECT current_level FROM teaql_id_space WHERE type_name = "
                + self._placeholder(1), entity)
            if current is None:
                try:
                    await connection.execute(
                        "INSERT INTO teaql_id_space(type_name, current_level) VALUES ("
                        + self._placeholder(1) + ", 1)", entity)
                    return 1
                except Exception:
                    winner = await connection.fetch_value(
                        "SELECT current_level FROM teaql_id_space WHERE type_name = "
                        + self._placeholder(1), entity)
                    if winner is None:
                        raise
                    continue
            current = int(current)
            if current >= 2**63 - 1:
                raise RuntimeError(f"ID space overflow for {entity}")
            next_value = current + 1
            changed = await connection.execute(
                "UPDATE teaql_id_space SET current_level = " + self._placeholder(1)
                + " WHERE type_name = " + self._placeholder(2)
                + " AND current_level = " + self._placeholder(3),
                next_value, entity, current)
            if changed == 1:
                return next_value
            if changed not in (0, None):
                raise RuntimeError(
                    f"ID space update for {entity} changed {changed} rows on attempt {attempt}")
        raise RuntimeError(
            f"Unable to allocate ID for {entity} after 100 optimistic-lock attempts")

    async def _ensure_id_floor(self, connection, entity, floor):
        await connection.execute(
            "CREATE TABLE IF NOT EXISTS teaql_id_space ("
            "type_name VARCHAR(255) PRIMARY KEY, current_level BIGINT NOT NULL)"
        )
        for attempt in range(1, 101):
            current = await connection.fetch_value(
                "SELECT current_level FROM teaql_id_space WHERE type_name = "
                + self._placeholder(1), entity)
            if current is None:
                try:
                    await connection.execute(
                        "INSERT INTO teaql_id_space(type_name, current_level) VALUES ("
                        + self._placeholder(1) + ", " + self._placeholder(2) + ")",
                        entity, floor)
                    return
                except Exception:
                    winner = await connection.fetch_value(
                        "SELECT current_level FROM teaql_id_space WHERE type_name = "
                        + self._placeholder(1), entity)
                    if winner is None:
                        raise
                    continue
            current = int(current)
            if current >= floor:
                return
            changed = await connection.execute(
                "UPDATE teaql_id_space SET current_level = " + self._placeholder(1)
                + " WHERE type_name = " + self._placeholder(2)
                + " AND current_level = " + self._placeholder(3),
                floor, entity, current)
            if changed == 1:
                return
            if changed not in (0, None):
                raise RuntimeError(
                    f"ID space floor update for {entity} changed {changed} rows on attempt {attempt}")
        raise RuntimeError(
            f"Unable to synchronize ID space floor for {entity} after 100 optimistic-lock attempts")

    async def mutate(self, context, req):
        command = req.cmd
        if not context.consume_mutation_checked(command):
            context.check_and_fix_mutation(command)
        started_ns = time.perf_counter_ns()
        owns_connection = self._graph_connection is None
        connection = await self._connect() if owns_connection else self._graph_connection
        try:
            async with (connection.transaction() if owns_connection else _NoopTransaction()):
                if hasattr(command, "payload"):
                    record = copy.deepcopy(command.payload)
                    table = await self._ensure_table(connection, command.entity, record)
                    record_id = record.get("id") or await self._next_id(connection, command.entity)
                    if record.get("id") is not None:
                        await self._ensure_id_floor(connection, command.entity, int(record_id))
                    record["id"] = record_id
                    record["version"] = int(record.get("version") or 0) + 1
                    fields = list(record.keys())
                    columns = ", ".join(self._identifier(field) for field in fields)
                    placeholders = ", ".join(
                        self._placeholder(index) for index in range(1, len(fields) + 1)
                    )
                    params = [self._normalize(record[field]) for field in fields]
                    sql = f"INSERT INTO {self._identifier(table)} ({columns}) VALUES ({placeholders})"
                    await connection.execute(sql, *params)
                    context.record_sql_evidence(
                        SqlLogOperation.Insert, sql, params,
                        (time.perf_counter_ns() - started_ns) // 1000, affected_rows=1,
                        audit_reason=req.comment,
                        trace_path=(("operation", "mutation"), ("entity", command.entity),
                                    ("provider", self.database_kind), ("sql", "insert")))
                    persisted = await connection.fetch_one(
                        f"SELECT * FROM {self._identifier(table)} "
                        f"WHERE {self._identifier('id')} = {self._placeholder(1)}",
                        record_id,
                    )
                    result = MutationResult(
                        {"success": True, "id": record_id, "version": persisted["version"]},
                        persisted)
                    await context.emit_mutation_audit(req, result)
                    return result

                if hasattr(command, "values"):
                    table = await self._ensure_table(connection, command.entity, command.values)
                    values = {
                        field: value for field, value in command.values.items()
                        if field not in ("id", "version")
                    }
                    params = [self._normalize(value) for value in values.values()]
                    assignments = [
                        f"{self._identifier(field)} = {self._placeholder(index)}"
                        for index, field in enumerate(values.keys(), 1)
                    ]
                    version = self._identifier("version")
                    assignments.append(f"{version} = {version} + 1")
                    params.append(command.pk)
                    predicates = [
                        f"{self._identifier('id')} = {self._placeholder(len(params))}"
                    ]
                    if command.expected_version is not None:
                        params.append(command.expected_version)
                        predicates.append(
                            f"{version} = {self._placeholder(len(params))}"
                        )
                    sql = (f"UPDATE {self._identifier(table)} SET {', '.join(assignments)} "
                           f"WHERE {' AND '.join(predicates)}")
                    affected = await connection.execute(sql, *params)
                    if affected != 1:
                        raise RuntimeError(
                            f"Optimistic lock failed or {command.entity}({command.pk}) does not exist"
                        )
                    context.record_sql_evidence(
                        SqlLogOperation.Update, sql, params,
                        (time.perf_counter_ns() - started_ns) // 1000, affected_rows=affected,
                        audit_reason=req.comment,
                        trace_path=(("operation", "mutation"), ("entity", command.entity),
                                    ("provider", self.database_kind), ("sql", "update")))
                    row = await connection.fetch_one(
                        f"SELECT * FROM {self._identifier(table)} "
                        f"WHERE {self._identifier('id')} = {self._placeholder(1)}",
                        command.pk,
                    )
                    result = MutationResult(
                        {"success": True, "id": command.pk, "version": row["version"]}, row)
                    await context.emit_mutation_audit(req, result)
                    return result

                if hasattr(command, "pk"):
                    table = await self._ensure_table(connection, command.entity)
                    params = [command.pk]
                    predicates = [
                        f"{self._identifier('id')} = {self._placeholder(1)}"
                    ]
                    if command.expected_version is not None:
                        params.append(command.expected_version)
                        predicates.append(
                            f"{self._identifier('version')} = {self._placeholder(len(params))}"
                        )
                    version = self._identifier("version")
                    sql = (f"UPDATE {self._identifier(table)} SET {version} = -({version} + 1) "
                           f"WHERE {' AND '.join(predicates)}")
                    affected = await connection.execute(sql, *params)
                    if affected != 1:
                        raise RuntimeError(
                            f"Optimistic lock failed or {command.entity}({command.pk}) does not exist"
                        )
                    context.record_sql_evidence(
                        SqlLogOperation.Delete, sql, params,
                        (time.perf_counter_ns() - started_ns) // 1000, affected_rows=affected,
                        audit_reason=req.comment,
                        trace_path=(("operation", "mutation"), ("entity", command.entity),
                                    ("provider", self.database_kind), ("sql", "delete")))
                    row = await connection.fetch_one(
                        f"SELECT * FROM {self._identifier(table)} "
                        f"WHERE {self._identifier('id')} = {self._placeholder(1)}",
                        command.pk,
                    )
                    result = MutationResult({
                        "success": True, "id": command.pk,
                        "version": row["version"], "deleted": True,
                    }, row)
                    await context.emit_mutation_audit(req, result)
                    return result

                raise TypeError(f"Unsupported mutation command: {type(command).__name__}")
        finally:
            if owns_connection:
                await connection.close()

    def _contains_predicate(self, field, placeholder):
        if self.database_kind == "mysql":
            return f"CAST({field} AS CHAR) LIKE CONCAT('%%', {placeholder}, '%%')"
        return f"CAST({field} AS TEXT) LIKE '%' || {placeholder} || '%'"

    def _compile_filter_expression(self, expression, params):
        field = self._identifier(expression["field"])
        operator = expression.get("type")
        if operator in ("in_subquery", "not_in_subquery"):
            child = expression["query"]
            projection = child._projection[0] if child._projection else "id"
            projected = self._identifier(projection)
            child_predicates = [
                self._compile_filter_expression(item, params) for item in child._filters
            ]
            child_schema = ENTITY_SCHEMAS.get(child.entity, {})
            if "version" in child_schema.get("columns", {}):
                child_predicates.append(f"{self._identifier('version')} > 0")
            negative = operator == "not_in_subquery"
            if negative:
                child_predicates.append(f"{projected} IS NOT NULL")
            where = " WHERE " + " AND ".join(child_predicates) if child_predicates else ""
            child_sql = (f"SELECT {projected} FROM "
                         f"{self._identifier(self._table_name(child.entity))}{where}")
            return f"{field} {'NOT IN' if negative else 'IN'} ({child_sql})"
        if operator in ("in", "not_in"):
            values = list(expression.get("value") or [])
            if not values:
                return "1 = 0" if operator == "in" else "1 = 1"
            placeholders = []
            for value in values:
                params.append(self._normalize(value))
                placeholders.append(self._placeholder(len(params)))
            return f"{field} {'IN' if operator == 'in' else 'NOT IN'} ({', '.join(placeholders)})"
        if operator in ("is_null", "is_not_null"):
            return f"{field} IS {'NULL' if operator == 'is_null' else 'NOT NULL'}"
        if operator == "between":
            bounds = list(expression.get("value") or [])
            if len(bounds) != 2:
                raise ValueError("between requires exactly two bounds")
            params.extend([self._normalize(bounds[0]), self._normalize(bounds[1])])
            return (f"{field} BETWEEN {self._placeholder(len(params)-1)} "
                    f"AND {self._placeholder(len(params))}")
        if operator == "sound_like":
            params.append(self._normalize(expression.get("value")))
            return f"SOUNDEX({field}) = SOUNDEX({self._placeholder(len(params))})"
        raw_value = expression.get("value")
        params.append(self._normalize(raw_value))
        placeholder = self._placeholder(len(params))
        if operator == "eq": return f"{field} = {placeholder}"
        if operator == "ne": return f"{field} <> {placeholder}"
        if operator == "contain": return self._contains_predicate(field, placeholder)
        if operator == "not_contain": return f"NOT ({self._contains_predicate(field, placeholder)})"
        if operator in ("begin_with", "not_begin_with", "end_with", "not_end_with"):
            raw = str(raw_value or "")
            params[-1] = ("%" if "end" in operator else "") + raw + ("%" if "begin" in operator else "")
            clause = f"{field} LIKE {placeholder}"
            return f"NOT ({clause})" if operator.startswith("not_") else clause
        if operator == "gte": return f"{field} >= {placeholder}"
        if operator == "lte": return f"{field} <= {placeholder}"
        if operator == "gt": return f"{field} > {placeholder}"
        if operator == "lt": return f"{field} < {placeholder}"
        params.pop()
        raise ValueError(f"Unsupported filter operator: {operator}")

    async def _prepare_id_set_page(self, context, original):
        query = copy.deepcopy(original)
        options = getattr(query, "id_set_pagination", None)
        if options is None or context is None or not hasattr(context, "id_set_get"):
            if context is not None and hasattr(context, "observe_id_set"):
                context.observe_id_set("ID_SET_DISABLED")
            return query, [], False
        if query._limit is None or query._limit <= 0 or query._partition_by is not None or query._aggregates or query._group_by:
            context.observe_id_set("ID_SET_FALLBACK_UNSUPPORTED_SHAPE")
            return query, [], False
        stable = copy.deepcopy(query)
        if not any(field == "id" for field, _direction in stable._order_by):
            stable._order_by.append(("id", "asc"))
        normalized = copy.deepcopy(stable)
        normalized._offset = None; normalized._limit = None
        normalized._projection = []; normalized._relations = []; normalized._relation_aggregates = []
        normalized._facets = []; normalized._comment = None; normalized._purpose = None
        normalized.id_set_pagination = None
        owner = context.get_resource("user_identifier") or ""
        active_root = context.get_resource("active_root")
        policy = context.get_resource("request_policy")
        source = context.get_resource("dataService")
        digest = hashlib.sha256(
            f'{options["namespace"]}|{owner}|{id(source)}|{id(policy)}|{active_root!r}|{vars(normalized)!r}'.encode("utf-8")
        ).hexdigest()
        query_key = f"teaql:id-set:v1:{digest}"
        retained = context.id_set_get(query_key)
        plan = "ID_SET_HIT"
        if retained is None:
            async with context.id_set_lock(query_key):
                retained = context.id_set_get(query_key)
                if retained is None:
                    id_query = copy.deepcopy(stable)
                    id_query._projection = ["id"]
                    id_query._relations = []; id_query._relation_aggregates = []; id_query._facets = []
                    id_query._offset = 0; id_query._limit = options["max_ids"] + 1
                    id_query.id_set_pagination = None
                    id_rows = (await self.query(context, QueryRequest(id_query))).rows
                    try: ids = tuple(int(row["id"]) for row in id_rows)
                    except (KeyError, TypeError, ValueError):
                        context.observe_id_set("ID_SET_FALLBACK_UNSUPPORTED_SHAPE")
                        return query, [], False
                    if len(ids) > options["max_ids"]:
                        context.observe_id_set("ID_SET_FALLBACK_LIMIT_EXCEEDED", "LOWER_BOUND", len(ids))
                        return query, [], False
                    try: context.id_set_put(query_key, ids, options["ttl_seconds"])
                    except Exception:
                        context.observe_id_set("ID_SET_FALLBACK_STORE_UNAVAILABLE")
                        return query, [], False
                    retained = context.id_set_get(query_key)
                    plan = "ID_SET_BUILD"
        ids = retained["ids"]
        context.observe_id_set(plan, "EXACT", len(ids))
        start = query._offset or 0
        if start >= len(ids): return query, [], True
        page_ids = list(ids[start:min(start + query._limit, len(ids))])
        query._offset = None; query._limit = None; query.id_set_pagination = None
        query._filters.append(in_list("id", page_ids))
        return query, page_ids, False

    async def query(self, context, req):
        started_ns = time.perf_counter_ns()
        query, id_set_order, id_set_empty = await self._prepare_id_set_page(context, req.query)
        if id_set_empty:
            return type('QueryResult', (object,), {'rows': [], 'facets': {}})
        query, continuous = _prepare_continuous_page(context, query)
        filter_values = {
            expression["field"]: expression.get("value") for expression in query._filters
        }
        connection = await self._connect()
        try:
            table = await self._ensure_table(connection, query.entity, filter_values)
            params = []
            predicates = []
            for expression in query._filters:
                predicates.append(self._compile_filter_expression(expression, params))

            group_fields = [self._identifier(field) for field in query._group_by]
            if query._aggregates:
                projections = list(group_fields)
                functions = {
                    "count": "COUNT", "sum": "SUM", "avg": "AVG",
                    "min": "MIN", "max": "MAX", "stddev": "STDDEV",
                    "stddev_pop": "STDDEV_POP", "var_samp": "VAR_SAMP",
                    "var_pop": "VAR_POP", "bit_and": "BIT_AND",
                    "bit_or": "BIT_OR", "bit_xor": "BIT_XOR",
                }
                for function, field, alias in query._aggregates:
                    sql_function = functions.get(function.lower())
                    if sql_function is None:
                        raise ValueError(f"Unsupported aggregate function: {function}")
                    projections.append(
                        f"{sql_function}({self._identifier(field)}) AS {self._identifier(alias)}"
                    )
                projection = ", ".join(projections)
            else:
                projection = ", ".join(self._identifier(field) for field in query._projection) if query._projection else "*"

            sql = f"SELECT {projection} FROM {self._identifier(table)}"
            if predicates: sql += " WHERE " + " AND ".join(predicates)
            if group_fields: sql += " GROUP BY " + ", ".join(group_fields)
            partition_by = getattr(query, "_partition_by", None)
            if partition_by:
                window_order = ""
                if query._order_by:
                    window_orders = []
                    for order_field, direction in query._order_by:
                        normalized_direction = direction.upper()
                        if normalized_direction not in ("ASC", "DESC"):
                            raise ValueError(f"Unsupported order direction: {direction}")
                        window_orders.append(f"{self._identifier(order_field)} {normalized_direction}")
                    window_order = " ORDER BY " + ", ".join(window_orders)
                projection += (
                    f", ROW_NUMBER() OVER (PARTITION BY {self._identifier(partition_by)}"
                    f"{window_order}) AS {self._identifier('__teaql_partition_rank')}"
                )
                sql = f"SELECT {projection} FROM {self._identifier(table)}"
                if predicates: sql += " WHERE " + " AND ".join(predicates)
                if group_fields: sql += " GROUP BY " + ", ".join(group_fields)

            if query._order_by and not partition_by:
                orders = []
                for field, direction in query._order_by:
                    normalized_direction = direction.upper()
                    if normalized_direction not in ("ASC", "DESC"):
                        raise ValueError(f"Unsupported order direction: {direction}")
                    orders.append(f"{self._identifier(field)} {normalized_direction}")
                sql += " ORDER BY " + ", ".join(orders)
            if partition_by:
                rank = self._identifier("__teaql_partition_rank")
                rank_predicates = []
                params.append(int(query._offset or 0))
                rank_predicates.append(f"{rank} > {self._placeholder(len(params))}")
                if query._limit is not None:
                    params.append(int(query._offset or 0) + int(query._limit))
                    rank_predicates.append(f"{rank} <= {self._placeholder(len(params))}")
                sql = (f"SELECT * FROM ({sql}) AS {self._identifier('__teaql_partitioned')} "
                       f"WHERE {' AND '.join(rank_predicates)} ORDER BY {rank}")
            elif query._limit is not None:
                params.append(int(query._limit))
                sql += f" LIMIT {self._placeholder(len(params))}"
            elif query._offset is not None and self.database_kind == "sqlite":
                sql += " LIMIT -1"
            elif query._offset is not None and self.database_kind == "mysql":
                sql += " LIMIT 18446744073709551615"
            if query._offset is not None and not partition_by:
                params.append(int(query._offset))
                sql += f" OFFSET {self._placeholder(len(params))}"
            rows = await connection.fetch_all(sql, *params)
            context.record_sql_evidence(
                SqlLogOperation.Select, sql, params,
                (time.perf_counter_ns() - started_ns) // 1000, result_count=len(rows),
                comment=query._comment, purpose=query._purpose,
                trace_path=(("operation", "query"), ("request", query.entity),
                            *query._trace_path,
                            ("provider", self.database_kind), ("sql", "select")))
        finally:
            await connection.close()

        await self._enhance_relations(context, query, rows)
        await self._enhance_relation_aggregates(context, query, rows)
        if id_set_order:
            by_id = {int(row["id"]): row for row in rows if row.get("id") is not None}
            rows = [by_id[entity_id] for entity_id in id_set_order if entity_id in by_id]
        _register_continuous_page(context, continuous, rows)
        facets = await _execute_facets(self, context, query)
        return type('QueryResult', (object,), {'rows': rows, 'facets': facets})

    async def _enhance_relations(self, context, query, parents):
        if not parents or not getattr(query, "_relations", None): return
        relations = ENTITY_SCHEMAS.get(query.entity, {}).get("relations", {})
        for load in query._relations:
            relation = relations.get(load["name"])
            if relation is None: raise ValueError(f"Missing relation {query.entity}.{load['name']}")
            parent_ids = [p[relation["local_key"]] for p in parents if relation["local_key"] in p]
            child_query = copy.deepcopy(load["query"])
            child_query._comment = query._comment
            child_query._purpose = query._purpose
            child_query._trace_path = [*query._trace_path,
                                       ("relation", f"{query.entity}.{load['name']}")]
            child_query._continuous_page_fetch_options = None
            child_query.entity = relation["target_entity"]
            if relation["foreign_key"] not in child_query._projection:
                child_query._projection.append(relation["foreign_key"])
            child_query._filters.append(one_of(relation["foreign_key"], parent_ids))
            if child_query._limit is not None: child_query._partition_by = relation["foreign_key"]
            children = (await self.query(context, QueryRequest(child_query))).rows
            buckets = {}
            for child in children:
                child.pop("__teaql_partition_rank", None)
                buckets.setdefault(child.get(relation["foreign_key"]), []).append(child)
            for parent in parents:
                related = buckets.get(parent.get(relation["local_key"]), [])
                parent[load["name"]] = related if relation["many"] else (related[0] if related else None)

    async def _enhance_relation_aggregates(self, context, query, parents):
        if not parents or not getattr(query, "_relation_aggregates", None): return
        relations = ENTITY_SCHEMAS.get(query.entity, {}).get("relations", {})
        for aggregate in query._relation_aggregates:
            relation = relations.get(aggregate["relation_name"])
            if relation is None:
                raise ValueError(f"Missing relation {query.entity}.{aggregate['relation_name']}")
            parent_ids = [p[relation["local_key"]] for p in parents if relation["local_key"] in p]
            child = copy.deepcopy(aggregate["query"])
            child._comment = query._comment
            child._purpose = query._purpose
            child._trace_path = [*query._trace_path,
                                 ("relation", f"{query.entity}.{aggregate['relation_name']}")]
            child._continuous_page_fetch_options = None
            child.entity = relation["target_entity"]
            child._projection = []; child._order_by = []; child._limit = None; child._offset = None
            child._relations = []; child._relation_aggregates = []
            if not child._aggregates: child._aggregates = [("count", "id", aggregate["alias"])]
            if relation["foreign_key"] not in child._group_by: child._group_by.append(relation["foreign_key"])
            child._filters.append(one_of(relation["foreign_key"], parent_ids))
            rows = (await self.query(context, QueryRequest(child))).rows
            buckets = {row[relation["foreign_key"]]: row for row in rows if relation["foreign_key"] in row}
            is_count = (not aggregate["query"]._aggregates or
                        aggregate["query"]._aggregates[0][0].lower() == "count")
            for parent in parents:
                row = buckets.get(parent.get(relation["local_key"]))
                if row is None:
                    parent[aggregate["alias"]] = (0 if aggregate["single_result"] and is_count
                                                   else None if aggregate["single_result"] else {})
                elif aggregate["single_result"]:
                    parent[aggregate["alias"]] = row.get(child._aggregates[0][2])
                else:
                    parent[aggregate["alias"]] = {
                        key: value for key, value in row.items()
                        if key != relation["foreign_key"]}

    async def close(self): pass


class PostgreSQLTeaQLClient(AsyncSqlTeaQLClient):
    database_kind = "postgres"

    async def _connect(self):
        try: import asyncpg
        except ImportError as error:
            raise RuntimeError("PostgreSQL support requires asyncpg") from error
        return _PostgreSQLConnection(await asyncpg.connect(self.database_url))


class MySQLTeaQLClient(AsyncSqlTeaQLClient):
    database_kind = "mysql"
    identifier_quote = "`"

    async def _connect(self):
        try: import aiomysql
        except ImportError as error:
            raise RuntimeError("MySQL support requires aiomysql") from error
        parsed = urlparse(self.database_url)
        if parsed.scheme not in ("mysql", "mysql+aiomysql"):
            raise ValueError("MySQL database_url must use mysql://")
        options = parse_qs(parsed.query)
        raw = await aiomysql.connect(
            host=parsed.hostname or "localhost",
            port=parsed.port or 3306,
            user=unquote(parsed.username or ""),
            password=unquote(parsed.password or ""),
            db=parsed.path.lstrip("/"),
            charset=options.get("charset", ["utf8mb4"])[0],
            autocommit=True,
            cursorclass=aiomysql.DictCursor,
        )
        return _MySQLConnection(raw)


class SQLiteTeaQLClient(AsyncSqlTeaQLClient):
    database_kind = "sqlite"

    def __init__(self, database_url):
        super().__init__(database_url)
        self._soundex_enabled = False

    async def _ensure_schema(self, context, invocation):
        self._soundex_enabled = True
        return await super()._ensure_schema(context, invocation)

    async def _connect(self):
        try: import aiosqlite
        except ImportError as error:
            raise RuntimeError("SQLite support requires aiosqlite") from error
        database = self.database_url
        if database.startswith("sqlite:"):
            parsed = urlparse(database)
            database = parsed.path
            if database == "/:memory:": database = ":memory:"
        raw = await aiosqlite.connect(database, isolation_level=None)
        raw.row_factory = aiosqlite.Row
        if self._soundex_enabled:
            await raw.create_function("soundex", 1, _soundex, deterministic=True)
        await raw.execute("PRAGMA foreign_keys = ON")
        return _SQLiteConnection(raw)