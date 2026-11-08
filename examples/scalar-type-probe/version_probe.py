"""Checked versions through generated Q/E/JSON and audited graph saves.

Direct SQL is used only to inject signed-64 boundary fixtures and to read an
independent physical oracle. Application operations use generated APIs.
"""
import asyncio
from decimal import Decimal
import json
import os
import sqlite3
from uuid import uuid4

from E import E
from Q import Q
from main import new_probe
from models.scalar_type_probe import ScalarTypeProbe
from name_probe import (AuditRecorder, CheckerRecorder, Observations, ObservedGraphService,
                        ObservedTransport, PolicyRecorder, pending)
from runtime_module import GENERATED_RUNTIME_MODULE
from teaql.core import MutationVersionError
from teaql.data_service import SQLiteTeaQLClient
from teaql.runtime import DelegatingMutationPolicyRegistry, JsonFieldNamingProfile, UserContext


MAX = (1 << 63) - 1
MIN = -(1 << 63)


async def load(context, identity):
    return await (Q.scalar_type_probes().with_id_is(identity).limit(1)
        .comment("load a signed-version boundary fixture")
        .purpose("verify generated version lifecycle").execute_for_one(context))


async def main():
    database = os.environ["TEAQL_SCALAR_PROBE_DB"]
    round_number = int(os.environ["TEAQL_PROBE_ROUND"])
    sql = Observations()
    client = SQLiteTeaQLClient(database)
    client.transport = ObservedTransport(database, sql)
    observed, policy, audit = ObservedGraphService(client), PolicyRecorder(), AuditRecorder()
    context = (UserContext().install(GENERATED_RUNTIME_MODULE).insert_resource("dataService", observed)
        .with_mutation_policy_registry(DelegatingMutationPolicyRegistry(lambda _: policy))
        .with_app_audit_event_sink(audit))
    checker = CheckerRecorder(context.get_resource("checker_registry"))
    context.with_checker_registry(checker)
    marker = "version-" + uuid4().hex
    cases, maximum_probe_ids, minimum_probe_ids = [], [], []

    def record(case, **details):
        value = {"case": case, "passed": True, **details}
        cases.append(value)
        print("PYTHON_VERSION_CASE=" + json.dumps(value, sort_keys=True), flush=True)

    def counters():
        return (dict(observed.calls), len(policy.plans), len(audit.events), len(checker.records),
                sql.authorizations, dict(sql.statements))

    def inject(table, identity, version):
        assert table in ("scalar_type_probe_data", "type_platform_data")
        with sqlite3.connect(database) as connection:
            connection.execute("UPDATE " + table + " SET version=? WHERE id=?", [version, identity])

    async def rejected(entity, reason, code):
        before, saved_pending, original = counters(), pending(entity), entity.version
        try:
            await entity.audit_as(reason).save(context)
            raise AssertionError("invalid original version reached persistence")
        except MutationVersionError as error:
            assert error.code == code
        assert counters() == before and pending(entity) == saved_pending and entity.version == original

    async def graph(identity):
        return await (Q.type_platforms().with_id_is(identity).limit(1)
            .select_scalar_type_probe_list_with(Q.scalar_type_probes().order_by_id_ascending().limit(2))
            .comment("load the bounded version-admission graph")
            .purpose("check every changed child before the first Fix").execute_for_one(context))

    try:
        await context.ensure_schema()
        await context.ensure_schema()
        independent = (await new_probe(context, marker + "-independent-pending", Decimal("2.00")))
        independent_before = pending(independent)
        for index, note in enumerate((None, "retained note")):
            row = (await new_probe(context, marker + "-live-" + str(index), Decimal("3.50")))
            row.update_optional_string(note)
            await row.audit_as("create a generated live version fixture").save(context)
            inject("scalar_type_probe_data", row.id, MAX - 1)
            row = await load(context, row.id)
            row.update_required_string(marker + "-last-legal-" + str(index))
            await row.audit_as("execute the last representable generated update").save(context)
            assert E.scalar_type_probe(row).version().eval() == MAX
            assert E.scalar_type_probe(row).optional_string().eval() == note
            for profile in JsonFieldNamingProfile:
                wire = row.to_json(profile=profile)
                assert json.loads(wire)[profile.render("version")] == str(MAX)
                decoded = ScalarTypeProbe.from_json(wire, profile=profile)
                assert E.scalar_type_probe(decoded).version().eval() == MAX
            record("last-update-and-json", id=row.id, version=str(row.version), nullableNote=note is None)
            row.update_required_string(marker + "-must-remain-pending-" + str(index))
            await rejected(row, "reject an exhausted generated update", "VERSION_EXHAUSTED")
            assert independent.id is None and pending(independent) == independent_before
            actual = await load(context, row.id)
            assert actual.version == MAX and E.scalar_type_probe(actual).optional_string().eval() == note
            assert E.scalar_type_probe(actual).required_string().eval() == marker + "-last-legal-" + str(index)
            maximum_probe_ids.append(actual.id)
            record("exhaustion-preserves-intent", id=actual.id, zeroHooksAndProvider=True, independentPending=True)

            original = E.scalar_type_probe(actual).required_string().eval()
            actual.update_required_string("temporary no-op")
            actual.update_required_string(original)
            before = counters()
            await actual.audit_as("unchanged exhausted rows are not updates").save(context)
            assert counters() == before and actual.version == MAX
            record("unchanged-exhausted-noop", id=actual.id, zeroHooksAndProvider=True)

            deleted = (await new_probe(context, marker + "-delete-" + str(index), Decimal("4.50")))
            deleted.update_optional_string(note)
            await deleted.audit_as("create a generated deletion fixture").save(context)
            inject("scalar_type_probe_data", deleted.id, MAX)
            deleted = await load(context, deleted.id)
            await deleted.mark_for_deletion().audit_as("delete the maximum live version").save(context)
            assert deleted.version == MIN
            minimum_probe_ids.append(deleted.id)
            await rejected(deleted.mark_for_deletion(), "reject repeated tombstone deletion", "INVALID_VERSION_STATE")
            assert deleted._teaql_entity_key() in deleted._entity_root.deleted_keys()
            record("maximum-delete-and-repeat-rejection", id=deleted.id, version=str(deleted.version), nullableNote=note is None)

        parent = ((await Q.type_platforms().comment("prepare a version graph owner")
            .purpose("verify early graph-wide version admission").new_entity(context)))
        parent.update_name(marker + "-owner")
        await parent.audit_as("create the generated graph owner").save(context)
        children = []
        for index in range(2):
            child = (await new_probe(context, marker + "-child-" + str(index), Decimal("5.50")))
            child.update_type_platform(parent)
            await child.audit_as("create the generated graph child").save(context)
            children.append(child)
        inject("scalar_type_probe_data", children[0].id, MAX)
        owner = await graph(parent.id)
        loaded_children = list(owner.scalar_type_probe_list())
        assert len(loaded_children) == 2 and loaded_children[0].version == MAX
        owner.update_name(marker + "-real-owner-edit")
        loaded_children[0].update_required_string(marker + "-invalid-child-edit")
        await rejected(owner, "reject the last invalid graph member before any Fix", "VERSION_EXHAUSTED")
        assert pending(loaded_children[0])["required_string"].val == marker + "-invalid-child-edit"
        loaded_children[0].update_required_string(marker + "-child-0")
        loaded_children[1].update_optional_string("real surviving child edit")
        await owner.audit_as("retry the same graph with the exhausted child unchanged").save(context)
        assert owner.version == 2 and [child.version for child in loaded_children] == [MAX, 2]
        maximum_probe_ids.append(loaded_children[0].id)
        record("whole-graph-admission-and-same-graph-retry", parentId=owner.id,
               childIds=[child.id for child in loaded_children], unchangedMaximumChild=True)

        # A configured Fix can mutate another reached object. The second whole
        # admission pass must catch that new intent before IDs/transaction/policy.
        owner = await graph(parent.id)
        loaded_children = list(owner.scalar_type_probe_list())
        original_checker = checker.original
        class FixRegistry:
            def checker(self, entity):
                original = original_checker.checker(entity)
                if original is None:
                    return None
                class Fix:
                    def check_and_fix(self, ctx, values, location, results):
                        if entity == "TypePlatform":
                            loaded_children[0].update_required_string(marker + "-introduced-by-Fix")
                        original.check_and_fix(ctx, values, location, results)
                return Fix()
        context.with_checker_registry(FixRegistry())
        owner.update_name(marker + "-Fix-owner-edit")
        before_calls, before_policy, before_audit = dict(observed.calls), len(policy.plans), len(audit.events)
        try:
            await owner.audit_as("reject exhausted child intent introduced by Fix").save(context)
            raise AssertionError("Fix bypassed whole-graph admission")
        except MutationVersionError:
            pass
        assert dict(observed.calls) == before_calls and len(policy.plans) == before_policy and len(audit.events) == before_audit
        context.with_checker_registry(checker)
        record("post-Fix-graph-admission", parentId=owner.id, zeroProviderAndPolicy=True)

        untouched = ((await Q.type_platforms().comment("prepare an unchanged exhausted relation")
            .purpose("do not confuse reference loading with mutation").new_entity(context)))
        untouched.update_name(marker + "-unchanged-reference")
        await untouched.audit_as("create the reference-only parent").save(context)
        inject("type_platform_data", untouched.id, MAX)
        reference = await (Q.type_platforms().with_id_is(untouched.id).limit(1)
            .comment("load the exhausted reference")
            .purpose("keep its unchanged state outside mutation admission").execute_for_one(context))
        late_owner = await graph(untouched.id)
        late_owner.scalar_type_probe_list().append(independent)
        class LateFixRegistry:
            def checker(self, entity):
                original = checker.original.checker(entity)
                if original is None:
                    return None
                class Fix:
                    def check_and_fix(self, ctx, values, location, results):
                        if entity == "ScalarTypeProbe":
                            late_owner.update_name(marker + "-late-invalid-owner-edit")
                        original.check_and_fix(ctx, values, location, results)
                return Fix()
        context.with_checker_registry(LateFixRegistry())
        before_calls, before_policy, before_audit = dict(observed.calls), len(policy.plans), len(audit.events)
        try:
            await late_owner.audit_as("reject late parent intent before reserving the new child ID").save(context)
            raise AssertionError("late Fix intent bypassed complete pre-ID admission")
        except MutationVersionError:
            pass
        assert independent.id is None and dict(observed.calls) == before_calls
        assert len(policy.plans) == before_policy and len(audit.events) == before_audit
        context.with_checker_registry(checker)
        record("late-Fix-before-new-ID", parentId=late_owner.id, zeroProviderAndPolicy=True, childIdUnassigned=True)
        late_owner.update_name(E.type_platform(reference).name().eval())
        await late_owner.audit_as("save the repaired graph without updating its exhausted parent").save(context)
        assert independent.version == 1 and reference.version == MAX
        record("unchanged-reference-and-independent-ledger", parentId=reference.id, childId=independent.id)
        report = {"round": round_number, "cases": cases, "maximumProbeIds": maximum_probe_ids,
                  "minimumProbeIds": minimum_probe_ids, "maximumParentId": reference.id,
                  "graphParentId": parent.id, "allPassed": True}
        print("PYTHON_VERSION_LIFECYCLE=" + json.dumps(report, sort_keys=True), flush=True)
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
