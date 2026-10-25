"""#236: SQLite never silently persists NaN as NULL or returns Infinity."""
import sqlite3

import pytest

from teaql.core.meta import EntityDescriptor, PropertyDescriptor
from teaql.core.mutation import InsertCommand, MutationRequest
from teaql.core.query import SelectQuery
from teaql.core.value import DataType, Value
from teaql.data_service import QueryRequest
from teaql.provider.sqlite import SimpleSchemaProvider, create_sqlite_service
from teaql.provider.sqlite.transport import SqliteTransport
from teaql.runtime import RuntimeModule
from teaql.sql.types import CompiledQuery


@pytest.mark.asyncio
@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -float("inf")])
@pytest.mark.parametrize("operation", ["fetch", "execute", "stream"])
async def test_nonfinite_bind_fails_before_connect(tmp_path, bad, operation):
    transport = SqliteTransport(str(tmp_path / "no-io.sqlite"))
    def forbidden():
        raise AssertionError("a nonfinite bind opened a connection")
    transport._connect = forbidden
    command = CompiledQuery("SELECT ?", [Value.F64(bad)])
    with pytest.raises(ValueError, match="nonfinite SQLite floating-point parameter"):
        if operation == "fetch":
            await transport.fetch_all_sql(command)
        elif operation == "execute":
            await transport.execute_sql(command)
        else:
            async for _ in transport.stream_sql(command, 1):
                pass
    assert not (tmp_path / "no-io.sqlite").exists()


def fixture(path):
    descriptor = (EntityDescriptor("FloatProbe").table_name("float_probe")
        .property(PropertyDescriptor("id", DataType.I64).is_id())
        .property(PropertyDescriptor("version", DataType.I64).is_version())
        .property(PropertyDescriptor("amount", DataType.F64).column_name("amount_column"))
        .property(PropertyDescriptor("note", DataType.Text)))
    schema = SimpleSchemaProvider()
    schema.register_entity(descriptor)
    service = create_sqlite_service(str(path), schema)
    context = RuntimeModule().schema_entity(descriptor).into_context().with_schema_provider(service)
    return descriptor, service, context


def query():
    return SelectQuery("FloatProbe").limit(20).comment("read finite scalars").purpose("verify no silent coercion")


@pytest.mark.asyncio
@pytest.mark.parametrize("bad", [float("inf"), -float("inf"), "PRIVATE_INVALID_FLOAT"])
@pytest.mark.parametrize("operation", ["list", "stream", "minimum"])
async def test_corrupt_float_read_rejects_with_canonical_value_free_error(tmp_path, bad, operation):
    database = tmp_path / "corrupt.sqlite"
    _, service, context = fixture(database)
    try:
        await context.ensure_schema()
        # Explicit corruption oracle, not the application mutation path.
        with sqlite3.connect(database) as connection:
            connection.execute("INSERT INTO float_probe VALUES (1,1,?,'bad fixture')", [bad])
        with pytest.raises(ValueError, match="invalid loaded Float/Double field FloatProbe.amount") as caught:
            if operation == "stream":
                async for _ in service.query_stream(context, QueryRequest(query()), 1):
                    pass
            else:
                await service.query(context, QueryRequest(query().min("amount", "lowest") if operation == "minimum" else query()))
        assert "PRIVATE_INVALID_FLOAT" not in str(caught.value)
        assert "inf" not in str(caught.value)
    finally:
        await service.close()


@pytest.mark.asyncio
async def test_finite_values_null_projection_count_alias_and_overflow_sum(tmp_path):
    descriptor, service, context = fixture(tmp_path / "finite.sqlite")
    try:
        await context.ensure_schema()
        for value in (-0.0, 1.25, None):
            result = await service.mutate(context, MutationRequest(InsertCommand.new("FloatProbe")
                .value("amount", value).value("note", "Infinity"), "create finite scalar fixture"))
            assert result.persisted_record["amount"] == value
        rows = (await service.query(context, QueryRequest(query().order_asc("id")))).rows
        assert [row["amount"] for row in rows] == [0.0, 1.25, None]
        assert all(row["note"] == "Infinity" for row in rows)
        partial = (await service.query(context, QueryRequest(query().projects(["id"])))).rows
        assert all("amount" not in row for row in partial)
        counted = (await service.query(context, QueryRequest(query().count_field("id", "amount")))).rows[0]
        assert type(counted["amount"]) is int and counted["amount"] == 3
        untouched = [{"amount_column": None, "note": "Infinity"}, {}]
        service._normalize_loaded_scalars(untouched, descriptor)
        assert untouched == [{"amount_column": None, "note": "Infinity"}, {}]
        for _ in range(2):
            await service.mutate(context, MutationRequest(InsertCommand.new("FloatProbe")
                .value("amount", 1e308), "create finite aggregate-overflow operands"))
        with pytest.raises(ValueError, match="invalid loaded Float/Double field FloatProbe.amount"):
            await service.query(context, QueryRequest(query().sum("amount", "total")))
    finally:
        await service.close()
