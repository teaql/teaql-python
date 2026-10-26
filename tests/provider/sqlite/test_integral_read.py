"""#236: corrupt stored integer values cannot be silently narrowed by Q or E."""
import sqlite3
from decimal import Decimal

import pytest

from teaql.core.meta import EntityDescriptor, PropertyDescriptor
from teaql.core.mutation import InsertCommand, MutationRequest, UpdateCommand
from teaql.core.query import SelectQuery
from teaql.core.value import DataType
from teaql.data_service import QueryRequest
from teaql.provider.sqlite import SimpleSchemaProvider, create_sqlite_service
from teaql.runtime import RuntimeModule


def fixture(database):
    descriptor = (EntityDescriptor("IntegerProbe").table_name("integer_probe")
        .property(PropertyDescriptor("id", DataType.I64).is_id())
        .property(PropertyDescriptor("version", DataType.I64).is_version())
        .property(PropertyDescriptor("integer_count", DataType.I64).integer32().column_name("count_column"))
        .property(PropertyDescriptor("long_count", DataType.I64)))
    schema = SimpleSchemaProvider()
    schema.register_entity(descriptor)
    service = create_sqlite_service(str(database), schema)
    context = RuntimeModule().schema_entity(descriptor).into_context().with_schema_provider(service)
    return descriptor, service, context


def query():
    return SelectQuery("IntegerProbe").limit(20).comment("read exact integers").purpose("reject corrupt stored values")


@pytest.mark.asyncio
@pytest.mark.parametrize("bad", [2**31, -(2**31) - 1, 1.5, "PRIVATE_INVALID_INTEGER"])
@pytest.mark.parametrize("operation", ["list", "stream", "min", "max"])
async def test_integral_read_rejects_corrupt_loaded_integer(tmp_path, bad, operation):
    database = tmp_path / "corrupt.sqlite"
    _, service, context = fixture(database)
    try:
        await context.ensure_schema()
        with sqlite3.connect(database) as connection:
            connection.execute("INSERT INTO integer_probe VALUES(1,1,?,42)", [bad])
        with pytest.raises(ValueError, match="invalid loaded Integer field IntegerProbe.integer_count") as error:
            if operation == "stream":
                async for _ in service.query_stream(context, QueryRequest(query()), 1):
                    pass
            else:
                selected = getattr(query(), operation)("integer_count", "value") if operation in ("min", "max") else query()
                await service.query(context, QueryRequest(selected))
        assert "PRIVATE_INVALID_INTEGER" not in str(error.value)
        # Invalid unselected columns do not poison a valid sparse projection.
        rows = (await service.query(context, QueryRequest(query().projects(["id", "long_count"])))) .rows
        assert rows == [{"id": 1, "long_count": 42}]
    finally:
        await service.close()


@pytest.mark.asyncio
async def test_integral_read_count_sum_and_average_have_their_own_result_domains(tmp_path):
    _, service, context = fixture(tmp_path / "aggregates.sqlite")
    try:
        await context.ensure_schema()
        for value in (2**31 - 1, 2**31 - 1, None):
            await service.mutate(context, MutationRequest(InsertCommand.new("IntegerProbe")
                .value("integer_count", value).value("long_count", 2**63 - 1), "create exact Integer operand"))
        result = (await service.query(context, QueryRequest(query().sum("integer_count", "integer_count")
            .count_field("id", "long_count").avg("integer_count", "average")))).rows[0]
        assert result == {"integer_count": 2 * (2**31 - 1), "long_count": 3, "average": float(2**31 - 1)}
    finally:
        await service.close()


def test_integral_read_validation_does_not_mutate_rows_or_conflate_absence_and_null(tmp_path):
    descriptor, service, _ = fixture(tmp_path / "unused.sqlite")
    rows = [{"integer_count": 1, "count_column": None}, {}]
    service._normalize_loaded_scalars(rows, descriptor)
    assert rows == [{"integer_count": 1, "count_column": None}, {}]
    corrupt = [{"integer_count": 1}, {"integer_count": 1.5}]
    with pytest.raises(ValueError):
        service._normalize_loaded_scalars(corrupt, descriptor)
    assert corrupt == [{"integer_count": 1}, {"integer_count": 1.5}]


@pytest.mark.asyncio
@pytest.mark.parametrize("field,expected", [("integer_count", 2**31 - 1), ("integer_count", -(2**31)),
    ("long_count", 2**63 - 1), ("long_count", -(2**63))])
@pytest.mark.parametrize("operation", ["insert", "update"])
async def test_integral_read_scaled_decimal_fix_output_binds_as_exact_integer(tmp_path, field, expected, operation):
    database = tmp_path / "exact.sqlite"
    _, service, context = fixture(database)
    try:
        await context.ensure_schema()
        value = Decimal(str(expected) + ".0")
        command = InsertCommand.new("IntegerProbe").value("integer_count", 0).value("long_count", 0)
        if operation == "update":
            saved = await service.mutate(context, MutationRequest(command, "create exact integral baseline"))
            command = UpdateCommand.new("IntegerProbe", saved.persisted_record["id"]).expected_version(1)
        command.value(field, value)
        saved = await service.mutate(context, MutationRequest(command, "persist exact integral Decimal from Fix"))
        assert type(saved.persisted_record[field]) is int and saved.persisted_record[field] == expected
        assert command.values[field].val is value, "SQL bindings must not rewrite customer policy input"
        physical = "count_column" if field == "integer_count" else "long_count"
        with sqlite3.connect(database) as connection:
            assert connection.execute(f"SELECT typeof({physical}),{physical} FROM integer_probe").fetchone() == ("integer", expected)
    finally:
        await service.close()
