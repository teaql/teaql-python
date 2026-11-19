"""Independent query projections and ledgers, using generated Q/E/audited save.

Run rounds 1 and 2 on one owned SQLite file. No handwritten mutation SQL,
generated-source changes, Context-wide ledger or implicit database reads.
The ledger inspection is test instrumentation, not application API discovery.
"""
import argparse
import asyncio
from collections import Counter
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import inspect
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / "generated"))
from E import E
from Q import Q
from runtime_module import GENERATED_RUNTIME_MODULE
import teaql
from teaql.core.value import Timestamp
from teaql.data_service import SQLiteTeaQLClient
from teaql.runtime import ContextEntityRef, FixedBusinessClock, TeaQLNotLoadedError, UserContext
from partial_root_loading import ZERO, ObservedGovernance, ObservedService


def pending(row):
    return deepcopy(dict(dict(row._entity_root.current_change_set().changes())
                         .get(row._teaql_entity_key(), {})))


def missing(expression, path):
    try:
        expression.eval()
    except TeaQLNotLoadedError as error:
        wire = error.to_wire()
        assert wire["code"] == "NOT_LOADED" and wire["attemptedInstancePath"] == path
        assert wire["expressionWithBrokenPoint"].count("<broken>") == 1
        return
    raise AssertionError("A view was silently widened: " + path)


