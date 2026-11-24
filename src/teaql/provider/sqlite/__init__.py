from .dialect import SqliteDialect
from .transport import SqliteTransport
from teaql.sql.executor import SchemaProvider, SimpleSchemaProvider, SqlDataServiceExecutor

def create_sqlite_service(url: str, schema_provider: SchemaProvider = None):
    dialect = SqliteDialect()
    path = url
    if path.startswith("sqlite://"):
        path = path.replace("sqlite://", "", 1)
        if path.startswith("/:memory:"):
            path = ":memory:"
        
    transport = SqliteTransport(path)
    if schema_provider is None:
        schema_provider = SimpleSchemaProvider()
    return SqlDataServiceExecutor(dialect, transport, schema_provider)
