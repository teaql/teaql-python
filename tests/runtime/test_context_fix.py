"""Context-wide eligibility and structured diagnostics over a tiny model."""
from copy import deepcopy
from datetime import datetime, timezone
import asyncio

import pytest

from teaql.core.meta import EntityDescriptor, PropertyDescriptor
from teaql.core.mutation import InsertCommand, UpdateCommand
from teaql.core.value import DataType, Timestamp, Value
from teaql.runtime import ContextFix, CheckException, CheckResult, FixedBusinessClock, ObjectLocation, RuntimeModule

A = datetime(2033, 1, 1, tzinfo=timezone.utc)
B = datetime(2033, 1, 2, tzinfo=timezone.utc)


def fixture():
    descriptor = (EntityDescriptor("Probe")
                  .property(PropertyDescriptor("id", DataType.I64).is_id())
                  .property(PropertyDescriptor("version", DataType.I64).is_version())
                  .property(PropertyDescriptor("name", DataType.Text)))
    descriptor.property(PropertyDescriptor("born_at", DataType.Timestamp).on_create_from_context("now"))
    descriptor.property(PropertyDescriptor("touched_at", DataType.Timestamp).on_create_from_context("now").on_update_from_context("now"))
    for name in ("source_ip", "opened_by", "last_ip", "changed_by"):
        prop = PropertyDescriptor(name, DataType.Text).on_create_from_context("identity")
        if name in ("last_ip", "changed_by"):
            prop.on_update_from_context("identity")
        descriptor.property(prop)
    calls = []

    class Checker:
        def check_and_fix(self, context, record, location, results):
            calls.append(1)
            operation = context.get_resource("fix_operation")
            for prop in descriptor.properties:
                fn = prop.create_function if operation == "insert" else prop.update_function
                if fn:
                    ContextFix.apply(context, record, prop.name, fn)
            if record.get("name") == Value.Text("INVALID"):
                results.append(CheckResult("required", ObjectLocation().property("name")))

    context = (RuntimeModule().schema_entity(descriptor).checker("Probe", Checker()).into_context()
               .with_business_clock(FixedBusinessClock(B)))
    requests = []

    def resolver(ctx, request):
        requests.append(request)
        return request.now if request.function == "now" else "B:" + request.field

    context.insert_resource("context_fix_resolver", resolver)
    return context, calls, requests


def update(values, old=None):
    return UpdateCommand("Probe", Value.I64(7), 3, values, old_values=old)


def test_unchanged_or_only_managed_values_never_enable_context_fix():
    context, checks, requests = fixture()
    for values in ({}, {}, {"last_ip": Value.Text("manual")}, {"version": Value.I64(4)}):
        command = update(deepcopy(values))
        context.check_and_fix_mutation(command)
        assert command.values == values
    assert len(checks) == 4 and not requests


def test_creation_needs_no_dirty_fields_and_update_preserves_create_only_fields():
    context, _, requests = fixture()
    created = InsertCommand("Probe")
    context.check_and_fix_mutation(created)
    assert created.values["source_ip"] == Value.Text("B:source_ip")
    assert created.values["born_at"] == Value.from_any(B)
    command = update({"name": Value.Text("changed")})
    context.check_and_fix_mutation(command)
    assert command.values["touched_at"] == Value.from_any(B)
    assert command.values["last_ip"] == Value.Text("B:last_ip")
    assert "source_ip" not in command.values and "born_at" not in command.values
    assert all(item.now == B for item in requests)


def test_restored_business_values_are_not_independent_mutations():
    context, _, requests = fixture()
    values = {"name": Value.Text("same")}
    context.check_and_fix_mutation(update(values, deepcopy(values)))
    assert not requests and values == {"name": Value.Text("same")}


def test_failed_check_discards_context_but_keeps_caller_value_and_allows_retry():
    context, _, _ = fixture()
    values = {"name": Value.Text("INVALID"), "last_ip": Value.Text("A:last_ip"), "touched_at": Value.from_any(A)}
    command = update(values)
    with pytest.raises(CheckException) as failure:
        context.check_and_fix_mutation(command)
    assert failure.value.violations[0].location.instance_path == "/name"
    assert failure.value.violations[0].entity_type == "Probe"
    assert values == {"name": Value.Text("INVALID"), "last_ip": Value.Text("A:last_ip"), "touched_at": Value.from_any(A)}
    values["name"] = Value.Text("valid")
    context.check_and_fix_mutation(command)
    assert values["last_ip"] == Value.Text("B:last_ip")
    assert context.get_resource("fix_time") is None


@pytest.mark.parametrize("failure", ("exception", "type", "overflow", "coroutine", "future"))
@pytest.mark.asyncio
async def test_context_provider_errors_are_safe_and_object_located(failure):
    context, _, _ = fixture()

    async def rejected():
        raise RuntimeError("PRIVATE_CONTEXT_CANARY")

    def resolver(ctx, request):
        if failure == "exception":
            raise RuntimeError("PRIVATE_CONTEXT_CANARY")
        if failure == "coroutine":
            return rejected()
        if failure == "future":
            future = asyncio.get_running_loop().create_future()
            future.set_exception(RuntimeError("PRIVATE_CONTEXT_CANARY"))
            return future
        if failure == "overflow":
            return Timestamp(1 << 80)
        return "not a timestamp"

    context.insert_resource("context_fix_resolver", resolver)
    values = {"name": Value.Text("edit")}
    with pytest.raises(CheckException) as error:
        context.check_and_fix_mutation(update(values))
    result = error.value.violations[0]
    assert result.location.instance_path == "/touchedAt"
    assert result.prefixed_by(ObjectLocation().property("children").index(1)).location.instance_path == "/children/1/touchedAt"
    assert result.entity_type == "Probe"
    assert "PRIVATE_CONTEXT_CANARY" not in str(error.value)
    assert error.value.__cause__ is None and error.value.__context__ is None
    assert values == {"name": Value.Text("edit")}
    await asyncio.sleep(0)  # Consume only the returned Future's diagnostic callback.


def test_default_context_functions_use_business_clock_and_strong_values():
    context, _, _ = fixture()
    context.insert_resource("context_fix_resolver", None)
    prop = PropertyDescriptor("token", DataType.Text).on_create_from_context("uniStr")
    context.entity("Probe").properties.append(prop)
    values = {}
    context.insert_resource("fix_time", B)
    with ContextFix.scope(context, "Probe", values, operation="insert"):
        ContextFix.apply(context, values, "born_at", "now")
        ContextFix.apply(context, values, "token", "uniStr", ("P-",))
    assert values["born_at"] == Value.from_any(B)
    assert values["token"].val.startswith("P-") and len(values["token"].val) == 34
    assert all(char in "0123456789abcdef" for char in values["token"].val[2:])
