"""#236 NAME-03: model-backed mutation keys are canonical before any hook."""
import pytest

from teaql.core.meta import EntityDescriptor, PropertyDescriptor, RelationDescriptor
from teaql.core.mutation import InsertCommand, UpdateCommand
from teaql.core.value import DataType, Value
from teaql.runtime import (
    CheckException, DelegatingMutationPolicyRegistry, MutationDecision,
    MutationOperation, MutationOperationKind, MutationPlan, MutationPolicyIdentity,
    RuntimeModule, UserContext,
)


BAD_FIELDS = [
    {"type_platform_id": Value.I64(1)},
    {"typePlatform": Value.I64(1)},
    {"requiredString": Value.Text("PRIVATE_BAD_ALIAS_VALUE")},
    {"unknown_field": Value.Text("PRIVATE_BAD_UNKNOWN_VALUE")},
    {"type_platform": Value.I64(1), "type_platform_id": Value.I64(1)},
    {"type_platform": Value.I64(1), "type_platform_id": Value.I64(2)},
]


class CheckerSpy:
    def __init__(self, add=None):
        self.calls = []
        self.add = add

    def check_and_fix(self, context, record, location, results):
        self.calls.append(dict(record))
        if self.add:
            record.update(self.add)


class PolicySpy:
    identity = MutationPolicyIdentity("canonical-fields", "1", "sha256:canonical-fields")

    def __init__(self):
        self.calls = []

    def review(self, context, plan):
        self.calls.append(plan)
        return MutationDecision.allowed()


def context(checker=None, policy=None):
    descriptor = (EntityDescriptor("NameProbe")
        .property(PropertyDescriptor("required_string", DataType.Text))
        .property(PropertyDescriptor("type_platform", DataType.I64))
        .relation(RelationDescriptor("type_platform", "Platform").local("type_platform").foreign("id")))
    module = RuntimeModule().schema_entity(descriptor)
    if checker:
        module.checker("NameProbe", checker)
    ctx = module.into_context()
    if policy:
        ctx.with_mutation_policy_registry(DelegatingMutationPolicyRegistry(lambda _: policy))
    return ctx


def command(operation, values):
    result = InsertCommand.new("NameProbe") if operation == "insert" else UpdateCommand.new("NameProbe", 1)
    for key, value in values.items():
        result.value(key, value)
    return result


def plan(values):
    return MutationPlan("namespace-check", "NameProbe.saveGraph", "NameProbe", "inspect canonical field vocabulary", (
        MutationOperation(MutationOperationKind.UPDATE, "NameProbe", Value.I64(1), 1, values),))


@pytest.mark.parametrize("operation", ["insert", "update"])
@pytest.mark.parametrize("values", BAD_FIELDS)
def test_canonical_mutation_fields_reject_alias_unknown_and_equal_duplicates_before_checker(operation, values):
    checker = CheckerSpy()
    ctx = context(checker)
    pending = command(operation, values)
    before = dict(pending.values)
    with pytest.raises(CheckException) as error:
        ctx.check_and_fix_mutation(pending)
    assert checker.calls == []
    assert pending.values == before  # No silent normalization, merge or key loss.
    assert all(item.rule_id == "unknown_field" and item.entity_type == "NameProbe" for item in error.value.violations)
    assert all(item.input_value is None for item in error.value.violations)
    assert "PRIVATE_BAD" not in str(error.value)


@pytest.mark.parametrize("operation", ["insert", "update"])
@pytest.mark.parametrize("field", ["type_platform_id", "requiredString"])
def test_canonical_mutation_fields_fix_cannot_introduce_a_noncanonical_key(operation, field):
    checker = CheckerSpy({field: Value.Text("PRIVATE_BAD_FIX_VALUE")})
    ctx = context(checker)
    with pytest.raises(CheckException) as error:
        ctx.check_and_fix_mutation(command(operation, {"required_string": Value.Text("valid")}))
    assert len(checker.calls) == 1
    assert error.value.violations[0].rule_id == "unknown_field"
    assert "PRIVATE_BAD" not in str(error.value)


