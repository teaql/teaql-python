from enum import Enum, auto
from dataclasses import dataclass
from typing import List, Optional
from datetime import date, datetime, timezone
from decimal import Decimal
import json
from contextlib import contextmanager
from teaql.core.value import Value, DataType, Timestamp

class DatabaseKind(Enum):
    PostgreSql = auto()
    Sqlite = auto()
    MySql = auto()

class SQLBindings(list):
    """Compiler-owned provenance; never supplied by incoming query payloads."""
    def __init__(self):
        super().__init__()
        self.policies = []
        self.current_policy = 'unknown'
        self.trusted = True

    def append(self, value, policy=None):
        super().append(value)
        self.policies.append(policy or self.current_policy)

    @contextmanager
    def policy(self, policy):
        previous = self.current_policy
        self.current_policy = policy or previous
        try:
            yield
        finally:
            self.current_policy = previous

@dataclass
class CompiledQuery:
    sql: str
    params: List[Value]
    comment: Optional[str] = None
    parameter_log_policies: Optional[List[str]] = None
    sql_origin: Optional[str] = None

    def __post_init__(self):
        if isinstance(self.params, SQLBindings):
            self.parameter_log_policies = list(self.params.policies)
            self.sql_origin = 'generated' if self.params.trusted else None

    def sql_with_comment(self) -> str:
        if self.comment:
            escaped = self.comment.replace("*/", "* /")
            return f"/* {escaped} */ {self.sql}"
        return self.sql

    def debug_sql(self, dialect: DatabaseKind) -> str:
        if dialect == DatabaseKind.PostgreSql:
            return _replace_numbered_placeholders(self.sql_with_comment(), self.params, dialect)
        return _replace_positional_placeholders(self.sql_with_comment(), self.params, dialect)

def render_log_sql(sql, params, dialect, literal):
    """Use the normal dialect scanner, with complete bind accounting for logs."""
    if not sql.strip():
        raise ValueError('Missing SQL template')
    used = set()
    def checked(index):
        if index < 0 or index >= len(params):
            raise ValueError('SQL bind count mismatch')
        used.add(index)
        return literal(index)
    scanner = (_replace_numbered_placeholders if dialect == DatabaseKind.PostgreSql
               else _replace_positional_placeholders)
    rendered = scanner(sql, params, dialect, checked)
    if len(used) != len(params):
        raise ValueError('Unused SQL bindings')
    return rendered

def _replace_numbered_placeholders(sql: str, params: List[Value], dialect: DatabaseKind, literal=None) -> str:
    output, index, state = [], 0, "sql"
    while index < len(sql):
        char = sql[index]
        next_char = sql[index + 1] if index + 1 < len(sql) else ""
        if state == "sql" and char == "'": output.append(char); state = "single"
        elif state == "sql" and char == '"': output.append(char); state = "double"
        elif state == "sql" and char == "-" and next_char == "-": output.extend("--"); index += 1; state = "line"
        elif state == "sql" and char == "/" and next_char == "*": output.extend("/*"); index += 1; state = "block"
        elif state == "single":
            output.append(char)
            if char == "'" and next_char == "'": output.append("'"); index += 1
            elif char == "'": state = "sql"
        elif state == "double":
            output.append(char)
            if char == '"' and next_char == '"': output.append('"'); index += 1
            elif char == '"': state = "sql"
        elif state == "line":
            output.append(char)
            if char in "\r\n": state = "sql"
        elif state == "block":
            output.append(char)
            if char == "*" and next_char == "/": output.append("/"); index += 1; state = "sql"
        elif char == "$" and next_char.isdigit():
            end = index + 1
            while end < len(sql) and sql[end].isdigit():
                end += 1
            parameter_index = int(sql[index + 1:end]) - 1
            output.append(literal(parameter_index) if literal else
                          _sql_literal(params[parameter_index], dialect)
                          if 0 <= parameter_index < len(params) else sql[index:end])
            index = end
            continue
        else:
            output.append(char)
        index += 1
    if literal and state not in ('sql', 'line'):
        raise ValueError('Unclosed SQL token')
    return "".join(output)

