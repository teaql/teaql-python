"""Eight naming vectors through generated APIs, real SQLite and graph rollback.

Raw ledger access and the SQLite authorizer below are explicit fault injection,
not application API discovery or a substitute for the generated Q/E APIs.
"""
import asyncio
from collections import Counter
from decimal import Decimal
import json
import os
from pathlib import Path
import sqlite3
from uuid import uuid4

import aiosqlite
from E import E, TeaQLNotLoadedError
from Q import Q
from main import new_probe
from json_roundtrip import ObservedService
from models.scalar_type_probe import ScalarTypeProbe
from models.type_platform import TypePlatform
from runtime_module import GENERATED_RUNTIME_MODULE
from teaql.core.value import Value
from teaql.data_service import SQLiteTeaQLClient
from teaql.provider.sqlite._decimal import DecimalConnection
from teaql.provider.sqlite.transport import SqliteTransport
from teaql.sql.executor import TransportError
from teaql.runtime import (CheckException, DelegatingMutationPolicyRegistry, EntityJSONError,
                           JsonFieldNamingProfile, MutationDecision, MutationPolicyIdentity, UserContext)


class Observations:
    def __init__(self):
        self.authorizations = 0
        self.statements = Counter()
        self.update_attempts = 0
        self.deny_second_update = False

    def authorize(self, action, table, column, database, source):
        self.authorizations += 1
        if action == sqlite3.SQLITE_UPDATE and table == "scalar_type_probe_data" and column == "required_string":
            self.update_attempts += 1
            if self.deny_second_update and self.update_attempts == 2:
                return sqlite3.SQLITE_DENY
        return sqlite3.SQLITE_OK

    def trace(self, statement):
        # Keep counters, not expanded statements or customer values.
        words = statement.lstrip().split(None, 2)
        if words:
            self.statements[words[0].upper()] += 1


class ObservedTransport(SqliteTransport):
    def __init__(self, database, observations):
        super().__init__(database)
        self.observations = observations

    def _connect(self):
        observations = self.observations
        class Connection(DecimalConnection):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.set_authorizer(observations.authorize)
                self.set_trace_callback(observations.trace)

            def execute(self, *args, **kwargs):
                # Reinstalling the authorizer expires cached prepared statements.
                # Do not let statement reuse bypass the second-write fault.
                self.set_authorizer(observations.authorize)
                return super().execute(*args, **kwargs)
        return aiosqlite.connect(self.db_path, factory=Connection)


class CheckerRecorder:
    def __init__(self, original):
        self.original, self.records = original, []

    def checker(self, entity):
        original, records = self.original.checker(entity), self.records
        if original is None:
            return None
        class Checker:
            def check_and_fix(self, context, record, location, results):
                records.append((entity, tuple(sorted(record))))
                original.check_and_fix(context, record, location, results)
        return Checker()


class PolicyRecorder:
    identity = MutationPolicyIdentity("canonical-name-probe", "1", "sha256:canonical-name-probe")

    def __init__(self):
        self.plans = []

    def review(self, context, plan):
        self.plans.append(plan)
        return MutationDecision.allowed()


class AuditRecorder:
    def __init__(self):
        self.events = []

    async def on_safe_event(self, context, event):
        self.events.append(event)


class ObservedGraphService(ObservedService):
    async def begin(self, *args, **kwargs):
        transaction = await super().begin(*args, **kwargs)
        observed = ObservedService(transaction)
        observed.calls = self.calls
        return observed


def pending(row):
    return dict(dict(row._entity_root.current_change_set().changes()).get(row._teaql_entity_key(), {}))


def raw(value):
    return value.val if isinstance(value, Value) else value


async def load(context, identity, *, forward=False):
    query = Q.scalar_type_probes().with_id_is(identity).limit(1)
    if forward:
        query = query.select_type_platform_with(Q.type_platforms().limit(1))
    return await (query.comment("reload canonical naming probe")
                  .purpose("verify generated mutation and hydration").execute_for_one(context))