@pytest.mark.parametrize("values", BAD_FIELDS)
def test_canonical_mutation_fields_reject_before_customer_policy(values):
    policy = PolicySpy()
    ctx = context(policy=policy)
    with pytest.raises(CheckException):
        ctx.review_mutation_plan(plan(values))
    assert policy.calls == []


@pytest.mark.asyncio
async def test_canonical_mutation_fields_reject_graph_preparation_before_transaction_and_retry():
    checker = CheckerSpy()
    ctx = context(checker)
    class Provider:
        begins = 0
        async def begin(self, context):
            self.begins += 1
            return self
        async def commit(self, context):
            pass
        async def rollback(self, context):
            pass
    provider = Provider()
    ctx.insert_resource("dataService", provider)
    async def prepare(graph):
        graph.context.preflight_mutation(command("insert", BAD_FIELDS[4]))
    async def forbidden(graph):
        raise AssertionError("malformed namespace entered work")
    with pytest.raises(CheckException):
        await ctx.execute_graph_save(forbidden, prepare=prepare, comment="reject malformed canonical fields")
    assert provider.begins == 0 and checker.calls == []
    async def retry(graph):
        return 7
    assert await ctx.execute_graph_save(retry, comment="retry after namespace rejection") == 7
    assert provider.begins == 1


def test_canonical_mutation_fields_preserve_model_keys_and_sparse_values():
    checker, policy = CheckerSpy(), PolicySpy()
    ctx = context(checker, policy)
    values = {"required_string": Value.Text("valid"), "type_platform": Value.I64(1)}
    pending = command("update", values)
    ctx.check_and_fix_mutation(pending)
    ctx.review_mutation_plan(plan(pending.values))
    assert checker.calls == [values] and len(policy.calls) == 1
    assert dict(policy.calls[0].operations[0].changed_values) == values
    ctx.check_and_fix_mutation(command("update", {}))


def test_canonical_mutation_fields_do_not_invent_a_model_for_legacy_contexts():
    ctx = UserContext()
    ctx.check_and_fix_mutation(command("insert", BAD_FIELDS[0]))
    ctx.review_mutation_plan(plan(BAD_FIELDS[0]))


def test_canonical_mutation_fields_are_entity_specific_not_a_global_suffix_ban():
    descriptor = EntityDescriptor("Counter").property(PropertyDescriptor("type_platform_id", DataType.I64))
    ctx = RuntimeModule().schema_entity(descriptor).into_context()
    ctx.check_and_fix_mutation(InsertCommand.new("Counter").value("type_platform_id", 1))


@pytest.mark.parametrize("key", [None, 1, ("PRIVATE_BAD_KEY",)])
def test_canonical_mutation_fields_nonstrings_have_a_value_free_root_location(key):
    with pytest.raises(CheckException) as error:
        context().check_and_fix_mutation(command("insert", {key: Value.Text("PRIVATE_BAD_VALUE")}))
    violation, = error.value.violations
    assert violation.rule_id == "unknown_field" and violation.location.instance_path == ""
    assert violation.input_value is None and "PRIVATE_BAD" not in str(error.value)


def test_canonical_mutation_fields_empty_legacy_descriptor_does_not_invent_fields():
    ctx = RuntimeModule().schema_entity(EntityDescriptor("NameProbe")).into_context()
    ctx.check_and_fix_mutation(command("insert", BAD_FIELDS[0]))


def test_canonical_mutation_fields_preserve_explicit_nested_location():
    from teaql.runtime import ObjectLocation
    with pytest.raises(CheckException) as error:
        context().check_and_fix_record_at("NameProbe", BAD_FIELDS[1], ObjectLocation().property("line_items").index(2))
    violation, = error.value.violations
    assert violation.location.model_path == "line_items[2].typePlatform"
    assert violation.location.instance_path == "/lineItems/2/typePlatform"


def test_canonical_mutation_fields_raw_ledger_admission_does_not_invoke_checker_or_policy():
    checker, policy = CheckerSpy(), PolicySpy()
    ctx = context(checker, policy)
    with pytest.raises(CheckException):
        ctx._validate_mutation_fields("NameProbe", BAD_FIELDS[0])
    assert checker.calls == [] and policy.calls == []
