"""Exercise exact Decimal using the generated scalar model's public Q/E API."""

import asyncio
import os
from datetime import date, datetime, time, timezone
from decimal import Decimal
from uuid import uuid4

from E import E, TeaQLNotLoadedError
from Q import Q
from models.type_platform import TypePlatform
from runtime_module import GENERATED_RUNTIME_MODULE
from teaql.data_service import SQLiteTeaQLClient
from teaql.runtime import CheckException, UserContext


def request(marker):
    return Q.scalar_type_probes().with_required_string_is(marker).limit(20)


def new_probe(context, marker, amount):
    row = (Q.scalar_type_probes().comment("prepare exact scalar probe")
           .purpose("verify generated mutation").new_entity(context))
    row.update_type_platform(TypePlatform.refer(1))
    row.update_required_string(marker)
    row.update_optional_string(None)
    row.update_large_text("Unicode scalar fixture: 精确数值")
    row.update_required_boolean(True)
    row.update_optional_boolean(None)
    row.update_required_integer(123)
    row.update_optional_integer(None)
    row.update_required_long(1234567890123)
    row.update_optional_long(None)
    row.update_required_decimal(amount)
    row.update_optional_decimal(None)
    row.update_required_float(1.25)
    row.update_optional_float(None)
    row.update_required_double(2.5)
    row.update_optional_double(None)
    row.update_required_date(date(2024, 2, 29))
    row.update_optional_date(None)
    row.update_required_time(time(9, 30, 15))
    row.update_optional_time(None)
    row.update_required_datetime(datetime(2026, 10, 20, 9, 30, tzinfo=timezone.utc))
    row.update_optional_datetime(None)
    return row


async def main():
    client = SQLiteTeaQLClient(os.environ["TEAQL_SCALAR_PROBE_DB"])
    context = UserContext().install(GENERATED_RUNTIME_MODULE).insert_resource("dataService", client)
    marker = "exact-decimal-" + uuid4().hex
    try:
        await context.ensure_schema()
        await context.ensure_schema()
        values = [Decimal(text) for text in ("123456789012.3456789", "3.50", "2", "10", "-0.1")]
        for amount in values:
            row = new_probe(context, marker, amount)
            await row.audit_as("create exact scalar fixture").save(context)
            assert row.id is not None and row.version == 1
            assert E.scalar_type_probe(row).required_decimal().eval() == amount
        rows = await (request(marker).order_by_required_decimal_ascending()
                      .comment("read numerically ordered decimals")
                      .purpose("verify generated Q and E").execute_for_list(context))
        assert [E.scalar_type_probe(row).required_decimal().eval() for row in rows] == sorted(values)
        assert all(isinstance(E.scalar_type_probe(row).required_decimal().eval(), Decimal) for row in rows)
        scaled = await (request(marker).with_required_decimal_is(Decimal("3.500"))
                        .comment("find a scale-equivalent decimal")
                        .purpose("verify numeric equality").execute_for_one(context))
        assert str(E.scalar_type_probe(scaled).required_decimal().eval()) == "3.50"
        assert E.scalar_type_probe(scaled).optional_decimal().eval() is None
        assert E.scalar_type_probe(scaled).required_time().eval() == time(9, 30, 15)
        aggregate = await (request(marker).sum_required_decimal_as("total")
                           .comment("sum exact decimals")
                           .purpose("verify generated aggregation").execute_for_rows(context))
        assert len(aggregate) == 1
        assert aggregate[0]["total"] == Decimal("123456789027.7456789")
        sparse = await (Q.scalar_type_probes_minimal().with_id_is(scaled.id).limit(1)
                        .select_required_string().comment("read a narrow scalar projection")
                        .purpose("verify not-loaded semantics").execute_for_one(context))
        try:
            E.scalar_type_probe(sparse).optional_decimal().eval()
            raise AssertionError("an unselected Decimal was treated as loaded null")
        except TeaQLNotLoadedError:
            pass
        replacement = Decimal("9007199254740993.123456789")
        scaled.update_required_decimal(replacement)
        scaled.update_optional_decimal(Decimal("0.10"))
        await scaled.audit_as("update exact scalar fixture").save(context)
        changed = await (request(marker).with_id_is(scaled.id)
                         .comment("reload changed exact decimal")
                         .purpose("verify mutation readback").execute_for_one(context))
        assert changed.version == 2
        assert E.scalar_type_probe(changed).required_decimal().eval() == replacement
        assert str(E.scalar_type_probe(changed).optional_decimal().eval()) == "0.10"
        changed.update_required_decimal(None)
        try:
            await changed.audit_as("reject missing required decimal").save(context)
            raise AssertionError("Checker accepted a null required Decimal")
        except CheckException as error:
            assert any(item.rule_id == "required" and item.location.model_path == "required_decimal"
                       for item in error.violations)
        unchanged = await (request(marker).with_id_is(scaled.id)
                           .comment("reload after rejected update")
                           .purpose("verify Checker blocked persistence").execute_for_one(context))
        assert unchanged.version == 2
        assert E.scalar_type_probe(unchanged).required_decimal().eval() == replacement
    finally:
        await client.close()
    print("PASS Python generated scalar Decimal: schema/Q/E/Checker/mutation/null/not-loaded/SUM")


if __name__ == "__main__":
    asyncio.run(main())
