"""Issue #54: exact Decimal behavior at the real SQLite provider boundary."""

from decimal import Decimal, localcontext

import pytest

from teaql.core.expr import Expr, BinaryExpr, BinaryOp, ExprFunction, FunctionExpr, column, in_list, value
from teaql.core.meta import EntityDescriptor, PropertyDescriptor
from teaql.core.mutation import InsertCommand, MutationRequest, UpdateCommand
from teaql.core.query import SelectQuery
from teaql.core.value import DataType, Value
from teaql.data_service import QueryRequest
from teaql.provider.sqlite import SimpleSchemaProvider, create_sqlite_service
from teaql.runtime import RuntimeModule
from teaql.sql.types import CompiledQuery, DatabaseKind, InvalidFunctionArgumentsError, _sql_literal


def amount_service(path):
    entity = EntityDescriptor("Amount").table_name("amount_data")
    entity.property(PropertyDescriptor("id", DataType.I64).is_id())
    entity.property(PropertyDescriptor("version", DataType.I64).is_version())
    entity.property(PropertyDescriptor("amount", DataType.Decimal))
    entity.property(PropertyDescriptor("label", DataType.Text))
    schema = SimpleSchemaProvider()
    schema.register_entity(entity)
    service = create_sqlite_service(str(path), schema)
    context = RuntimeModule.new().entity(entity).into_context().with_schema_provider(service)
    return service, context, entity


def bounded_query():
    return (SelectQuery("Amount").limit(100)
            .comment("read exact decimal fixture").purpose("verify issue 54"))


async def insert(service, context, amount, label="decimal fixture"):
    return await service.mutate(context, MutationRequest(
        InsertCommand.new("Amount").value("amount", amount).value("label", label),
        comment="create exact decimal fixture"))


@pytest.mark.asyncio
async def test_decimal_persists_exactly_through_readback_query_update_and_stream(tmp_path):
    service, context, _ = amount_service(tmp_path / "exact.sqlite")
    try:
        await context.ensure_schema()
        await context.ensure_schema()
        precise = Decimal("123456789012.3456789")
        created = await insert(service, context, precise)
        assert created.persisted_record["amount"] == precise
        assert isinstance(created.persisted_record["amount"], Decimal)
        scaled = await insert(service, context, Decimal("3.50"))
        assert str(scaled.persisted_record["amount"]) == "3.50"
        rows = (await service.query(context, QueryRequest(bounded_query().order_asc("id")))).rows
        assert [row["amount"] for row in rows] == [precise, Decimal("3.50")]
        chunks = [chunk async for chunk in service.query_stream(
            context, QueryRequest(bounded_query().order_asc("id")), 1)]
        assert [row["amount"] for chunk in chunks for row in chunk.rows] == [precise, Decimal("3.50")]
        replacement = Decimal("9007199254740993.123456789")
        changed = await service.mutate(context, MutationRequest(
            UpdateCommand.new("Amount", created.persisted_record["id"])
            .expected_version(created.persisted_record["version"]).value("amount", replacement),
            comment="update exact decimal fixture"))
        assert changed.persisted_record["amount"] == replacement
        physical = await service.transport.fetch_all_sql(CompiledQuery(
            "SELECT typeof(amount) AS storage, amount FROM amount_data ORDER BY id", []))
        assert physical == [{"storage": "text", "amount": str(replacement)},
                            {"storage": "text", "amount": "3.50"}]
    finally:
        await service.close()


