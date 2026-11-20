"""Approve a vendor application through independently selected Context capabilities."""

import asyncio
import json
from pathlib import Path
import sys

from E import E
from Q import Q
from runtime_module import GENERATED_RUNTIME_MODULE
from teaql.core.value import Value
from teaql.provider.sqlite import create_sqlite_service
from teaql.runtime import UserContext
from teaql.runtime.i18n import CheckException, CheckResult


class SupplierReadPolicy:
    def __init__(self):
        self.denied = False
        self.calls = []

    def apply(self, query):
        self.calls.append(query.entity)
        if self.denied and query.entity == "VendorApplication":
            raise PermissionError("the principal cannot review supplier applications")


class SupplierNameCheck:
    def __init__(self, generated):
        self.generated = generated
        self.repaired = 0
        self.denied = 0

    def check_and_fix(self, context, record, location, results):
        self.generated.check_and_fix(context, record, location, results)
        if "legal_name" not in record:
            return
        name = record["legal_name"].try_text()
        if name is None:
            return
        canonical = " ".join(name.split())
        if not canonical:
            self.denied += 1
            results.append(CheckResult("required", "legal_name"))
        elif canonical != name:
            self.repaired += 1
            record["legal_name"] = Value.Text(canonical)


class SupplierCheckers:
    def __init__(self, generated):
        self.generated = generated
        self.supplier = SupplierNameCheck(generated.checker("VendorApplication"))

    def checker(self, entity):
        if entity == "VendorApplication":
            return self.supplier
        return self.generated.checker(entity)


class SchemaOnly:
    def __init__(self, service):
        self.service = service
        self.calls = 0

    async def _ensure_schema(self, context, capability):
        self.calls += 1
        await self.service._ensure_schema(context, capability)


class SupplierAudit:
    def __init__(self):
        self.events = []

    def on_safe_event(self, context, event):
        self.events.append(event)


class Operation:
    def __init__(self, operation):
        self.name = operation.name
        self.outcome = None

    def success(self, attributes=None):
        self.outcome = "success"

    def failure(self, error):
        self.outcome = "failure"


class SupplierTelemetry:
    def __init__(self):
        self.events = []
        self.outage = False

    def start(self, operation):
        if self.outage:
            raise OSError("the review telemetry sink is unavailable")
        scope = Operation(operation)
        self.events.append(scope)
        return scope


class ReviewDeskIds:
    def __init__(self, initial_floor):
        self.level = initial_floor
        self.calls = []
        self.lock = asyncio.Lock()

    async def next_id(self, entity):
        async with self.lock:
            self.level += 1
            self.calls.append((entity, self.level))
            return self.level

    async def ensure_id_floor(self, entity, floor):
        async with self.lock:
            self.level = max(self.level, floor)


async def prepare(caller, reference, name):
    application = await Q.vendor_applications().comment("Prepare a vendor application").purpose(
        "Review the supplier's legal identity").new_entity(caller)
    return application.update_platform(1).update_reference(reference).update_legal_name(name)


async def find(caller, reference):
    return await Q.vendor_applications().with_reference_is(reference).limit(1).comment(
        "Read the supplier application").purpose("Confirm the reviewed identity").execute_for_one(caller)


async def main(database, phase):
    service = create_sqlite_service(str(database))
    try:
        caller = UserContext.new().install(GENERATED_RUNTIME_MODULE).insert_resource("dataService", service)
        caller.disable_sql_log()
        schema = SchemaOnly(service)
        caller.with_schema_provider(schema)
        assert not hasattr(schema, "query") and not hasattr(schema, "mutate")
        await caller.ensure_schema()
        await caller.ensure_schema()
        assert schema.calls == 2

        accepted_id, reference, name = ((700, "SUP-700", "Cedar Valve Works") if phase == "first"
                                        else (710, "SUP-710", "Harbor Parts Supply"))
        ids = ReviewDeskIds(accepted_id - 1)
        policy, audit, telemetry = SupplierReadPolicy(), SupplierAudit(), SupplierTelemetry()
        checker = SupplierCheckers(caller.get_resource("checker_registry"))
        caller.with_request_policy(policy).with_checker_registry(checker).with_app_audit_event_sink(
            audit).with_runtime_telemetry(telemetry).with_internal_id_allocator(ids)

        raw_name = name.replace(" ", "  ")
        application = await prepare(caller, reference, raw_name)
        assert application.id == accepted_id
        await application.audit_as("Approve the supplier application").save(caller)
        found = await find(caller, reference)
        assert found is not None and (found.id, found.version) == (accepted_id, 1)
        assert E.vendor_application(found).legal_name().eval() == name

        denied = await prepare(caller, "REJECTED-" + reference, "   ")
        try:
            await denied.audit_as("Reject a supplier application without a legal name").save(caller)
        except CheckException as failure:
            assert any(v.rule_id == "required" and v.location.model_path == "legal_name"
                       for v in failure.violations)
        else:
            raise AssertionError("The nameless supplier application reached storage")
        assert await find(caller, denied.reference) is None
        assert checker.supplier.repaired == checker.supplier.denied == 1
        assert ids.calls == [("VendorApplication", accepted_id), ("VendorApplication", accepted_id + 1)]
        assert len(audit.events) == 1
        written = audit.events[0]
        assert (written.entity, int(written.entity_id)) == ("VendorApplication", accepted_id)

        policy.denied = True
        prior_operations = len(telemetry.events)
        try:
            await find(caller, reference)
        except PermissionError as failure:
            assert str(failure) == "the principal cannot review supplier applications"
        else:
            raise AssertionError("An unauthorized vendor lookup succeeded")
        assert len(telemetry.events) == prior_operations

        policy.denied = False
        telemetry.outage = True
        # Optional telemetry can be unavailable while the same read still succeeds.
        retained = await find(caller, reference)
        assert retained is not None and retained.id == accepted_id
        if phase == "restart":
            previous = await find(caller, "SUP-700")
            assert previous is not None and (previous.id, previous.legal_name) == (700, "Cedar Valve Works")

        outcomes = [(item.name, item.outcome) for item in telemetry.events]
        assert [outcome for operation, outcome in outcomes if operation == "graph.save"] == ["success", "failure"]
        assert ("VendorApplication.audit", "success") in outcomes
        assert ("VendorApplication.list", "success") in outcomes
        assert policy.calls == ["VendorApplication"] * (4 if phase == "first" else 5)
        print("VENDOR_REGISTRATION=" + json.dumps(dict(
            phase=phase, id=accepted_id, reference=reference, legalName=name,
            schemaCalls=schema.calls, checkerCalls=[checker.supplier.repaired, checker.supplier.denied],
            allocatorCalls=ids.calls, auditIds=[int(written.entity_id)], policyCalls=len(policy.calls),
            deniedReadBeforeExecution=True, telemetryOutcomes=outcomes, readDuringTelemetryOutage=True,
        )))
    finally:
        await service.close()


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[2] not in {"first", "restart"}:
        raise SystemExit("Usage: main.py DATABASE {first|restart}")
    asyncio.run(main(Path(sys.argv[1]), sys.argv[2]))
