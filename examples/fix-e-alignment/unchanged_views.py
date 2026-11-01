"""No-op view preservation and real commit invalidation through generated Q/E/save.

Use one owned SQLite file for rounds 1 and 2. The only direct SQL is a read-only
independent storage oracle. No generated implementation is inspected or changed.
"""
import argparse
import asyncio
from collections import Counter
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
from teaql.core.expr import column, in_list, value
from teaql.core.query import SelectQuery
from teaql.data_service import SQLiteTeaQLClient
from teaql.runtime import ContextEntityRef, FixedBusinessClock, UserContext
from teaql.runtime.entity_json import EntityJSONError
from teaql.runtime.query_properties import capture_entity_query_properties
from partial_root_loading import ZERO, ObservedGovernance, ObservedService, storage
from projection_views import missing, pending


def aliases(request):
    request.query.project_expr("_null", value(None))
    request.query.project_expr("_zero", value(0))
    request.query.project_expr("_empty", value(""))
    request.query.project_expr("_row_id", column("id"))
    request.query.project_expr("_phone", column("contact_phone"))
    return request


def properties(row):
    assert row.get_dynamic_property("_null") is None and row.get_dynamic_property("_missing") is None
    selected = row._projection_properties.selected_values()  # Read-only test observation.
    assert "_null" in selected and "_missing" not in row._projection_properties.as_dict()
    assert row.get_dynamic_property("_zero") == 0 and row.get_dynamic_property("_empty") == ""
    assert row.get_dynamic_property("_row_id") == row.id
    assert row.get_dynamic_property("_phone") == E.purchase_order(row).contact_phone().eval()
    payload = json.loads(row.to_json())
    assert payload["_null"] is None and payload["_zero"] == 0 and payload["_empty"] == ""
    assert payload["_row_id"] == row.id and "_missing" not in payload


