"""Quote three freight bookings with exact monetary and delivery values."""

import asyncio
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
import json
from pathlib import Path
import sys

from E import E, TeaQLNotLoadedError
from Q import Q
from models.freight_quote import FreightQuote
from runtime_module import GENERATED_RUNTIME_MODULE
from teaql.provider.sqlite import create_sqlite_service
from teaql.runtime import CheckException, UserContext


DATE = date(2026, 10, 31)
PICKUP = time(9, 30, 15, 123456)
QUOTED = datetime(2026, 10, 31, 1, 45, 0, 123000, timezone(timedelta(hours=8)))
SHIPMENT = 9_007_199_254_740_993
PRECISE_AMOUNT = Decimal("123456789012.3456789")
QUOTES = [
    ("SEA-001", Decimal("0.10"), SHIPMENT, 2, None),
    ("SEA-002", Decimal("0.20"), SHIPMENT + 1, 3, ""),
    ("SEA-003", Decimal("3.50"), SHIPMENT + 2, 2_147_483_647, "Hold for inspection"),
]


async def create_quotes(caller, platform):
    for reference, amount, number, count, instructions in QUOTES:
        quote = await Q.freight_quotes().comment("Prepare a freight quote").purpose(
            "Price the shipment for its delivery window").new_entity(caller)
        quote.update_platform(platform).update_reference(reference).update_amount(amount)
        quote.update_shipment_number(number).update_package_count(count)
        quote.update_delivery_date(DATE).update_pickup_time(PICKUP).update_quoted_at(QUOTED)
        quote.update_instructions(instructions)
        await quote.audit_as("Register a freight quote").save(caller)

    revised = await quote_by_reference(caller, "SEA-003")
    assert str(E.freight_quote(revised).amount().eval()) == "3.50"
    revised.update_amount(PRECISE_AMOUNT)
    await revised.audit_as("Accept the revised offshore freight rate").save(caller)


async def quote_by_reference(caller, reference):
    result = await Q.freight_quotes().with_reference_is(reference).limit(1).comment(
        "Read the selected freight quote").purpose("Verify the exact delivery commitment").execute_for_one(caller)
    assert result is not None
    return result


async def verify_quotes(caller, phase):
    rows = await Q.freight_quotes().order_by_amount_ascending().limit(3).comment(
        "Compare open freight amounts").purpose("Rank freight bids numerically").execute_for_list(caller)
    assert [row.reference for row in rows] == ["SEA-001", "SEA-002", "SEA-003"]
    assert [str(E.freight_quote(row).amount().eval()) for row in rows] == ["0.10", "0.20", str(PRECISE_AMOUNT)]
    assert [E.freight_quote(row).instructions().eval() for row in rows] == [None, "", "Hold for inspection"]
    assert [E.freight_quote(row).shipment_number().eval() for row in rows] == [SHIPMENT, SHIPMENT + 1, SHIPMENT + 2]
    high = rows[-1]
    same_amount = await Q.freight_quotes().with_amount_is(PRECISE_AMOUNT).limit(1).comment(
        "Find the matching freight rate").purpose("Use exact Decimal equality").execute_for_one(caller)
    assert same_amount is not None and same_amount.id == high.id and high.version == 2
    total = await Q.freight_quotes().sum_amount_as("total").limit(1).comment(
        "Sum the accepted freight quotes").purpose("Preserve base-ten precision").execute_for_rows(caller)
    expected_total = PRECISE_AMOUNT + Decimal("0.30")
    assert len(total) == 1 and total[0]["total"] == expected_total

    wire = high.to_json()
    document = json.loads(wire)
    assert document["amount"] == str(PRECISE_AMOUNT)
    assert document["shipmentNumber"] == str(SHIPMENT + 2) and document["packageCount"] == 2_147_483_647
    restored = E.freight_quote(FreightQuote.from_json(wire))
    assert restored.amount().eval() == PRECISE_AMOUNT and restored.shipment_number().eval() == SHIPMENT + 2
    assert restored.delivery_date().eval() == DATE and restored.pickup_time().eval() == PICKUP
    assert restored.quoted_at().eval() == QUOTED.astimezone(timezone.utc)

    sparse = await Q.freight_quotes_minimal().with_id_is(high.id).select_reference().limit(1).comment(
        "Read only the quote reference").purpose("Keep unselected delivery instructions distinct").execute_for_one(caller)
    assert sparse is not None and "instructions" not in json.loads(sparse.to_json())
    try:
        E.freight_quote(FreightQuote.from_json(sparse.to_json())).instructions().eval()
        raise AssertionError("Unselected instructions became a value")
    except TeaQLNotLoadedError:
        pass

    high.update_amount(None)
    try:
        await high.audit_as("Reject a quote without its required amount").save(caller)
        raise AssertionError("A missing freight amount was saved")
    except CheckException as error:
        assert any(item.rule_id == "required" and item.location.model_path == "amount" for item in error.violations)
    retained = await quote_by_reference(caller, "SEA-003")
    assert retained.version == 2 and retained.amount == PRECISE_AMOUNT
    return dict(phase=phase, quotes=len(rows), total=str(expected_total), precise=str(retained.amount),
                version=retained.version, invalidAmountRejected=True, sparseInstructionsNotLoaded=True)


async def main(database: Path, phase: str):
    service = create_sqlite_service(str(database))
    try:
        caller = UserContext.new().install(GENERATED_RUNTIME_MODULE).insert_resource("dataService", service)
        caller.disable_sql_log()
        await caller.ensure_schema()
        if phase == "first":
            await create_quotes(caller, 1)
        print("FREIGHT_QUOTE=" + json.dumps(await verify_quotes(caller, phase)))
    finally:
        await service.close()


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[2] not in {"first", "restart"}:
        raise SystemExit("Usage: main.py DATABASE {first|restart}")
    asyncio.run(main(Path(sys.argv[1]), sys.argv[2]))
