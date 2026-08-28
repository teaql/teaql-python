import pytest
import tempfile
import os
from datetime import date
import aiosqlite
from teaql.provider.sqlite import create_sqlite_service, SimpleSchemaProvider
from teaql.core.meta import EntityDescriptor, PropertyDescriptor, RelationDescriptor
from teaql.core.value import DataType, Timestamp, Value
from teaql.core.query import SelectQuery
from teaql.core.expr import BinaryExpr, BinaryOp, ColumnExpr, ValueExpr, contain
from teaql.core.mutation import InsertCommand, UpdateCommand, DeleteCommand, MutationRequest
from teaql.data_service import QueryRequest
from teaql.runtime import RuntimeModule
from teaql.provider.sqlite.transport import SqliteTransport
from teaql.sql.types import CompiledQuery, DatabaseKind
from teaql.runtime.telemetry import RuntimeOperation
from teaql.core.graph import GraphNode

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
async def test_schema_bootstrap_is_idempotent_reconciles_constants_and_preserves_root(temp_db):
    provider = SimpleSchemaProvider()
    platform = MockEntityDescriptor("Platform")
    platform.properties = [
        MockPropertyDescriptor("id", DataType.I64, is_id=True),
        MockPropertyDescriptor("name", DataType.Text),
        MockPropertyDescriptor("version", DataType.I64, is_version=True),
    ]
    school_type = MockEntityDescriptor("SchoolType")
    school_type.properties = [
        MockPropertyDescriptor("id", DataType.I64, is_id=True),
        MockPropertyDescriptor("name", DataType.Text),
        MockPropertyDescriptor("code", DataType.Text),
        MockPropertyDescriptor("version", DataType.I64, is_version=True),
    ]
    provider.register_entity(platform)
    provider.register_entity(school_type)
    service = create_sqlite_service(temp_db, provider)
    assert not hasattr(service, "ensure_schema")
    root = GraphNode("Platform").set("id", 1).set("name", "Campus Learning Platform")
    primary = (GraphNode("SchoolType").set("id", 1001)
        .set("name", "Primary").set("code", "PRIMARY"))
    secondary = (GraphNode("SchoolType").set("id", 1002)
        .set("name", "Secondary").set("code", "SECONDARY"))
    context = (RuntimeModule.new().entity(platform).entity(school_type)
        .root_graph(root).initial_graph(primary).initial_graph(secondary).into_context())

    context.with_schema_provider(service)
    await context.ensure_schema()
    await service.mutate(context, MutationRequest(
        UpdateCommand("Platform", Value.I64(1)).value("name", "Customer Name")))
    primary.set("name", "Primary School")
    await context.ensure_schema()

    platforms = (await service.query(context, QueryRequest(SelectQuery("Platform")))).rows
    constants = (await service.query(context, QueryRequest(SelectQuery("SchoolType")))).rows
    assert [(row["id"], row["name"]) for row in platforms] == [(1, "Customer Name")]
    assert [(row["id"], row["name"], row["code"]) for row in constants] == [
        (1001, "Primary School", "PRIMARY"),
        (1002, "Secondary", "SECONDARY"),
    ]
    assert next(row["version"] for row in constants if row["id"] == 1001) == 2
    assert next(row["version"] for row in constants if row["id"] == 1002) == 1
    assert await service.next_id("SchoolType") > 1002

@pytest.mark.asyncio
async def test_crud(temp_db, schema_provider, service):
    async with aiosqlite.connect(temp_db) as db:
        await db.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name VARCHAR(255), version INTEGER)")
        await db.commit()

    # Insert
    insert_req = MutationRequest(InsertCommand("User", {"id": Value.I64(1), "name": Value.Text("Alice"), "version": Value.I64(1)}))
    res = await service.mutate(None, insert_req)
    assert res.affected_rows == 1
    assert res.persisted_record == {"id": 1, "name": "Alice", "version": 1}

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
    assert res.persisted_record["name"] == "Bob"

    query_res = await service.query(None, query_req)
    assert query_res.rows[0]["name"] == "Bob"

    # Delete
    delete_req = MutationRequest(DeleteCommand("User", Value.I64(1)).hard_delete())
    res = await service.mutate(None, delete_req)
    assert res.affected_rows == 1

    query_res = await service.query(None, query_req)
    assert len(query_res.rows) == 0

