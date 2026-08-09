from teaql.sql.dialect import SqlDialect, quote_identifier_if_needed
from teaql.sql.types import DatabaseKind, UnsupportedSchemaTypeError
from teaql.core.value import DataType
from teaql.core.meta import PropertyDescriptor
from typing import Any

class SqliteDialect(SqlDialect):
    def kind(self) -> DatabaseKind:
        return DatabaseKind.Sqlite

    def quote_ident(self, ident: str) -> str:
        return quote_identifier_if_needed(ident, '"')

    def placeholder(self, index: int) -> str:
        return "?"

    def schema_type_sql(self, data_type: Any, property_desc: PropertyDescriptor) -> str:
        if isinstance(data_type, str):
            dt_str = data_type.lower()
            if dt_str in ("bool", "boolean"): return "INTEGER"
            if dt_str in ("i64", "u64", "i32", "u32", "int", "integer"): return "INTEGER"
            if dt_str in ("f64", "f32", "float", "double"): return "REAL"
            if dt_str in ("decimal", "numeric"): return "NUMERIC"
            if dt_str in ("text", "string", "varchar"): return "VARCHAR(255)"
            if dt_str in ("largetext", "json", "date", "timestamp"): return "TEXT"
            raise UnsupportedSchemaTypeError(data_type)

        if data_type == DataType.Bool: 
            return "INTEGER"
        if data_type in (DataType.I64, DataType.U64): 
            return "INTEGER"
        if data_type == DataType.F64: 
            return "REAL"
        if data_type == DataType.Decimal: 
            return "NUMERIC"
        if data_type == DataType.Text: 
            return "VARCHAR(255)"
        if data_type in (DataType.LargeText, DataType.Json, DataType.Date, DataType.Timestamp): 
            return "TEXT"
            
        raise UnsupportedSchemaTypeError(data_type)

    def compile_add_column(self, entity, property_desc) -> str:
        def_sql = self.column_definition_sql(property_desc)
        def_without_not_null = def_sql.replace(" NOT NULL", "")
        table_name = getattr(entity, 'table_name_val', getattr(entity, '_name', ''))
        return f"ALTER TABLE {self.quote_ident(table_name)} ADD COLUMN {def_without_not_null}"
