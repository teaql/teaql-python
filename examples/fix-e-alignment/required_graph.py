"""Generated parent/child admission and retry, with actual SQLite call counters."""
import argparse
import asyncio
from datetime import datetime, timezone
from decimal import Decimal
import json
from pathlib import Path
import sqlite3
import sys


async def verify(options):
    assert options.database.is_absolute() and not options.database.exists()
    sys.path.insert(0, str(options.generated.resolve()))
    from E import E
    from Q import Q
    from runtime_module import GENERATED_RUNTIME_MODULE
    from teaql.data_service import SQLiteTeaQLClient
    from teaql.runtime import CheckException, ContextEntityRef, UserContext

    instant = datetime(2032, 2, 29, 10, 15, 30, tzinfo=timezone.utc)
    class Clock:
        calls = 0
        def now(self):
            self.calls += 1
            return instant
    clock = Clock()
    client = SQLiteTeaQLClient(str(options.database))
    context = (UserContext().install(GENERATED_RUNTIME_MODULE)
               .insert_resource("dataService", client)
               .with_active_root(ContextEntityRef("Tenant", 1))
               .with_business_clock(clock))
    calls = []
    for name in ("enable_soundex", "verify_schema", "fetch_all_sql", "execute_sql", "begin_sql"):
        original = getattr(client.transport, name)
        async def counted(*args, _original=original, _name=name, **kwargs):
            calls.append(_name)
            return await _original(*args, **kwargs)
        setattr(client.transport, name, counted)
    try:
        await context.ensure_schema()
        assert calls, "counter must observe actual provider setup"
        order = (Q.purchase_orders().comment("Prepare an invalid child graph")
                 .purpose("Reject before parent or child ID reservation").new_entity(context))
        order.update_contact_phone("5550100").update_internal_note(None)
        child = (Q.order_items().comment("Prepare a missing product name")
                 .purpose("Exercise indexed required input diagnostics").new_entity(context))
        child.update_unit_price(Decimal("10.00"))
        order.order_item_list().append(child)
        before = len(calls)
        clock_before = clock.calls
        try:
            await order.audit_as("Reject incomplete child input").save(context)
            raise AssertionError("invalid child was accepted")
        except CheckException as error:
            failure = next(v for v in error.violations if v.rule_id == "required")
            assert failure.location.model_path == "order_item_list[0].product_name"
            assert failure.location.instance_path == "/orderItemList/0/productName"
        assert len(calls) == before, f"rejected child touched provider: {calls[before:]}"
        assert order.id is None and child.id is None
        # Business Required is evaluated after customer Fix. An unsuccessful
        # preparation captures one graph clock, but still performs no provider
        # calls and reserves no identities. Identity/root admission is earlier.
        assert clock.calls == clock_before + 1
        retry_clock_before = clock.calls

        child.update_product_name("Corrected synthetic product")
        await order.audit_as("Save corrected parent and child").save(context)
        assert len(calls) > before
        assert clock.calls == retry_clock_before + 1
        row = await (Q.order_items().with_id_is(child.id).limit(1)
                     .comment("Reload corrected generated child")
                     .purpose("Verify real Q and E after retry").execute_for_one(context))
        assert E.order_item(row).product_name().eval() == "Corrected synthetic product"
        assert E.order_item(row).create_time().eval() == instant
        with sqlite3.connect(f"file:{options.database}?mode=ro", uri=True) as db:
            assert db.execute("SELECT purchase_order FROM order_item_data WHERE id = ?", (child.id,)).fetchone() == (order.id,)

        child.update_product_name(None)
        before = len(calls)
        update_clock_before = clock.calls
        try:
            await order.audit_as("Reject an invalid changed child").save(context)
            raise AssertionError("invalid child update was accepted")
        except CheckException as error:
            assert any(v.rule_id == "required" and v.location.model_path == "order_item_list[0].product_name"
                       for v in error.violations)
        assert len(calls) == before
        assert clock.calls == update_clock_before + 1
        unchanged = await (Q.order_items().with_id_is(child.id).limit(1)
                           .comment("Reload after rejected child update")
                           .purpose("Verify persisted value and version survived").execute_for_one(context))
        assert unchanged.version == 1
        assert E.order_item(unchanged).product_name().eval() == "Corrected synthetic product"

        # A persisted child can move to a newly created parent. During pure
        # preparation that parent has no assigned ID: retain the typed reference
        # until final preflight, rather than comparing two None IDs as equal.
        child.update_product_name("Corrected synthetic product")
        replacement = (Q.purchase_orders().comment("Prepare a new owner for an existing child")
                       .purpose("Verify unresolved reference identity survives preparation").new_entity(context))
        replacement.update_contact_phone("5550101").update_internal_note(None)
        replacement.order_item_list().append(child)
        await replacement.audit_as("Move one existing child to a new parent").save(context)
        moved = await (Q.order_items().with_id_is(child.id).limit(1)
                      .comment("Reload the child after reassignment")
                      .purpose("Verify the prepared FK and optimistic version").execute_for_one(context))
        assert E.order_item(moved).product_name().eval() == "Corrected synthetic product"
        assert moved.version == 2
        with sqlite3.connect(f"file:{options.database}?mode=ro", uri=True) as db:
            assert db.execute("SELECT purchase_order FROM order_item_data WHERE id = ?", (child.id,)).fetchone() == (replacement.id,)
        print("REQUIRED_GRAPH_ADMISSION=" + json.dumps({"language": "python", "passed": True,
              "invalidChildCreateCalls": 0, "invalidChildUpdateCalls": 0,
              "sameGraphRetry": True, "unallocatedIdsOnRejection": True,
              "singleFixClockOnSuccess": True, "existingChildToNewParent": True, "observedProviderCalls": len(calls),
              "requiredAdmissionAfterFix": True, "failedCreateClockCaptures": 1,
              "successfulRetryClockCaptures": 1, "failedUpdateClockCaptures": 1}))
    finally:
        await client.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--generated", type=Path, required=True)
    parser.add_argument("--database", type=Path, required=True)
    asyncio.run(verify(parser.parse_args()))
