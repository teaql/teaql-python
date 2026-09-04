import pytest
import tempfile
import os
from datetime import date
from decimal import Decimal
import aiosqlite
import asyncio
from teaql.provider.sqlite import create_sqlite_service, SimpleSchemaProvider
from teaql.core.meta import EntityDescriptor, PropertyDescriptor, RelationDescriptor
from teaql.core.value import DataType, Timestamp, Value
from teaql.core.query import SelectQuery, RelationAggregate, Aggregate, AggregateFunction
from teaql.core.expr import (BinaryExpr, BinaryOp, ColumnExpr, ValueExpr, between,
    contain, column, in_list, in_subquery, is_not_null, is_null, not_in_subquery,
    value)
from teaql.core.mutation import InsertCommand, UpdateCommand, DeleteCommand, MutationRequest, TraceNode
from teaql.data_service import QueryRequest
from teaql.runtime import RuntimeModule
from teaql.runtime.context import InMemoryIdSetStore, ContextEntityRef
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
async def test_ensure_schema_registers_soundex_on_every_sqlite_connection(temp_db):
    provider = SimpleSchemaProvider()
    entity = MockEntityDescriptor("Person")
    entity.properties = [MockPropertyDescriptor("id", DataType.I64, is_id=True)]
    provider.register_entity(entity)
    service = create_sqlite_service(temp_db, provider)
    context = RuntimeModule.new().entity(entity).into_context()
    context.with_schema_provider(service)
    await context.ensure_schema()
    await context.ensure_schema()
    rows = await service.transport.fetch_all_sql(CompiledQuery(
        "SELECT soundex('Robert') AS encoded, "
        "soundex('Robert') = soundex('Rupert') AS matched, soundex(NULL) AS empty", []))
    assert rows == [{"encoded": "R163", "matched": 1, "empty": "?000"}]

@pytest.mark.asyncio
async def test_query_attaches_batched_relation_aggregate_aliases(temp_db):
    provider = SimpleSchemaProvider()
    school = MockEntityDescriptor("School")
    school.properties = [MockPropertyDescriptor("id", DataType.I64, is_id=True)]
    school.relation(RelationDescriptor("students", "Student").foreign("school_id").many())
    student = MockEntityDescriptor("Student")
    student.properties = [
        MockPropertyDescriptor("id", DataType.I64, is_id=True),
        MockPropertyDescriptor("school_id", DataType.I64),
        MockPropertyDescriptor("score", DataType.I64),
    ]
    provider.register_entity(school)
    provider.register_entity(student)
    service = create_sqlite_service(temp_db, provider)
    async with aiosqlite.connect(temp_db) as db:
        await db.execute("CREATE TABLE schools(id INTEGER PRIMARY KEY)")
        await db.execute("CREATE TABLE students(id INTEGER PRIMARY KEY, school_id INTEGER, score INTEGER)")
        await db.executemany("INSERT INTO schools(id) VALUES (?)", [(1,), (2,)])
        await db.executemany("INSERT INTO students(id,school_id,score) VALUES (?,?,?)", [(10,1,11),(11,1,31)])
        await db.commit()
    query = SelectQuery("School")
    query.relation_aggregates.extend([
        RelationAggregate("students", "record_count", SelectQuery("Student").count("inner_count"), True),
        RelationAggregate("students", "score_total", SelectQuery("Student", aggregates=[
            Aggregate(AggregateFunction.Sum, "score", "inner_total")]), True),
    ])

    rows = (await service.query(None, QueryRequest(query))).rows

    assert rows[0]["record_count"] == 2
    assert rows[0]["score_total"] == 42
    assert rows[1]["record_count"] == 0
    assert rows[1]["score_total"] is None

