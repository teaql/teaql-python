"""Declaring Checker identity and lossless structured graph error composition."""
from dataclasses import fields
import pytest

from teaql.core.meta import EntityDescriptor, PropertyDescriptor
from teaql.core.mutation import InsertCommand
from teaql.runtime import (CheckException, CheckResult, JsonFieldNamingProfile,
                           ObjectLocation, RuntimeModule)


@pytest.mark.parametrize("declared", [None, "", "  \t", "SpecializedChild"])
@pytest.mark.parametrize("locale", ["en", "zh-CN"])
def test_checker_owner_is_bound_before_localization_without_overwriting_specialization(declared, locale):
    original = CheckResult("required", ObjectLocation().property("user_url"),
                           entity_type=declared, source_instance_path="/submitted~1url")
    context = (RuntimeModule().schema_entity(EntityDescriptor("Child")
               .property(PropertyDescriptor("user_url"))).into_context().set_locale_code(locale))

    class Checker:
        def check_and_fix(self, context, record, location, results):
            results.append(original)

    class Registry:
        def checker(self, entity):
            assert entity == "Child"
            return Checker()

    context.with_checker_registry(Registry())
    translated = []
    translate = context.translate_check_results

    def observe(results):
        translated.extend(result.entity_type for result in results)
        translate(results)

    context.translate_check_results = observe
    with pytest.raises(CheckException) as error:
        context.check_and_fix_mutation(InsertCommand.new("Child"))
    expected = declared if declared and declared.strip() else "Child"
    assert translated == [expected]
    result = error.value.violations[0]
    assert result is not original
    assert original.entity_type == declared and original.message is None
    assert result.entity_type == expected
    assert result.message and not result.message.startswith("checker.")
    assert result.to_wire()["sourceInstancePath"] == "/submitted~1url"
    assert result.location.segments == (("property", "user_url"),)
    assert context.get_resource("fix_time") is None
    assert context.get_resource("fix_operation") is None


@pytest.mark.parametrize("profile,expected", [
    (JsonFieldNamingProfile.CAMEL_CASE, "/orderItems/2/userUrl"),
    (JsonFieldNamingProfile.SNAKE_CASE, "/order_items/2/user_url"),
    (JsonFieldNamingProfile.PASCAL_CASE, "/OrderItems/2/UserUrl"),
])
def test_graph_prefix_preserves_every_non_location_field(profile, expected):
    original = CheckResult("required", ObjectLocation().property("user_url"),
                           input_value="synthetic", system_value=7, message="custom safe message",
                           entity_type="SpecializedChild", source_instance_path="/order_items/2/a~1b~0c")
    prefix = ObjectLocation().property("order_items").index(2)
    result = original.prefixed_by(prefix)
    assert result is not original
    for field in fields(original):
        if field.name != "location":
            assert getattr(result, field.name) == getattr(original, field.name)
    assert original.location.model_path == "user_url"
    assert result.location.model_path == "order_items[2].user_url"
    assert result.to_wire(profile)["instancePath"] == expected
    assert result.to_wire(profile)["sourceInstancePath"] == "/order_items/2/a~1b~0c"
    twice = result.prefixed_by(ObjectLocation().property("batches").index(1))
    assert twice.location.model_path == "batches[1].order_items[2].user_url"
    assert twice.entity_type == "SpecializedChild"
