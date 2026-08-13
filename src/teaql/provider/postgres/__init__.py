from teaql.provider.postgres.dialect import PostgresDialect
from teaql.provider.postgres.transport import PostgresTransport
from teaql.sql.executor import SqlDataServiceExecutor, SchemaProvider

def create_postgres_service(db_url: str, schema_provider: SchemaProvider) -> SqlDataServiceExecutor:
    dialect = PostgresDialect()
    transport = PostgresTransport(db_url)
    return SqlDataServiceExecutor(dialect, transport, schema_provider)
