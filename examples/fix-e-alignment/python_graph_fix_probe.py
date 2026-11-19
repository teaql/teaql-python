"""Observe generated graph Fix without modifying generated/runtime code.

The caller owns the database prefix. Repeated rounds retain the same files.
"""
import argparse
import asyncio
from collections import Counter
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import inspect
import json
from pathlib import Path
import sys


class AdvancingClock:
    def __init__(self, round_number):
        self.base = datetime(2033, 1, round_number, tzinfo=timezone.utc)
        self.calls = 0

    def now(self):
        value = self.base + timedelta(milliseconds=self.calls)
        self.calls += 1
        return value


class Meter:
    def __init__(self, delegate, counts=None):
        self.delegate = delegate
        self.counts = counts if counts is not None else Counter()

    def __getattr__(self, name):
        return getattr(self.delegate, name)

    async def begin(self, context):
        self.counts["begins"] += 1
        return Meter(await self.delegate.begin(context), self.counts)

    async def query(self, context, request):
        self.counts["queries"] += 1
        return await self.delegate.query(context, request)

    async def next_id(self, entity):
        self.counts["ids"] += 1
        return await self.delegate.next_id(entity)

    async def mutate(self, context, request):
        self.counts["mutations"] += 1
        return await self.delegate.mutate(context, request)

    async def commit(self, context):
        self.counts["commits"] += 1
        return await self.delegate.commit(context)

    async def rollback(self, context):
        self.counts["rollbacks"] += 1
        return await self.delegate.rollback(context)

    def effects(self):
        return {key: self.counts[key] for key in
                ("begins", "queries", "ids", "mutations", "commits", "rollbacks")}


class RecordingRegistry:
    def __init__(self, delegate, meter):
        self.delegate, self.meter = delegate, meter
        self.visits = []

    def checker(self, entity):
        original = self.delegate.checker(entity)
        if original is None:
            return None
        owner = self

        class RecordingChecker:
            def check_and_fix(self, context, record, location, results):
                before = owner.meter.effects()
                original.check_and_fix(context, record, location, results)
                now = context.get_resource("fix_time")
                owner.visits.append({"entity": entity,
                    "operation": context.get_resource("fix_operation"),
                    "instantMillis": int(now.timestamp() * 1000),
                    "providerEffectsDuringFix": {
                        key: value - before[key]
                        for key, value in owner.meter.effects().items()}})

        return RecordingChecker()


async def scenario(args, name):
    from Q import Q
    from E import E
    from runtime_module import GENERATED_RUNTIME_MODULE
    from teaql.data_service import SQLiteTeaQLClient
    from teaql.runtime import ContextEntityRef, UserContext

    database = Path(str(args.database_prefix) + "." + name + ".sqlite")
    meter = Meter(SQLiteTeaQLClient(str(database)))
    context = (UserContext.new().install(GENERATED_RUNTIME_MODULE)
               .insert_resource("dataService", meter)
               .with_active_root(ContextEntityRef("Tenant", 1)))
    await context.ensure_schema()
    clock = AdvancingClock(args.round)
    context.with_business_clock(clock)
    registry = RecordingRegistry(context.require_resource("checker_registry"), meter)
    context.with_checker_registry(registry)

    allocations_before_creation = meter.effects()["ids"]
    order = ((await Q.purchase_orders().comment("Prepare the graph Fix order")
             .purpose("Verify generated graph identity and once-per-save Fix")
             .new_entity(context)))
    child = ((await Q.order_items().comment("Prepare the graph Fix child")
             .purpose("Verify one child object reached through two list entries")
             .new_entity(context)))
    construction_reservations = meter.effects()["ids"] - allocations_before_creation
    reserved_ids = (order.id, child.id)
    assert construction_reservations == 2
    assert all(type(identity) is int and identity > 0 for identity in reserved_ids)
    order.update_contact_phone("5550710").update_internal_note(None)
    child.update_product_name("Graph fixture item").update_unit_price(Decimal("12.34"))
    order.order_item_list().append(child)
    if name == "repeated-child":
        order.order_item_list().append(child)
    meter.counts.clear()
    registry.visits.clear()
    before_clock = clock.calls
    failure = None
    try:
        await order.audit_as("Save the generated graph Fix fixture").save(context)
    except Exception as error:
        failure = {"type": type(error).__name__,
                   "rules": [v.rule_id for v in getattr(error, "violations", ())]}
    effects = meter.effects()
    visits = list(registry.visits)
    invocations = Counter(row["entity"] for row in visits)
    once = invocations == {"PurchaseOrder": 1, "OrderItem": 1}
    saved = None
    if failure is None:
        saved = await (Q.purchase_orders().with_id_is(order.id).limit(1)
                       .comment("Reload the graph Fix parent")
                       .purpose("Verify authoritative persisted graph state")
                       .execute_for_one(context))
        item = await (Q.order_items().with_id_is(child.id).limit(1)
                      .comment("Reload the graph Fix child")
                      .purpose("Verify the child was persisted once")
                      .execute_for_one(context))
        assert E.purchase_order(saved).version().eval() == 1
        assert E.order_item(item).version().eval() == 1
        assert E.order_item(item).unit_price().eval() == Decimal("12.34")
    passed = (failure is None and once and (order.id, child.id) == reserved_ids and effects == {
        "begins": 1, "queries": 0, "ids": 0, "mutations": 2,
        "commits": 1, "rollbacks": 0})
    row = {"case": name, "round": args.round, "passed": passed,
           "saved": saved is not None, "fixOnce": once,
           "clockCaptures": clock.calls - before_clock, "visits": visits,
           "effects": effects, "error": failure,
           "parentId": order.id, "childId": child.id,
           "constructionReservations": construction_reservations,
           "savedReservedIdentities": (order.id, child.id) == reserved_ids,
           "runtimeFile": inspect.getfile(UserContext),
           "database": str(database)}
    print("PYTHON_GRAPH_FIX_CASE=" + json.dumps(row, sort_keys=True))
    return passed


async def main(args):
    sys.path.insert(0, str(args.generated.resolve()))
    outcomes = [await scenario(args, name) for name in ("single-child", "repeated-child")]
    print("PYTHON_GRAPH_FIX_RESULT=" + json.dumps({"round": args.round,
          "passed": all(outcomes), "cases": len(outcomes)}))
    return all(outcomes)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--generated", type=Path, required=True)
    parser.add_argument("--database-prefix", type=Path, required=True)
    parser.add_argument("--round", type=int, choices=(1, 2), required=True)
    sys.exit(0 if asyncio.run(main(parser.parse_args())) else 1)
