"""#64: metadata-driven native UTC instants, not millisecond-looking strings."""
from datetime import datetime, timedelta, timezone
import sqlite3

import pytest

from teaql.core.expr import Expr
from teaql.core.meta import EntityDescriptor, PropertyDescriptor
from teaql.core.mutation import InsertCommand, MutationRequest
from teaql.core.query import SelectQuery
from teaql.core.value import DataType, Timestamp, Value
from teaql.data_service import QueryRequest
from teaql.provider.sqlite import SimpleSchemaProvider, create_sqlite_service
from teaql.runtime import RuntimeModule
from teaql.sql.types import CompiledQuery

EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)


@pytest.mark.parametrize("millis", [1001, 1003, 1005, 1007, 1009, 1011, -1001, -1, 0, 1961662530123])
def test_native_datetime_conversion_does_not_lose_a_millisecond(millis):
    native = EPOCH + timedelta(milliseconds=millis)
    for offset in (0, 8, -5):
        value = native.astimezone(timezone(timedelta(hours=offset)))
        assert Value.from_any(value).val == Timestamp(millis)
        assert Value.from_any(value).to_json_value() == millis


def fixture(path):
    entity = EntityDescriptor("ClockRecord").table_name("clock_data")
    entity.property(PropertyDescriptor("id", DataType.I64).is_id())
    entity.property(PropertyDescriptor("version", DataType.I64).is_version())
    entity.property(PropertyDescriptor("instant", DataType.Timestamp).column_name("instant_column"))
    entity.property(PropertyDescriptor("note", DataType.Text))
    schema = SimpleSchemaProvider()
    schema.register_entity(entity)
    service = create_sqlite_service(str(path), schema)
    context = RuntimeModule.new().entity(entity).into_context().with_schema_provider(service)
    return service, context


def query():
    return (SelectQuery("ClockRecord").limit(20).comment("read native UTC instants")
            .purpose("verify typed timestamp round trips"))


async def insert(service, context, instant):
    return await service.mutate(context, MutationRequest(
        InsertCommand.new("ClockRecord").value("instant", instant).value("note", "1234"),
        comment="create timestamp regression operand"))


@pytest.mark.asyncio
async def test_timestamps_are_native_in_readback_list_stream_and_json(tmp_path):
    service, context = fixture(tmp_path / "typed.sqlite")
    millis = [-315619199877, -1, 0, 86400123, 1961662530123]
    expected = [EPOCH + timedelta(milliseconds=value) for value in millis]
    try:
        await context.ensure_schema()
        await context.ensure_schema()
        for value, native in zip(millis, expected):
            saved = await insert(service, context, Timestamp(value))
            assert saved.persisted_record["instant"] == native
            assert isinstance(saved.persisted_record["instant"], datetime)
        await insert(service, context, None)
        rows = (await service.query(context, QueryRequest(query().order_asc("id")))).rows
        assert [row["instant"] for row in rows] == expected + [None]
        assert all(row["note"] == "1234" for row in rows), "never guess a text field is an instant"
        assert [Value.from_any(row["instant"]).to_json_value() for row in rows] == millis + [None]
        chunks = [chunk async for chunk in service.query_stream(context, QueryRequest(query().order_asc("id")), 2)]
        assert [row["instant"] for chunk in chunks for row in chunk.rows] == expected + [None]
        partial = (await service.query(context, QueryRequest(query().projects(["id"])))).rows
        assert all("instant" not in row for row in partial)
        physical = await service.transport.fetch_all_sql(CompiledQuery(
            "SELECT typeof(instant_column) AS storage FROM clock_data ORDER BY id", []))
        assert [row["storage"] for row in physical] == ["integer"] * len(millis) + ["null"]
    finally:
        await service.close()


@pytest.mark.asyncio
async def test_timestamp_order_range_and_typed_aliases(tmp_path):
    service, context = fixture(tmp_path / "ordered.sqlite")
    millis = [-315619199877, -1, 0, 1, 1000]
    try:
        await context.ensure_schema()
        for value in reversed(millis):
            await insert(service, context, Timestamp(value))
        ordered = (await service.query(context, QueryRequest(query().order_asc("instant")))).rows
        assert [row["instant"] for row in ordered] == [EPOCH + timedelta(milliseconds=value) for value in millis]
        before = (await service.query(context, QueryRequest(query().filter(Expr.lt("instant", Timestamp(0)))))).rows
        assert len(before) == 2
        aggregates = query().min("instant", "earliest").max("instant", "latest")
        row = (await service.query(context, QueryRequest(aggregates))).rows[0]
        assert row == {"earliest": EPOCH + timedelta(milliseconds=millis[0]),
                       "latest": EPOCH + timedelta(milliseconds=millis[-1])}
        collision = (await service.query(context, QueryRequest(query().count_field("id", "instant")))).rows[0]
        assert collision == {"instant": len(millis)}, "aggregate alias is not a native timestamp column"
    finally:
        await service.close()


@pytest.mark.asyncio
async def test_legacy_text_timestamp_requires_explicit_migration_without_rewrite(tmp_path):
    database = tmp_path / "legacy.sqlite"
    with sqlite3.connect(database) as connection:
        connection.execute("CREATE TABLE clock_data (id INTEGER PRIMARY KEY, version INTEGER, instant_column TEXT, note TEXT)")
        connection.execute("INSERT INTO clock_data VALUES (1, 1, '-1', 'legacy')")
    service, context = fixture(database)
    try:
        with pytest.raises(ValueError, match="SQLITE_TIMESTAMP_MIGRATION_REQUIRED"):
            await context.ensure_schema()
        with sqlite3.connect(database) as connection:
            assert connection.execute("SELECT instant_column, typeof(instant_column) FROM clock_data").fetchall() == [("-1", "text")]
    finally:
        await service.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("bad", ["PRIVATE_INVALID_INSTANT", 1.5, 9223372036854775807])
async def test_invalid_loaded_timestamp_is_value_free_and_not_silently_coerced(tmp_path, bad):
    database = tmp_path / "invalid.sqlite"
    service, context = fixture(database)
    try:
        await context.ensure_schema()
        with sqlite3.connect(database) as connection:
            connection.execute("INSERT INTO clock_data (id, version, instant_column, note) VALUES (1, 1, ?, 'invalid fixture')", [bad])
        with pytest.raises(ValueError, match="invalid loaded Timestamp field ClockRecord.instant") as error:
            await service.query(context, QueryRequest(query()))
        assert str(bad) not in str(error.value)
    finally:
        await service.close()
