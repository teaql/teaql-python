from teaql.provider.mysql.dialect import MysqlDialect
from teaql.provider.mysql.transport import MysqlTransport
from teaql.sql.executor import SchemaProvider, SimpleSchemaProvider, SqlDataServiceExecutor

def create_mysql_service(db_url: str, schema_provider: SchemaProvider | None = None) -> SqlDataServiceExecutor:
    dialect = MysqlDialect()
    transport = MysqlTransport(db_url)
    if schema_provider is None:
        schema_provider = SimpleSchemaProvider()
    return SqlDataServiceExecutor(dialect, transport, schema_provider)
