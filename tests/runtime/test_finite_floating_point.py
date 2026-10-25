"""#236: trusted floating-point metadata is enforced after customer Fix."""
import json
from datetime import datetime, timezone

import pytest

from teaql.core.meta import EntityDescriptor, PropertyDescriptor
from teaql.core.mutation import InsertCommand, MutationRequest, UpdateCommand
from teaql.core.value import DataType, Value
from teaql.runtime import CheckException, ObjectLocation, RuntimeModule


def fixture(checker=None):
    descriptor = (EntityDescriptor("FloatProbe")
        .property(PropertyDescriptor("required_float", DataType.F64).required())
        .property(PropertyDescriptor("optional_double", "Double"))
        .property(PropertyDescriptor("text", DataType.Text)))
    module = RuntimeModule().schema_entity(descriptor)
    if checker is not None:
        module.checker("FloatProbe", checker)
    return module.into_context()


@pytest.mark.parametrize("operation", ["insert", "update"])
@pytest.mark.parametrize("field", ["required_float", "optional_double"])
@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -float("inf"), "NaN", "PRIVATE_FLOAT", True])
def test_invalid_floats_are_typed_canonical_value_free_failures(operation, field, bad):
    context = fixture()
    command = InsertCommand.new("FloatProbe") if operation == "insert" else UpdateCommand.new("FloatProbe", 1)
    command.value(field, bad)
    with pytest.raises(CheckException) as caught:
        context.check_and_fix_mutation(command)
    result, = caught.value.violations
    assert result.rule_id == "invalid_type"
    assert result.entity_type == "FloatProbe"
    assert result.location.model_path == field
    assert result.location.instance_path == "/" + ("requiredFloat" if field == "required_float" else "optionalDouble")
    wire = result.to_wire()
    assert "inputValue" not in wire, "nonfinite input must not be turned into fabricated JSON null"
    json.dumps(wire, allow_nan=False)
    assert "PRIVATE_FLOAT" not in str(caught.value)
    assert context.get_resource("fix_time") is None


def test_custom_fix_can_repair_a_nonfinite_value_before_metadata_admission():
    class Repair:
        def check_and_fix(self, context, record, location, results):
            record["required_float"] = Value.F64(1.25)
    context = fixture(Repair())
    command = InsertCommand.new("FloatProbe").value("required_float", float("nan"))
    context.check_and_fix_mutation(command)
    assert command.values["required_float"].val == 1.25


def test_custom_fix_cannot_introduce_an_unrepresentable_value():
    class Break:
        def check_and_fix(self, context, record, location, results):
            record["optional_double"] = Value.F64(float("inf"))
    with pytest.raises(CheckException) as caught:
        fixture(Break()).check_and_fix_mutation(InsertCommand.new("FloatProbe").value("required_float", 1.25))
    assert caught.value.violations[0].location.model_path == "optional_double"


def test_nested_location_null_absence_and_unrelated_text_are_preserved():
    context = fixture()
    record = {"required_float": Value.F64(float("nan")), "optional_double": Value.Null(), "text": Value.Text("Infinity")}
    location = ObjectLocation().property("line_items").index(2)
    with pytest.raises(CheckException) as caught:
        context.check_and_fix_record_at("FloatProbe", record, location)
    assert caught.value.violations[0].location.model_path == "line_items[2].required_float"
    assert caught.value.violations[0].location.instance_path == "/lineItems/2/requiredFloat"
    assert record["optional_double"].is_null() and record["text"].val == "Infinity"
    context.check_and_fix_record("FloatProbe", {"required_float": Value.F64(-0.0)})
    context.check_and_fix_record("FloatProbe", {})


def test_legacy_class_without_storage_metadata_is_not_a_scalar_schema():
    class Legacy:
        _name = "Legacy"
    RuntimeModule().entity(Legacy).into_context().check_and_fix_record("Legacy", {})


def test_unrepresentable_integer_is_not_silently_coerced_to_float():
    with pytest.raises(CheckException) as caught:
        fixture().check_and_fix_mutation(InsertCommand.new("FloatProbe").value("required_float", 10 ** 400))
    assert caught.value.violations[0].location.model_path == "required_float"


def test_finite_admission_does_not_read_another_business_clock():
    now, reads, observed = datetime(2026, 10, 25, tzinfo=timezone.utc), [], []
    class Clock:
        def now(self):
            reads.append(1)
            return now
    class Inspect:
        def check_and_fix(self, context, record, location, results):
            observed.append(context.get_resource("fix_time"))
    context = fixture(Inspect()).with_business_clock(Clock())
    context.check_and_fix_mutation(InsertCommand.new("FloatProbe").value("required_float", 1.5))
    assert reads == [1] and observed == [now]
    assert context.get_resource("fix_time") is None


@pytest.mark.asyncio
async def test_direct_provider_boundary_rejects_before_transport_begin_or_id(tmp_path):
    from teaql.provider.sqlite import SimpleSchemaProvider, create_sqlite_service
    context = fixture()
    descriptor = context.entity("FloatProbe")
    schema = SimpleSchemaProvider()
    schema.register_entity(descriptor)
    service = create_sqlite_service(str(tmp_path / "must-not-exist.sqlite"), schema)
    calls = []
    async def forbidden(*args, **kwargs):
        calls.append("I/O")
        raise AssertionError("invalid scalar crossed the provider boundary")
    service.transport.begin_sql = forbidden
    service.transport.execute_sql = forbidden
    service.transport.fetch_all_sql = forbidden
    service.next_id = forbidden
    try:
        with pytest.raises(CheckException):
            await service.mutate(context, MutationRequest(InsertCommand.new("FloatProbe")
                .value("required_float", float("nan")), "reject invalid float"))
        assert calls == []
        assert not (tmp_path / "must-not-exist.sqlite").exists()
    finally:
        await service.close()
