import json

import pytest

from teaql.runtime import ExpressionPath, JsonFieldNamingProfile, TeaQLNotLoadedError


def test_early_repeated_relation_preserves_suffix_and_first_positional_breakpoint():
    parent = ExpressionPath("E.node(<root>)").member("parent", "parent").mark_missing()
    leaf = parent.member("parent", "parent").member("user_url", "user_url")
    error = TeaQLNotLoadedError(parent, "parent").with_path(leaf).terminal("eval()")
    wire = error.to_wire()
    assert wire["code"] == "NOT_LOADED"
    assert wire["instancePath"] == "/parent"
    assert wire["attemptedInstancePath"] == "/parent/parent/userUrl"
    assert wire["originalExpression"] == "E.node(<root>).parent().parent().user_url().eval()"
    assert wire["expressionWithBrokenPoint"] == "E.node(<root>).parent()<broken>.parent().user_url().eval()"
    assert wire["expressionWithBrokenPoint"].count("<broken>") == 1
    assert wire["breakPointIndex"] == 0
    assert wire["suggestedFix"] == {"action": "preload", "location": wire["location"]}
    assert json.loads(str(error)) == wire


@pytest.mark.parametrize("profile", list(JsonFieldNamingProfile))
def test_real_indices_profiles_and_nontraversal_operations(profile):
    items = ExpressionPath("E.order(<root>)", profile).member("order_items", "order_item_list").mark_missing()
    error = TeaQLNotLoadedError(items.index(12).member("user_url", "user_url"), "order_items").terminal("eval()")
    assert error.to_wire()["attemptedLocation"][1] == {"kind": "index", "index": 12}
    assert error.to_wire()["location"] == [{"kind": "property", "name": "order_items"}]
    assert ".get(12).user_url().eval()" in str(error)
    first = TeaQLNotLoadedError(items.index(0, first=True), "order_items").terminal("eval()")
    assert ".first().eval()" in str(first)
    size = TeaQLNotLoadedError(items.operation("size()"), "order_items").terminal("eval()")
    assert size.to_wire()["attemptedLocation"] == size.to_wire()["location"]


def test_siblings_literal_punctuation_and_error_export_do_not_parse_or_leak_values():
    parent = ExpressionPath("E.node(<root>)").member("a~/b.c", "safe_method").mark_missing()
    first = TeaQLNotLoadedError(parent.member("name", "name"), "a~/b.c").terminal("or_if_null(<fallback>)")
    second = TeaQLNotLoadedError(parent.member("code", "code"), "a~/b.c").terminal("eval()")
    assert first.to_wire()["instancePath"] == "/a~0~1b.c"
    assert ".name().or_if_null(<fallback>)" in str(first)
    assert ".code()" not in str(first)
    assert "root" not in second.to_wire()
    assert "inputValue" not in second.to_wire()
