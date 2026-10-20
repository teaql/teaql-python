from teaql.sql.dialect import SqlDialect, quote_identifier_if_needed
from teaql.sql.types import DatabaseKind, UnsupportedSchemaTypeError
from teaql.core.value import DataType
from teaql.core.expr import ColumnExpr
from teaql.core.meta import PropertyDescriptor
from teaql.sql.types import InvalidFunctionArgumentsError
from ._decimal import parse_decimal
from typing import Any

class SqliteDialect(SqlDialect):
    def kind(self) -> DatabaseKind:
        return DatabaseKind.Sqlite

    def quote_ident(self, ident: str) -> str:
        return quote_identifier_if_needed(ident, '"')

    def placeholder(self, index: int) -> str:
        return "?"

    def relation_top_n_policy(self) -> str:
        return "always_probe"

    def normalize_decimal(self, value):
        return parse_decimal(value)

    def aggregate_call_sql(self, entity, function_name, argument, params):
        prop = next((p for p in entity.properties if isinstance(argument, ColumnExpr)
                     and p.name == argument.name), None)
        decimal = prop is not None and (prop.property_type == DataType.Decimal
                    or str(prop.property_type).lower() in ("decimal", "numeric"))
        if not decimal or function_name == "COUNT":
            return super().aggregate_call_sql(entity, function_name, argument, params)
        if function_name not in ("SUM", "MIN", "MAX"):
            raise InvalidFunctionArgumentsError(
                f"SQLite exact Decimal {function_name} requires an explicit precision policy")
        function = "teaql_decimal_sum" if function_name == "SUM" else function_name
        field = self.compile_expr(entity, argument, params)
        return f"({function}({field}) COLLATE TEAQL_DECIMAL)"

    def _decimal_schema(self, property_desc):
        definition = "TEAQL_DECIMAL_TEXT COLLATE TEAQL_DECIMAL"
        if property_desc is not None:
            column = self.quote_ident(property_desc.column_name_val)
            definition += (f" CHECK ({column} IS NULL OR (typeof({column}) = 'text' "
                           f"AND teaql_decimal_valid({column})))")
        return definition

    def schema_type_sql(self, data_type: Any, property_desc: PropertyDescriptor) -> str:
        if isinstance(data_type, str):
            dt_str = data_type.lower()
            if dt_str in ("bool", "boolean"): return "INTEGER"
            if dt_str in ("i64", "u64", "i32", "u32", "int", "integer"): return "INTEGER"
            if dt_str in ("f64", "f32", "float", "double"): return "REAL"
            if dt_str in ("decimal", "numeric"): return self._decimal_schema(property_desc)
            if dt_str in ("text", "string", "varchar"): return "VARCHAR(255)"
            if dt_str in ("largetext", "json", "date", "time", "timestamp"): return "TEXT"
            raise UnsupportedSchemaTypeError(data_type)

        if data_type == DataType.Bool: 
            return "INTEGER"
        if data_type in (DataType.I64, DataType.U64): 
            return "INTEGER"
        if data_type == DataType.F64: 
            return "REAL"
        if data_type == DataType.Decimal: 
            return self._decimal_schema(property_desc)
        if data_type == DataType.Text: 
            return "VARCHAR(255)"
        if data_type in (DataType.LargeText, DataType.Json, DataType.Date, DataType.Time, DataType.Timestamp):
            return "TEXT"
            
        raise UnsupportedSchemaTypeError(data_type)

    def compile_add_column(self, entity, property_desc) -> str:
        def_sql = self.column_definition_sql(property_desc)
        def_without_not_null = def_sql.replace(" NOT NULL", "")
        table_name = getattr(entity, 'table_name_val', getattr(entity, '_name', ''))
        return f"ALTER TABLE {self.quote_ident(table_name)} ADD COLUMN {def_without_not_null}"
