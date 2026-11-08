"""Generated E boundary regression over a real, bounded SQLite Q/save graph.

Two caller-owned rounds share a database. No generated implementation changes,
implicit database calls or direct mutation SQL are used by the fixture.
"""
import argparse
import asyncio
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import inspect
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / "generated"))
from E import E
from Q import Q
from runtime_module import GENERATED_RUNTIME_MODULE
import teaql
from teaql.data_service import SQLiteTeaQLClient
from teaql.runtime import ContextEntityRef, FixedBusinessClock, TeaQLNotLoadedError, UserContext
from partial_root_loading import ZERO, ObservedGovernance, ObservedService


WIRE_KEYS = {"code", "location", "instancePath", "breakPoint", "attemptedLocation",
             "attemptedInstancePath", "breakPointIndex", "originalExpression",
             "expressionWithBrokenPoint", "suggestedFix"}


def segments(names):
    return [{"kind": "index", "index": n} if isinstance(n, int)
            else {"kind": "property", "name": n} for n in names]


def failure(action, location, attempted, pointer, attempted_pointer, chain, native):
    try:
        action()
    except TeaQLNotLoadedError as error:
        wire, human = error.to_wire(), str(error)
        assert set(wire) == WIRE_KEYS, wire
        assert wire["code"] == "NOT_LOADED"
        assert wire["location"] == segments(location), wire
        assert wire["attemptedLocation"] == segments(attempted), wire
        assert wire["instancePath"] == pointer and wire["attemptedInstancePath"] == attempted_pointer, wire
        assert wire["breakPoint"] == location[-1] and wire["breakPointIndex"] == len(location) - 1
        assert wire["originalExpression"] == chain.replace("<broken>", ""), wire
        assert wire["expressionWithBrokenPoint"] == chain, wire
        assert chain.count("<broken>") == 1
        assert wire["suggestedFix"] == {"action": "preload", "location": segments(location)}
        assert human == (f"TeaQLNotLoadedError: access_path={native} break_point={location[-1]}"
                         f" — select the missing field or relation expression={chain}"), human
        assert "PRIVATE_PY_E_" not in json.dumps(wire) + human
        return {"wire": wire, "human": human}
    raise AssertionError("NotLoaded was hidden by an E terminal")


