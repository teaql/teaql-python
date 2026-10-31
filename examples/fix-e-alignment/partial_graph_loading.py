"""Modified descendants behind untouched partial ancestors: generated Q/E/save.

The caller owns the SQLite path. Run rounds 1 and 2 without deleting its data.
API discovery uses the model's object/action and reverse-field Assist, not the
generated implementation. No handwritten mutation SQL or manual bootstrap.
"""
import argparse
import asyncio
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / "generated"))
from E import E
from Q import Q
from runtime_module import GENERATED_RUNTIME_MODULE
from teaql.data_service import SQLiteTeaQLClient
from teaql.runtime import CheckException, ContextEntityRef, FixedBusinessClock, TeaQLNotLoadedError, UserContext


class ObservedService:
    """Delegate to real SQLite; rejected saves must not enter this boundary."""
    def __init__(self, service):
        self.service = service
        self.calls = Counter(query=0, mutate=0, begin=0, next_id=0)

    def __getattr__(self, name):
        return getattr(self.service, name)

    async def query(self, *args, **kwargs):
        self.calls["query"] += 1
        return await self.service.query(*args, **kwargs)

    async def mutate(self, *args, **kwargs):
        self.calls["mutate"] += 1
        return await self.service.mutate(*args, **kwargs)

    async def begin(self, *args, **kwargs):
        self.calls["begin"] += 1
        return await self.service.begin(*args, **kwargs)

    async def next_id(self, *args, **kwargs):
        self.calls["next_id"] += 1
        return await self.service.next_id(*args, **kwargs)


def missing(expression, path):
    try:
        expression.eval()
    except TeaQLNotLoadedError as error:
        wire = error.to_wire()
        assert wire["code"] == "NOT_LOADED" and wire["attemptedInstancePath"] == path
        assert wire["expressionWithBrokenPoint"].count("<broken>") == 1
        return wire
    raise AssertionError("A partial ancestor was silently promoted: " + path)


