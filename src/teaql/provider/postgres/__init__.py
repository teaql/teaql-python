from teaql.provider.postgres.dialect import PostgresDialect
from teaql.provider.postgres.transport import PostgresTransport
from teaql.sql.executor import SqlDataServiceExecutor

def create_postgres_service(db_url: str) -> SqlDataServiceExecutor:
    dialect = PostgresDialect()
    transport = PostgresTransport(db_url)
    return SqlDataServiceExecutor(dialect, transport)