@pytest.mark.asyncio
async def test_schema_provider_does_not_interpret_legacy_bootstrap_graphs(temp_db):
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
    platforms = (await service.query(context, QueryRequest(SelectQuery("Platform")))).rows
    constants = (await service.query(context, QueryRequest(SelectQuery("SchoolType")))).rows
    assert platforms == []
    assert constants == []

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
async def test_id_set_pagination_jumps_restores_order_and_avoids_count(temp_db, schema_provider):
    service = create_sqlite_service(temp_db, schema_provider)
    context = RuntimeModule.new().entity(schema_provider.get_entity("User")).into_context()
    context.with_schema_provider(service).with_user_identifier("tenant:user")
    await context.ensure_schema()
    async with aiosqlite.connect(temp_db) as db:
        await db.executemany(
            "INSERT INTO users(id,name,version) VALUES (?,?,?)",
            [(1, "one", 1), (2, "two", 1), (3, "three", 1), (4, "four", 1), (5, "five", 1)])
        await db.commit()

    calls = 0
    fetch = service.transport.fetch_all_sql
    async def counted_fetch(compiled):
        nonlocal calls
        calls += 1
        return await fetch(compiled)
    service.transport.fetch_all_sql = counted_fetch

    jumped = SelectQuery("User").order_desc("id").offset(2).limit(2)
    jumped.optimize_pagination_with_id_set_config("users", 60, 100)
    rows = (await service.query(context, QueryRequest(jumped))).rows
    assert [row["id"] for row in rows] == [3, 2]
    assert context.id_set_count() == (5, "EXACT")
    assert context.id_set_plan() == "ID_SET_BUILD"

    first = SelectQuery("User").order_desc("id").offset(0).limit(2)
    first.optimize_pagination_with_id_set_config("users", 60, 100)
    rows = (await service.query(context, QueryRequest(first))).rows
    assert [row["id"] for row in rows] == [5, 4]
    assert context.id_set_count() == (5, "EXACT")
    assert context.id_set_plan() == "ID_SET_HIT"
    assert calls == 3  # one ID build plus two page queries; no COUNT(*)

@pytest.mark.asyncio
async def test_id_set_pagination_lifecycle_isolation_and_fallbacks(temp_db, schema_provider):
    service = create_sqlite_service(temp_db, schema_provider)
    async with aiosqlite.connect(temp_db) as db:
        await db.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT, version INTEGER)")
        await db.executemany(
            "INSERT INTO users(id,name,version) VALUES (?,?,?)",
            [(1, "one", 1), (2, "two", 1), (3, "three", 1), (4, "four", 1), (5, "five", 1)])
        await db.commit()

    def new_context(store=None, user="tenant:user", root=1, source=None, policy=None):
        context = RuntimeModule.new().entity(schema_provider.get_entity("User")).into_context()
        context.with_schema_provider(service).with_user_identifier(user)
        context.with_active_root(ContextEntityRef("Platform", root))
        if source is not None:
            context.insert_resource("db", source)
        if policy is not None:
            context.insert_resource("request_policy", policy)
        if store is not None:
            context.set_id_set_store(store)
        return context

    # Empty sequences are retained and do not issue a second SQL query.
    context = new_context(InMemoryIdSetStore())
    calls = 0
    compiled_sql = []
    fetch = service.transport.fetch_all_sql
    async def counted_fetch(compiled):
        nonlocal calls
        calls += 1
        compiled_sql.append(compiled.sql)
        return await fetch(compiled)
    service.transport.fetch_all_sql = counted_fetch
    for _ in range(2):
        empty = SelectQuery("User").and_filter(BinaryExpr(
            ColumnExpr("name"), BinaryOp.Eq, ValueExpr(Value.Text("missing"))))
        empty.order_asc("name").offset(0).limit(2)
        empty.optimize_pagination_with_id_set_config("empty", 60, 10)
        assert (await service.query(context, QueryRequest(empty))).rows == []
    assert calls == 1
    assert "ORDER BY name ASC, id ASC" in compiled_sql[0]
    assert context.id_set_count() == (0, "EXACT")
    assert context.id_set_plan() == "ID_SET_HIT"

    # max_ids + 1 is a lower bound and visibly falls back.
    overflow = SelectQuery("User").order_desc("id").offset(0).limit(2)
    overflow.optimize_pagination_with_id_set_config("overflow", 60, 3)
    assert len((await service.query(context, QueryRequest(overflow))).rows) == 2
    assert context.id_set_count() == (4, "LOWER_BOUND")
    assert context.id_set_plan() == "ID_SET_FALLBACK_LIMIT_EXCEEDED"

    # Unsupported grouped shape and store failure preserve ordinary results.
    unsupported = SelectQuery("User").count("row_count").limit(2)
    unsupported.optimize_pagination_with_id_set_config("unsupported", 60, 10)
    assert (await service.query(context, QueryRequest(unsupported))).rows[0]["row_count"] == 5
    assert context.id_set_plan() == "ID_SET_FALLBACK_UNSUPPORTED_SHAPE"

    class UnavailableStore:
        def get(self, _key): raise RuntimeError("down")
        def put(self, _retained): raise RuntimeError("down")
        def invalidate(self, _key): raise RuntimeError("down")
    context.set_id_set_store(UnavailableStore())
    fallback = SelectQuery("User").order_desc("id").offset(0).limit(2)
    fallback.optimize_pagination_with_id_set_config("store-down", 60, 10)
    assert [row["id"] for row in (await service.query(context, QueryRequest(fallback))).rows] == [5, 4]
    assert context.id_set_plan() == "ID_SET_FALLBACK_STORE_UNAVAILABLE"

    # TTL expiry rebuilds; principal, predicate, and active root produce separate keys.
    store = InMemoryIdSetStore()
    context = new_context(store)
    ttl = SelectQuery("User").order_desc("id").offset(0).limit(1)
    ttl.optimize_pagination_with_id_set_config("ttl", 1, 10)
    await service.query(context, QueryRequest(ttl))
    await asyncio.sleep(1.05)
    ttl = SelectQuery("User").order_desc("id").offset(0).limit(1)
    ttl.optimize_pagination_with_id_set_config("ttl", 1, 10)
    await service.query(context, QueryRequest(ttl))
    assert context.id_set_plan() == "ID_SET_BUILD"

    source_one, source_two, policy_one, policy_two = object(), object(), object(), object()
    cases = [
        ("tenant:user-a", 1, "one", source_one, policy_one),
        ("tenant:user-b", 1, "one", source_one, policy_one),
        ("tenant:user-b", 1, "two", source_one, policy_one),
        ("tenant:user-b", 2, "two", source_one, policy_one),
        ("tenant:user-b", 2, "two", source_two, policy_one),
        ("tenant:user-b", 2, "two", source_two, policy_two),
    ]
    for user, root, name, source, policy in cases:
        isolated = new_context(store, user, root, source, policy)
        query = SelectQuery("User").and_filter(BinaryExpr(
            ColumnExpr("name"), BinaryOp.Eq, ValueExpr(Value.Text(name))))
        query.order_desc("id").offset(0).limit(1)
        query.optimize_pagination_with_id_set_config("isolation", 60, 10)
        await service.query(isolated, QueryRequest(query))
        assert isolated.id_set_plan() == "ID_SET_BUILD"

    # A retained page does not shift when one of its IDs is deleted.
    context = new_context(InMemoryIdSetStore())
    snapshot = SelectQuery("User").order_desc("id").offset(2).limit(2)
    snapshot.optimize_pagination_with_id_set_config("deletion", 60, 10)
    assert [row["id"] for row in (await service.query(context, QueryRequest(snapshot))).rows] == [3, 2]
    async with aiosqlite.connect(temp_db) as db:
        await db.execute("DELETE FROM users WHERE id=3")
        await db.commit()
    snapshot = SelectQuery("User").order_desc("id").offset(2).limit(2)
    snapshot.optimize_pagination_with_id_set_config("deletion", 60, 10)
    assert [row["id"] for row in (await service.query(context, QueryRequest(snapshot))).rows] == [2]
    assert context.id_set_plan() == "ID_SET_HIT"

