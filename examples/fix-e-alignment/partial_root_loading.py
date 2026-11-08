"""Managed-root admission through two untouched, partially loaded ancestors.

Use an owned SQLite path and run rounds 1 and 2 without resetting it. All data
setup and changes use generated Q/E/audited save. Read-only SQLite is a separate
storage oracle, not an alternative mutation path. No generated source is edited.
"""
import argparse
import asyncio
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal
import json
from pathlib import Path
import sqlite3
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / "generated"))
from E import E
from Q import Q
from runtime_module import GENERATED_RUNTIME_MODULE
from teaql.data_service import SQLiteTeaQLClient
from teaql.runtime import (
    CheckException, ContextEntityRef, FixedBusinessClock, MutationDecision,
    MutationPolicyIdentity, TeaQLNotLoadedError, UserContext,
)


ZERO = dict.fromkeys(("queries", "mutations", "begins", "commits", "rollbacks",
                      "allocations", "policyLookups", "policyReviews", "audits"), 0)


class ObservedTransaction:
    def __init__(self, transaction, calls):
        self.transaction, self.calls = transaction, calls

    def __getattr__(self, name):
        return getattr(self.transaction, name)

    async def query(self, *args, **kwargs):
        self.calls["queries"] += 1
        return await self.transaction.query(*args, **kwargs)

    async def mutate(self, *args, **kwargs):
        self.calls["mutations"] += 1
        return await self.transaction.mutate(*args, **kwargs)

    async def next_id(self, *args, **kwargs):
        self.calls["allocations"] += 1
        return await self.transaction.next_id(*args, **kwargs)

    async def commit(self, context):
        self.calls["commits"] += 1
        return await self.transaction.commit(context)

    async def rollback(self, context):
        self.calls["rollbacks"] += 1
        return await self.transaction.rollback(context)


class ObservedService:
    def __init__(self, service, calls):
        self.service, self.calls = service, calls

    def __getattr__(self, name):
        return getattr(self.service, name)

    async def query(self, *args, **kwargs):
        self.calls["queries"] += 1
        return await self.service.query(*args, **kwargs)

    async def mutate(self, *args, **kwargs):
        self.calls["mutations"] += 1
        return await self.service.mutate(*args, **kwargs)

    async def next_id(self, *args, **kwargs):
        self.calls["allocations"] += 1
        return await self.service.next_id(*args, **kwargs)

    async def begin(self, context):
        self.calls["begins"] += 1
        return ObservedTransaction(await self.service.begin(context), self.calls)


class ObservedGovernance:
    identity = MutationPolicyIdentity("partial-root-example", "1", "partial-root-v1")

    def __init__(self, calls):
        self.calls, self.operations, self.events = calls, [], []

    def resolve(self, request_key):
        self.calls["policyLookups"] += 1
        return self

    def review(self, context, plan):
        self.calls["policyReviews"] += 1
        self.operations.append(tuple((op.entity, op.kind.value) for op in plan.operations))
        return MutationDecision.allowed()

    async def on_safe_event(self, context, event):
        self.calls["audits"] += 1
        self.events.append(event.entity)


def storage(database):
    """No writes, WAL checkpoint, cleanup or shared connection in this oracle."""
    with sqlite3.connect(database.resolve().as_uri() + "?mode=ro&immutable=1", uri=True) as db:
        db.row_factory = sqlite3.Row
        return {table: [dict(row) for row in db.execute("SELECT * FROM " + table + " ORDER BY id")]
                for table in ("tenant_data", "purchase_order_data", "order_item_data")}


def require_partial(expression, path):
    try:
        expression.eval()
    except TeaQLNotLoadedError as error:
        wire = error.to_wire()
        assert wire["code"] == "NOT_LOADED" and wire["attemptedInstancePath"] == path
        assert wire["expressionWithBrokenPoint"].count("<broken>") == 1
        return
    raise AssertionError("Untouched ancestor was promoted: " + path)