@pytest.mark.asyncio
async def test_crud_emits_balanced_runtime_telemetry(temp_db, schema_provider, service):
    async with aiosqlite.connect(temp_db) as db:
        await db.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name VARCHAR(255), version INTEGER)")
        await db.commit()

    events = []
    class Telemetry:
        def start(self, operation: RuntimeOperation):
            events.append(("start", operation.family))
            class Scope:
                def success(self, attributes=None): events.append(("success", operation.family))
                def failure(self, error): events.append(("failure", operation.family))
            return Scope()

    context = RuntimeModule.new().into_context().with_runtime_telemetry(Telemetry())
    await service.mutate(context, MutationRequest(InsertCommand("User", {
        "id": Value.I64(1), "name": Value.Text("Alice"), "version": Value.I64(1)
    })))
    await service.query(context, QueryRequest(SelectQuery("User")))

    starts = [family for phase, family in events if phase == "start"]
    assert set(starts) >= {"mutation", "provider", "audit", "query"}
    assert len(starts) == len([1 for phase, _ in events if phase != "start"])

@pytest.mark.asyncio
async def test_mutation_returns_external_database_default_in_same_transaction(temp_db):
    async with aiosqlite.connect(temp_db) as db:
        await db.execute(
            "CREATE TABLE widgets (id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "name TEXT DEFAULT 'database-default', version INTEGER DEFAULT 1)"
        )
        await db.commit()

    provider = SimpleSchemaProvider()
    entity = MockEntityDescriptor("Widget")
    entity.properties = [
        MockPropertyDescriptor("id", DataType.I64, is_id=True),
        MockPropertyDescriptor("name", DataType.Text),
        MockPropertyDescriptor("version", DataType.I64, is_version=True),
    ]
    provider.register_entity(entity)
    service = create_sqlite_service(temp_db, provider)

    result = await service.mutate(
        None, MutationRequest(InsertCommand("Widget", {"version": Value.I64(1)})))

    assert result.persisted_record["id"] > 0
    assert result.persisted_record["name"] == "database-default"
    assert result.persisted_record["version"] == 1

