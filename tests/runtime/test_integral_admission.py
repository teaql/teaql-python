"""#236: post-Fix integer admission is exact and independent of Python coercion."""
import json
from decimal import Decimal

import pytest

from teaql.core.meta import EntityDescriptor, PropertyDescriptor, RelationDescriptor
from teaql.core.mutation import InsertCommand, MutationRequest, UpdateCommand
from teaql.core.value import DataType, Value
from teaql.runtime import CheckException, ObjectLocation, RuntimeModule


def context(checker=None):
    entity = (EntityDescriptor("IntegralProbe")
        .property(PropertyDescriptor("required_long", DataType.I64))
        .property(PropertyDescriptor("unsigned_number", DataType.U64)))
    module = RuntimeModule().schema_entity(entity)
    if checker:
        module.checker("IntegralProbe", checker)
    return module.into_context()


@pytest.mark.parametrize("operation", ["insert", "update"])
@pytest.mark.parametrize("bad", [Decimal("12.75"), 2**63, -(2**63) - 1,
    12.0, "PRIVATE_INVALID_INTEGER", True, Decimal("NaN")])
def test_integral_admission_rejects_after_customer_fix_with_value_free_locations(operation, bad):
    observed = []
    class Break:
        def check_and_fix(self, ctx, record, location, results):
            observed.append(ctx.require_resource("fix_time"))
            record["required_long"] = Value.from_any(bad)
    ctx = context(Break())
    command = InsertCommand.new("IntegralProbe") if operation == "insert" else UpdateCommand.new("IntegralProbe", 1)
    command.value("required_long", 5)
    with pytest.raises(CheckException) as error:
        ctx.check_and_fix_mutation(command)
    violation, = error.value.violations
    assert violation.rule_id == "invalid_type"
    assert violation.entity_type == "IntegralProbe"
    assert violation.location.model_path == "required_long"
    assert violation.location.instance_path == "/requiredLong"
    wire = violation.to_wire()
    assert "inputValue" not in wire and "PRIVATE_INVALID_INTEGER" not in str(error.value)
    json.dumps(wire, allow_nan=False)
    assert len(observed) == 1 and ctx.get_resource("fix_time") is None


@pytest.mark.parametrize("bad", [-1, 2**64, Decimal("1.5"), 1.0, True, "1"])
def test_integral_admission_unsigned_domain_is_checked(bad):
    with pytest.raises(CheckException):
        context().check_and_fix_mutation(InsertCommand.new("IntegralProbe").value("unsigned_number", bad))


def test_integral_admission_fix_repair_and_sparse_null_are_preserved():
    class Repair:
        def check_and_fix(self, ctx, record, location, results):
            record["required_long"] = Value.Decimal(Decimal("9223372036854775807"))
    command = InsertCommand.new("IntegralProbe").value("required_long", Decimal("12.75"))
    context(Repair()).check_and_fix_mutation(command)
    assert command.values["required_long"].val == Decimal(2**63 - 1)
    context().check_and_fix_record("IntegralProbe", {})
    context().check_and_fix_record("IntegralProbe", {"required_long": Value.Null()})
    context().check_and_fix_record("IntegralProbe", {"required_long": Value.I64(-(2**63)),
        "unsigned_number": Value.U64(2**64 - 1)})


def test_integral_admission_nested_location_is_canonical():
    with pytest.raises(CheckException) as error:
        context().check_and_fix_record_at("IntegralProbe", {"required_long": Value.Decimal(Decimal("1.5"))},
            ObjectLocation().property("line_items").index(2))
    assert error.value.violations[0].location.model_path == "line_items[2].required_long"
    assert error.value.violations[0].location.instance_path == "/lineItems/2/requiredLong"


@pytest.mark.parametrize("field,bad", [("integer_count", 2**31), ("integer_count", -(2**31) - 1),
    ("integer_count", Decimal("2147483648")), ("parent_record", -1), ("parent_record", Decimal("1.5")),
    ("parent_record", 1.0), ("parent_record", True), ("parent_record", "PRIVATE_BAD_REFERENCE")])
