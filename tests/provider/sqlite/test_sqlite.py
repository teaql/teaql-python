import pytest
import tempfile
import os
import aiosqlite
from teaql.provider.sqlite import create_sqlite_service, SimpleSchemaProvider
from teaql.core.meta import EntityDescriptor, PropertyDescriptor
from teaql.core.value import DataType, Value
from teaql.core.query import SelectQuery
from teaql.core.mutation import InsertMutation, UpdateMutation, DeleteMutation, MutationRequest
from teaql.data_service import QueryRequest

@pytest.fixture
def temp_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    os.unlink(path)

class MockEntityDescriptor(EntityDescriptor):
    def __init__(self, name):
        super().__init__(name)
        self.table_name_val = name.lower() + "s"
        self.properties = []

class MockPropertyDescriptor(PropertyDescriptor):
    def __init__(self, name, ptype, is_id=False, is_version=False):
        super().__init__(name, ptype)
        self.column_name = name
        self.property_type = ptype
        self.is_id_val = is_id
        self.is_version_val = is_version
    def is_id(self): return self.is_id_val
    def is_version(self): return self.is_version_val

@pytest.fixture
def schema_provider():
    provider = SimpleSchemaProvider()
    
    entity = MockEntityDescriptor("User")
    entity.properties = [
        MockPropertyDescriptor("id", DataType.I64, is_id=True),
        MockPropertyDescriptor("name", DataType.Text),
        MockPropertyDescriptor("version", DataType.I64, is_version=True),
    ]
    provider.register_entity(entity)
    return provider

@pytest.fixture
def service(temp_db, schema_provider):
    return create_sqlite_service(temp_db, schema_provider)

@pytest.mark.asyncio
async def test_crud(temp_db, schema_provider, service):
    async with aiosqlite.connect(temp_db) as db:
        await db.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name VARCHAR(255), version INTEGER)")
        await db.commit()

    # Insert
    insert_req = MutationRequest(InsertMutation("User", {"id": Value.I64(1), "name": Value.Text("Alice"), "version": Value.I64(1)}))
    res = await service.mutate(None, insert_req)
    assert res.affected_rows == 1

    # Query
    query_req = QueryRequest(SelectQuery("User"))
    query_res = await service.query(None, query_req)
    assert len(query_res.rows) == 1
    assert query_res.rows[0]["id"] == 1
    assert query_res.rows[0]["name"] == "Alice"
    assert query_res.rows[0]["version"] == 1

    # Update
    update_req = MutationRequest(UpdateMutation("User", Value.I64(1)).value("name", Value.Text("Bob")))
    res = await service.mutate(None, update_req)
    assert res.affected_rows == 1

    query_res = await service.query(None, query_req)
    assert query_res.rows[0]["name"] == "Bob"

    # Delete
    delete_req = MutationRequest(DeleteMutation("User", Value.I64(1)).hard_delete())
    res = await service.mutate(None, delete_req)
    assert res.affected_rows == 1

    query_res = await service.query(None, query_req)
    assert len(query_res.rows) == 0
