from teaql.sql.dialect import SqlDialect, quote_identifier_if_needed
from teaql.sql.types import DatabaseKind, UnsupportedSchemaTypeError
from teaql.core.value import DataType
from teaql.core.meta import PropertyDescriptor

class PostgresDialect(SqlDialect):
    def kind(self) -> DatabaseKind:
        return DatabaseKind.Postgres

    def quote_ident(self, ident: str) -> str:
        return quote_identifier_if_needed(ident, '"')

    def placeholder(self, index: int) -> str:
        return f"${index}"

    def schema_type_sql(self, data_type: DataType, property_desc: PropertyDescriptor) -> str:
        if data_type == DataType.Bool: 
            return "BOOLEAN"
        if data_type in (DataType.I64, DataType.U64): 
            return "BIGINT"
        if data_type == DataType.F64: 
            return "DOUBLE PRECISION"
        if data_type == DataType.Decimal: 
            return "NUMERIC"
        if data_type == DataType.Text: 
            return "VARCHAR(255)"
        if data_type == DataType.LargeText: 
            return "TEXT"
        if data_type == DataType.Json: 
            return "JSONB"
        if data_type == DataType.Date:
            return "DATE"
        if data_type == DataType.Timestamp:
            return "TIMESTAMPTZ"
            
        raise UnsupportedSchemaTypeError(data_type)

    def compile_add_column(self, entity, property_desc) -> str:
        def_sql = self.column_definition_sql(property_desc)
        def_without_not_null = def_sql.replace(" NOT NULL", "")
        table_name = getattr(entity, 'table_name_val', getattr(entity, '_name', ''))
        return f"ALTER TABLE {self.quote_ident(table_name)} ADD COLUMN {def_without_not_null}"