@pytest.mark.parametrize("operation", ["insert", "update"])
def test_integral_admission_integer_width_and_references(field, bad, operation):
    descriptor = (EntityDescriptor("Child")
        .property(PropertyDescriptor("integer_count", DataType.I64).integer32())
        .property(PropertyDescriptor("parent_record", DataType.I64))
        .relation(RelationDescriptor("parent_record", "Parent").local("parent_record").foreign("id")))
    ctx = RuntimeModule().schema_entity(descriptor).into_context()
    command = InsertCommand.new("Child") if operation == "insert" else UpdateCommand.new("Child", 1)
    command.value(field, bad)
    with pytest.raises(CheckException) as error:
        ctx.check_and_fix_mutation(command)
    assert error.value.violations[0].location.model_path == field
    ctx.check_and_fix_record("Child", {"integer_count": Value.I64(-(2**31)), "parent_record": Value.I64(2**63 - 1)})


@pytest.mark.asyncio
@pytest.mark.parametrize("operation", ["insert", "update"])
async def test_integral_admission_direct_provider_never_begins_or_reserves_id(tmp_path, operation):
    from teaql.provider.sqlite import SimpleSchemaProvider, create_sqlite_service
    ctx = context()
    schema = SimpleSchemaProvider()
    schema.register_entity(ctx.entity("IntegralProbe"))
    database = tmp_path / "must-not-exist.sqlite"
    service = create_sqlite_service(str(database), schema)
    calls = []
    async def forbidden(*args, **kwargs):
        calls.append("I/O")
        raise AssertionError("invalid integral entered the provider")
    service.transport.begin_sql = forbidden
    service.transport.execute_sql = forbidden
    service.transport.fetch_all_sql = forbidden
    service.next_id = forbidden
    command = InsertCommand.new("IntegralProbe") if operation == "insert" else UpdateCommand.new("IntegralProbe", 1)
    command.value("required_long", Decimal("12.75"))
    try:
        with pytest.raises(CheckException):
            await service.mutate(ctx, MutationRequest(command, "reject invalid integral"))
        assert calls == [] and not database.exists()
    finally:
        await service.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["original", "wrong_type", "not_new", "introduced_by_fix", "changed_id_by_fix"])
async def test_integral_admission_pending_reference_is_typed_owned_and_frozen_before_fix(mode):
    from teaql.core.entity import EntityKey, EntityRoot
    class Parent:
        id = None
        def __init__(self):
            self._entity_root = EntityRoot()
            self._entity_root.mark_as_new(self._teaql_entity_key())
        def _teaql_entity_key(self):
            return EntityKey("Parent", -1)
    class Other(Parent):
        pass
    parent = Other() if mode == "wrong_type" else Parent()
    if mode == "not_new":
        parent._entity_root = EntityRoot()
    descriptor = (EntityDescriptor("Child")
        .property(PropertyDescriptor("parent_record", DataType.I64))
        .relation(RelationDescriptor("parent_record", "Parent").local("parent_record").foreign("id")))
    class Fix:
        def check_and_fix(self, ctx, record, location, results):
            if mode == "introduced_by_fix":
                record["parent_record"] = Value.Object(parent)
            elif mode == "changed_id_by_fix":
                parent.id = -1
    ctx = RuntimeModule().entity(Parent).schema_entity(descriptor).checker("Child", Fix()).into_context()
    class NoProvider:
        async def begin(self, *_):
            raise AssertionError("this preparation probe must never begin")
    ctx.insert_resource("dataService", NoProvider())
    command = InsertCommand.new("Child").value("parent_record", 1) if mode == "introduced_by_fix" else (
        InsertCommand.new("Child").value("parent_record", Value.Object(parent)))
    class Prepared(Exception):
        pass
    async def prepare(graph):
        graph.context.check_and_fix_mutation(command)
        raise Prepared()
    async def work(graph):
        raise AssertionError("this preparation probe must never execute")
    with pytest.raises(Prepared if mode == "original" else CheckException):
        await ctx.execute_graph_save(work, prepare=prepare, comment="validate owned pending reference")
