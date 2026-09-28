from teaql.sql.dialect import SqlDialect, quote_identifier_if_needed
from teaql.sql.types import DatabaseKind


class MysqlDialect(SqlDialect):
    def kind(self) -> DatabaseKind:
        return DatabaseKind.MySql

    def quote_ident(self, ident: str) -> str:
        return quote_identifier_if_needed(ident, "`")

    def placeholder(self, index: int) -> str:
        return "%s"
