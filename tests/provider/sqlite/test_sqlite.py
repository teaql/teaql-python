import pytest
import tempfile
import os
import aiosqlite
from teaql.provider.sqlite import create_sqlite_service, SimpleSchemaProvider
from teaql.core.meta import EntityDescriptor, PropertyDescriptor, RelationDescriptor
from teaql.core.value import DataType, Value
from teaql.core.query import SelectQuery
from teaql.core.mutation import InsertCommand, UpdateCommand, DeleteCommand, MutationRequest
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
    insert_req = MutationRequest(InsertCommand("User", {"id": Value.I64(1), "name": Value.Text("Alice"), "version": Value.I64(1)}))
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
    update_req = MutationRequest(UpdateCommand("User", Value.I64(1)).value("name", Value.Text("Bob")))
    res = await service.mutate(None, update_req)
    assert res.affected_rows == 1

    query_res = await service.query(None, query_req)
    assert query_res.rows[0]["name"] == "Bob"

    # Delete
    delete_req = MutationRequest(DeleteCommand("User", Value.I64(1)).hard_delete())
    res = await service.mutate(None, delete_req)
    assert res.affected_rows == 1

    query_res = await service.query(None, query_req)
    assert len(query_res.rows) == 0

@pytest.mark.asyncio
async def test_nested_relation_limit_is_applied_per_parent(temp_db):
    async with aiosqlite.connect(temp_db) as db:
        await db.execute("CREATE TABLE orders (id INTEGER PRIMARY KEY, version INTEGER)")
        await db.execute("CREATE TABLE orderline (id INTEGER PRIMARY KEY, order_id INTEGER, name TEXT)")
        await db.executemany("INSERT INTO orders VALUES (?, ?)", [(11, 1), (12, 1)])
        lines = [(order_id * 100 + index, order_id, f"line-{order_id}-{index}")
                 for order_id in (11, 12) for index in range(1, 6)]
        await db.executemany("INSERT INTO orderline VALUES (?, ?, ?)", lines)
        await db.commit()

    provider = SimpleSchemaProvider()
    order = MockEntityDescriptor("Order")
    order.table_name_val = "orders"
    order.properties = [
        MockPropertyDescriptor("id", DataType.I64, is_id=True),
        MockPropertyDescriptor("version", DataType.I64, is_version=True),
    ]
    order.relation(RelationDescriptor("lines", "OrderLine").local("id").foreign("order_id").many())
    line = MockEntityDescriptor("OrderLine")
    line.table_name_val = "orderline"
    line.properties = [
        MockPropertyDescriptor("id", DataType.I64, is_id=True),
        MockPropertyDescriptor("order_id", DataType.I64),
        MockPropertyDescriptor("name", DataType.Text),
    ]
    provider.register_entity(order)
    provider.register_entity(line)
    service = create_sqlite_service(temp_db, provider)
    query = (SelectQuery("Order").order_asc("id").relation_query(
        "lines", SelectQuery("OrderLine").project("id", "name").order_desc("id").limit(3)))

    result = await service.query(None, QueryRequest(query))

    assert len(result.rows) == 2
    assert [len(parent["lines"]) for parent in result.rows] == [3, 3]
    assert all("__teaql_partition_rank" not in child
               for parent in result.rows for child in parent["lines"])