@pytest.mark.asyncio
async def test_structured_sql_evidence_is_parameterized_and_filterable(temp_db, schema_provider, service):
    async with aiosqlite.connect(temp_db) as db:
        await db.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name VARCHAR(255), version INTEGER)")
        await db.commit()

    context = RuntimeModule.new().into_context()
    context.enable_all_sql_log()
    secret = "secret-customer-value"
    insert = MutationRequest(InsertCommand("User", {
        "id": Value.I64(1), "name": Value.Text(secret), "version": Value.I64(1)
    }))
    await service.mutate(context, insert)
    query = SelectQuery("User").filter(
        BinaryExpr(ColumnExpr("name"), BinaryOp.Eq, ValueExpr(Value.Text(secret))))
    await service.query(context, QueryRequest(query))

    entries = context.sql_logs()
    assert len(entries) == 2
    assert all(entry.sql and secret not in entry.sql for entry in entries)
    assert all(entry.params for entry in entries)
    assert any(entry.result_count is not None for entry in entries)
    assert any(entry.affected_rows is not None for entry in entries)

    context.enable_select_sql_log()
    await service.mutate(context, MutationRequest(InsertCommand("User", {
        "id": Value.I64(2), "name": Value.Text("ignored"), "version": Value.I64(1)
    })))
    assert context.sql_logs() == []
    context.enable_mutation_sql_log()
    await service.query(context, QueryRequest(SelectQuery("User")))
    assert context.sql_logs() == []
    context.disable_sql_log()
    assert context.sql_logs() == []

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
async def test_temporal_debug_sql_matches_prepared_sqlite_storage(temp_db):
    async with aiosqlite.connect(temp_db) as db:
        await db.execute("CREATE TABLE temporal_fixture(id INTEGER, d TEXT, t INTEGER)")
        await db.commit()

    transport = SqliteTransport(temp_db)
    prepared = CompiledQuery(
        "INSERT INTO temporal_fixture VALUES (?, ?, ?) /* ignored ? */",
        [Value.I64(1), Value.Date(date(2024, 2, 29)), Value.Timestamp(Timestamp(-123))],
        "teaql source=temporal ?",
    )
    await transport.execute_sql(prepared)
    literal_sql = prepared.debug_sql(DatabaseKind.Sqlite).replace(
        "VALUES (1,", "VALUES (2,", 1)
    await transport.execute_sql(CompiledQuery(literal_sql, []))

    async with aiosqlite.connect(temp_db) as db:
        async with db.execute(
            "SELECT d, t, typeof(d), typeof(t) FROM temporal_fixture ORDER BY id"
        ) as cursor:
            rows = await cursor.fetchall()
    assert rows == [
        ("2024-02-29", -123, "text", "integer"),
        ("2024-02-29", -123, "text", "integer"),
    ]

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
    context = RuntimeModule.new().entity(entity).audit_event_sink(raw).into_context().with_app_audit_event_sink(app)
    command = InsertCommand("User", {"id": Value.I64(1), "name": Value.Text("Alice Example"), "version": Value.I64(1)})
    command.trace_chain.append(type("Trace", (), {"comment": "approved change"})())
    result = await service.mutate(context, MutationRequest(command))

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
async def test_relation_facet_merges_outer_filter_and_supports_include_all(temp_db):
    async with aiosqlite.connect(temp_db) as db:
        await db.execute("CREATE TABLE schools (id INTEGER PRIMARY KEY, name TEXT, school_type INTEGER, version INTEGER)")
        await db.execute("CREATE TABLE school_types (id INTEGER PRIMARY KEY, code TEXT, version INTEGER)")
        await db.executemany("INSERT INTO schools VALUES (?, ?, ?, 1)", [
            (1, "Riverside", 1001), (2, "Riverside Annex", 1001), (3, "Other", 1002)])
        await db.executemany("INSERT INTO school_types VALUES (?, ?, 1)", [
            (1001, "PRIMARY"), (1002, "SECONDARY"), (1003, "VOCATIONAL")])
        await db.commit()

    provider = SimpleSchemaProvider()
    school = MockEntityDescriptor("School")
    school.table_name_val = "schools"
    school.properties = [
        MockPropertyDescriptor("id", DataType.I64, is_id=True),
        MockPropertyDescriptor("name", DataType.Text),
        MockPropertyDescriptor("school_type", DataType.I64),
        MockPropertyDescriptor("version", DataType.I64, is_version=True),
    ]
    school_type = MockEntityDescriptor("SchoolType")
    school_type.table_name_val = "school_types"
    school_type.properties = [
        MockPropertyDescriptor("id", DataType.I64, is_id=True),
        MockPropertyDescriptor("code", DataType.Text),
        MockPropertyDescriptor("version", DataType.I64, is_version=True),
    ]
    provider.register_entity(school)
    provider.register_entity(school_type)
    service = create_sqlite_service(temp_db, provider)

    nested = SelectQuery("SchoolType").project("id", "code").count_field("id", "school_count")
    outer = (SelectQuery("School")
        .and_filter(contain("name", "Riverside"))
        .facet_by("types", "school_type", nested))
    result = await service.query(None, QueryRequest(outer))
    assert [(row["code"], row["school_count"]) for row in result.facets["types"]] == [
        ("PRIMARY", 2), ("SECONDARY", 0), ("VOCATIONAL", 0)]

    outer.facets[0].include_all_facets = False
    matched = await service.query(None, QueryRequest(outer))
    assert [(row["code"], row["school_count"]) for row in matched.facets["types"]] == [("PRIMARY", 2)]