@pytest.mark.asyncio
async def test_decimal_predicates_numeric_order_and_scale_equivalent_groups(tmp_path):
    service, context, _ = amount_service(tmp_path / "queries.sqlite")
    try:
        await context.ensure_schema()
        values = [Decimal(s) for s in ("10", "2", "-10", "-0.1", "3.50", "3.5", "0.1")]
        for amount in values:
            await insert(service, context, amount)
        ordered = (await service.query(context, QueryRequest(bounded_query().order_asc("amount")))).rows
        assert [row["amount"] for row in ordered] == sorted(values)
        for predicate, expected in [
            (Expr.eq("amount", Decimal("3.500")), [Decimal("3.50"), Decimal("3.5")]),
            (Expr.gt("amount", Decimal("3.5")), [Decimal("10")]),
            (in_list("amount", [Decimal("2.0"), Decimal("10.00")]), [Decimal("2"), Decimal("10")]),
        ]:
            rows = (await service.query(context, QueryRequest(
                bounded_query().filter(predicate).order_asc("amount")))).rows
            assert [row["amount"] for row in rows] == expected
        grouped = (await service.query(context, QueryRequest(
            bounded_query().group_by("amount").count_field("id", "rows").order_asc("amount")))).rows
        assert len(grouped) == 6
        assert next(row["rows"] for row in grouped if row["amount"] == Decimal("3.5")) == 2
    finally:
        await service.close()


@pytest.mark.asyncio
async def test_decimal_sum_min_max_are_exact_and_independent_of_decimal_context(tmp_path):
    service, context, _ = amount_service(tmp_path / "aggregates.sqlite")
    try:
        await context.ensure_schema()
        for amount in [Decimal("123456789012.3456789"), Decimal("0.0000001"), None]:
            await insert(service, context, amount)
        query = bounded_query().sum("amount", "total").min("amount", "smallest").max("amount", "largest")
        with localcontext() as arithmetic:
            arithmetic.prec = 3
            row = (await service.query(context, QueryRequest(query))).rows[0]
        assert row == {"total": Decimal("123456789012.3456790"),
                       "smallest": Decimal("0.0000001"),
                       "largest": Decimal("123456789012.3456789")}
        collision = (await service.query(context, QueryRequest(
            bounded_query().count_field("id", "amount")))).rows[0]
        assert collision["amount"] == 3 and isinstance(collision["amount"], int)
        empty = (await service.query(context, QueryRequest(
            bounded_query().filter(Expr.lt("id", 0)).sum("amount", "total")))).rows[0]
        assert empty["total"] is None
    finally:
        await service.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("declaration", ["NUMERIC", "REAL", "TEXT", "TEAQL_DECIMAL_TEXT",
                                          "TEAQL_DECIMAL_TEXT COLLATE TEAQL_DECIMAL"])
async def test_decimal_existing_schema_requires_explicit_migration(tmp_path, declaration):
    service, context, _ = amount_service(tmp_path / "legacy.sqlite")
    try:
        await service.transport.execute_sql(CompiledQuery(
            f"CREATE TABLE amount_data (id INTEGER PRIMARY KEY, version INTEGER, amount {declaration}, label TEXT)", []))
        with pytest.raises(ValueError, match="SQLITE_DECIMAL_MIGRATION_REQUIRED"):
            await context.ensure_schema()
    finally:
        await service.close()


@pytest.mark.asyncio
async def test_decimal_checks_reject_malformed_storage_and_text_is_not_a_decimal(tmp_path):
    service, context, _ = amount_service(tmp_path / "validation.sqlite")
    try:
        await context.ensure_schema()
        for text in ("NaN", "Infinity", "not-a-decimal", "1_000", " 1.2 "):
            with pytest.raises(Exception, match="CHECK constraint failed"):
                await service.transport.execute_sql(CompiledQuery(
                    "INSERT INTO amount_data (id, version, amount) VALUES (100, 1, ?)", [Value.Text(text)]))
        sentinel = "__teaql_decimal__:1.25"
        created = await insert(service, context, None, sentinel)
        assert created.persisted_record["label"] == sentinel
    finally:
        await service.close()


def test_decimal_average_requires_an_explicit_precision_policy():
    service, _, entity = amount_service("unused.sqlite")
    with pytest.raises(InvalidFunctionArgumentsError, match="precision policy"):
        service.dialect.compile_select(entity, bounded_query().avg("amount", "average"))