async def main(database, round_number):
    assert round_number in (1, 2)
    first = datetime(2032 + round_number - 1, 3, 1, 10, 15, 30, tzinfo=timezone.utc)
    second = first.replace(day=2)
    service = ObservedService(SQLiteTeaQLClient(str(database)))
    context = (UserContext.new().install(GENERATED_RUNTIME_MODULE).insert_resource("dataService", service)
               .with_business_clock(FixedBusinessClock(first)).with_active_root(ContextEntityRef("Tenant", 1)))
    cases = []
    try:
        await context.ensure_schema()
        order = (Q.purchase_orders().comment("Prepare an owned partial-ancestor test graph")
                 .purpose("Verify modified-only loading completeness").new_entity(context))
        order.update_contact_phone("555060" + str(round_number)).update_internal_note(None)
        child = (Q.order_items().comment("Prepare the complete leaf")
                 .purpose("Calibrate real SQLite graph persistence").new_entity(context))
        child.update_product_name("Partial graph initial " + str(round_number)).update_unit_price(Decimal("10.00"))
        order.order_item_list().append(child)
        await order.audit_as("Create the partial-ancestor loading control").save(context)

        async def graph(partial_leaf=False):
            leaf = Q.order_items_minimal() if partial_leaf else Q.order_items()
            middle = (Q.purchase_orders_minimal().with_id_is(order.id).limit(1)
                      .select_order_item_list_with(leaf.with_id_is(child.id).limit(1)
                          .comment("Load the selected leaf shape"))
                      .comment("Keep the unmodified middle object partial"))
            return await (Q.tenants_minimal().with_id_is(1).limit(1)
                          .select_purchase_order_list_with(middle)
                          .comment("Load partial ancestors with an explicitly selected leaf")
                          .purpose("Verify traversal does not prune untouched partial ancestors")
                          .execute_for_one(context))

        async def persisted_leaf():
            return await (Q.order_items().with_id_is(child.id).limit(1)
                          .comment("Read back the leaf independently")
                          .purpose("Verify exact persisted leaf fields and version").execute_for_one(context))

        root = await graph()
        middle = root.purchase_order_list()[0]
        leaf = middle.order_item_list()[0]
        before_calls = dict(service.calls)
        missing(E.tenant(root).name(), "/name")
        missing(E.purchase_order(middle).contact_phone(), "/contactPhone")
        assert E.order_item(leaf).product_name().eval() == "Partial graph initial " + str(round_number)
        assert E.order_item(leaf).unit_price().eval() == Decimal("10.00")
        projection = json.loads(root.to_json())
        assert "name" not in projection and "contactPhone" not in projection["purchaseOrderList"][0]
        assert service.calls == before_calls
        cases.append("partial-ancestor-guards-and-JSON-no-I/O")

        context.with_business_clock(FixedBusinessClock(second))
        leaf.update_product_name("Partial graph updated " + str(round_number))
        await root.audit_as("Persist only the complete modified descendant").save(context)
        loaded = await persisted_leaf()
        assert loaded.version == 2
        assert E.order_item(loaded).product_name().eval() == "Partial graph updated " + str(round_number)
        assert E.order_item(loaded).create_time().eval() == first
        assert E.order_item(loaded).update_time().eval() == second
        missing(E.tenant(root).name(), "/name")
        missing(E.purchase_order(middle).contact_phone(), "/contactPhone")
        parent = await (Q.purchase_orders().with_id_is(order.id).limit(1)
                        .comment("Read the untouched parent's version")
                        .purpose("Verify a leaf change did not update ancestors").execute_for_one(context))
        assert parent.version == order.version == 1
        assert E.tenant(root).version().eval() == 1
        assert all(service.calls[name] > 0 for name in ("query", "begin", "next_id"))
        cases.append("complete-leaf-saved-through-two-untouched-partial-ancestors")

        sparse = await graph(partial_leaf=True)
        sparse_leaf = sparse.purchase_order_list()[0].order_item_list()[0]
        sparse_leaf.update_product_name("Must not persist")
        rejections = []
        for _ in (1, 2):
            before_calls = dict(service.calls)
            try:
                await sparse.audit_as("Reject a genuinely modified partial descendant").save(context)
            except CheckException as error:
                violations = [v.to_wire() for v in error.violations]
                assert any(v["location"] for v in violations)
                rejections.append(violations)
            else:
                raise AssertionError("A modified partial descendant bypassed complete-object checking")
            assert service.calls == before_calls
            assert E.order_item(sparse_leaf).product_name().eval() == "Must not persist"
        loaded = await persisted_leaf()
        assert loaded.version == 2 and E.order_item(loaded).product_name().eval() == "Partial graph updated " + str(round_number)
        cases.append("partial-leaf-rejected-twice-before-provider-with-intent-retained")

        # Internal cascade wiring is not permission to replace the trusted root.
        outside = (Q.tenants().comment("Prepare another independently persisted root")
                   .purpose("Verify managed reverse wiring retains Context-root checks").new_entity(context))
        outside.update_name("Outside active root " + str(round_number))
        await outside.audit_as("Create the independent root control").save(context)
        wrong = (Q.purchase_orders().comment("Prepare a child below the wrong active root")
                 .purpose("Reject a cascade association that contradicts Context").new_entity(context))
        wrong.update_contact_phone("555069" + str(round_number)).update_internal_note(None)
        outside.purchase_order_list().append(wrong)
        before_calls = dict(service.calls)
        try:
            await outside.audit_as("Reject managed association outside the active root").save(context)
        except CheckException as error:
            assert any(v.rule_id == "context_root_mismatch" for v in error.violations)
        else:
            raise AssertionError("An internal cascade bypassed the trusted Context root")
        assert service.calls == before_calls and outside.version == 1
        cases.append("managed-cascade-root-mismatch-rejected-before-provider")
        print("PARTIAL_GRAPH_LOAD=" + json.dumps({"language": "python", "round": round_number, "passed": True,
              "cases": cases, "rootId": "1", "orderId": str(order.id), "leafId": str(child.id),
              "ancestorVersions": [1, 1], "leafVersion": 2, "rejections": rejections,
              "outsideRootId": str(outside.id), "database": str(database), "calibratedProvider": True}))
    finally:
        await service.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--round", type=int, choices=(1, 2), required=True)
    args = parser.parse_args()
    asyncio.run(main(args.database, args.round))
