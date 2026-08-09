from teaql.provider.mysql.dialect import MysqlDialect
from teaql.provider.mysql.transport import MysqlTransport
from teaql.sql.executor import SqlDataServiceExecutor

def create_mysql_service(db_url: str) -> SqlDataServiceExecutor:
    dialect = MysqlDialect()
    transport = MysqlTransport(db_url)
    return SqlDataServiceExecutor(dialect, transport)
