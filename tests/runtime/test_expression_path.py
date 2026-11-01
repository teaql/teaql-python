import json

import pytest

from teaql.runtime import ExpressionPath, JsonFieldNamingProfile, TeaQLNotLoadedError


@pytest.mark.parametrize("profile,pointer", [
    (JsonFieldNamingProfile.CAMEL_CASE, "/schoolType/2/a~0~1b.c"),
    (JsonFieldNamingProfile.SNAKE_CASE, "/school_type/2/a~0~1b.c"),
    (JsonFieldNamingProfile.PASCAL_CASE, "/SchoolType/2/A~0~1b.c"),
])
def test_literal_punctuation_and_indices_preserve_canonical_identity_in_all_wire_profiles(profile, pointer):
    import os
    path = ExpressionPath("E.node(<root>)", profile).member("school_type", "school_type")
    path = path.index(2).member("a~/b.c", "safe_field").mark_missing()
    wire = TeaQLNotLoadedError(path, "a~/b.c").terminal("eval()").to_wire()
    assert wire["instancePath"] == pointer
    assert wire["attemptedInstancePath"] == pointer
    assert wire["location"] == [{"kind":"property", "name":"school_type"},
                                {"kind":"index", "index":2}, {"kind":"property", "name":"a~/b.c"}]
    assert wire["attemptedLocation"] == wire["location"]
    assert wire["suggestedFix"]["location"] == wire["location"]
    assert wire["breakPointIndex"] == 2
    assert wire["breakPoint"] == "a~/b.c"
    assert wire["expressionWithBrokenPoint"] == "E.node(<root>).school_type().get(2).safe_field()<broken>.eval()"
    record = json.dumps({"language":"python", "profile":profile.value, "wire":wire})
    print("E_POINTER_PROFILE_CASE=" + record)
    if output := os.environ.get("TEAQL_POINTER_PROFILE_EVIDENCE"):
        with open(output, "a", encoding="utf-8") as stream:
            stream.write(record + "\n")


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
    assert str(error) == ("TeaQLNotLoadedError: access_path=parent break_point=parent"
                          " — select the missing field or relation expression="
                          + wire["expressionWithBrokenPoint"])
    assert json.loads(json.dumps(error.to_wire())) == wire


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
