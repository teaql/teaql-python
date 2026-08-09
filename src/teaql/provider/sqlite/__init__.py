from .dialect import SqliteDialect
from .transport import SqliteTransport
from teaql.sql.executor import SqlDataServiceExecutor, SchemaProvider

class SimpleSchemaProvider(SchemaProvider):
    def __init__(self):
        self.entities = {}

    def get_entity(self, name: str):
        return self.entities.get(name)

    def register_entity(self, entity):
        self.entities[getattr(entity, '_name', '')] = entity

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
