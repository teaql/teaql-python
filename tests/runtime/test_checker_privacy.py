"""Checker presentations use model policy without changing business inputs."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, fields
from decimal import Decimal
from types import MappingProxyType
import json

import pytest

from teaql.core.meta import EntityDescriptor, PropertyDescriptor, RelationDescriptor
from teaql.core.value import Value
from teaql.runtime import (CheckException, CheckResult, I18nCatalog, JsonFieldNamingProfile,
                           Locale, ObjectLocation, RuntimeModule)
from teaql.runtime.audit import _mask
from teaql.runtime.log_privacy import PLAINTEXT_ACK, PLAINTEXT_ENV, REDACTED

PHONE = "customer-contact-9182"
TOKEN = "authkey-7734-do-not-share"


def context():
    order = (EntityDescriptor("PurchaseOrder").audit_mask_fields(["contact_phone", "_private_note"])
             .property(PropertyDescriptor("contact_phone").column_name("stored_phone"))
             .property(PropertyDescriptor("public_label"))
             .property(PropertyDescriptor("payload_json", "Json"))
             .property(PropertyDescriptor("api_token"))
             .relation(RelationDescriptor("line_items", "OrderItem").many()))
    child = (EntityDescriptor("OrderItem").audit_mask_fields(["contact_phone"])
             .property(PropertyDescriptor("contact_phone")).property(PropertyDescriptor("public_label")))
    plain = EntityDescriptor("PlainDiagnostic").audit_mask_fields([]).property(PropertyDescriptor("contact_phone"))
    return RuntimeModule().schema_entity(order).schema_entity(child).schema_entity(plain).into_context()


def check_failure(result, *, ctx=None, record=None, callback=None, thrown=False):
    ctx = ctx or context()
    record = {"contact_phone": Value.Text(PHONE)} if record is None else record

    class Checker:
        def check_and_fix(self, context, values, location, results):
            if callback:
                callback(values)
            if thrown:
                raise CheckException([result])
            results.append(result)

    class Registry:
        def checker(self, entity):
            return Checker()

    ctx.with_checker_registry(Registry())
    with pytest.raises(CheckException) as caught:
        ctx.check_and_fix_record("PurchaseOrder", record)
    return caught.value


def diagnostic(field="contact_phone", value=PHONE, system=8, **kwargs):
    return CheckResult("max_length", ObjectLocation().property(field), value, system,
                       entity_type="PurchaseOrder", **kwargs)


def presented(result):
    return json.dumps(result.to_wire(), default=str, ensure_ascii=False) + repr(result) + str(result)


def test_modeled_mask_protects_wire_native_and_exception_without_changing_record():
    original = diagnostic()
    values = {"contact_phone": Value.Text(PHONE)}
    error = check_failure(original, record=values)
    result = error.violations[0]
    assert result.input_value == _mask(PHONE)
    assert PHONE not in presented(result) + str(error)
    assert values["contact_phone"].val == PHONE
    assert original.input_value == PHONE and original.message is None


@pytest.mark.parametrize("profile", list(JsonFieldNamingProfile))
def test_every_wire_profile_preserves_model_location_and_submitted_alias(profile):
    location = ObjectLocation().property("line_items").index(2).property("contact_phone")
    original = CheckResult("max_length", location, PHONE, 3, entity_type="OrderItem",
                           source_instance_path="/submitted~1phone")
    error = check_failure(original)
    wire = error.violations[0].to_wire(profile)
    assert wire["entityType"] == "OrderItem"
    assert wire["sourceInstancePath"] == "/submitted~1phone"
    assert wire["instancePath"] == location.instance_path_for(profile)
    assert PHONE not in json.dumps(wire, default=str)


def test_original_unicode_length_survives_relocalization_and_graph_prefix():
    value = "秘密🙂ABC中文🙂Z"
    result = diagnostic(value=value, system=2)
    ctx = context()
    ctx.translate_check_results([result])
    assert str(len(value)) in result.message
    prefixed = result.prefixed_by(ObjectLocation().property("line_items").index(1))
    ctx.set_locale_code("zh-CN").translate_check_results([prefixed])
    assert str(len(value)) in prefixed.message
    assert prefixed.input_value == _mask(value)
    assert value not in presented(prefixed)


def test_customer_cached_results_are_not_rebound_or_rewritten_by_save():
    original = CheckResult("max_length", "contact_phone", PHONE, 2)
    first = check_failure(original).violations[0]
    second = check_failure(original).violations[0]
    assert first is not original and second is not original and first is not second
    assert original.entity_type is None and original.message is None and original.input_value == PHONE
    assert first.entity_type == second.entity_type == "PurchaseOrder"
    assert PHONE not in presented(first) + presented(second)


@pytest.mark.parametrize("declaring", ["UnregisteredCustomDiagnostic", "PlainDiagnostic"])
def test_diagnostic_type_cannot_weaken_actual_request_owner_policy(declaring):
    result = diagnostic()
    result.entity_type = declaring
    value = check_failure(result).violations[0]
    assert value.entity_type == declaring
    assert value.location.model_path == "contact_phone"
    assert value.input_value == _mask(PHONE)


def test_unknown_type_does_not_blanket_mask_ordinary_values():
    result = diagnostic("public_label", "ordinary label", system=4)
    result.entity_type = "UnknownDiagnostic"
    value = check_failure(result, record={"public_label": Value.Text("ordinary label")}).violations[0]
    assert value.input_value == "ordinary label" and value.system_value == 4


def test_direct_catalog_translation_hides_credentials_without_context_metadata():
    result = CheckResult("max_length", "api_key", TOKEN, TOKEN)
    I18nCatalog.builtin().translate_check_result(result, Locale.ENGLISH)
    assert TOKEN not in presented(result)
    assert result.input_value == result.system_value == REDACTED


def test_wire_projection_alone_hides_credentials_without_mutating_owner():
    result = CheckResult("custom", "password", TOKEN, message="refused " + TOKEN)
    assert TOKEN not in presented(result)
    assert result.input_value == TOKEN and result.message == "refused " + TOKEN


def test_short_credentials_do_not_corrupt_typed_bounds_or_public_paths():
    result = CheckResult("max_length", "password", "1", 1000)
    I18nCatalog.builtin().translate_check_result(result, Locale.ENGLISH)
    assert result.input_value == REDACTED and result.system_value == 1000
    assert "password" in result.message and "1000" in result.message


def test_ordinary_values_decimal_bounds_and_rule_vocabulary_stay_typed():
    result = CheckResult("max", "public_label", Decimal("123.50"), Decimal("99.99"), entity_type="PurchaseOrder")
    context().translate_check_results([result])
    assert result.input_value == Decimal("123.50") and result.system_value == Decimal("99.99")
    assert result.to_wire()["ruleId"] == "max"
    assert isinstance(result.to_wire()["systemValue"], Decimal)


def test_root_and_sibling_messages_use_before_and_after_fix_sensitive_inputs():
    second = "replaced-private-contact"
    result = CheckResult("custom", ObjectLocation(), message=PHONE + " -> " + second)
    error = check_failure(result, callback=lambda values: values.update(contact_phone=Value.Text(second)))
    assert PHONE not in str(error) and second not in str(error)
    assert "->" in error.violations[0].message


def test_custom_catalog_literals_are_scrubbed_before_typed_substitution():
    ctx = context()
    catalog = I18nCatalog.from_dict({"schema": "teaql.i18n/v1", "locales": {"en": {"messages": {
        "checker.maxLength": "private " + PHONE + " / {location} / {system} / {input_len}"}}}}, I18nCatalog.builtin())
    ctx.insert_resource("i18n_catalog", catalog)
    result = diagnostic()
    ctx.translate_check_results([result])
    assert PHONE not in result.message and str(len(PHONE)) in result.message and "8" in result.message


def test_input_placeholder_text_is_not_recursively_interpreted():
    result = CheckResult("custom", "public_label", "literal {system}", 42, entity_type="PurchaseOrder")
    catalog = I18nCatalog.from_dict({"schema": "teaql.i18n/v1", "locales": {"en": {"messages": {
        "checker.custom": "{input} / {system}"}}}}, I18nCatalog.builtin())
    catalog.translate_check_result(result, Locale.ENGLISH)
    assert result.message == "literal {system} / 42"


def test_nested_json_credentials_are_hidden_and_ordinary_siblings_remain():
    payload = {"public": "visible", "nested": {"authorization": TOKEN}}
    result = diagnostic("payload_json", Value.Json(payload))
    context().translate_check_results([result])
    assert TOKEN not in presented(result)
    assert "visible" in presented(result)
    assert payload["nested"]["authorization"] == TOKEN


def test_credential_ancestor_protects_an_ordinary_leaf_name():
    result = CheckResult("custom", ObjectLocation().property("credentials").property("value"), TOKEN)
    context().translate_check_results([result])
    assert TOKEN not in presented(result)


def test_structured_root_values_obey_model_masks_for_every_json_spelling():
    for name in ["contact_phone", "contactPhone", "ContactPhone", "stored_phone"]:
        result = CheckResult("custom", ObjectLocation(), {name: PHONE, "public_label": "visible"}, entity_type="PurchaseOrder")
        context().translate_check_results([result])
        assert PHONE not in presented(result)
        assert "visible" in presented(result)


def test_real_relation_is_traversed_before_declaring_leaf_shortcut():
    ctx = context()
    ctx.entity("PurchaseOrder").audit_mask_fields_val.append("public_label")
    result = CheckResult("custom", ObjectLocation().property("line_items").index(0).property("public_label"),
                         "ordinary child", entity_type="PurchaseOrder")
    ctx.translate_check_results([result])
    assert result.input_value == "ordinary child"


def test_json_scalar_contents_do_not_borrow_surrounding_model_masks():
    result = CheckResult("custom", ObjectLocation().property("payload_json").property("contact_phone"),
                         "ordinary JSON text", entity_type="PurchaseOrder")
    context().translate_check_results([result])
    assert result.input_value == "ordinary JSON text"


def test_dynamic_field_mask_does_not_change_its_model_path():
    result = diagnostic("_private_note")
    context().translate_check_results([result])
    assert result.location.model_path == "_private_note" and result.input_value == _mask(PHONE)


def test_readonly_maps_and_typed_json_are_inspected_without_arbitrary_stringification():
    @dataclass
    class Payload:
        public_name: str
        access_token: str

        def __str__(self):
            raise AssertionError("must not stringify an entire application payload")

    for value in [MappingProxyType({"api_key": TOKEN, "public_name": "visible"}), Payload("visible", TOKEN)]:
        result = diagnostic("payload_json", value)
        context().translate_check_results([result])
        assert TOKEN not in presented(result) and "visible" in presented(result)


def test_cycles_and_nonfinite_values_do_not_break_error_serialization():
    value = {"api_key": TOKEN, "nonfinite": float("nan")}
    value["cycle"] = value
    result = diagnostic("payload_json", value)
    context().translate_check_results([result])
    assert TOKEN not in json.dumps(result.to_wire(), allow_nan=False)


def test_output_collection_mutation_does_not_alias_the_cached_safe_snapshot():
    value = {"api_key": TOKEN, "public": ["visible"]}
    result = diagnostic("payload_json", value)
    context().translate_check_results([result])
    wire = result.to_wire()
    wire["inputValue"]["public"].append("changed")
    assert value["public"] == ["visible"]
    assert result.to_wire()["inputValue"]["public"] == ["visible"]


def test_escaped_message_variants_cannot_restore_known_sensitive_strings():
    value = 'private-"quote"-秘密'
    result = diagnostic(value=value, message="payload=" + json.dumps(value))
    value = check_failure(result, record={"contact_phone": Value.Text(value)}).violations[0]
    assert 'private-' not in value.message and "payload=" in value.message


def test_exact_debug_opt_in_reveals_model_values_but_never_credentials(monkeypatch):
    monkeypatch.setenv(PLAINTEXT_ENV, "true")
    result = diagnostic()
    context().translate_check_results([result])
    assert result.input_value == _mask(PHONE)
    monkeypatch.setenv(PLAINTEXT_ENV, PLAINTEXT_ACK)
    visible = diagnostic()
    context().translate_check_results([visible])
    assert visible.input_value == PHONE
    credential = CheckResult("max_length", "password", TOKEN, 2)
    I18nCatalog.builtin().translate_check_result(credential, Locale.ENGLISH)
    assert TOKEN not in presented(credential)


def test_cached_debug_output_returns_to_safe_mode_and_keeps_original_length(monkeypatch):
    monkeypatch.setenv(PLAINTEXT_ENV, PLAINTEXT_ACK)
    result = diagnostic()
    ctx = context()
    ctx.translate_check_results([result])
    monkeypatch.delenv(PLAINTEXT_ENV)
    assert PHONE not in presented(result)
    ctx.translate_check_results([result])
    assert result.input_value == _mask(PHONE) and str(len(PHONE)) in result.message
    assert PHONE not in repr(getattr(result, "_presentation", None))


def test_custom_thrown_checker_exceptions_use_the_same_safe_boundary():
    error = check_failure(diagnostic(message="refused " + PHONE), thrown=True)
    assert PHONE not in str(error) + presented(error.violations[0])
    assert error.__cause__ is None and error.__context__ is None


def test_contexts_can_concurrently_reuse_one_customer_owned_result():
    original = CheckResult("max_length", "contact_phone", PHONE, 2)

    def run(index):
        ctx = context()
        if index % 2:
            ctx.entity("PurchaseOrder").audit_mask_fields([])
        return check_failure(original, ctx=ctx).violations[0].input_value

    with ThreadPoolExecutor(max_workers=4) as pool:
        values = list(pool.map(run, range(12)))
    assert values == [_mask(PHONE) if i % 2 == 0 else PHONE for i in range(12)]
    assert original.input_value == PHONE and original.entity_type is None and original.message is None


def test_public_dataclass_fields_and_positional_construction_remain_stable():
    result = CheckResult("required", "public_label", None, None, None, "PurchaseOrder", "/raw")
    assert [f.name for f in fields(result)] == ["rule_id", "location", "input_value", "system_value", "message", "entity_type", "source_instance_path"]
    context().translate_check_results([result])
    assert "_presentation" not in asdict(result)
