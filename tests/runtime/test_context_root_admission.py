"""No implicit I/O or ownership rewrite at the generated save boundary."""
from copy import deepcopy
from itertools import product
from types import SimpleNamespace

import pytest

from teaql.core.value import Value
from teaql.runtime import (CheckException, ContextEntityRef, JsonFieldNamingProfile,
                           ObjectLocation, UserContext)


def check(context, action="Update", original=None, current=None, pending=None):
    context._validate_context_root_input("OrderItem", "account_root", "Account", action,
                                        original or {}, current or {}, pending or {})


def active(root_id=1):
    return UserContext.new().with_active_root(ContextEntityRef("Account", root_id))


@pytest.mark.parametrize("action", ["Update", "Delete"])
@pytest.mark.parametrize("carrier", [1, Value.I64(1), {"id": 1}, SimpleNamespace(id=1)])
def test_unchanged_loaded_ownership_is_not_pruned_with_an_unrelated_delta(action, carrier):
    original, current, pending = {"account_root": carrier}, {"account_root": carrier}, {"name": Value.Text("edited")}
    snapshot = deepcopy((original, current, pending))
    check(active(), action, original, current, pending)
    assert (original, current, pending) == snapshot
    with pytest.raises(CheckException) as error:
        check(active(2), action, original, current, pending)
    assert error.value.violations[0].rule_id == "context_root_mismatch"
    assert (original, current, pending) == snapshot


@pytest.mark.parametrize("source", ["original", "current", "pending"])
@pytest.mark.parametrize("bad", [None, 2, True, "1", -1])
def test_every_original_and_proposed_reference_is_checked(source, bad):
    values = {name: {"account_root": Value.I64(1)} for name in ("original", "current", "pending")}
    values[source]["account_root"] = bad
    with pytest.raises(CheckException) as error:
        check(active(), **values)
    wire = error.value.violations[0].to_wire()
    assert wire["ruleId"] == "context_root_mismatch" and wire["entityType"] == "OrderItem"
    assert wire["instancePath"] == "/accountRoot"
    assert "inputValue" not in wire and "systemValue" not in wire


@pytest.mark.parametrize("context", [UserContext.new(),
    UserContext.new().with_active_root(ContextEntityRef("OtherType", 1)),
    active(0), active(True), active("1")])
def test_untrusted_or_missing_context_root_fails_before_fix_and_provider(context):
    with pytest.raises(CheckException) as error:
        check(context, current={"account_root": Value.I64(1)})
    assert error.value.violations[0].rule_id == "context_root_missing"
    assert context.last_fix_evidence() == () and context.get_resource("fix_time") is None


def test_create_defers_only_an_absent_root_not_a_conflicting_one():
    check(active(), "Create")
    check(active(), "Create", current={"account_root": None})
    with pytest.raises(CheckException):
        check(active(), "Create", current={"account_root": 2})
    with pytest.raises(CheckException):
        check(active(), "Update")
    # Changing the in-memory field to match a new caller does not erase its old owner.
    with pytest.raises(CheckException):
        check(active(2), original={"account_root": 1}, current={"account_root": 2}, pending={"account_root": 2})


@pytest.mark.parametrize("locale,profile,rule", tuple(product(
    ("en", "zh-CN", "zh-TW", "ja", "ko", "de", "fr", "es", "pt", "ar", "th", "id", "fil", "uk", "vi"),
    tuple(JsonFieldNamingProfile), ("context_root_missing", "context_root_mismatch"))))
def test_root_diagnostics_preserve_full_canonical_path_and_render_all_profiles(locale, profile, rule):
    context = active(2).set_locale_code(locale) if rule.endswith("mismatch") else UserContext.new().set_locale_code(locale)
    with pytest.raises(CheckException) as error:
        check(context, current={"account_root": 1})
    prefix = ObjectLocation().property("purchase_order_list").index(0).property("order_item_list").index(0)
    result = error.value.violations[0].prefixed_by(prefix)
    context.translate_check_results([result])
    wire = result.to_wire(profile)
    assert wire["ruleId"] == rule and wire["entityType"] == "OrderItem"
    assert wire["instancePath"] == prefix.property("account_root").instance_path_for(profile)
    assert wire["location"][-1] == {"kind": "property", "name": "account_root"}
    assert "checker." not in wire["message"]
    # Human presentation no longer repeats the native path; the canonical path
    # and every machine segment remain unchanged. Unknown custom rules receive
    # a complete localized generic sentence and both owning collection positions.
    from teaql.runtime import Locale
    from teaql.runtime.checker_message_catalog import BUILTIN
    selected = Locale.parse(locale)
    classifier = "项" if selected in (Locale.CHINESE_SIMPLIFIED, Locale.CHINESE_TRADITIONAL) else ""
    owners = [BUILTIN.item(selected, name, 0, classifier) for name in ("purchase order list", "order item list")]
    expected = BUILTIN.select(selected, "checker.invalid", "deep").render({
        "field": "account root", "objectPath": BUILTIN.separator(selected).join(owners)})
    assert wire["message"] == expected
    assert result.location.model_path == "purchase_order_list[0].order_item_list[0].account_root"
    assert wire["location"] == [{"kind": "property", "name": "purchase_order_list"}, {"kind": "index", "index": 0},
        {"kind": "property", "name": "order_item_list"}, {"kind": "index", "index": 0}, {"kind": "property", "name": "account_root"}]
    assert "inputValue" not in wire and "systemValue" not in wire