@pytest.mark.asyncio
async def test_id_set_pagination_coalesces_concurrent_contexts(temp_db, schema_provider):
    service = create_sqlite_service(temp_db, schema_provider)
    async with aiosqlite.connect(temp_db) as db:
        await db.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT, version INTEGER)")
        await db.executemany("INSERT INTO users VALUES (?,?,?)", [(1,"one",1),(2,"two",1)])
        await db.commit()
    store = InMemoryIdSetStore()
    calls = 0
    fetch = service.transport.fetch_all_sql
    async def counted_fetch(compiled):
        nonlocal calls
        calls += 1
        await asyncio.sleep(0.01)
        return await fetch(compiled)
    service.transport.fetch_all_sql = counted_fetch

    async def execute():
        context = RuntimeModule.new().entity(schema_provider.get_entity("User")).into_context()
        context.with_schema_provider(service).with_user_identifier("same-user")
        context.set_id_set_store(store)
        query = SelectQuery("User").order_desc("id").offset(0).limit(1)
        query.optimize_pagination_with_id_set_config("single-flight", 60, 10)
        return await service.query(context, QueryRequest(query))

    results = await asyncio.gather(execute(), execute())
    assert [[row["id"] for row in result.rows] for result in results] == [[2], [2]]
    assert calls == 3  # one ID build plus one page query per caller