def assert_not_loaded(operation):
    try:
        operation()
    except TeaQLNotLoadedError:
        return
    raise AssertionError("missing projection became loaded")


async def main():
    database = os.environ["TEAQL_SCALAR_PROBE_DB"] + ".names.sqlite"
    observations = Observations()
    client = SQLiteTeaQLClient(database)
    client.transport = ObservedTransport(database, observations)
    observed = ObservedGraphService(client)
    context = UserContext().install(GENERATED_RUNTIME_MODULE).insert_resource("dataService", observed)
    checker = CheckerRecorder(context.get_resource("checker_registry"))
    policy, audit = PolicyRecorder(), AuditRecorder()
    context.with_checker_registry(checker)
    context.with_mutation_policy_registry(DelegatingMutationPolicyRegistry(lambda _: policy))
    context.with_app_audit_event_sink(audit)
    marker = "canonical-" + uuid4().hex
    cases = []
    try:
        await context.ensure_schema()
        parents = []
        for suffix in ("original", "replacement"):
            parent = ((await Q.type_platforms().comment("prepare canonical naming parent")
                      .purpose("verify relation identity").new_entity(context)))
            parent.update_name(marker + "-" + suffix)
            await parent.audit_as("create canonical naming parent").save(context)
            parents.append(parent)
        rows = [(await new_probe(context, marker + "-" + suffix, Decimal("3.50"))) for suffix in ("first", "second")]
        for row in rows:
            row.update_type_platform(TypePlatform.refer(parents[0].id))
            values = pending(row)
            assert "required_string" in values and "requiredString" not in values
            assert "type_platform" in values and "type_platform_id" not in values and "typePlatform" not in values
            await row.audit_as("create canonical naming row").save(context)
        cases.append({"case": "NAME-01", "canonicalScalar": True})
        first = await load(context, rows[0].id, forward=True)
        first.update_type_platform(TypePlatform.refer(parents[1].id))
        assert raw(pending(first)["type_platform"]) == parents[1].id
        assert "type_platform_id" not in pending(first) and "typePlatform" not in pending(first)
        assert_not_loaded(lambda: E.scalar_type_probe(first).type_platform().name().eval())
        await first.audit_as("change canonical forward identity").save(context)
        cases.append({"case": "NAME-02", "createAndUpdate": True, "invalidatedOldDetail": True})

        namespace_checks = []
        bad_fields = [
            ("storage-alias", {"type_platform_id": parents[0].id}),
            ("native-alias", {"typePlatform": parents[0].id}),
            ("scalar-alias", {"requiredString": "PRIVATE_BAD_ALIAS"}),
            ("unknown", {"unknown_field": "PRIVATE_BAD_UNKNOWN"}),
            ("duplicate-equal", {"type_platform": parents[0].id, "type_platform_id": parents[0].id}),
            ("duplicate-unequal", {"type_platform": parents[0].id, "type_platform_id": parents[1].id}),
        ]
        for operation in ("create", "update"):
            for name, fields in bad_fields:
                candidate = ((await new_probe(context, marker, Decimal("3.50"))) if operation == "create"
                             else await load(context, rows[0].id))
                for field, value in fields.items():
                    candidate._entity_root.set(candidate._teaql_entity_key(), field, Value.from_any(value))
                before = (dict(observed.calls), observations.authorizations, len(checker.records), len(policy.plans), len(audit.events))
                try:
                    await candidate.audit_as("reject malformed canonical mutation fields").save(context)
                except CheckException as error:
                    assert any(item.rule_id == "unknown_field" for item in error.violations)
                    assert "PRIVATE_BAD" not in str(error)
                else:
                    raise AssertionError("generated save dropped malformed ledger keys: " + operation + "/" + next(iter(fields)))
                assert before == (dict(observed.calls), observations.authorizations, len(checker.records), len(policy.plans), len(audit.events))
                namespace_checks.append(operation + "/" + name)
        for operation in ("create", "update"):
            candidate = ((await new_probe(context, marker, Decimal("3.50"))) if operation == "create"
                         else await load(context, rows[0].id))
            candidate.update_required_string(None)
            before = (dict(observed.calls), observations.authorizations, len(audit.events))
            try:
                await candidate.audit_as("reject canonical required value").save(context)
            except CheckException as error:
                assert any(item.rule_id == "required" and item.location.model_path == "required_string"
                           and item.location.instance_path == "/requiredString" for item in error.violations)
            else:
                raise AssertionError("required canonical field was accepted")
            assert before == (dict(observed.calls), observations.authorizations, len(audit.events))
        assert all("type_platform_id" not in keys and "requiredString" not in keys for _, keys in checker.records)
        assert any(entity == "ScalarTypeProbe" and {"type_platform", "required_string"}.issubset(keys)
                   for entity, keys in checker.records)
        assert observations.authorizations > 0 and observations.statements["INSERT"] > 0
        cases.append({"case": "NAME-03", "namespaceRejections": len(namespace_checks), "namespaceChecks": namespace_checks,
                      "requiredRejections": 2, "rejectionProviderCalls": dict(query=0, mutate=0, begin=0, next_id=0),
                      "rejectionSQLiteAuthorizations": 0, "beforeCheckerAndPolicy": True})

        with sqlite3.connect(database) as connection:
            columns = [item[1] for item in connection.execute("PRAGMA table_info(scalar_type_probe_data)")]
            physical = connection.execute("SELECT version,type_platform,required_string FROM scalar_type_probe_data WHERE id=?", [first.id]).fetchone()
        assert "type_platform" in columns and "type_platform_id" not in columns and "required_string" in columns
        assert physical == (2, parents[1].id, marker + "-first")
        cases.append({"case": "NAME-04", "physicalColumns": columns, "logicalForeignColumn": "type_platform"})
        first = await load(context, first.id, forward=True)
        assert E.scalar_type_probe(first).type_platform().id().eval() == parents[1].id
        assert E.scalar_type_probe(first).type_platform().name().eval() == marker + "-replacement"
        assert E.scalar_type_probe(first).optional_string().eval() is None
        sparse = await (Q.scalar_type_probes_minimal().with_id_is(first.id).select_required_string().limit(1)
                        .comment("read canonical sparse projection").purpose("verify loaded state").execute_for_one(context))
        before = dict(observed.calls)
        assert_not_loaded(lambda: E.scalar_type_probe(sparse).optional_string().eval())
        assert observed.calls == before
        cases.append({"case": "NAME-05", "loadedNullAndNotLoaded": True, "foreignIdentity": str(parents[1].id)})
        cases.append({"case": "NAME-06", "nativeGeneratedQEMutation": True})
        for profile in JsonFieldNamingProfile:
            wire = first.to_json(profile=profile)
            document = json.loads(wire)
            relation_name = profile.render("type_platform")
            # An explicitly selected target is a typed nested document, not a
            # scalar reference. Its identity still uses the same wire profile.
            assert document[relation_name][profile.render("id")] == str(parents[1].id)
            assert document[profile.render("required_string")] == marker + "-first"
            assert "type_platform_id" not in document
            decoded = ScalarTypeProbe.from_json(wire, profile=profile)
            assert E.scalar_type_probe(decoded).type_platform().id().eval() == parents[1].id
            duplicate = wire.rstrip()[:-1] + "," + json.dumps(relation_name) + ":" + json.dumps(document[relation_name]) + "}"
            try:
                ScalarTypeProbe.from_json(duplicate, profile=profile)
            except EntityJSONError as error:
                assert error.code == "WIRE_FIELD_COLLISION" and error.location.model_path == "type_platform"
            else:
                raise AssertionError("equal JSON field collision was accepted")
        cases.append({"case": "NAME-07", "defaultWire": ["requiredString", "typePlatform"],
                      "profiles": 3, "equalCollisionRejected": True, "typedTargetPreserved": True})

        # Return the first child to its original parent; both children then belong
        # to one loaded graph. The first child has version 3 before the graph edit.
        first.update_type_platform(TypePlatform.refer(parents[0].id))
        await first.audit_as("restore canonical graph membership").save(context)
        graph = await (Q.type_platforms().with_id_is(parents[0].id).limit(1)
                       .select_scalar_type_probe_list_with(Q.scalar_type_probes().order_by_id_ascending().limit(2))
                       .comment("load canonical two-child mutation graph")
                       .purpose("verify atomic rollback and retry").execute_for_one(context))
        children = list(graph.scalar_type_probe_list())
        assert len(children) == 2 and {item.id for item in children} == {item.id for item in rows}
        versions = {item.id: item.version for item in children}
        expected = {child.id: marker + "-graph-" + str(index) for index, child in enumerate(children)}
        for index, child in enumerate(children):
            child.update_required_string(expected[child.id])
            child.audit_as("canonical child update")
            assert set(pending(child)) == {"required_string"}
        observations.update_attempts = 0
        observations.deny_second_update = True
        before_sql, before_audit = observations.statements.copy(), len(audit.events)
        try:
            await graph.audit_as("save canonical two-child graph").save(context)
        except TransportError as error:
            assert isinstance(error.__cause__, sqlite3.DatabaseError)
        else:
            raise AssertionError("second real SQLite update did not fail")
        finally:
            observations.deny_second_update = False
        assert observations.update_attempts == 2
        assert observations.statements["UPDATE"] - before_sql["UPDATE"] == 1
        assert observations.statements["ROLLBACK"] - before_sql["ROLLBACK"] == 1
        assert len(audit.events) == before_audit
        for child in children:
            unchanged = await load(context, child.id)
            assert unchanged.version == versions[child.id]
            assert E.scalar_type_probe(unchanged).required_string().eval() != raw(pending(child)["required_string"])
        assert all("required_string" in pending(child) for child in children)
        before_audit = len(audit.events)
        await graph.audit_as("save canonical two-child graph").save(context)
        committed = audit.events[before_audit:]
        assert len(committed) == 2 and {raw(event.entity_id) for event in committed} == set(versions)
        for event in committed:
            assert event.entity == "ScalarTypeProbe" and "required_string" in {item.field for item in event.fields}
            assert "type_platform_id" not in {item.field for item in event.fields}
            assert any(node.comment == "canonical child update" for node in event.trace_chain)
        for child in children:
            changed = await load(context, child.id)
            assert changed.version == versions[child.id] + 1 and not pending(child)
            assert E.scalar_type_probe(changed).required_string().eval() == expected[child.id]
            assert E.scalar_type_probe(changed).type_platform_id().eval() == parents[0].id
        assert all("type_platform_id" not in operation.changed_values and "requiredString" not in operation.changed_values
                   for plan in policy.plans for operation in plan.operations)
        cases.append({"case": "NAME-08", "firstUpdateRolledBack": True, "failedAuditCount": 0,
                      "pendingIntentRetained": True, "retryAudits": 2, "typedTargets": True,
                      "canonicalPolicyAndAudit": True, "versionsBefore": {str(k): v for k, v in versions.items()},
                      "rollbackSQL": dict(attempts=2, executedUpdates=1, rollbacks=1)})
        assert [item["case"] for item in cases] == ["NAME-" + str(i).zfill(2) for i in range(1, 9)]
        report = dict(schema="teaql.python-generated-canonical-name-example/v1", passed=True, cases=cases,
                      childIds=[str(row.id) for row in rows], parentIds=[str(parent.id) for parent in parents],
                      providerCalibrated=all(observed.calls[key] > 0 for key in ("query", "mutate", "begin", "next_id")),
                      calibratedProviderMethods=sorted(observed.calls), successfulProviderCalls=dict(observed.calls),
                      sqliteAuthorizerCalibrated=observations.authorizations > 0,
                      physicalSchemaCrossRuntimeAccepted=False)
        report_path = Path(database + "." + uuid4().hex + ".report.json")
        report_path.write_text(json.dumps(report, indent=2) + "\n")
        print("PYTHON_CANONICAL_NAME=" + json.dumps(report))
    finally:
        await observed.close()


if __name__ == "__main__":
    asyncio.run(main())
