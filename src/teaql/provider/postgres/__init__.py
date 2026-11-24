from teaql.provider.postgres.dialect import PostgresDialect
from teaql.provider.postgres.transport import PostgresTransport
from teaql.sql.executor import SchemaProvider, SimpleSchemaProvider, SqlDataServiceExecutor

def create_postgres_service(db_url: str, schema_provider: SchemaProvider | None = None) -> SqlDataServiceExecutor:
    dialect = PostgresDialect()
    transport = PostgresTransport(db_url)
    if schema_provider is None:
        schema_provider = SimpleSchemaProvider()
    return SqlDataServiceExecutor(dialect, transport, schema_provider)
