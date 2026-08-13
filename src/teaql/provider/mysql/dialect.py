from teaql.core.meta import PropertyDescriptor
from teaql.core.value import DataType
from teaql.sql.dialect import SqlDialect, quote_identifier_if_needed
from teaql.sql.types import DatabaseKind, UnsupportedSchemaTypeError


class MysqlDialect(SqlDialect):
    def kind(self) -> DatabaseKind:
        return DatabaseKind.MySql

    def quote_ident(self, ident: str) -> str:
        return quote_identifier_if_needed(ident, "`")

    def placeholder(self, index: int) -> str:
        return "%s"

    def schema_type_sql(self, data_type: DataType, property_desc: PropertyDescriptor) -> str:
        if data_type == DataType.Bool:
            return "TINYINT(1)"
        if data_type in (DataType.I64, DataType.U64):
            return "BIGINT"
        if data_type == DataType.F64:
            return "DOUBLE"
        if data_type == DataType.Decimal:
            return "DECIMAL(38, 12)"
        if data_type == DataType.Text:
            return "VARCHAR(255)"
        if data_type == DataType.LargeText:
            return "LONGTEXT"
        if data_type == DataType.Json:
            return "JSON"
        if data_type == DataType.Date:
            return "DATE"
        if data_type == DataType.Timestamp:
            return "DATETIME(6)"
        raise UnsupportedSchemaTypeError(data_type)

    def compile_add_column(self, entity, property_desc) -> str:
        definition = self.column_definition_sql(property_desc).replace(" NOT NULL", "")
        table_name = getattr(entity, "table_name_val", getattr(entity, "_name", ""))
        return f"ALTER TABLE {self.quote_ident(table_name)} ADD COLUMN {definition}"
