"""Query-owned read-only projections do not turn unknown state into JSON input."""
from copy import deepcopy
from decimal import Decimal
import json
import math

import pytest

from teaql.core.projection_properties import ProjectionProperties
from teaql.core.query import SelectQuery
from teaql.runtime.entity_json import EntityJSONError, EntityJSONField, EntityJSONSchema
from teaql.runtime.i18n import JsonFieldNamingProfile
from teaql.runtime.query_properties import capture_entity_query_properties


class Node:
    def __init__(self, **values):
        known = ("id", "version", "displayName", "parent", "children")
        self._loaded_fields = set(values).intersection(known)
        self._projection_properties = ProjectionProperties(values, known)
        self.__dict__.update({name: value for name, value in values.items() if name in known})

    @property
    def _entity_root(self):
        pytest.fail("query properties must not inspect a mutation ledger")


Node._teaql_json_schema = SCHEMA = EntityJSONSchema("Node", (
    EntityJSONField("id", "id", "id"),
    EntityJSONField("version", "version", "version"),
    EntityJSONField("display_name", "displayName", "text"),
    EntityJSONField("parent", "parent", "reference", factory=lambda: Node),
    EntityJSONField("children", "children", "many", factory=lambda: Node),
))


def query(*aliases):
    result = SelectQuery("Node")
    for alias in aliases:
        result.sum("metric", alias)
    return result


@pytest.mark.parametrize("profile", list(JsonFieldNamingProfile))
def test_selected_properties_keep_null_zero_decimal_and_exact_large_int_without_loading_or_mutating(profile):
    source = {"id": 7, "version": 1, "total": None, "rows": 0,
              "amount_sum": Decimal("3.50"), "large": 2**63 - 1, "zero": -0.0,
              "private": {"authorization": "must never serialize"}}
    entity = Node(**source)
    before = set(entity._loaded_fields)
    capture_entity_query_properties(entity, query("total", "rows", "amount_sum", "large", "zero"))
    wire = json.loads(SCHEMA.dumps(entity, profile=profile))
    assert wire == {profile.render("id"): "7", profile.render("version"): "1", "total": None, "rows": 0,
                    "amount_sum": "3.50", "large": "9223372036854775807", "zero": -0.0}
    assert math.copysign(1, wire["zero"]) == -1
    assert entity._loaded_fields == before
    assert source["amount_sum"].as_tuple().exponent == -2
    assert "private" not in wire


def test_projection_views_are_immutable_snapshots_and_capture_cannot_change_a_shared_previous_view():
    raw = {"id": 1, "a": [1, None], "b": 0}
    original = ProjectionProperties(raw, ("id",))
    selected = original.with_selected_aliases(["a"])
    assert deepcopy(original) is original and deepcopy(selected) is selected
    raw["a"].append(2)
    values = selected.selected_values()
    values["a"].append(3)
    assert selected.selected_values() == {"a": [1, None]}
    assert original.selected_values() == {}
    assert selected.with_selected_aliases(["b"]).selected_values() == {"b": 0}


@pytest.mark.parametrize("alias", ["id", "version", "display_name", "displayName", "DisplayName", "children"])
def test_query_aliases_cannot_shadow_any_modeled_native_or_json_profile_name(alias):
    entity = Node(id=1, **{alias: 1}) if alias != "id" else Node(id=1)
    old = entity._projection_properties
    with pytest.raises(EntityJSONError) as error:
        capture_entity_query_properties(entity, query(alias))
    assert error.value.code == "WIRE_QUERY_PROPERTY_COLLISION"
    assert entity._projection_properties is old


def test_missing_selected_alias_is_not_silently_fabricated_as_null():
    with pytest.raises(ValueError, match="not present"):
        capture_entity_query_properties(Node(id=1), query("missing"))


def test_duplicate_selected_alias_is_rejected():
    with pytest.raises(ValueError, match="Duplicate"):
        capture_entity_query_properties(Node(id=1, total=0), query("total", "total"))


def test_only_explicitly_loaded_relations_are_visited_and_selected():
    child = Node(id=2, total=None)
    unloaded = Node(id=3, total=0)
    root = Node(id=1, children=[child], parent=unloaded)
    root._loaded_fields.remove("parent")
    request = query().relation_query("children", query("total")).relation_query("parent", query("total"))
    capture_entity_query_properties(root, request)
    assert child._projection_properties.selected_values() == {"total": None}
    assert unloaded._projection_properties.selected_values() == {}
    assert json.loads(SCHEMA.dumps(root)) == {"id": "1", "children": [{"id": "2", "total": None}]}


def test_late_child_collision_does_not_partially_replace_any_graph_snapshot():
    child = Node(id=2, displayName="valid model value")
    root = Node(id=1, total=None, children=[child])
    old = root._projection_properties
    with pytest.raises(EntityJSONError):
        capture_entity_query_properties(root, query("total").relation_query("children", query("displayName")))
    assert root._projection_properties is old
    assert old.selected_values() == {}


def test_unselected_unknown_fields_stay_private_and_projection_input_stays_unknown():
    entity = Node(id=7, total=None, private={"cookie": "sensitive"}, arbitrary=object())
    assert json.loads(SCHEMA.dumps(entity)) == {"id": "7"}
    capture_entity_query_properties(entity, query("total"))
    wire = SCHEMA.dumps(entity)
    assert json.loads(wire) == {"id": "7", "total": None}
    with pytest.raises(EntityJSONError) as error:
        SCHEMA.loads(Node, wire)
    assert error.value.code == "WIRE_UNKNOWN_FIELD"
    assert error.value.instance_path == "/total"


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf, Decimal("NaN"),
                                   Decimal("Infinity"), Decimal("1E+1000000"), 2**64, object()])
def test_query_properties_cannot_bypass_native_scalar_and_size_guards(value):
    entity = capture_entity_query_properties(Node(id=1, total=value), query("total"))
    with pytest.raises(EntityJSONError) as error:
        SCHEMA.dumps(entity)
    assert error.value.instance_path == "/total"


def test_selected_objects_obey_the_same_depth_and_output_limits():
    nested = {}
    for _ in range(70):
        nested = {"next": nested}
    entity = capture_entity_query_properties(Node(id=1, total=nested), query("total"))
    with pytest.raises(EntityJSONError) as error:
        SCHEMA.dumps(entity)
    assert error.value.code == "WIRE_JSON_LIMIT"
    huge = capture_entity_query_properties(Node(id=1, total="x" * (1024 * 1024)), query("total"))
    with pytest.raises(EntityJSONError) as error:
        SCHEMA.dumps(huge)
    assert error.value.code == "WIRE_JSON_LIMIT"


def test_query_graph_depth_failure_keeps_previous_views_unchanged():
    root = current = Node(id=1, total=0)
    request = current_query = query("total")
    for index in range(66):
        child = Node(id=index + 2, total=0)
        current.children = [child]
        current._loaded_fields.add("children")
        nested = query("total")
        # This is a malformed native unit input, not a generated application.
        from teaql.core.query import RelationLoad
        current_query.relations.append(RelationLoad("children", nested))
        current, current_query = child, nested
    original = root._projection_properties
    with pytest.raises(ValueError, match="depth limit"):
        capture_entity_query_properties(root, request)
    assert root._projection_properties is original
