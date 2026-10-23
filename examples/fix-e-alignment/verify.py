"""Local generated Q/E + SQLite save regression; no generated-source modifications.

Pass --generated from FixExpressionFixtureExportTest and a NEW --database path.
The caller owns the synthetic database; this example never deletes it.
"""
import argparse
import asyncio
from datetime import datetime, timezone
from decimal import Decimal
import json
from pathlib import Path
import sys


def arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("--generated", type=Path, required=True)
    parser.add_argument("--database", type=Path, required=True)
    result = parser.parse_args()
    if result.database.exists():
        parser.error("Use a new SQLite path; never overwrite an existing database")
    return result


def instant(value):
    # Existing SQLite hydration can expose Timestamp's millisecond storage text.
    # Compare the instant without claiming that scalar representation is aligned.
    if isinstance(value, (int, float)) or (isinstance(value, str) and value.lstrip("-").isdigit()):
        return datetime.fromtimestamp(int(value) / 1000, tz=timezone.utc)
    if isinstance(value, str):
        value = datetime.fromisoformat(value.replace("Z", "+00:00"))
    assert isinstance(value, datetime), f"Expected a datetime-compatible result, got {type(value).__name__}"
    return value.replace(tzinfo=value.tzinfo or timezone.utc).astimezone(timezone.utc)


async def verify(options):
    sys.path.insert(0, str(options.generated.resolve()))
    from E import E
    from Q import Q
    from models.purchase_order import PurchaseOrder
    from models.tenant import Tenant
    from runtime_module import GENERATED_RUNTIME_MODULE
    from teaql.data_service import SQLiteTeaQLClient
    from teaql.runtime import ContextEntityRef, FixedBusinessClock, TeaQLNotLoadedError, UserContext

    diagnostics = []

    def missing(expression, location, attempted, marked, terminal="eval", fallback=None):
        try:
            getattr(expression, terminal)(*(() if fallback is None else (fallback,)))
        except TeaQLNotLoadedError as error:
            wire = error.to_wire()
            assert wire["code"] == "NOT_LOADED"
            assert wire["instancePath"] == location
            assert wire["attemptedInstancePath"] == attempted
            assert wire["expressionWithBrokenPoint"] == marked, wire
            assert marked.count("<broken>") == 1
            assert "root" not in wire and "inputValue" not in wire
            assert fallback is None or fallback not in str(error)
            diagnostics.append(wire)
        else:
            raise AssertionError("NotLoaded must not be treated as loaded null or fallback")

    partial = PurchaseOrder(id=900, version=1)
    missing(E.purchase_order(partial).tenant().name(), "/tenant", "/tenant/name",
            "E.purchase_order(<root>).tenant()<broken>.name().eval()")
    missing(E.purchase_order(partial).tenant().purchase_order_list().first().tenant().name(),
            "/tenant", "/tenant/purchaseOrderList/0/tenant/name",
            "E.purchase_order(<root>).tenant()<broken>.purchase_order_list().first().tenant().name().eval()")
    missing(E.purchase_order(partial).order_item_list().get(2).product_name(),
            "/orderItemList", "/orderItemList/2/productName",
            "E.purchase_order(<root>).order_item_list()<broken>.get(2).product_name().eval()")
    missing(E.purchase_order(partial).internal_note(), "/internalNote", "/internalNote",
            "E.purchase_order(<root>).internal_note()<broken>.or_if_null(<fallback>)",
            terminal="or_if_null", fallback="PRIVATE-FALLBACK")
    late = PurchaseOrder(id=901, version=1, tenant=Tenant(id=1, version=1))
    missing(E.purchase_order(late).tenant().name(), "/tenant/name", "/tenant/name",
            "E.purchase_order(<root>).tenant().name()<broken>.eval()")
    nulls = PurchaseOrder(id=902, version=1, tenant=None, internal_note=None, order_item_list=[])
    assert E.purchase_order(nulls).tenant().name().eval() is None
    assert E.purchase_order(nulls).internal_note().or_if_null("fallback") == "fallback"
    assert E.purchase_order(nulls).order_item_list().first().product_name().eval() is None
    assert E.purchase_order(nulls).order_item_list().get(-1).product_name().eval() is None

    first = datetime(2032, 2, 29, 10, 15, 30, tzinfo=timezone.utc)
    second = datetime(2032, 3, 1, 11, 16, 31, tzinfo=timezone.utc)
    client = SQLiteTeaQLClient(str(options.database))
    context = (UserContext.new().install(GENERATED_RUNTIME_MODULE)
               .insert_resource("dataService", client)
               .with_business_clock(FixedBusinessClock(first))
               .with_active_root(ContextEntityRef("Tenant", 1)))
    await context.ensure_schema()
    order = (Q.purchase_orders().comment("Prepare the clock fixture order")
             .purpose("Verify generated Fix and E behavior").new_entity(context))
    order.update_contact_phone("5550100").update_internal_note(None)
    child = (Q.order_items().comment("Prepare the clock fixture item")
             .purpose("Verify one captured clock across a saved graph").new_entity(context))
    child.update_product_name("Synthetic fixture item").update_unit_price(Decimal("10.00"))
    order.order_item_list().append(child)
    saved = await order.audit_as("Create the synthetic Fix graph").save(context)
    assert instant(E.purchase_order(saved).create_time().eval()) == first
    assert instant(E.purchase_order(saved).update_time().eval()) == first
    assert E.purchase_order(saved).tenant_id().eval() == 1
    assert instant(E.order_item(child).create_time().eval()) == first
    assert instant(E.order_item(child).update_time().eval()) == first
    assert E.order_item(child).tenant_id().eval() == 1

    context.with_business_clock(FixedBusinessClock(second))
    loaded = await (Q.purchase_orders().with_id_is(saved.id).limit(1)
                    .comment("Reload the complete saved order")
                    .purpose("Verify persisted time fixes before an update").execute_for_one(context))
    assert instant(E.purchase_order(loaded).create_time().eval()) == first
    loaded.update_contact_phone("5550101")
    await loaded.audit_as("Update the synthetic Fix order").save(context)
    persisted = await (Q.purchase_orders().with_id_is(saved.id).limit(1)
                       .comment("Reload the updated order")
                       .purpose("Verify create time is preserved and update time advances").execute_for_one(context))
    assert instant(E.purchase_order(persisted).create_time().eval()) == first
    assert instant(E.purchase_order(persisted).update_time().eval()) == second
    assert E.purchase_order(persisted).contact_phone().eval() == "5550101"
    assert context.get_resource("fix_time") is None
    print("FIX_E_EXAMPLE=" + json.dumps({"language": "python", "passed": True,
          "normalGeneratedSave": True, "database": str(options.database),
          "createTimePreserved": True, "updateTimeAdvanced": True,
          "observedTimestampRepresentation": type(E.purchase_order(persisted).create_time().eval()).__name__,
          "declaredContextRootInjected": True, "diagnostics": diagnostics}))


if __name__ == "__main__":
    asyncio.run(verify(arguments()))