@pytest.mark.asyncio
async def test_decimal_aggregate_expressions_and_having_keep_numeric_semantics(tmp_path):
    service, context, _ = amount_service(tmp_path / "expressions.sqlite")
    try:
        await context.ensure_schema()
        for amount, label in [(Decimal("2.0"), "small"), (Decimal("10.00"), "large")]:
            await insert(service, context, amount, label)
        total = FunctionExpr(ExprFunction.Sum, [column("amount")])
        query = (bounded_query().group_by("label").sum("amount", "total")
                 .having(BinaryExpr(total, BinaryOp.Gt, value(Decimal("3")))))
        rows = (await service.query(context, QueryRequest(query))).rows
        assert rows == [{"label": "large", "total": Decimal("10.00")}]
        projection = bounded_query().project_expr("result", total)
        rows = (await service.query(context, QueryRequest(projection))).rows
        assert rows == [{"result": Decimal("12.00")}]
    finally:
        await service.close()


@pytest.mark.asyncio
async def test_decimal_sum_exceeds_default_context_precision_without_rounding(tmp_path):
    service, context, _ = amount_service(tmp_path / "wide.sqlite")
    try:
        await context.ensure_schema()
        for amount in [Decimal("123456789012345678901234567890.1234"), Decimal("0.0001")]:
            await insert(service, context, amount)
        with localcontext() as arithmetic:
            arithmetic.prec = 3
            row = (await service.query(context, QueryRequest(
                bounded_query().sum("amount", "total")))).rows[0]
        assert row["total"] == Decimal("123456789012345678901234567890.1235")
    finally:
        await service.close()


@pytest.mark.asyncio
async def test_decimal_transaction_rollback_and_sparse_projection_keep_the_contract(tmp_path):
    service, context, _ = amount_service(tmp_path / "transaction.sqlite")
    try:
        await context.ensure_schema()
        transaction = await service.transport.begin_sql()
        try:
            await transaction.execute_sql(CompiledQuery(
                "INSERT INTO amount_data (id, version, amount) VALUES (99, 1, ?)",
                [Value.Decimal(Decimal("3.50"))]))
            rows = await transaction.fetch_all_sql(CompiledQuery(
                "SELECT teaql_decimal_sum(amount) AS total FROM amount_data", []))
            assert rows == [{"total": "3.50"}]
        finally:
            await transaction.rollback_sql()
        assert not (await service.query(context, QueryRequest(bounded_query()))).rows
        created = await insert(service, context, None)
        rows = (await service.query(context, QueryRequest(bounded_query().project("id")))).rows
        assert rows == [{"id": created.persisted_record["id"]}]
    finally:
        await service.close()


@pytest.mark.parametrize("text", ["NaN", "Infinity", "-Infinity", "1E+1000000000", "1E-1000000000"])
def test_decimal_binding_rejects_nonfinite_or_unbounded_values_without_echoing_them(text):
    service, _, _ = amount_service("unused.sqlite")
    with pytest.raises(ValueError) as failure:
        service.transport._bind_values([Value.Decimal(Decimal(text))])
    assert text not in str(failure.value)


@pytest.mark.asyncio
async def test_decimal_debug_sql_replay_preserves_the_actual_text_binding(tmp_path):
    service, _, _ = amount_service(tmp_path / "debug.sqlite")
    precise = Decimal("123456789012.3456789")
    query = CompiledQuery("SELECT ? AS exact_value", [Value.Decimal(precise)])
    try:
        bound = await service.transport.fetch_all_sql(query)
        replayed = await service.transport.fetch_all_sql(CompiledQuery(query.debug_sql(DatabaseKind.Sqlite), []))
        assert bound == replayed == [{"exact_value": str(precise)}]
        assert _sql_literal(Value.Decimal(precise), DatabaseKind.PostgreSql) == str(precise)
        assert _sql_literal(Value.Decimal(precise), DatabaseKind.MySql) == str(precise)
    finally:
        await service.close()
