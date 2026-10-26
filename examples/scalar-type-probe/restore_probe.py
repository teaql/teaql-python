"""Known persisted originals through the immutable generated Q/E/save library."""
import asyncio
from datetime import datetime, timezone
from decimal import Decimal
import json
import math
import os
from pathlib import Path
from uuid import uuid4

from E import E, TeaQLNotLoadedError
from Q import Q
from main import new_probe
from name_probe import AuditRecorder, Observations, ObservedGraphService, ObservedTransport, PolicyRecorder
from runtime_module import GENERATED_RUNTIME_MODULE
from teaql.core.value import Value
from teaql.data_service import SQLiteTeaQLClient
from teaql.runtime import CheckException, DelegatingMutationPolicyRegistry, FixedBusinessClock, UserContext


async def load(context, identity):
    return await (Q.scalar_type_probes().with_id_is(identity).limit(1)
                  .comment("load the persisted restoration baseline")
                  .purpose("verify generated mutation cancellation").execute_for_one(context))


async def main():
    database = os.environ["TEAQL_SCALAR_PROBE_DB"]
    sql = Observations()
    client = SQLiteTeaQLClient(database)
    client.transport = ObservedTransport(database, sql)
    observed, audit, policy = ObservedGraphService(client), AuditRecorder(), PolicyRecorder()
    context = (UserContext().install(GENERATED_RUNTIME_MODULE).insert_resource("dataService", observed)
               .with_app_audit_event_sink(audit)
               .with_mutation_policy_registry(DelegatingMutationPolicyRegistry(lambda _: policy))
               .with_business_clock(FixedBusinessClock(datetime(2032, 2, 29, tzinfo=timezone.utc))))
    cases = []
    def case(name, **details):
        value = {"case": name, "passed": True, **details}
        cases.append(value)
        print("PYTHON_RESTORATION_CASE=" + json.dumps(value, sort_keys=True), flush=True)

    async def unchanged(entity, reason):
        version = entity.version
        before, audits, plans = observed.calls.copy(), len(audit.events), len(policy.plans)
        authorizations, statements = sql.authorizations, sql.statements.copy()
        loaded = set(entity._loaded_fields)  # Explicit state assertion, never API discovery.
        await entity.audit_as(reason).save(context)
        assert entity.version == version and set(entity._loaded_fields) == loaded
        assert observed.calls == before and len(audit.events) == audits and len(policy.plans) == plans
        assert sql.authorizations == authorizations and sql.statements == statements
    try:
        await context.ensure_schema()
        seed = new_probe(context, "restore-" + uuid4().hex, Decimal("37.00"))
        await seed.audit_as("create an independent restoration fixture").save(context)
        row = await load(context, seed.id)
        original = E.scalar_type_probe(row).required_string().eval()
        version = row.version
        row.update_required_string("temporary value that must not survive")
        row.update_required_string(original)
        before, audit_count, policy_count = observed.calls.copy(), len(audit.events), len(policy.plans)
        authorizations, statements = sql.authorizations, sql.statements.copy()
        await row.audit_as("restore the known original without a mutation").save(context)
        delta = {key: observed.calls[key] - before[key] for key in before}
        report = {"round": os.environ.get("TEAQL_PROBE_ROUND", "1"), "id": row.id,
                  "originalVersion": version, "returnedVersion": row.version,
                  "providerCalls": delta, "auditEvents": len(audit.events) - audit_count,
                  "policyPlans": len(policy.plans) - policy_count,
                  "sqliteAuthorizations": sql.authorizations - authorizations,
                  "sqliteStatements": sum((sql.statements - statements).values()),
                  "valueRestored": E.scalar_type_probe(row).required_string().eval() == original}
        print("PYTHON_LOADED_RESTORE=" + json.dumps(report, sort_keys=True), flush=True)
        assert report["valueRestored"]
        assert row.version == version, "restoring a known original unnecessarily changed its version"
        assert not any(delta.values()), "empty final plan touched the provider"
        assert report["auditEvents"] == report["policyPlans"] == 0
        assert report["sqliteAuthorizations"] == report["sqliteStatements"] == 0
        reloaded = await load(context, seed.id)
        assert reloaded.version == version
        assert E.scalar_type_probe(reloaded).required_string().eval() == original
        case("known-value", id=row.id, version=version, providerCalls=delta)

        row.update_optional_string("temporary optional value")
        row.update_optional_string(None)
        await unchanged(row, "restore an original loaded null")
        assert E.scalar_type_probe(row).optional_string().eval() is None
        case("known-null", id=row.id, version=row.version)

        # Raw access is a deliberate generic-ledger fault-injection control.
        row._entity_root.set(row._teaql_entity_key(), "required_string", Value.Text(original))
        await unchanged(row, "normalize an admitted generic-ledger restoration")
        case("generic-ledger", id=row.id, version=row.version)

        expected_time = datetime(2032, 3, 1, 12, 30, tzinfo=timezone.utc)
        context.with_business_clock(FixedBusinessClock(expected_time))
        row.update_required_string("cancelled intermediate")
        row.update_required_string(original)
        row.update_optional_string("real surviving edit")
        await row.audit_as("save only the genuine remaining field").save(context)
        assert row.version == 2
        assert "required_string" not in policy.plans[-1].operations[0].changed_values
        actual = await load(context, row.id)
        assert E.scalar_type_probe(actual).optional_string().eval() == "real surviving edit"
        assert E.scalar_type_probe(actual).update_time().eval() == expected_time
        case("remaining-edit-and-clock", id=row.id, version=row.version, restoredFieldExcluded=True)

        sparse = await (Q.scalar_type_probes_minimal().with_id_is(row.id).select_required_string().limit(1)
                        .comment("load only one known field")
                        .purpose("keep unknown originals distinct from null").execute_for_one(context))
        try:
            E.scalar_type_probe(sparse).optional_string().eval()
            raise AssertionError("unknown original became a loaded null")
        except TeaQLNotLoadedError:
            pass
        sparse.update_optional_string(None)
        before = observed.calls.copy()
        authorizations = sql.authorizations
        try:
            await sparse.audit_as("reject an unknown-original partial update").save(context)
            raise AssertionError("modified partial entity was accepted")
        except CheckException:
            assert observed.calls == before
            assert sql.authorizations == authorizations
        case("unknown-original", id=row.id, noProvider=True)

        malformed = await load(context, row.id)
        key = malformed._teaql_entity_key()
        malformed._entity_root.set(key, "required_string", Value.Text(original))
        malformed._entity_root.set(key, "requiredString", Value.Null())
        before = observed.calls.copy()
        authorizations = sql.authorizations
        try:
            await malformed.audit_as("reject an equal malformed ledger key").save(context)
            raise AssertionError("invalid ledger namespace was silently discarded")
        except CheckException:
            assert observed.calls == before
            assert sql.authorizations == authorizations
            assert malformed._entity_root.get(key, "required_string") == Value.Text(original)
        case("admission-before-discard", id=row.id, noProvider=True)

        row.update_required_decimal(Decimal("37.000"))
        await row.audit_as("retain an explicit Decimal scale change").save(context)
        assert row.version == 3
        actual = await load(context, row.id)
        assert str(E.scalar_type_probe(actual).required_decimal().eval()) == "37.000"
        case("decimal-representation", id=row.id, version=row.version, decimal="37.000")

        row.update_required_double(0.0)
        await row.audit_as("prepare a signed-zero mutation control").save(context)
        row.update_required_double(-0.0)
        await row.audit_as("do not erase signed-zero mutation intent").save(context)
        changed = policy.plans[-1].operations[0].changed_values["required_double"].val
        assert row.version == 5 and math.copysign(1.0, changed) == -1
        case("signed-zero-intent", id=row.id, version=row.version, sqliteSignedZeroReadbackNotClaimed=True)

        parent = (Q.type_platforms().comment("prepare a graph restoration owner")
                  .purpose("test a clean parent with changed children").new_entity(context))
        parent.update_name("restoration owner " + uuid4().hex)
        await parent.audit_as("create the independent graph owner").save(context)
        for index in range(2):
            child = new_probe(context, "restore-child-" + str(index) + "-" + uuid4().hex, Decimal("37.00"))
            child.update_type_platform(parent)
            await child.audit_as("create a graph restoration child").save(context)
        graph = await (Q.type_platforms().with_id_is(parent.id).limit(1)
                       .select_scalar_type_probe_list_with(Q.scalar_type_probes().order_by_id_ascending().limit(2))
                       .comment("load the bounded restoration graph")
                       .purpose("keep real child work when the parent is clean").execute_for_one(context))
        children = list(graph.scalar_type_probe_list())
        assert len(children) == 2
        parent_name = E.type_platform(graph).name().eval()
        graph.update_name("temporary graph owner name")
        graph.update_name(parent_name)
        children[0].update_optional_string("real graph child edit")
        await graph.audit_as("save a changed child beneath a restored parent").save(context)
        assert graph.version == 1 and [item.version for item in children] == [2, 1]
        assert len(policy.plans[-1].operations) == 1
        assert policy.plans[-1].operations[0].entity == "ScalarTypeProbe"
        case("clean-parent-dirty-child", parentId=graph.id, childIds=[item.id for item in children])

        children[0].update_optional_string("temporary child edit")
        children[0].update_optional_string("real graph child edit")
        await unchanged(graph, "restore the only graph edit without opening a transaction")
        case("empty-final-graph", parentId=graph.id, childIds=[item.id for item in children])

        children[1].update_required_string("temporary value before deletion")
        children[1].mark_for_deletion()
        await graph.audit_as("keep a pending child deletion").save(context)
        absent = await (Q.scalar_type_probes().with_id_is(children[1].id).limit(1)
                        .comment("read the deleted restoration child")
                        .purpose("confirm deletion was not cancelled").execute_for_list(context))
        assert not absent and graph.version == 1 and children[0].version == 2
        case("pending-deletion", parentId=graph.id, deletedId=children[1].id)

        complete = {"schema": "teaql.python-known-baseline-restoration/v1", "passed": True,
                    "round": os.environ.get("TEAQL_PROBE_ROUND", "1"), "cases": cases,
                    "standaloneId": row.id, "standaloneVersion": row.version, "parentId": graph.id,
                    "children": [{"id": item.id, "version": item.version} for item in children],
                    "generatedSourceEdited": False, "successfulProviderCalls": dict(observed.calls),
                    "sqliteAuthorizations": sql.authorizations, "sqliteStatements": dict(sql.statements)}
        assert all(count > 0 for count in observed.calls.values()) and sql.authorizations > 0
        Path(database + ".restore-" + complete["round"] + ".report.json").write_text(json.dumps(complete, indent=2) + "\n")
        print("PYTHON_RESTORATION_COMPLETE=" + json.dumps(complete, sort_keys=True), flush=True)
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
