"""#236: reject original-version defects before customer hooks or provider I/O."""
import pytest

from teaql.core.meta import EntityDescriptor, PropertyDescriptor
from teaql.core.mutation import DeleteCommand, MutationRequest, RecoverCommand, UpdateCommand
from teaql.core.value import DataType, Value
from teaql.runtime import (
    DelegatingMutationPolicyRegistry, MutationDecision, MutationOperation,
    MutationOperationKind, MutationPlan, MutationPolicyIdentity, RuntimeModule,
)


MAX = (1 << 63) - 1
MIN = -(1 << 63)


def fixture():
    events = []

    class Checker:
        def check_and_fix(self, context, record, location, results):
            events.append("checker")

    class Policy:
        identity = MutationPolicyIdentity("version-admission", "1", "sha256:version-admission")

        def review(self, context, plan):
            events.append("policy")
            return MutationDecision.allowed()

    entity = (EntityDescriptor("VersionProbe")
              .property(PropertyDescriptor("id", DataType.I64).is_id())
              .property(PropertyDescriptor("version", DataType.I64).is_version())
              .property(PropertyDescriptor("name", DataType.Text)))
    context = RuntimeModule().schema_entity(entity).checker("VersionProbe", Checker()).into_context()
    context.with_mutation_policy_registry(DelegatingMutationPolicyRegistry(lambda _: Policy()))
    return context, events


@pytest.mark.parametrize("version", [0, -1, MIN, MAX, MAX + 1])
def test_invalid_update_rejects_before_checker_and_retains_input(version):
    context, events = fixture()
    command = UpdateCommand.new("VersionProbe", 7).expected_version(version).value("name", "pending")
    with pytest.raises(ValueError):
        context.check_and_fix_mutation(command)
    assert events == []
    assert command.values == {"name": Value.Text("pending")} and command.expected_version_val == version


@pytest.mark.parametrize("operation,version", [(MutationOperationKind.UPDATE, MAX),
    (MutationOperationKind.DELETE, -2), (MutationOperationKind.RECOVER, MIN)])
def test_plan_rejects_invalid_original_before_customer_policy(operation, version):
    context, events = fixture()
    plan = MutationPlan("invalid-version", "VersionProbe.saveGraph", "VersionProbe", "reject invalid original version", (
        MutationOperation(operation, "VersionProbe", Value.I64(7), version, {"name": Value.Text("pending")}),))
    with pytest.raises(ValueError):
        context.review_mutation_plan(plan)
    assert events == []


def test_legal_create_update_delete_recover_and_physical_delete_keep_their_roles():
    context, events = fixture()
    operations = (
        MutationOperation(MutationOperationKind.CREATE, "VersionProbe", Value.I64(1), None, {}),
        MutationOperation(MutationOperationKind.UPDATE, "VersionProbe", Value.I64(2), MAX - 1, {}),
        MutationOperation(MutationOperationKind.DELETE, "VersionProbe", Value.I64(3), MAX, {}),
        MutationOperation(MutationOperationKind.RECOVER, "VersionProbe", Value.I64(4), MIN + 2, {}),
        MutationOperation(MutationOperationKind.HARD_DELETE, "VersionProbe", Value.I64(5), MIN, {}),
    )
    context.review_mutation_plan(MutationPlan("legal-roles", "VersionProbe.saveGraph", "VersionProbe", "inspect legal roles", operations))
    assert events == ["policy"]


def test_whole_plan_is_admitted_before_policy_even_if_last_operation_is_invalid():
    context, events = fixture()
    plan = MutationPlan("whole-plan", "VersionProbe.saveGraph", "VersionProbe", "admit whole plan", (
        MutationOperation(MutationOperationKind.UPDATE, "VersionProbe", Value.I64(1), 1, {"name": Value.Text("valid")}),
        MutationOperation(MutationOperationKind.UPDATE, "VersionProbe", Value.I64(2), MAX, {"name": Value.Text("pending")}),))
    with pytest.raises(ValueError):
        context.review_mutation_plan(plan)
    assert events == []


def test_fix_cannot_change_an_admitted_command_to_an_exhausted_original():
    context, _ = fixture()
    command = UpdateCommand.new("VersionProbe", 1).expected_version(1).value("name", "pending")
    class Checker:
        def check_and_fix(self, context, record, location, results):
            command.expected_version_val = MAX
    class Registry:
        def checker(self, entity):
            return Checker()
    context.insert_resource("checker_registry", Registry())
    with pytest.raises(ValueError):
        context.check_and_fix_mutation(command)


@pytest.mark.asyncio
async def test_invalid_nested_native_batch_rejects_before_first_checker_or_provider(tmp_path):
    from teaql.core.mutation import InsertCommand
    from teaql.provider.sqlite import SimpleSchemaProvider, create_sqlite_service
    context, events = fixture()
    schema = SimpleSchemaProvider()
    schema.register_entity(context.entity("VersionProbe"))
    database = tmp_path / "must-not-open.sqlite"
    service = create_sqlite_service(str(database), schema)
    async def forbidden(*args):
        events.append("provider")
        raise AssertionError("invalid batch entered provider")
    service.transport.begin_sql = forbidden
    service.transport.execute_sql = forbidden
    service.transport.fetch_all_sql = forbidden
    service.next_id = forbidden
    async def audit(event):
        events.append("audit")
    context.send_audit_event = audit
    first = InsertCommand.new("VersionProbe").value("name", "would require ID")
    bad = UpdateCommand.new("VersionProbe", 2).expected_version(MAX).value("name", "pending")
    request = MutationRequest.Batch([MutationRequest.Insert(first, "create first"),
        MutationRequest.Batch([MutationRequest.Update(bad, "invalid last")], "nested last")], "admit complete native batch")
    try:
        with pytest.raises(ValueError):
            await service.mutate(context, request)
        assert events == [] and not database.exists()
        assert first.values == {"name": Value.Text("would require ID")}
        assert bad.values == {"name": Value.Text("pending")} and bad.expected_version_val == MAX
    finally:
        await service.close()