@pytest.mark.asyncio
async def test_relation_subquery_resolves_generated_entity_name_and_executes(temp_db):
    provider = SimpleSchemaProvider()
    group = MockEntityDescriptor("QueryGroup")
    group.table_name_val = "query_group_data"
    group.properties = [
        MockPropertyDescriptor("id", DataType.I64, is_id=True),
        MockPropertyDescriptor("name", DataType.Text),
        MockPropertyDescriptor("version", DataType.I64, is_version=True),
    ]
    record = MockEntityDescriptor("QueryRecord")
    record.table_name_val = "query_record_data"
    record.properties = [
        MockPropertyDescriptor("id", DataType.I64, is_id=True),
        MockPropertyDescriptor("query_group", DataType.I64),
        MockPropertyDescriptor("name", DataType.Text),
        MockPropertyDescriptor("version", DataType.I64, is_version=True),
    ]
    provider.register_entity(group)
    provider.register_entity(record)
    service = create_sqlite_service(temp_db, provider)
    context = RuntimeModule.new().entity(group).entity(record).into_context()
    context.with_schema_provider(service)
    await context.ensure_schema()
    async with aiosqlite.connect(temp_db) as db:
        await db.executemany(
            "INSERT INTO query_group_data(id,name,version) VALUES (?,?,?)",
            [(1, "Core", 1), (2, "Other", 1), (3, "Empty", 1)])
        await db.executemany(
            "INSERT INTO query_record_data(id,query_group,name,version) VALUES (?,?,?,?)",
            [(11, 1, "included", 1), (12, 2, "excluded", 1),
             (13, None, "orphan", 1)])
        await db.commit()
    child = SelectQuery("QueryGroup").and_filter(BinaryExpr(
        column("name"), BinaryOp.Eq, ValueExpr(Value.Text("Core")))).project("id")
    included = SelectQuery("QueryRecord").and_filter(
        in_subquery(column("query_group"), "QueryGroup", child))
    excluded = SelectQuery("QueryRecord").and_filter(
        not_in_subquery(column("query_group"), "QueryGroup", child))

    assert [row["name"] for row in (await service.query(context, QueryRequest(included))).rows] == ["included"]
    assert [row["name"] for row in (await service.query(context, QueryRequest(excluded))).rows] == ["excluded"]

    async def ids(query):
        return [row["id"] for row in (await service.query(context, QueryRequest(query))).rows]

    assert await ids(SelectQuery("QueryRecord").and_filter(
        is_not_null(column("query_group"))).order_asc("id")) == [11, 12]
    assert await ids(SelectQuery("QueryRecord").and_filter(
        is_null(column("query_group"))).order_asc("id")) == [13]
    assert await ids(SelectQuery("QueryRecord").and_filter(
        in_subquery(column("query_group"), "QueryGroup", child)).order_asc("id")) == [11]
    assert await ids(SelectQuery("QueryRecord").and_filter(
        not_in_subquery(column("query_group"), "QueryGroup", child)).order_asc("id")) == [12]

    all_records = SelectQuery("QueryRecord").project("query_group")
    assert await ids(SelectQuery("QueryGroup").and_filter(
        in_subquery(column("id"), "QueryRecord", all_records)).order_asc("id")) == [1, 2]
    assert await ids(SelectQuery("QueryGroup").and_filter(
        not_in_subquery(column("id"), "QueryRecord", all_records)).order_asc("id")) == [3]

