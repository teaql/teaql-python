import json
from importlib.resources import files
import pytest

from teaql.runtime import CheckResult, I18nCatalog, JsonFieldNamingProfile, Locale, ObjectLocation, UnsupportedLocaleError, UserContext

def test_object_location_preserves_all_three_path_dialects():
    location = ObjectLocation().property("order_items").index(2).property("user_url")
    assert location.model_path == "order_items[2].user_url"
    assert location.native_path == "order_items[2].user_url"
    assert location.instance_path == "/orderItems/2/userUrl"
    assert location.instance_path_for(JsonFieldNamingProfile.SNAKE_CASE) == "/order_items/2/user_url"
    assert location.instance_path_for(JsonFieldNamingProfile.PASCAL_CASE) == "/OrderItems/2/UserUrl"
    escaped = ObjectLocation().property("a/b~c")
    assert escaped.instance_path == "/a~1b~0c"

def test_wire_checker_result_preserves_submitted_alias():
    result = CheckResult("required", ObjectLocation().property("user_url"),
                         entity_type="customer_account", source_instance_path="/user_url")
    wire = result.to_wire()
    assert wire["instancePath"] == "/userUrl"
    assert wire["sourceInstancePath"] == "/user_url"
    assert wire["location"] == [{"kind":"property", "name":"user_url"}]

def test_fifteen_locales_times_five_checker_rules():
    catalog = I18nCatalog.builtin()
    results = [CheckResult("required", "name"), CheckResult("min", "age", 1, 2),
               CheckResult("max", "age", 3, 2), CheckResult("min_length", "name", "a", 2),
               CheckResult("max_length", "name", "abc", 2)]
    cells = 0
    for locale in Locale:
        for result in results:
            catalog.translate_check_result(result, locale)
            assert result.message and not result.message.startswith("checker.")
            assert "{location}" not in result.message
            cells += 1
    assert cells == 75

def test_alias_and_context_preservation_on_invalid_locale():
    context = UserContext().set_locale_code("ZH_hans")
    assert context.language() is Locale.CHINESE_SIMPLIFIED
    with pytest.raises(UnsupportedLocaleError): context.set_locale_code("xx")
    assert context.language() is Locale.CHINESE_SIMPLIFIED

def test_application_selected_then_english_then_builtin_fallback():
    app = I18nCatalog.from_dict({"schema":"teaql.i18n/v1", "defaultLocale":"en", "locales":{
        "zh-CN":{"messages":{"checker.required":"APP {location}"},"vocabulary":{}},
        "en":{"messages":{"custom":"custom english"},"vocabulary":{}}
    }}, I18nCatalog.builtin())
    assert app.message(Locale.CHINESE_SIMPLIFIED, "checker.required") == "APP {location}"
    assert app.message(Locale.CHINESE_SIMPLIFIED, "custom") == "custom english"
    assert app.message(Locale.CHINESE_SIMPLIFIED, "checker.min") != "checker.min"
    assert app.message(Locale.CHINESE_SIMPLIFIED, "missing.key") == "missing.key"
