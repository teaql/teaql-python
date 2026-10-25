"""#236: Python bool is not interchangeable with an integer in a typed entity."""
import sqlite3
import pytest
from teaql.core.meta import EntityDescriptor, PropertyDescriptor
from teaql.core.mutation import InsertCommand, MutationRequest
from teaql.core.query import SelectQuery
from teaql.core.value import DataType
from teaql.data_service import QueryRequest
from teaql.provider.sqlite import SimpleSchemaProvider, create_sqlite_service
from teaql.runtime import RuntimeModule


def fixture(path):
    descriptor = (EntityDescriptor("BooleanProbe").table_name("boolean_probe")
        .property(PropertyDescriptor("id", DataType.I64).is_id())
        .property(PropertyDescriptor("version", DataType.I64).is_version())
        .property(PropertyDescriptor("active", DataType.Bool).column_name("active_column"))
        .property(PropertyDescriptor("note", DataType.Text)))
    schema = SimpleSchemaProvider()
    schema.register_entity(descriptor)
    service = create_sqlite_service(str(path), schema)
    context = RuntimeModule.new().entity(descriptor).into_context().with_schema_provider(service)
    return descriptor, service, context


def query():
    return SelectQuery("BooleanProbe").limit(20).comment("read typed booleans").purpose("verify bool is not integer")


@pytest.mark.asyncio
async def test_native_bool_list_stream_and_mutation_readback(tmp_path):
    _, service, context = fixture(tmp_path / "boolean.sqlite")
    try:
        await context.ensure_schema()
        for value in (False, True, None):
            result = await service.mutate(context, MutationRequest(InsertCommand.new("BooleanProbe")
                .value("active", value).value("note", "0"), "create typed boolean fixture"))
            actual = result.persisted_record["active"]
            assert type(actual) is type(value) and actual == value
        rows = (await service.query(context, QueryRequest(query().order_asc("id")))).rows
        assert [type(row["active"]) for row in rows] == [bool, bool, type(None)]
        assert [row["active"] for row in rows] == [False, True, None]
        assert all(type(row["note"]) is str and row["note"] == "0" for row in rows)
        chunks = [chunk async for chunk in service.query_stream(context, QueryRequest(query().order_asc("id")), 2)]
        assert [type(row["active"]) for chunk in chunks for row in chunk.rows] == [bool, bool, type(None)]
        partial = (await service.query(context, QueryRequest(query().projects(["id"])))).rows
        assert all("active" not in row for row in partial)
        counted = (await service.query(context, QueryRequest(query().count_field("id", "active")))).rows[0]
        assert type(counted["active"]) is int and counted["active"] == 3, "computed alias is not a modeled Boolean"
        bounds = (await service.query(context, QueryRequest(query().min("active", "lowest").max("active", "highest")))).rows[0]
        assert type(bounds["lowest"]) is bool and bounds["lowest"] is False
        assert type(bounds["highest"]) is bool and bounds["highest"] is True
    finally:
        await service.close()


@pytest.mark.parametrize("value", [0, 1, False, True, None])
def test_canonical_physical_keys_and_null_are_not_conflated(tmp_path, value):
    descriptor, service, _ = fixture(tmp_path / "unit.sqlite")
    rows = [{"active": value, "active_column": value, "note": 0}, {}]
    service._normalize_loaded_scalars(rows, descriptor)
    expected = None if value is None else bool(value)
    for field in ("active", "active_column"):
        assert type(rows[0][field]) is type(expected) and rows[0][field] == expected
    assert type(rows[0]["note"]) is int and rows[1] == {}


@pytest.mark.asyncio
@pytest.mark.parametrize("bad", [2, -1, "PRIVATE_BAD_BOOLEAN", 0.5])
async def test_corrupt_boolean_read_is_field_specific_and_value_free(tmp_path, bad):
    database = tmp_path / "corrupt.sqlite"
    _, service, context = fixture(database)
    try:
        await context.ensure_schema()
        # Explicit low-level corruption oracle, never replacement business code.
        with sqlite3.connect(database) as connection:
            connection.execute("INSERT INTO boolean_probe(id,version,active_column,note) VALUES(1,1,?,'corrupt')", [bad])
        with pytest.raises(ValueError, match="invalid loaded Boolean field BooleanProbe.active") as error:
            await service.query(context, QueryRequest(query()))
        assert str(bad) not in str(error.value)
    finally:
        await service.close()
