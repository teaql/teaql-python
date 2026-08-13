from teaql.provider.mysql.dialect import MysqlDialect
from teaql.provider.mysql.transport import MysqlTransport
from teaql.sql.executor import SqlDataServiceExecutor, SchemaProvider

def create_mysql_service(db_url: str, schema_provider: SchemaProvider) -> SqlDataServiceExecutor:
    dialect = MysqlDialect()
    transport = MysqlTransport(db_url)
    return SqlDataServiceExecutor(dialect, transport, schema_provider)
