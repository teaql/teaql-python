import copy
import json
import os
import re
import tempfile
from datetime import date, datetime
from decimal import Decimal
from urllib.parse import parse_qs, unquote, urlparse

ENTITY_SCHEMAS = {
"CommercePlatform": {
    "table": "commerce_platform_data",
    "columns": {"id": "integer", "name": "text", "create_time": "date", "update_time": "date", "version": "integer"},
    "relations": {"customer_list": {"target_entity": "Customer", "local_key": "id", "foreign_key": "commerce_platform", "many": True}, "order_status_list": {"target_entity": "OrderStatus", "local_key": "id", "foreign_key": "commerce_platform", "many": True}, "customer_order_list": {"target_entity": "CustomerOrder", "local_key": "id", "foreign_key": "commerce_platform", "many": True}, "product_list": {"target_entity": "Product", "local_key": "id", "foreign_key": "commerce_platform", "many": True}, "order_line_list": {"target_entity": "OrderLine", "local_key": "id", "foreign_key": "commerce_platform", "many": True}, "order_search_preset_list": {"target_entity": "OrderSearchPreset", "local_key": "id", "foreign_key": "commerce_platform", "many": True}},
},
"Customer": {
    "table": "customer_data",
    "columns": {"id": "integer", "name": "text", "email": "text", "commerce_platform": "integer", "create_time": "date", "update_time": "date", "version": "integer"},
    "relations": {"customer_order_list": {"target_entity": "CustomerOrder", "local_key": "id", "foreign_key": "customer", "many": True}},
},
"OrderStatus": {
    "table": "order_status_data",
    "columns": {"id": "integer", "name": "text", "code": "text", "color": "text", "display_order": "integer", "commerce_platform": "integer", "version": "integer"},
    "relations": {"customer_order_list": {"target_entity": "CustomerOrder", "local_key": "id", "foreign_key": "status", "many": True}},
},
"CustomerOrder": {
    "table": "customer_order_data",
    "columns": {"id": "integer", "order_number": "text", "order_date": "date", "total_amount": "integer", "status": "integer", "customer": "integer", "commerce_platform": "integer", "create_time": "date", "update_time": "date", "version": "integer"},
    "relations": {"order_line_list": {"target_entity": "OrderLine", "local_key": "id", "foreign_key": "customer_order", "many": True}},
},
"Product": {
    "table": "product_data",
    "columns": {"id": "integer", "name": "text", "sku": "text", "image_url": "text", "commerce_platform": "integer", "create_time": "date", "update_time": "date", "version": "integer"},
    "relations": {"order_line_list": {"target_entity": "OrderLine", "local_key": "id", "foreign_key": "product", "many": True}},
},
"OrderLine": {
    "table": "order_line_data",
    "columns": {"id": "integer", "customer_order": "integer", "product": "integer", "product_name": "text", "sku": "text", "quantity": "integer", "commerce_platform": "integer", "create_time": "date", "version": "integer"},
    "relations": {},
},
"OrderSearchPreset": {
    "table": "order_search_preset_data",
    "columns": {"id": "integer", "name": "text", "filter_json": "text", "request_id": "text", "owner_user_id": "text", "commerce_platform": "integer", "create_time": "date", "update_time": "date", "version": "integer"},
    "relations": {},
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
        self._limit = None
        self._offset = None
        self._order_by = []
        self._group_by = []
        self._aggregates = []
        self._filters = []
        self._relations = []
        self._partition_by = None

    def comment(self, c): self._comment = c
    def purpose(self, p): self._purpose = p
    def limit(self, n): self._limit = n
    def offset(self, n): self._offset = n
    def order_by(self, f, d): self._order_by.append((f, d))
    def group_by(self, f): self._group_by.append(f)
    def count_field(self, f, n): self._aggregates.append(("count", f, n))
    def aggregate(self, func, field, ret_name): self._aggregates.append((func, field, ret_name))
    def and_filter(self, expr): self._filters.append(expr)
    def relation_query(self, name, query): self._relations.append({"name": name, "query": query})

class QueryRequest:
    def __init__(self, query):
        self.query = query

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
def contain(a, b): return {"type": "contain", "field": a, "value": b}
def one_of(a, values): return {"type": "in", "field": a, "value": list(values)}
def gte(a, b): return {"type": "gte", "field": a, "value": b}
def lte(a, b): return {"type": "lte", "field": a, "value": b}

class TeaQLClient:
    def __init__(self, storage_path=None):
        self.storage_path = storage_path
        self._data = {}
        self._next_ids = {}
        self._load()

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
        table = self._data.setdefault(command.entity, {})
        if hasattr(command, "payload"):
            record = copy.deepcopy(command.payload)
            record_id = record.get("id") or self._next_id(command.entity)
            record["id"] = record_id
            record["version"] = int(record.get("version") or 0) + 1
            table[str(record_id)] = record
            self._persist()
            result = {"success": True, "id": record_id, "version": record["version"]}
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
            self._persist()
            result = {"success": True, "id": record_id, "version": record["version"]}
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
            del table[str(record_id)]
            self._persist()
            result = {"success": True, "id": record_id, "deleted": True}
            await context.emit_mutation_audit(req, result)
            return result
        raise TypeError(f"Unsupported mutation command: {type(command).__name__}")

    async def query(self, context, req):
        query = req.query
        rows = [copy.deepcopy(row) for row in self._data.get(query.entity, {}).values()]
        for expression in query._filters:
            if expression.get("type") == "eq":
                rows = [row for row in rows if row.get(expression["field"]) == expression["value"]]
            elif expression.get("type") == "contain":
                rows = [row for row in rows if expression["value"] in str(row.get(expression["field"], ""))]
            elif expression.get("type") == "in":
                rows = [row for row in rows if row.get(expression["field"]) in expression["value"]]
            elif expression.get("type") == "gte":
                rows = [row for row in rows if row.get(expression["field"]) >= expression["value"]]
            elif expression.get("type") == "lte":
                rows = [row for row in rows if row.get(expression["field"]) <= expression["value"]]
        for field, direction in reversed(query._order_by):
            rows.sort(key=lambda row: (row.get(field) is None, row.get(field)), reverse=direction.lower() == "desc")
        start = query._offset or 0
        end = None if query._limit is None else start + query._limit
        return type('QueryResult', (object,), {'rows': rows[start:end]})

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
        for field, value in (values or {}).items():
            columns.setdefault(field, self._logical_type(value))
        for field, logical_type in columns.items():
            if field in ("id", "version") or await self._column_exists(connection, table, field):
                continue
            await connection.execute(
                f"ALTER TABLE {quoted_table} ADD COLUMN {self._identifier(field)} "
                f"{self._column_type(logical_type)}"
            )
        return table

    async def ensure_schema(self):
        connection = await self._connect()
        try:
            async with connection.transaction():
                for entity in ENTITY_SCHEMAS:
                    await self._ensure_table(connection, entity)
        finally:
            await connection.close()

    async def _next_id(self, connection, entity):
        await connection.execute(
            "CREATE TABLE IF NOT EXISTS teaql_id_space ("
            "entity VARCHAR(255) PRIMARY KEY, next_id BIGINT NOT NULL)"
        )
        if self.database_kind == "postgres":
            return await connection.fetch_value(
                "INSERT INTO teaql_id_space(entity, next_id) VALUES ($1, 1000) "
                "ON CONFLICT(entity) DO UPDATE SET next_id = teaql_id_space.next_id + 1 "
                "RETURNING next_id",
                entity,
            )
        if self.database_kind == "mysql":
            await connection.execute(
                "INSERT INTO teaql_id_space(entity, next_id) VALUES (%s, 1000) "
                "ON DUPLICATE KEY UPDATE next_id = LAST_INSERT_ID(next_id + 1)",
                entity,
            )
            return await connection.fetch_value(
                "SELECT next_id FROM teaql_id_space WHERE entity = %s", entity
            )
        return await connection.fetch_value(
            "INSERT INTO teaql_id_space(entity, next_id) VALUES (?, 1000) "
            "ON CONFLICT(entity) DO UPDATE SET next_id = teaql_id_space.next_id + 1 "
            "RETURNING next_id",
            entity,
        )

    async def mutate(self, context, req):
        command = req.cmd
        connection = await self._connect()
        try:
            async with connection.transaction():
                if hasattr(command, "payload"):
                    record = copy.deepcopy(command.payload)
                    table = await self._ensure_table(connection, command.entity, record)
                    record_id = record.get("id") or await self._next_id(connection, command.entity)
                    record["id"] = record_id
                    record["version"] = int(record.get("version") or 0) + 1
                    fields = list(record.keys())
                    columns = ", ".join(self._identifier(field) for field in fields)
                    placeholders = ", ".join(
                        self._placeholder(index) for index in range(1, len(fields) + 1)
                    )
                    params = [self._normalize(record[field]) for field in fields]
                    await connection.execute(
                        f"INSERT INTO {self._identifier(table)} ({columns}) VALUES ({placeholders})",
                        *params,
                    )
                    result = {"success": True, "id": record_id, "version": record["version"]}
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
                    affected = await connection.execute(
                        f"UPDATE {self._identifier(table)} SET {', '.join(assignments)} "
                        f"WHERE {' AND '.join(predicates)}",
                        *params,
                    )
                    if affected != 1:
                        raise RuntimeError(
                            f"Optimistic lock failed or {command.entity}({command.pk}) does not exist"
                        )
                    row = await connection.fetch_one(
                        f"SELECT {version} FROM {self._identifier(table)} "
                        f"WHERE {self._identifier('id')} = {self._placeholder(1)}",
                        command.pk,
                    )
                    result = {"success": True, "id": command.pk, "version": row["version"]}
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
                    affected = await connection.execute(
                        f"DELETE FROM {self._identifier(table)} WHERE {' AND '.join(predicates)}",
                        *params,
                    )
                    if affected != 1:
                        raise RuntimeError(
                            f"Optimistic lock failed or {command.entity}({command.pk}) does not exist"
                        )
                    result = {"success": True, "id": command.pk, "deleted": True}
                    await context.emit_mutation_audit(req, result)
                    return result

                raise TypeError(f"Unsupported mutation command: {type(command).__name__}")
        finally:
            await connection.close()

    def _contains_predicate(self, field, placeholder):
        if self.database_kind == "mysql":
            return f"CAST({field} AS CHAR) LIKE CONCAT('%%', {placeholder}, '%%')"
        return f"CAST({field} AS TEXT) LIKE '%' || {placeholder} || '%'"

    async def query(self, context, req):
        query = req.query
        filter_values = {
            expression["field"]: expression.get("value") for expression in query._filters
        }
        connection = await self._connect()
        try:
            table = await self._ensure_table(connection, query.entity, filter_values)
            params = []
            predicates = []
            for expression in query._filters:
                field = self._identifier(expression["field"])
                operator = expression.get("type")
                if operator == "in":
                    values = list(expression.get("value") or [])
                    if not values:
                        predicates.append("1 = 0")
                        continue
                    placeholders = []
                    for value in values:
                        params.append(self._normalize(value))
                        placeholders.append(self._placeholder(len(params)))
                    predicates.append(f"{field} IN ({', '.join(placeholders)})")
                    continue
                params.append(self._normalize(expression.get("value")))
                placeholder = self._placeholder(len(params))
                if operator == "eq":
                    predicates.append(f"{field} = {placeholder}")
                elif operator == "contain":
                    predicates.append(self._contains_predicate(field, placeholder))
                elif operator == "gte":
                    predicates.append(f"{field} >= {placeholder}")
                elif operator == "lte":
                    predicates.append(f"{field} <= {placeholder}")
                else:
                    raise ValueError(f"Unsupported filter operator: {operator}")

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
                projection = "*"

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
        finally:
            await connection.close()

        await self._enhance_relations(context, query, rows)
        return type('QueryResult', (object,), {'rows': rows})

    async def _enhance_relations(self, context, query, parents):
        if not parents or not getattr(query, "_relations", None): return
        relations = ENTITY_SCHEMAS.get(query.entity, {}).get("relations", {})
        for load in query._relations:
            relation = relations.get(load["name"])
            if relation is None: raise ValueError(f"Missing relation {query.entity}.{load['name']}")
            parent_ids = [p[relation["local_key"]] for p in parents if relation["local_key"] in p]
            child_query = copy.deepcopy(load["query"])
            child_query.entity = relation["target_entity"]
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
        await raw.execute("PRAGMA foreign_keys = ON")
        return _SQLiteConnection(raw)