from enum import Enum, auto
from dataclasses import dataclass
from typing import List, Optional
from teaql.core.value import Value, DataType

class DatabaseKind(Enum):
    PostgreSql = auto()
    Sqlite = auto()
    MySql = auto()

@dataclass
class CompiledQuery:
    sql: str
    params: List[Value]
    comment: Optional[str] = None

    def sql_with_comment(self) -> str:
        if self.comment:
            escaped = self.comment.replace("*/", "* /")
            return f"/* {escaped} */ {self.sql}"
        return self.sql

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
