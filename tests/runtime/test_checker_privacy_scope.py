"""Request-only source values and concurrent request-owner policy."""
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from decimal import Decimal

import pytest

from teaql.core.meta import EntityDescriptor, PropertyDescriptor
from teaql.core.mutation import UpdateCommand
from teaql.core.value import Value
from teaql.runtime import CheckException, CheckResult, RuntimeModule
from teaql.runtime.audit import _mask


def configured(result):
    private = EntityDescriptor("PrivateOwner").audit_mask_fields(["contact_phone"]).property(PropertyDescriptor("contact_phone"))
    plain = EntityDescriptor("PlainOwner").audit_mask_fields([]).property(PropertyDescriptor("contact_phone"))
    ctx = RuntimeModule().schema_entity(private).schema_entity(plain).into_context()

    class Checker:
        def check_and_fix(self, context, record, location, results):
            results.append(result)

    class Registry:
        def checker(self, entity):
            return Checker()

    return ctx.with_checker_registry(Registry())


@pytest.mark.parametrize("field", ["contact_phone", "password"])
def test_old_values_are_invocation_local_root_message_redaction_inputs(field):
    secret = "previous-private-value-8190"
    result = CheckResult("custom", "", message="old value: " + secret)
    ctx = configured(result)
    mutation = UpdateCommand.new("PrivateOwner", 1).expected_version(1)
    mutation.old_values = {field: Value.Text(secret)}
    with pytest.raises(CheckException) as caught:
        ctx.check_and_fix_mutation(mutation)
    error = caught.value
    assert secret not in str(error) + repr(error.violations)
    assert mutation.old_values[field].val == secret
    assert result.message == "old value: " + secret and result.entity_type is None
    assert error.__context__ is None and error.__cause__ is None


def test_one_context_keeps_concurrent_request_owners_separate():
    secret = "request-private-contact-7721"
    original = CheckResult("max_length", "contact_phone", secret, 2)
    ctx = configured(original)

    def run(index):
        owner = "PrivateOwner" if index % 2 == 0 else "PlainOwner"
        try:
            ctx.check_and_fix_record(owner, {"contact_phone": Value.Text(secret)})
        except CheckException as error:
            return error.violations[0].input_value
        raise AssertionError("expected the configured Checker diagnostic")

    with ThreadPoolExecutor(max_workers=4) as pool:
        values = list(pool.map(run, range(16)))
    assert values == [_mask(secret) if index % 2 == 0 else secret for index in range(16)]
    assert original.input_value == secret and original.entity_type is None and original.message is None


def test_marker_shaped_json_cannot_reuse_a_decimal_input_snapshot():
    result = CheckResult("custom", "contact_phone", Decimal("12.50"))
    ctx = configured(result)
    ctx.translate_check_results([result])
    result.input_value = {"$decimal": "12.50"}
    ctx.translate_check_results([result])
    assert result.input_value == {"$decimal": "12.50"}
    assert result.to_wire()["inputValue"] == {"$decimal": "12.50"}


def test_marker_shaped_json_cannot_reuse_a_date_system_snapshot():
    result = CheckResult("custom", "contact_phone", "ordinary", date(2026, 10, 31))
    ctx = configured(result)
    ctx.translate_check_results([result])
    result.system_value = {"$date": "2026-10-31"}
    ctx.translate_check_results([result])
    assert result.system_value == {"$date": "2026-10-31"}
    assert result.to_wire()["systemValue"] == {"$date": "2026-10-31"}