async def main(database, round_number):
    first = datetime(2032, 2, 29, 10, 15, 30, tzinfo=timezone.utc) + timedelta(days=round_number - 1)
    second = first + timedelta(hours=2)
    calls = Counter(ZERO)
    service = ObservedService(SQLiteTeaQLClient(str(database)), calls)
    governance = ObservedGovernance(calls)
    context = (UserContext.new().install(GENERATED_RUNTIME_MODULE)
               .insert_resource("dataService", service)
               .with_business_clock(FixedBusinessClock(first))
               .with_active_root(ContextEntityRef("Tenant", 1))
               .with_mutation_policy_registry(governance)
               .with_app_audit_event_sink(governance))
    outcomes = []

    async def seed():
        context.with_business_clock(FixedBusinessClock(first))
        allocations_before_creation = calls["allocations"]
        row = ((await Q.purchase_orders().comment("Prepare an independent projection fixture")
               .purpose("Verify query-view isolation and independent pending mutations")
               .new_entity(context)))
        reserved_id = row.id
        assert type(reserved_id) is int and reserved_id > 0
        assert calls["allocations"] == allocations_before_creation + 1
        row.update_contact_phone("5550700").update_internal_note(None)
        before = dict(calls)
        await row.audit_as("Create the projection fixture through generated mutation").save(context)
        assert calls["mutations"] > before["mutations"] and calls["commits"] > before["commits"]
        assert calls["allocations"] == before["allocations"] and row.id == reserved_id
        assert calls["audits"] > before["audits"]
        return row

    async def full(identity):
        return await (Q.purchase_orders().with_id_is(identity).limit(1)
                      .comment("Load a complete independent order view")
                      .purpose("Compare explicit projections for the same persisted identity")
                      .execute_for_one(context))

    def emit(case, identity, facts):
        record = dict(case=case, round=round_number, orderId=str(identity), passed=True, facts=facts)
        outcomes.append(record)
        print("PYTHON_PROJECTION_VIEW_CASE=" + json.dumps(record, sort_keys=True), flush=True)

    try:
        await context.ensure_schema()

        original = await seed()
        sparse = await (Q.purchase_orders_minimal().with_id_is(original.id).limit(1)
                        .comment("Load only the sparse identity view")
                        .purpose("A later full query must not widen the earlier projection")
                        .execute_for_one(context))
        missing(E.purchase_order(sparse).contact_phone(), "/contactPhone")
        before_json = sparse.to_json()
        wide = await full(original.id)
        assert sparse is not wide and sparse.id == wide.id
        before = dict(calls)
        missing(E.purchase_order(sparse).contact_phone(), "/contactPhone")
        missing(E.purchase_order(sparse).internal_note(), "/internalNote")
        assert E.purchase_order(wide).contact_phone().eval() == "5550700"
        assert E.purchase_order(wide).internal_note().eval() is None
        narrow_json, wide_json = json.loads(sparse.to_json()), json.loads(wide.to_json())
        assert "contactPhone" not in narrow_json and "internalNote" not in narrow_json
        assert "internalNote" in wide_json and wide_json["internalNote"] is None
        assert sparse.to_json() == before_json and not pending(sparse) and not pending(wide)
        assert dict(calls) == before and wide.version == 1
        emit("independent-query-projection-boundary", original.id, {
            "sameIdentity": True, "separateViews": True, "sparseJsonUnchanged": True,
            "sparseJsonOmitsFields": True, "wideNullIsLoaded": True,
            "implicitProviderCalls": 0, "hydrationDirtyKeys": 0, "version": 1})

        original = await seed()
        left, other = await full(original.id), await full(original.id)
        assert left is not other
        left.update_contact_phone("5550701")
        other.update_internal_note("pending-other-view")
        assert pending(other)["internal_note"].val == "pending-other-view"
        context.with_business_clock(FixedBusinessClock(second))
        await left.audit_as("Save only the first independently queried order view").save(context)
        stored = await full(original.id)
        assert stored.version == 2 and E.purchase_order(stored).contact_phone().eval() == "5550701"
        assert E.purchase_order(stored).internal_note().eval() is None
        assert other.version == 1 and E.purchase_order(other).contact_phone().eval() == "5550700"
        intent, before = pending(other), dict(calls)
        failure = None
        try:
            await other.audit_as("Reject the stale independent view without discarding its edit").save(context)
        except Exception as error:
            failure = error
        print("PYTHON_STALE_VIEW_OBSERVATION=" + json.dumps({"round": round_number, "orderId": str(original.id),
              "errorType": type(failure).__name__ if failure else None, "message": str(failure) if failure else None,
              "effects": {key: calls[key] - before[key] for key in ZERO}}, sort_keys=True), flush=True)
        assert failure is not None, "A stale independent view was reported as successfully saved"
        assert type(failure) is RuntimeError
        assert str(failure) == "Mutation provider did not return authoritative persisted state for PurchaseOrder"
        assert calls["mutations"] > before["mutations"] and calls["rollbacks"] == before["rollbacks"] + 1
        assert calls["commits"] == before["commits"] and calls["audits"] == before["audits"]
        after = pending(other)
        for name, value in intent.items():
            assert after[name] == value
        derived = sorted(set(after) - set(intent))
        assert set(derived).issubset({"update_time"}), "Only the successful managed Fix may be added to pending intent"
        if derived:
            value = after["update_time"].val
            assert value == second or (isinstance(value, Timestamp) and value.millis == int(second.timestamp() * 1000))
        assert other.version == 1 and E.purchase_order(other).internal_note().eval() == "pending-other-view"
        stored = await full(original.id)
        assert stored.version == 2 and E.purchase_order(stored).contact_phone().eval() == "5550701"
        assert E.purchase_order(stored).internal_note().eval() is None
        emit("same-identity-independent-mutation-ledgers", original.id, {
            "separateViews": True, "otherPendingEditRetained": True, "noCrossViewWrite": True,
            "staleException": type(failure).__name__, "storedVersion": 2, "otherVersion": 1,
            "derivedFixFields": derived, "rejectionRolledBack": True, "commitAuditsOnRejection": 0})

        original = await seed()
        root = await (Q.tenants_minimal().with_id_is(1).limit(1)
                      .select_purchase_order_list_with(Q.purchase_orders_minimal().with_id_is(original.id).limit(1)
                          .select_tenant_with(Q.tenants().limit(1).comment("Load this explicit full root alias"))
                          .comment("Load a sparse order and its complete forward root"))
                      .comment("Keep the outer root sparse despite its full nested alias")
                      .purpose("Identity deduplication must not union separately requested projections")
                      .execute_for_one(context))
        order = root.purchase_order_list()[0]
        alias = E.purchase_order(order).tenant().eval()
        assert root.id == alias.id
        before = dict(calls)
        missing(E.tenant(root).name(), "/name")
        name = E.tenant(alias).name().eval()
        assert name is not None
        graph = json.loads(root.to_json())
        assert "name" not in graph and graph["purchaseOrderList"][0]["tenant"]["name"] == name
        assert not pending(root) and not pending(alias) and dict(calls) == before
        emit("intra-query-repeated-identity-projection-boundary", original.id, {
            "sameIdentity": True, "sparseRootNameNotLoaded": True, "nestedTargetNameLoaded": True,
            "jsonRespectsBothViews": True, "implicitProviderCalls": 0})
        print("PYTHON_PROJECTION_VIEW_COMPLETE=" + json.dumps({"round": round_number, "passed": True,
              "cases": len(outcomes), "database": str(database), "calibratedProvider": True}), flush=True)
    finally:
        await service.close()
        print("PYTHON_PROJECTION_VIEW_ORIGINS=" + json.dumps({"round": round_number,
              "runtime": str(Path(teaql.__file__).resolve()), "sqlite": str(Path(inspect.getfile(SQLiteTeaQLClient)).resolve()),
              "generated": str(Path(inspect.getfile(Q)).resolve())}), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--round", type=int, choices=(1, 2), required=True)
    options = parser.parse_args()
    asyncio.run(main(options.database, options.round))