async def main(database, round_number):
    first = datetime(2032 + round_number - 1, 4, 1, 10, 15, 30, tzinfo=timezone.utc)
    second = first.replace(day=2)
    calls = Counter(ZERO)
    service = ObservedService(SQLiteTeaQLClient(str(database)), calls)
    governance = ObservedGovernance(calls)

    def context_for(root_id, instant):
        return (UserContext.new().install(GENERATED_RUNTIME_MODULE)
                .insert_resource("dataService", service)
                .with_business_clock(FixedBusinessClock(instant))
                .with_active_root(ContextEntityRef("Tenant", root_id))
                .with_mutation_policy_registry(governance)
                .with_app_audit_event_sink(governance))

    context = context_for(1, first)
    try:
        await context.ensure_schema()
        order = ((await Q.purchase_orders().comment("Prepare the managed-root partial graph")
                 .purpose("Calibrate actual generated graph persistence").new_entity(context)))
        order.update_contact_phone("555080" + str(round_number)).update_internal_note(None)
        child = ((await Q.order_items().comment("Prepare the complete managed-root leaf")
                 .purpose("Verify ownership before mutation I/O").new_entity(context)))
        child.update_product_name("Managed partial initial " + str(round_number)).update_unit_price(Decimal("10.00"))
        order.order_item_list().append(child)
        await order.audit_as("Create the owned managed-root control").save(context)
        other = ((await Q.tenants().comment("Create a real independent root")
                 .purpose("Avoid trusting an unpersisted root identifier").new_entity(context)))
        other.update_name("Independent partial root " + str(round_number))
        await other.audit_as("Create the independent root control").save(context)
        assert other.id != 1

        # Calibrate rollback against a real empty SQLite transaction too: an
        # unused observer must never masquerade as a zero-side-effect guarantee.
        rollback = await service.begin(context)
        await rollback.rollback(context)
        root = await (Q.tenants_minimal().with_id_is(1).limit(1)
                      .select_purchase_order_list_with(
                          Q.purchase_orders_minimal().with_id_is(order.id).limit(1)
                          .select_order_item_list_with(
                              Q.order_items().with_id_is(child.id).limit(1)
                              .comment("Load the complete selected descendant"))
                          .comment("Keep the unmodified middle ancestor partial"))
                      .comment("Load the sparse managed-root graph")
                      .purpose("Verify ownership across untouched partial ancestors")
                      .execute_for_one(context))
        middle = root.purchase_order_list()[0]
        leaf = middle.order_item_list()[0]
        require_partial(E.tenant(root).name(), "/name")
        require_partial(E.purchase_order(middle).contact_phone(), "/contactPhone")
        assert E.order_item(leaf).product_name().eval() == "Managed partial initial " + str(round_number)
        assert E.order_item(leaf).unit_price().eval() == Decimal("10.00")
        calibration = dict(calls)
        assert all(value > 0 for value in calibration.values()), calibration

        leaf.update_product_name("Managed partial retry " + str(round_number))
        intent = deepcopy(tuple(leaf._entity_root.current_change_set().changes()))
        assert intent, "the control must have real pending mutation intent"
        projection = json.loads(root.to_json())
        assert "name" not in projection and "contactPhone" not in projection["purchaseOrderList"][0]
        persisted = storage(database)
        wrong = context_for(other.id, second)
        denials = []
        for attempt in (1, 2):
            calls.clear()
            calls.update(ZERO)
            try:
                await root.audit_as("Reject the wrong trusted root before any I/O").save(wrong)
            except CheckException as error:
                violations = [violation.to_wire() for violation in error.violations]
                assert len(violations) == 1, violations
                violation = violations[0]
                assert violation["ruleId"] == "context_root_mismatch", violations
                assert violation["entityType"] == "OrderItem", violations
                assert violation["location"] == [
                    {"kind": "property", "name": "purchase_order_list"}, {"kind": "index", "index": 0},
                    {"kind": "property", "name": "order_item_list"}, {"kind": "index", "index": 0},
                    {"kind": "property", "name": "tenant"}], violations
                assert violation["instancePath"] == "/purchaseOrderList/0/orderItemList/0/tenant", violations
            else:
                raise AssertionError("Sparse ancestors bypassed the trusted root check")
            assert dict(calls) == ZERO, dict(calls)
            assert tuple(leaf._entity_root.current_change_set().changes()) == intent
            assert json.loads(root.to_json()) == projection
            assert storage(database) == persisted
            assert not wrong.last_fix_evidence()
            denials.append({"attempt": attempt, "effects": dict(calls), "violations": violations,
                            "intentRetained": True, "sparseViewUnchanged": True, "storageUnchanged": True})

        calls.clear()
        calls.update(ZERO)
        governance.operations.clear()
        governance.events.clear()
        context.with_business_clock(FixedBusinessClock(second))
        await root.audit_as("Retry the same graph under its correct trusted root").save(context)
        accepted = dict(calls)
        assert accepted["mutations"] == accepted["commits"] == accepted["audits"] == 1, accepted
        assert accepted["allocations"] == accepted["queries"] == accepted["rollbacks"] == 0, accepted
        assert accepted["policyReviews"] > 0 and accepted["policyLookups"] > 0, accepted
        assert governance.operations == [(("OrderItem", "update"),)], governance.operations
        assert governance.events == ["OrderItem"], governance.events
        assert leaf._entity_root.current_change_set().is_empty()
        require_partial(E.tenant(root).name(), "/name")
        require_partial(E.purchase_order(middle).contact_phone(), "/contactPhone")
        assert root.version == middle.version == 1

        loaded = await (Q.order_items().with_id_is(child.id).limit(1)
                        .comment("Read back the authorized leaf independently")
                        .purpose("Verify persisted value version and business-clock timestamps")
                        .execute_for_one(context))
        assert loaded.version == 2
        assert E.order_item(loaded).product_name().eval() == "Managed partial retry " + str(round_number)
        assert E.order_item(loaded).create_time().eval() == first
        assert E.order_item(loaded).update_time().eval() == second
        physical = storage(database)
        actual = next(row for row in physical["order_item_data"] if row["id"] == child.id)
        assert actual["version"] == 2 and actual["tenant"] == 1 and actual["purchase_order"] == order.id
        assert actual["product_name"] == "Managed partial retry " + str(round_number)
        assert physical["tenant_data"] == persisted["tenant_data"]
        assert physical["purchase_order_data"] == persisted["purchase_order_data"]
        print("PYTHON_PARTIAL_ROOT_RESULT=" + json.dumps({
            "language": "python", "round": round_number, "passed": True,
            "orderId": order.id, "leafId": child.id, "otherRootId": other.id,
            "ancestorVersions": [1, 1], "leafVersion": 2, "calibration": calibration,
            "denials": denials, "acceptedEffects": accepted, "sameGraphRetry": True,
            "intentClearedAfterCommit": True, "generatedImplementationsModified": False}))
    finally:
        await service.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--round", type=int, choices=(1, 2), required=True)
    args = parser.parse_args()
    asyncio.run(main(args.database, args.round))
