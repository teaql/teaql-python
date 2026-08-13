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
from teaql.runtime import RuntimeModule
from teaql.provider.sqlite.transport import SqliteTransport
from teaql.sql.types import CompiledQuery

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
async def test_sqlite_stream_is_chunked_and_closes_after_early_stop(temp_db):
    async with aiosqlite.connect(temp_db) as db:
        await db.execute("CREATE TABLE stream_fixture(id INTEGER)")
        await db.executemany("INSERT INTO stream_fixture VALUES (?)", [(i,) for i in range(1, 6)])
        await db.commit()

    transport = SqliteTransport(temp_db)
    query = CompiledQuery("SELECT id FROM stream_fixture ORDER BY id", [])
    chunks = [chunk async for chunk in transport.stream_sql(query, 2)]
    assert [len(chunk) for chunk in chunks] == [2, 2, 1]
    assert [row["id"] for chunk in chunks for row in chunk] == [1, 2, 3, 4, 5]

    stream = transport.stream_sql(query, 2)
    assert len(await anext(stream)) == 2
    await stream.aclose()
    async with aiosqlite.connect(temp_db) as db:
        async with db.execute("SELECT count(*) FROM stream_fixture") as cursor:
            assert (await cursor.fetchone())[0] == 5

@pytest.mark.asyncio
async def test_successful_mutation_emits_raw_and_independently_masked_app_audit(temp_db):
    async with aiosqlite.connect(temp_db) as db:
        await db.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name VARCHAR(255), version INTEGER)")
        await db.commit()

    provider = SimpleSchemaProvider()
    entity = MockEntityDescriptor("User").audit_mask_fields(["name"])
    entity.properties = [
        MockPropertyDescriptor("id", DataType.I64, is_id=True),
        MockPropertyDescriptor("name", DataType.Text),
        MockPropertyDescriptor("version", DataType.I64, is_version=True),
    ]
    provider.register_entity(entity)
    service = create_sqlite_service(temp_db, provider)

    class RawSink:
        events = []
        def on_event(self, context, event): self.events.append(event)
    class AppSink:
        events = []
        async def on_safe_event(self, context, event): self.events.append(event)

    raw, app = RawSink(), AppSink()
    ctx = RuntimeModule.new().entity(entity).audit_event_sink(raw).into_context().with_app_audit_event_sink(app)
    command = InsertCommand("User", {"id": Value.I64(1), "name": Value.Text("Alice Example"), "version": Value.I64(1)})
    command.trace_chain.append(type("Trace", (), {"comment": "approved change"})())
    result = await service.mutate(ctx, MutationRequest(command))

    assert result.affected_rows == 1
    assert len(raw.events) == 1 and raw.events[0].changes[1].new_value.val == "Alice Example"
    assert raw.events[0].trace_chain[0].comment == "approved change"
    assert len(app.events) == 1
    name_field = next(field for field in app.events[0].fields if field.field == "name")
    assert name_field.masked and name_field.value != "Alice Example"

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

@pytest.mark.asyncio
async def test_continuous_page_fetch_uses_seek_against_sqlite(temp_db, schema_provider):
    async with aiosqlite.connect(temp_db) as db:
        await db.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT, version INTEGER)")
        await db.executemany(
            "INSERT INTO users VALUES (?, ?, 1)",
            [(value, f"user-{value}") for value in range(1, 101)],
        )
        await db.commit()

    service = create_sqlite_service(temp_db, schema_provider)
    ctx = RuntimeModule.new().into_context().with_user_identifier("tenant-1:user-1")
    first = (SelectQuery("User").order_desc("id").offset(0).limit(10)
             .optimize_for_continuous_page_fetch_with("users", 60))
    second = (SelectQuery("User").order_desc("id").offset(10).limit(10)
              .optimize_for_continuous_page_fetch_with("users", 60))

    first_rows = (await service.query(ctx, QueryRequest(first).comment("browse").purpose("browse users"))).rows
    second_result = await service.query(ctx, QueryRequest(second).comment("browse").purpose("browse users"))

    assert first_rows[-1]["id"] == 91
    assert second_result.rows[0]["id"] == 90
    assert "WHERE" in second_result.metadata.debug_query and "id <" in second_result.metadata.debug_query
    assert "OFFSET 10" not in second_result.metadata.debug_query
    assert ctx.continuous_page_plan() == "CURSOR_SEEK"