async def main(database, round_number):
    assert round_number in (1, 2)
    calls = Counter(ZERO)
    service = ObservedService(SQLiteTeaQLClient(str(database)), calls)
    governance = ObservedGovernance(calls)
    clock = datetime(2032, 2, 29, 10, 15, 30, tzinfo=timezone.utc)
    context = (UserContext.new().install(GENERATED_RUNTIME_MODULE)
               .insert_resource("dataService", service)
               .with_business_clock(FixedBusinessClock(clock))
               .with_active_root(ContextEntityRef("Tenant", 1))
               .with_mutation_policy_registry(governance).with_app_audit_event_sink(governance))
    cases = []

    def emit(name, value):
        record = dict(name=name, round=round_number, value=value, passed=True)
        cases.append(record)
        print("PYTHON_E_BOUNDARY_CASE=" + json.dumps(record, sort_keys=True), flush=True)

    try:
        await context.ensure_schema()
        order = ((await Q.purchase_orders().comment("Prepare the expression graph")
                 .purpose("Verify generated E terminals and side-effect boundaries").new_entity(context)))
        order.update_contact_phone("5550960").update_internal_note(None)
        for i in range(3):
            child = ((await Q.order_items().comment("Prepare an expression item")
                     .purpose("Exercise real numeric list indices").new_entity(context)))
            child.update_product_name("Expression item " + str(i)).update_unit_price(Decimal("10.00"))
            order.order_item_list().append(child)
        await order.audit_as("Create the bounded expression graph").save(context)
        empty = ((await Q.purchase_orders().comment("Prepare an empty expression owner")
                 .purpose("Distinguish loaded empty collections from NotLoaded").new_entity(context)))
        empty.update_contact_phone("5550962").update_internal_note(None)
        await empty.audit_as("Create the loaded-empty expression control").save(context)
        order.update_contact_phone("5550961")
        await order.audit_as("Calibrate actual update and audit observers").save(context)
        rollback = await service.begin(context)
        await rollback.rollback(context)

        def query(identity):
            return Q.purchase_orders().with_id_is(identity).limit(1)

        full = await query(order.id).select_order_item_list_with(
            Q.order_items().limit(10).comment("Load complete selected items")) \
            .comment("Load the complete expression graph").purpose("Keep E evaluation in the loaded graph").execute_for_one(context)
        loaded_empty = await query(empty.id).select_order_item_list_with(
            Q.order_items().limit(10).comment("Explicitly load the empty list")) \
            .comment("Load the empty expression graph").purpose("Distinguish empty from NotLoaded").execute_for_one(context)
        fk_only = await query(order.id).comment("Load FK-only expression graph") \
            .purpose("Do not fabricate a loaded relation from its foreign key").execute_for_one(context)
        late = await (Q.purchase_orders_minimal().with_id_is(order.id).limit(1)
                      .select_tenant_with(Q.tenants_minimal().limit(1).comment("Load only root identity"))
                      .comment("Load an identity-only relation target")
                      .purpose("Put the missing breakpoint at the real target leaf").execute_for_one(context))
        indexed = await (Q.purchase_orders_minimal().with_id_is(order.id).limit(1)
                         .select_order_item_list_with(Q.order_items_minimal().limit(10).comment("Load only item identities"))
                         .comment("Load identity-only indexed targets")
                         .purpose("Retain a numeric index before the missing product name").execute_for_one(context))
        calibration = dict(calls)
        assert all(n > 0 for n in calibration.values()), calibration
        views = [full, loaded_empty, fk_only, late, indexed]
        roots = [v._entity_root for v in views]

        def state():
            return ([v.to_json() for v in views],
                    [deepcopy(tuple(v._entity_root.current_change_set().changes())) for v in views])

        before = state()
        before_hash = hashlib.sha256(json.dumps(before[0], sort_keys=True).encode()).hexdigest()
        prefix = "E.purchase_order(<root>)"
        emit("late-leaf", failure(lambda: E.purchase_order(late).tenant().name().eval(),
             ["tenant", "name"], ["tenant", "name"], "/tenant/name", "/tenant/name",
             prefix + ".tenant().name()<broken>.eval()", "tenant.name"))
        emit("indexed-leaf", failure(lambda: E.purchase_order(indexed).order_item_list().get(2).product_name().eval(),
             ["order_item_list", 2, "product_name"], ["order_item_list", 2, "product_name"],
             "/orderItemList/2/productName", "/orderItemList/2/productName",
             prefix + ".order_item_list().get(2).product_name()<broken>.eval()", "order_item_list[2].product_name"))
        emit("first-indexed-leaf", failure(lambda: E.purchase_order(indexed).order_item_list().first().product_name().eval(),
             ["order_item_list", 0, "product_name"], ["order_item_list", 0, "product_name"],
             "/orderItemList/0/productName", "/orderItemList/0/productName",
             prefix + ".order_item_list().first().product_name()<broken>.eval()", "order_item_list[0].product_name"))
        assert E.purchase_order(full).internal_note().eval() is None
        assert E.purchase_order(full).internal_note().or_if_null("PRIVATE_PY_E_NULL") == "PRIVATE_PY_E_NULL"
        emit("loaded-null", {"value": None, "fallbackUsed": True})
        assert E.purchase_order(loaded_empty).order_item_list().first().product_name().eval() is None
        assert E.purchase_order(loaded_empty).order_item_list().get(2).product_name().eval() is None
        empty_size = E.purchase_order(loaded_empty).order_item_list().size().eval()
        assert empty_size == 0
        emit("loaded-empty", {"size": empty_size, "first": None, "index": None})
        for index in (-1, 3):
            assert E.purchase_order(full).order_item_list().get(index).product_name().eval() is None
        emit("out-of-range", {"negativeIndex": -1, "index": 3, "value": None})

        missing = E.purchase_order(fk_only).tenant().name()
        emit("missing-list-size", failure(lambda: E.purchase_order(fk_only).order_item_list().size().eval(),
             ["order_item_list"], ["order_item_list"], "/orderItemList", "/orderItemList",
             prefix + ".order_item_list()<broken>.size().eval()", "order_item_list"))
        terminals = []
        for terminal, args, rendered in [
                ("eval", (), "eval()"), ("or_if_null", ("PRIVATE_PY_E_FALLBACK",), "or_if_null(<fallback>)")]:
            terminals.append(failure(lambda: getattr(missing, terminal)(*args), ["tenant"], ["tenant", "name"],
                 "/tenant", "/tenant/name", prefix + ".tenant()<broken>.name()." + rendered, "tenant"))
        emit("terminals", {"observations": terminals})
        root = E.purchase_order(fk_only)
        left, right = root.tenant().name(), root.order_item_list().get(2).product_name()
        left_before = failure(left.eval, ["tenant"], ["tenant", "name"], "/tenant", "/tenant/name",
                              prefix + ".tenant()<broken>.name().eval()", "tenant")
        right_failure = failure(right.eval, ["order_item_list"], ["order_item_list", 2, "product_name"],
             "/orderItemList", "/orderItemList/2/productName", prefix + ".order_item_list()<broken>.get(2).product_name().eval()", "order_item_list")
        left_after = failure(left.eval, ["tenant"], ["tenant", "name"], "/tenant", "/tenant/name",
                             prefix + ".tenant()<broken>.name().eval()", "tenant")
        assert left_before == left_after
        emit("sibling-paths", {"leftBefore": left_before, "leftAfter": left_after, "right": right_failure})
        assert E.purchase_order(fk_only).tenant_id().eval() == 1
        emit("fk-only-not-loaded", {"fk": 1, "failure": failure(missing.eval, ["tenant"], ["tenant", "name"],
             "/tenant", "/tenant/name", prefix + ".tenant()<broken>.name().eval()", "tenant")})
        repeated = E.purchase_order(fk_only).tenant().purchase_order_list().first().tenant().name()
        emit("repeated-relation", failure(repeated.eval, ["tenant"], ["tenant", "purchase_order_list", 0, "tenant", "name"],
             "/tenant", "/tenant/purchaseOrderList/0/tenant/name",
             prefix + ".tenant()<broken>.purchase_order_list().first().tenant().name().eval()", "tenant"))
        assert state() == before
        assert all(a is b for a, b in zip(roots, [v._entity_root for v in views]))
        effects = {key: calls[key] - calibration[key] for key in ZERO}
        assert effects == ZERO, effects
        emit("no-side-effects", {"before": before_hash, "after": before_hash, "effects": effects,
             "calibration": calibration, "ledgerIdentitiesUnchanged": True})
        print("PYTHON_E_BOUNDARY_RESULT=" + json.dumps({"language": "python", "round": round_number,
              "passed": True, "cases": [r["name"] for r in cases], "parentId": order.id, "emptyParentId": empty.id,
              "childIds": [row.id for row in full.order_item_list()], "terminalObservations": len(terminals),
              "generatedCases": len(cases), "nativeLocationCases": 0, "fullDiagnosticContractAccepted": False}, sort_keys=True), flush=True)
    finally:
        await service.close()
        print("PYTHON_E_BOUNDARY_ORIGINS=" + json.dumps({"runtime": str(Path(teaql.__file__).resolve()),
              "sqlite": str(Path(inspect.getfile(SQLiteTeaQLClient)).resolve()), "generated": str(Path(inspect.getfile(Q)).resolve())}), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--round", type=int, choices=(1, 2), required=True)
    options = parser.parse_args()
    asyncio.run(main(options.database, options.round))
