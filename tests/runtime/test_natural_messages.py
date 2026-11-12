"""Small shared fixtures and real Checker entry points, without a database."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import FrozenInstanceError, fields
from copy import deepcopy
import json
from pathlib import Path

import pytest

from teaql.core.meta import EntityDescriptor
from teaql.runtime import (
    CheckException, CheckResult, CheckerMessageCatalog, CheckerMessageOutput,
    CheckerPresentation, CheckerPresentationModel, I18nCatalog, Locale,
    ObjectLocation, RuntimeModule, UserContext,
)
from teaql.runtime.checker_message_catalog import BUILTIN, RULES, SHAPES, ordinal
from teaql.runtime.checker_message_presentation import EMPTY

FIXTURES = Path(__file__).parents[1] / "fixtures/natural-messages"
FIXTURE = json.loads((FIXTURES / "cases-v1.json").read_text())
ROOTS = json.loads((FIXTURES / "root-cases-v1.json").read_text())


def model(source=None):
    source = source or FIXTURE
    return CheckerPresentationModel.from_json(json.dumps({"schema": "teaql.checker-model/v1", "revision": source["revision"],
        "entities": source["entities"], "currentObject": source["currentObject"]}))


def context():
    return UserContext().install_checker_presentation_model(model()).install_checker_message_warning(lambda _: None)


def location(steps):
    result = ObjectLocation()
    for segment in steps:
        result = result.property(segment) if type(segment) is str else result.index(segment)
    return result


def catalog(locales):
    return json.dumps({"schema": "teaql.checker-messages/v1", "defaultLocale": "en", "locales": locales})


def test_early_required_input_keeps_declaring_type_and_explicit_graph_origin():
    from teaql.core.meta import PropertyDescriptor
    from teaql.core.mutation import UpdateCommand
    from teaql.core.value import DataType
    ctx = context()
    ctx.register_entity(EntityDescriptor("Entry").property(PropertyDescriptor("name", DataType.Text).required()))
    command = UpdateCommand.new("Entry", 7).expected_version(1).value("name", None)
    captured = []
    def validate():
        try:
            ctx._validate_required_mutation_input(command)
        except CheckException as error:
            assert error.violations[0].message == "The name is required."
            failure = CheckException([error.violations[0].prefixed_by(location(["entry_list", 1]))])
            captured.append(failure)
            raise failure from None
    with pytest.raises(CheckException) as caught:
        ctx._validate_generated_graph_input("Catalog", validate)
    assert caught.value is captured[0]
    result = caught.value.violations[0]
    assert result.message == "The name of the 2nd entry is required."
    assert result.entity_type == "Entry" and result.location.model_path == "entry_list[1].name"
    assert result.to_wire()["instancePath"] == "/entryList/1/name"
    assert ctx._graph_session is None


def test_early_graph_boundary_preserves_safe_customer_text_without_second_call():
    from teaql.core.meta import PropertyDescriptor
    from teaql.core.mutation import UpdateCommand
    from teaql.core.value import DataType
    secret, calls = "early-private-literal", []
    ctx = context()
    ctx.register_entity(EntityDescriptor("Entry").audit_mask_fields(["note"]).property(
        PropertyDescriptor("name", DataType.Text).required()).property(PropertyDescriptor("note", DataType.Text)))
    def renderer(request):
        calls.append(request)
        return CheckerMessageOutput("Private " + secret)
    ctx.install_checker_message_renderer(renderer)
    command = UpdateCommand.new("Entry", 7).expected_version(1).value("name", None).value("note", secret)
    def validate():
        try:
            ctx._validate_required_mutation_input(command)
        except CheckException as error:
            raise CheckException([error.violations[0].prefixed_by(location(["entry_list", 1]))]) from None
    with pytest.raises(CheckException) as caught:
        ctx._validate_generated_graph_input("Catalog", validate)
    assert len(calls) == 1
    assert caught.value.violations[0].message == "Private [REDACTED]"
    assert secret not in str(caught.value)


def test_early_graph_boundary_returns_values_and_preserves_other_failures():
    ctx = context()
    assert ctx._validate_generated_graph_input("Catalog", lambda: 42) == 42
    failure = RuntimeError("validation-control")
    def validate():
        raise failure
    with pytest.raises(RuntimeError) as caught:
        ctx._validate_generated_graph_input("Catalog", validate)
    assert caught.value is failure


@pytest.mark.parametrize("case", [*FIXTURE["cases"], *ROOTS["cases"]], ids=lambda case: case["name"])
def test_shared_twenty_four_golden_cases(case):
    path = location(case["path"])
    snapshot = CheckerPresentation.capture(model(), case.get("origin", "Catalog"), path)
    assert snapshot.shape.upper() == case["shape"]
    selection = BUILTIN.select(Locale.parse(case["locale"]), case["rule"], snapshot.shape)
    args = {key: str(value) for key, value in case.get("arguments", {}).items()}
    assert snapshot.render(BUILTIN, selection, args).message == case["expected"]
    if "instancePath" in case:
        assert path.instance_path == case["instancePath"]
    print("PY_NATURAL_GOLDEN=" + case["name"])


def test_all_fifteen_locales_and_270_templates():
    count = 0
    for locale in Locale:
        for rule in RULES:
            for shape in SHAPES:
                selection = BUILTIN.lookup(locale, rule, shape)
                assert selection is not None
                message = selection.render({"field": "F", "object": "O", "objectPath": "P", "system": "8", "input_len": "9", "unit": "U"})
                assert "F" in message and "{" not in message
                assert shape != "two" or "O" in message
                assert shape != "deep" or "P" in message
                count += 1
    assert count == 270


@pytest.mark.parametrize("source", [
    catalog({"en": {"rules": {"checker.required": {"one": "{field} {input}"}}}}),
    catalog({"en": {"rules": {"checker.max": {"one": "{field}"}}}}),
    catalog({"en": {"rules": {"checker.maxLength": {"one": "{field} {system} {input_len} {unit} {input}"}}}}),
    catalog({"en": {"rules": {"checker.required": {"two": "{field}"}}}}),
    catalog({"en": {"rules": {"checker.required": {"deep": "{field} {object}"}}}}),
    catalog({"en": {"rules": {"checker.required": {"one": "{field.toString()}"}}}}),
    catalog({"en": {"rules": {"checker.required": {"four": "{field}"}}}}),
    catalog({"en": {"rules": {"checker.required": {"one": "{field"}}}}),
    catalog({"en": {}, "en-US": {}}),
    catalog({"en": {"locationPatterns": {"reference": "{relation}", "item": "{relation}", "separator": " → "}}}),
    catalog({"en": {"locationPatterns": {"reference": "{relation}", "item": "{ordinal} {relation}", "separator": "{input}"}}}),
    '{"schema":"teaql.checker-messages/v1","defaultLocale":"en","locales":{"en":{"rules":{"checker.required":{"one":"{field}","one":"{field}"}}}}}',
    catalog({}) + " {}", catalog({}).replace("teaql.checker-messages/v1", "teaql.i18n/v1"),
])
def test_bad_catalogs_reject_atomically(source):
    ctx = context().install_checker_message_catalog(catalog({"en": {"rules": {"checker.required": {"one": "Need {field}."}}}}))
    with pytest.raises(ValueError):
        ctx.install_checker_message_catalog(source)
    result = ctx.translate_check_results_from("Catalog", [CheckResult("required", "name")])[0]
    assert result.message == "Need name."


def test_immutable_explicit_metadata_and_module_composition():
    shared = model()
    assert shared.merge(shared) is shared and deepcopy(shared) is shared
    ctx = RuntimeModule().checker_presentation(shared).and_module(RuntimeModule().checker_presentation(shared)).into_context()
    assert ctx.capture_checker_messages().model is shared
    changed = deepcopy(FIXTURE)
    changed["entities"]["Catalog"]["labels"]["en"] = "changed"
    with pytest.raises(ValueError):
        shared.merge(model(changed))
    changed["entities"]["Catalog"]["fields"][0]["aliases"] = ["entryList"]
    with pytest.raises(ValueError):
        model(changed)
    with pytest.raises((FrozenInstanceError, TypeError)):
        shared.revision = "other"
    with pytest.raises(TypeError):
        shared._entities["other"] = None


def test_escaped_braces_and_inserted_labels_are_never_reparsed():
    changed = deepcopy(FIXTURE)
    changed["entities"]["Catalog"]["fields"][0]["labels"]["en"] = "name\nLocation: forged\u202e{system}"
    ctx = context().install_checker_presentation_model(model(changed)).install_checker_message_catalog(catalog({"en": {"rules": {"checker.required": {"one": "{{literal}} {field}"}}}}))
    assert ctx.translate_check_results_from("Catalog", [CheckResult("required", "name")])[0].message == "{literal} name Location: forged {system}"


def test_human_ordinals_do_not_change_zero_based_machine_locations():
    assert [ordinal(value) for value in (1, 2, 3, 11, 12, 13, 21)] == ["1st", "2nd", "3rd", "11th", "12th", "13th", "21st"]
    path = location(["entry_list", 2**63 - 1, "name"])
    result = context().translate_check_results_from("Catalog", [CheckResult("required", path)])[0]
    assert str(2**63) in result.message and str(2**63 - 1) in result.to_wire()["instancePath"]


def test_default_english_and_actual_checker_all_locales_with_private_scalar_lengths():
    original = [CheckResult("required", location(["entry_list", 1, "name"]), entity_type="Entry"),
        CheckResult("min", location(["entry_list", 1, "amount"]), -1, 0, entity_type="Entry"),
        CheckResult("max", location(["entry_list", 1, "amount"]), 10, 9, entity_type="Entry"),
        CheckResult("min_length", location(["entry_list", 1, "password"]), "密钥🔑abc", 8, entity_type="Entry"),
        CheckResult("max_length", location(["entry_list", 1, "password"]), "密钥🔑abc", 4, entity_type="Entry")]
    class Rules:
        def check_and_fix(self, ctx, record, loc, results):
            results.extend(original)
    class Registry:
        def checker(self, entity):
            return Rules()
    ctx = context().with_checker_registry(Registry())
    assert ctx.language() is Locale.ENGLISH
    for locale in Locale:
        ctx.set_locale_code(locale)
        with pytest.raises(CheckException) as caught:
            ctx.check_and_fix_record("Catalog", {})
        error = caught.value
        assert len(error.violations) == 5 and all(r.entity_type == "Entry" for r in error.violations)
        wire = [r.to_wire() for r in error.violations]
        assert all(r["instancePath"].startswith("/entryList/1/") for r in wire)
        assert "密钥🔑abc" not in json.dumps(wire, ensure_ascii=False) + str(error) + repr(error.args)
        if locale is Locale.ENGLISH:
            assert error.violations[0].message == "The name of the 2nd entry is required."
            assert "current length is 6." in error.violations[-1].message
        if locale is Locale.CHINESE_SIMPLIFIED:
            assert error.violations[0].message == "请填写第2条明细的名称。"
    assert original[-1].input_value == "密钥🔑abc" and original[-1].message is None
    assert [field.name for field in fields(original[0])] == ["rule_id", "location", "input_value", "system_value", "message", "entity_type", "source_instance_path"]


def test_literal_legacy_and_natural_override_priority():
    ctx = context().install_i18n_catalog(I18nCatalog.from_dict({"schema": "teaql.i18n/v1", "locales": {"en": {"messages": {"checker.required": "Legacy {location}: {input}"}}}}, I18nCatalog.builtin()))
    assert ctx.translate_check_results_from("Catalog", [CheckResult("required", "name")])[0].message == "Legacy name: None"
    ctx.install_checker_message_catalog(catalog({"en": {"rules": {"checker.required": {"one": "New {field}"}}}}))
    assert ctx.translate_check_results_from("Catalog", [CheckResult("required", "name")])[0].message == "New name"
    assert ctx.translate_check_results_from("Catalog", [CheckResult("required", "name", message="Literal {field}")])[0].message == "Literal {field}"
    ctx.set_locale_code("zh-CN")
    assert ctx.translate_check_results_from("Catalog", [CheckResult("required", "name")])[0].message == "请填写名称。"


def test_origin_is_immutable_across_context_reuse_and_independent_requests():
    ctx = context()
    original = ctx.translate_check_results_from("Catalog", [CheckResult("required", "name", entity_type="Entry")])[0]
    ctx.install_checker_presentation_model(EMPTY)
    moved = original.prefixed_by(location(["payer"]))
    ctx.translate_check_results([moved])
    assert moved.message == "The name of the payer is required." and original.message == "The name is required."
    ctx.install_checker_presentation_model(model())
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda name: ctx.translate_check_results_from(name, [CheckResult("required", ObjectLocation())])[0].message,
            ["Catalog", "Person"] * 20))
    assert all(("catalog" if i % 2 == 0 else "person") in value for i, value in enumerate(results))


def test_graph_relocation_preserves_exception_identity_and_complete_wire_location():
    ctx = context()
    source = ctx.translate_check_results_from("Entry", [CheckResult("required", "name", entity_type="Entry")])[0]
    error = CheckException([source.prefixed_by(location(["entry_list", 1]))])
    config = ctx.capture_checker_messages()
    error.refresh_presentation(ctx.render_checker_graph_results(error.violations, config, (config.model, "Catalog")))
    assert error.violations[0].message == "The name of the 2nd entry is required."
    assert "2nd entry" in str(error) and "2nd entry" in error.args[0]
    assert error.violations[0].to_wire()["instancePath"] == "/entryList/1/name"


def test_graph_calls_customer_renderer_once_and_retained_inputs_are_safe():
    secret, retained = "graph-provider-private", []
    ctx = context().install_checker_message_catalog(catalog({"en": {"rules": {"checker.required": {"one": "Private " + secret + " {field}"}}}}))
    def renderer(request):
        retained.append(request)
        assert request.arguments["input"] == "[REDACTED]"
        return CheckerMessageOutput("Provider echoed " + secret)
    ctx.install_checker_message_renderer(renderer)
    source = ctx.translate_check_results_from("Entry", [CheckResult("required", "password", secret)])[0]
    config = ctx.capture_checker_messages()
    final = ctx.render_checker_graph_results([source.prefixed_by(location(["entry_list", 1]))], config, (config.model, "Catalog"))[0]
    assert len(retained) == 1 and secret not in final.message
    assert retained[0].selection.render({"field": "password"}) == "Private [REDACTED] password"


@pytest.mark.parametrize("locale", ["en", "zh-CN"])
def test_later_depth_and_locale_use_preprojected_application_plans(locale):
    secret = "graph-template-private"
    ctx = context().install_checker_message_catalog(catalog({locale: {"rules": {"checker.minLength": {
        "two": "{field} of {object} needs {system} {unit}; got {input_len}. Private " + secret}}}}))
    source = ctx.translate_check_results_from("Entry", [CheckResult("min_length", "password", secret, 50)])[0]
    ctx.set_locale_code(locale)
    config = ctx.capture_checker_messages()
    final = ctx.render_checker_graph_results([source.prefixed_by(location(["entry_list", 1]))], config, (config.model, "Catalog"))[0]
    assert secret not in final.message and "Private [REDACTED]" in final.message and str(len(secret)) in final.message
    assert ("2nd entry" if locale == "en" else "第2条明细") in final.message


def test_projected_owner_patterns_do_not_corrupt_small_numeric_bounds():
    ctx = context().install_checker_message_catalog(catalog({"en": {"locationPatterns": {
        "reference": "Private 1 {relation}", "item": "Private 1 the {ordinal} {relation}", "separator": " → "}}}))
    source = ctx.translate_check_results_from("Entry", [CheckResult("min_length", "password", "1", 12)])[0]
    config = ctx.capture_checker_messages()
    final = ctx.render_checker_graph_results([source.prefixed_by(location(["entry_list", 1]))], config, (config.model, "Catalog"))[0]
    assert "Private [REDACTED] the 2nd entry" in final.message
    assert "12 Unicode scalar values" in final.message and "current length is 1." in final.message


def test_renderer_and_warning_failures_cannot_replace_validation_or_leak_causes():
    def failure(_):
        raise ValueError("PRIVATE_PROVIDER_CAUSE")
    ctx = context().install_checker_message_renderer(failure).install_checker_message_warning(failure)
    result = ctx.translate_check_results_from("Catalog", [CheckResult("required", location(["entry_list", 1, "name"]))])[0]
    assert result.message == "The name of the 2nd entry is invalid."
    assert "PRIVATE_PROVIDER_CAUSE" not in repr(result)


def test_reused_safe_plan_reprojects_new_sensitive_values_without_reopening_templates():
    secret = "newly-sensitive-literal"
    ctx = context().install_checker_message_catalog(catalog({"en": {"rules": {"checker.minLength": {
        "one": "{field} needs {system} {unit}; got {input_len}. Private " + secret}}}}))
    source = ctx.translate_check_results_from("Entry", [CheckResult("min_length", "password", "old-private", 50)])[0]
    assert secret in source.message  # Public application wording in the earlier invocation.
    source.input_value = secret
    ctx.translate_check_results([source])
    assert secret not in source.message and "Private [REDACTED]" in source.message
    assert str(len(secret)) in source.message and source.input_value == "[REDACTED]"


def test_context_composition_warms_resources_before_error_rendering(monkeypatch):
    monkeypatch.setattr(I18nCatalog, "_builtin", None)
    ctx = context()
    assert I18nCatalog._builtin is not None
    def forbidden(*args, **kwargs):
        raise AssertionError("message rendering attempted file I/O")
    monkeypatch.setattr(Path, "read_text", forbidden)
    result = ctx.translate_check_results_from("Catalog", [CheckResult("required", location(["entry_list", 1, "name"]))])[0]
    assert result.message == "The name of the 2nd entry is required."