@pytest.mark.asyncio
async def test_complete_scalar_fixture_including_nullable_boolean_executes(temp_db):
    provider = SimpleSchemaProvider()
    record = MockEntityDescriptor("QueryRecord")
    record.table_name_val = "query_record_scalar"
    record.properties = [
        MockPropertyDescriptor("id", DataType.I64, is_id=True),
        MockPropertyDescriptor("required_text", DataType.Text),
        MockPropertyDescriptor("optional_text", DataType.Text),
        MockPropertyDescriptor("required_integer", DataType.I64),
        MockPropertyDescriptor("optional_long", DataType.I64),
        MockPropertyDescriptor("required_decimal", DataType.Decimal),
        MockPropertyDescriptor("required_float", DataType.F64),
        MockPropertyDescriptor("required_double", DataType.F64),
        MockPropertyDescriptor("required_date", DataType.Date),
        MockPropertyDescriptor("required_time", DataType.I64),
        MockPropertyDescriptor("required_timestamp", DataType.Timestamp),
        MockPropertyDescriptor("active", DataType.Bool),
        MockPropertyDescriptor("reviewed", DataType.Bool),
        MockPropertyDescriptor("version", DataType.I64, is_version=True),
    ]
    provider.register_entity(record)
    service = create_sqlite_service(temp_db, provider)
    context = RuntimeModule.new().entity(record).into_context()
    context.with_schema_provider(service)
    await context.ensure_schema()
    async with aiosqlite.connect(temp_db) as db:
        await db.executemany(
            "INSERT INTO query_record_scalar VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            [
                (1, "Alpha", "optional", 42, 42_000_000_000, "42.125", 42.5, 42.75,
                 "2026-08-29", 34_200_000, 1_777_632_600_000, 1, 0, 1),
                (2, "Beta", None, 7, None, "7.500", 7.5, 7.75,
                 "2026-08-30", 36_000_000, 1_777_720_400_000, 0, None, 1),
                (3, "Gamma", "tail", 99, 99_000_000_000, "99.875", 99.5, 99.75,
                 "2026-08-31", 37_800_000, 1_777_808_200_000, 1, 1, 1),
            ])
        await db.commit()

    async def ids(expr):
        query = SelectQuery("QueryRecord").project("id").and_filter(expr).order_asc("id")
        return [row["id"] for row in (await service.query(context, QueryRequest(query))).rows]

    assert await ids(BinaryExpr(column("required_text"), BinaryOp.Eq, value("Alpha"))) == [1]
    assert await ids(BinaryExpr(column("required_text"), BinaryOp.Ne, value("Alpha"))) == [2, 3]
    assert await ids(in_list("required_text", ["Alpha", "Gamma"])) == [1, 3]
    assert await ids(contain("required_text", "et")) == [2]
    assert await ids(between(column("required_integer"), value(40), value(100))) == [1, 3]
    assert await ids(BinaryExpr(column("required_decimal"), BinaryOp.Gt, value(Decimal("50")))) == [3]
    assert await ids(BinaryExpr(column("required_float"), BinaryOp.Lte, value(7.5))) == [2]
    assert await ids(BinaryExpr(column("required_double"), BinaryOp.Gte, value(99.75))) == [3]
    assert await ids(between(column("required_date"), value(date(2026, 8, 30)), value(date(2026, 8, 31)))) == [2, 3]
    assert await ids(BinaryExpr(column("required_time"), BinaryOp.Gt, value(36_000_000))) == [3]
    assert await ids(BinaryExpr(column("required_timestamp"), BinaryOp.Lt, value(Timestamp(1_777_750_000_000)))) == [1, 2]
    assert await ids(is_null(column("optional_text"))) == [2]
    assert await ids(is_not_null(column("optional_long"))) == [1, 3]
    assert await ids(BinaryExpr(column("active"), BinaryOp.Eq, value(False))) == [2]
    assert await ids(BinaryExpr(column("reviewed"), BinaryOp.Eq, value(True))) == [3]
    assert await ids(BinaryExpr(column("reviewed"), BinaryOp.Eq, value(False))) == [1]
    assert await ids(is_null(column("reviewed"))) == [2]

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
    assert context.sql_log_options().select and context.sql_log_options().mutation
    secret = "secret-customer-value"
    insert = MutationRequest(InsertCommand("User", {
        "id": Value.I64(1), "name": Value.Text(secret), "version": Value.I64(1)
    }))
    await service.mutate(context, insert)
    query = SelectQuery("User").filter(
        BinaryExpr(ColumnExpr("name"), BinaryOp.Eq, ValueExpr(Value.Text(secret))))
    request = QueryRequest(query, trace_chain=[
        TraceNode(kind="relation", name="User.organization", comment="organization"),
        TraceNode(kind="relation", name="Organization.region", comment="region"),
        TraceNode(kind="relation", name="Region.country", comment="country"),
    ]).comment("what: load governed users").purpose("why: verify trace inheritance")
    await service.query(context, request)

    entries = context.sql_logs()
    assert len(entries) == 2
    assert all(entry.sql and secret not in entry.sql for entry in entries)
    assert all(entry.params for entry in entries)
    assert any(entry.result_count is not None for entry in entries)
    assert any(entry.affected_rows is not None for entry in entries)
    select_entry = next(entry for entry in entries if entry.operation.is_select())
    assert select_entry.comment == "what: load governed users"
    assert select_entry.purpose == "why: verify trace inheritance"
    assert [node.kind for node in select_entry.trace_path] == [
        "operation", "request", "relation", "relation", "relation", "provider", "sql"
    ]

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
        await db.execute("CREATE TABLE orderline (id INTEGER PRIMARY KEY, order_id INTEGER, name TEXT, state TEXT, version INTEGER)")
        await db.executemany("INSERT INTO orders VALUES (?, ?)", [(11, 1), (12, 1), (13, 1)])
        lines = [(order_id * 100 + index, order_id, "same", "visible", 1)
                 for order_id in (11, 12) for index in range(1, 6)]
        lines.append((9999, 11, "same", "hidden", 1))
        await db.executemany("INSERT INTO orderline VALUES (?, ?, ?, ?, ?)", lines)
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
        MockPropertyDescriptor("state", DataType.Text),
        MockPropertyDescriptor("version", DataType.I64, is_version=True),
    ]
    provider.register_entity(order)
    provider.register_entity(line)
    service = create_sqlite_service(temp_db, provider)
    queries = []
    delegate = service.transport.fetch_all_sql
    async def recording_fetch(compiled):
        queries.append(compiled.sql)
        return await delegate(compiled)
    service.transport.fetch_all_sql = recording_fetch

    completions = []
    class Telemetry:
        def start(self, operation):
            class Scope:
                def success(self, attributes=None):
                    if operation.family == "relation_load":
                        completions.append(attributes)
                def failure(self, error): pass
            return Scope()
    context = RuntimeModule.new().into_context().with_runtime_telemetry(Telemetry())

    def nested(threshold=None):
        child = (SelectQuery("OrderLine").project("id", "name")
                 .and_filter(BinaryExpr(column("state"), BinaryOp.Eq, value("visible")))
                 .and_filter(BinaryExpr(column("version"), BinaryOp.Gt, value(0)))
                 .order_desc("name").limit(3))
        if threshold is not None:
            child.top_n_probe_parent_threshold(threshold)
        return SelectQuery("Order").order_asc("id").relation_query("lines", child)

    def relation_ids(rows):
        return {parent["id"]: [child["id"] for child in parent["lines"]]
                for parent in rows}

    result = await service.query(context, QueryRequest(nested()))
    assert len(result.rows) == 3
    assert [len(parent["lines"]) for parent in result.rows] == [3, 3, 0]
    assert len(queries) == 4
    assert all("COUNT(" not in sql.upper() for sql in queries)
    assert all("state" in sql and "version" in sql for sql in queries[1:])
    assert all("__teaql_partition_rank" not in child
               for parent in result.rows for child in parent["lines"])
    relation_entries = [entry for entry in context.sql_logs()
                        if any(node.kind == "relation" for node in entry.trace_path)]
    assert relation_entries
    assert [node.kind for node in relation_entries[0].trace_path] == [
        "operation", "request", "relation", "provider", "sql"]
    assert relation_entries[0].trace_path[2].name == "Order.lines"
    probe_ids = relation_ids(result.rows)

    queries.clear()
    window = await service.query(context, QueryRequest(nested(0)))
    assert len(queries) == 2 and "ROW_NUMBER() OVER" in queries[1]
    assert relation_ids(window.rows) == probe_ids
    assert "state" in queries[1] and "version" in queries[1]

    for threshold, expected_queries in ((3, 4), (2, 2)):
        queries.clear()
        first = await service.query(context, QueryRequest(nested(threshold)))
        first_sql = list(queries)
        queries.clear()
        second = await service.query(context, QueryRequest(nested(threshold)))
        assert relation_ids(first.rows) == relation_ids(second.rows) == probe_ids
        assert queries == first_sql
        assert len(queries) == expected_queries

    assert any(event["teaql.relation.selected_plan"] == "window"
               and event["teaql.relation.parent_count"] == 3
               and event["teaql.relation.per_parent_limit"] == 3
               for event in completions)

@pytest.mark.asyncio
async def test_top_n_relation_index_ensure_is_idempotent(temp_db):
    provider = SimpleSchemaProvider()
    line = MockEntityDescriptor("OrderLine")
    line.table_name_val = "orderline"
    line.properties = [
        MockPropertyDescriptor("id", DataType.I64, is_id=True),
        MockPropertyDescriptor("order_id", DataType.I64),
    ]
    provider.register_entity(line)
    service = create_sqlite_service(temp_db, provider)
    context = (RuntimeModule.new().entity(line)
               .provide_custom_dependency("dataService", service)
               .provide_custom_dependency("schema_provider", service).into_context())
    await context.ensure_schema()
    await context.ensure_schema()
    async with aiosqlite.connect(temp_db) as db:
        rows = await (await db.execute("PRAGMA index_list('orderline')")).fetchall()
    assert [row[1] for row in rows].count("idx_orderline_order_id_id_desc") == 1

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