async def main(database, round_number):
    first = datetime(2032, 2, 29, 10, 15, 30, tzinfo=timezone.utc) + timedelta(days=round_number - 1)
    second = first + timedelta(hours=2)
    calls = Counter(ZERO)
    service = ObservedService(SQLiteTeaQLClient(str(database)), calls)
    governance = ObservedGovernance(calls)
    context = (UserContext.new().install(GENERATED_RUNTIME_MODULE)
               .insert_resource("dataService", service).with_business_clock(FixedBusinessClock(first))
               .with_active_root(ContextEntityRef("Tenant", 1))
               .with_mutation_policy_registry(governance).with_app_audit_event_sink(governance))
    cases = []

    def real_write(before):
        delta = {key: calls[key] - before[key] for key in ZERO}
        assert delta == dict(queries=0, mutations=1, begins=1, commits=1, rollbacks=0,
                             allocations=0, policyLookups=1, policyReviews=1, audits=1), delta
        return delta

    async def seed():
        row = (Q.purchase_orders().comment("Prepare an unchanged-view fixture")
               .purpose("Verify view preservation through generated audited mutations").new_entity(context))
        row.update_contact_phone("5550800").update_internal_note(None)
        await row.audit_as("Create the unchanged-view fixture").save(context)
        return row

    async def noop(row, name):
        payload, fields = row.to_json(), sorted(row._loaded_fields)
        ledger, key = row._entity_root, row._teaql_entity_key()
        version, original, lineage = row.version, ledger.original_version(key), ledger.trace_chain(key)
        before = dict(calls)
        result = await row.audit_as("Save unchanged view: " + name).save(context)
        assert dict(calls) == before and row.to_json() == payload and result.to_json() == payload
        assert sorted(result._loaded_fields) == fields and result.version == version == 1
        assert ledger.original_version(key) == original and ledger.trace_chain(key) == lineage and not pending(row)
        properties(row)
        properties(result)
        record = dict(round=round_number, case=name, orderId=row.id, passed=True, before=before, after=dict(calls),
                      effects={key: calls[key] - before[key] for key in ZERO}, loadedFields=fields,
                      versionBefore=version, versionAfter=result.version, originalVersionPreserved=True,
                      lineagePreserved=True, jsonPreserved=True, selectedNullPresent=True, absentPropertyPresent=False,
                      zero=0, empty="", rowOwnedProperty=row.id, pending=False)
        cases.append(record)
        print("PYTHON_UNCHANGED_VIEW_CASE=" + json.dumps(record, sort_keys=True), flush=True)

    try:
        await context.ensure_schema()
        existing = await (Q.purchase_orders().limit(5).comment("Determine the retained unchanged-view round")
                          .purpose("Use one unreset store for consecutive tests").execute_for_list(context))
        assert len(existing) == (round_number - 1) * 2
        one, two = await seed(), await seed()
        # Exercise and observe a real rollback as well as successful commits.
        rollback = await service.begin(context)
        await rollback.rollback(context)
        assert all(count > 0 for count in calls.values()), calls

        request = aliases(Q.purchase_orders_minimal().with_id_is(one.id).select_contact_phone().select_internal_note()
                          .select_tenant_with(Q.tenants_minimal().limit(1).comment("Retain only the selected root identity"))
                          .limit(1).comment("Load a sparse view with readonly query properties"))
        sparse = await request.purpose("Restoring fields must retain the original projection").execute_for_one(context)
        properties(sparse)
        missing(E.purchase_order(sparse).create_time(), "/createTime")
        missing(E.purchase_order(sparse).tenant().name(), "/tenant/name")
        assert E.purchase_order(sparse).tenant().id().eval() == 1
        assert E.purchase_order(sparse).internal_note().eval() is None
        sparse.update_contact_phone("5550899").update_contact_phone("5550800")
        sparse.update_internal_note("temporary null replacement").update_internal_note(None)
        await noop(sparse, "sparse-restored-values-null-properties-and-edge")
        missing(E.purchase_order(sparse).create_time(), "/createTime")
        missing(E.purchase_order(sparse).tenant().name(), "/tenant/name")
        assert E.purchase_order(sparse).tenant().id().eval() == 1
        await noop(sparse, "repeat-clean-sparse-save")

        request = aliases(Q.purchase_orders().limit(2).comment("Load two rows with identical query geometry"))
        request.query.and_filter(in_list("id", [one.id, two.id]))
        pair = await request.purpose("Keep readonly values and mutable ledgers row-owned").execute_for_list(context)
        left, right = sorted(pair, key=lambda row: row.id)
        assert left.id == one.id and right.id == two.id
        properties(left)
        properties(right)
        right.update_internal_note("independent pending value")
        right_intent = pending(right)
        left.update_contact_phone("5550899").update_contact_phone("5550800")
        await noop(left, "other-row-pending-intent-and-values-retained")
        assert pending(right) == right_intent and right.get_dynamic_property("_row_id") == two.id
        assert E.purchase_order(right).internal_note().eval() == "independent pending value"
        right.update_internal_note(None)
        await noop(right, "row-owned-properties-and-loaded-null-retained")

        before, payload = dict(calls), left.to_json()
        try:
            capture_entity_query_properties(left, SelectQuery("PurchaseOrder").project_expr("contact_phone", value(0)))
            raise AssertionError("A modeled-field collision was accepted")
        except EntityJSONError as error:
            assert error.code == "WIRE_QUERY_PROPERTY_COLLISION"
        try:
            capture_entity_query_properties(left, SelectQuery("PurchaseOrder").project_expr("_missing", value(None)))
            raise AssertionError("A missing query alias was invented")
        except ValueError as error:
            assert "not present" in str(error)
        assert dict(calls) == before and left.to_json() == payload
        await noop(left, "rejected-property-selection-retains-prior-view")

        context.with_business_clock(FixedBusinessClock(second))
        right.update_contact_phone("5550801")
        before = dict(calls)
        saved = await right.audit_as("Persist a genuine edit after unchanged saves").save(context)
        effects = real_write(before)
        assert E.purchase_order(saved).contact_phone().eval() == "5550801" and saved.version == 2
        assert E.purchase_order(saved).create_time().eval() == first and E.purchase_order(saved).update_time().eval() == second
        assert saved.get_dynamic_property("_phone") is None, "A real save exported a stale query-result alias"
        assert "_phone" not in json.loads(saved.to_json())
        properties(left)
        assert left.version == 1
        print("PYTHON_UNCHANGED_VIEW_WRITE=" + json.dumps(dict(round=round_number, orderId=right.id,
              before=before, after=dict(calls), effects=effects, phone="5550801", version=2,
              stalePropertyReinstalled=False, passed=True), sort_keys=True), flush=True)
        rows = storage(database)
        assert len(rows["purchase_order_data"]) == round_number * 2 and rows["order_item_data"] == []
        for index, row in enumerate(rows["purchase_order_data"]):
            instant = first - timedelta(days=round_number - 1) + timedelta(days=index // 2)
            assert row == dict(id=index+1, tenant=1, contact_phone="5550801" if index % 2 else "5550800",
                              internal_note=None, version=2 if index % 2 else 1,
                              create_time=int(instant.timestamp()*1000),
                              update_time=int((instant + timedelta(hours=2 if index % 2 else 0)).timestamp()*1000))
        print("PYTHON_UNCHANGED_VIEW_PHYSICAL=" + json.dumps(dict(round=round_number, rows=rows, passed=True), sort_keys=True), flush=True)
        print("PYTHON_UNCHANGED_VIEW_COMPLETE=" + json.dumps(dict(round=round_number, cases=len(cases),
              passed=True, database=str(database), calibratedProvider=True), sort_keys=True), flush=True)
    finally:
        await service.close()
        print("PYTHON_UNCHANGED_VIEW_ORIGINS=" + json.dumps(dict(round=round_number,
              runtime=str(Path(teaql.__file__).resolve()), sqlite=str(Path(inspect.getfile(SQLiteTeaQLClient)).resolve()),
              generated=str(Path(inspect.getfile(Q)).resolve())), sort_keys=True), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--round", type=int, choices=(1, 2), required=True)
    options = parser.parse_args()
    asyncio.run(main(options.database, options.round))