def _replace_positional_placeholders(sql: str, params: List[Value], dialect: DatabaseKind, literal=None) -> str:
    output, index, parameter_index, state = [], 0, 0, "sql"
    while index < len(sql):
        char = sql[index]
        next_char = sql[index + 1] if index + 1 < len(sql) else ""
        if state == "sql" and char == "'":
            output.append(char)
            state = "single_quote"
        elif state == "sql" and char == '"':
            output.append(char)
            state = "double_quote"
        elif state == "sql" and char == '`':
            output.append(char); state = "backtick"
        elif state == "sql" and char == "-" and next_char == "-":
            output.extend((char, next_char)); index += 1; state = "line_comment"
        elif state == "sql" and char == "/" and next_char == "*":
            output.extend((char, next_char)); index += 1; state = "block_comment"
        elif state == "single_quote":
            output.append(char)
            if char == "'" and next_char == "'":
                output.append("'")
                index += 1
            elif char == "'":
                state = "sql"
        elif state == "double_quote":
            output.append(char)
            if char == '"' and next_char == '"':
                output.append('"'); index += 1
            elif char == '"':
                state = "sql"
        elif state == "line_comment":
            output.append(char)
            if char in "\r\n": state = "sql"
        elif state == "backtick":
            output.append(char)
            if char == '`' and next_char == '`': output.append('`'); index += 1
            elif char == '`': state = 'sql'
        elif state == "block_comment":
            output.append(char)
            if char == "*" and next_char == "/":
                output.append("/"); index += 1; state = "sql"
        elif (char == "?" or (dialect == DatabaseKind.MySql and char == "%" and next_char == "s")) and (literal or parameter_index < len(params)):
            output.append(literal(parameter_index) if literal else _sql_literal(params[parameter_index], dialect))
            parameter_index += 1
            if char == "%": index += 1
        else:
            output.append(char)
        index += 1
    if literal and state not in ('sql', 'line_comment'):
        raise ValueError('Unclosed SQL token')
    return "".join(output)

def _sql_literal(value: Value, dialect: DatabaseKind) -> str:
    raw = value.val
    if raw is None:
        return "NULL"
    if isinstance(raw, bool):
        return "TRUE" if raw else "FALSE"
    if isinstance(raw, (int, float, Decimal)):
        return str(raw)
    if isinstance(raw, date):
        literal = _quote_sql_string(raw.isoformat())
        if dialect == DatabaseKind.PostgreSql: return f"DATE {literal}"
        if dialect == DatabaseKind.MySql: return f"CAST({literal} AS DATE)"
        return literal
    if isinstance(raw, Timestamp):
        if dialect == DatabaseKind.Sqlite: return str(raw.millis)
        instant = datetime.fromtimestamp(raw.millis / 1000, tz=timezone.utc)
        text = instant.strftime("%Y-%m-%d %H:%M:%S.%f")[:23]
        if dialect == DatabaseKind.PostgreSql: return f"TIMESTAMPTZ {_quote_sql_string(text + 'Z')}"
        return f"CAST({_quote_sql_string(text)} AS DATETIME(3))"
    if isinstance(raw, list):
        items = ", ".join(_sql_literal(item if isinstance(item, Value) else Value.from_any(item), dialect) for item in raw)
        return f"ARRAY[{items}]" if dialect == DatabaseKind.PostgreSql else f"({items})"
    if isinstance(raw, dict):
        return _quote_sql_string(json.dumps(value.to_json_value(), separators=(",", ":"), sort_keys=True))
    return _quote_sql_string(str(raw))

def _quote_sql_string(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"

class SqlCompileError(Exception):
    pass

class UnknownEntityError(SqlCompileError):
    def __init__(self, entity: str):
        super().__init__(f"unknown entity: {entity}")

class UnknownFieldError(SqlCompileError):
    def __init__(self, field: str):
        super().__init__(f"unknown field: {field}")

class EmptyInListError(SqlCompileError):
    def __init__(self):
        super().__init__("IN requires at least one value")

class MissingIdPropertyError(SqlCompileError):
    def __init__(self, entity: str):
        super().__init__(f"entity {entity} has no id property")

class MissingVersionPropertyError(SqlCompileError):
    def __init__(self, entity: str):
        super().__init__(f"entity {entity} has no version property")

class EmptyMutationError(SqlCompileError):
    def __init__(self, kind: str):
        super().__init__(f"{kind} requires at least one writable field")

class InvalidRecoverVersionError(SqlCompileError):
    def __init__(self, version: int):
        super().__init__(f"recover requires a negative version, got {version}")

class UnsupportedSchemaTypeError(SqlCompileError):
    def __init__(self, data_type: DataType):
        super().__init__(f"unsupported schema type: {data_type}")

class InvalidFunctionArgumentsError(SqlCompileError):
    def __init__(self, message: str):
        super().__init__(message)

class InvalidSubQueryOperatorError(SqlCompileError):
    def __init__(self, operator: str):
        super().__init__(f"subquery does not support operator: {operator}")
