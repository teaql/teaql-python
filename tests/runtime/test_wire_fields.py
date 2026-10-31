import pytest
from teaql.runtime import CheckResult, JsonFieldNamingProfile, ObjectLocation, WireInputError, create_wire_entity_metadata, encode_wire_output, normalize_wire_input, retain_submitted_paths

def metadata():
    return create_wire_entity_metadata("School", ["name", "school_type"], JsonFieldNamingProfile.CAMEL_CASE, {"school_type": ["school_type"]})

def test_normalizes_declared_alias_and_retains_provenance():
    normalized = normalize_wire_input({"name": "Riverside", "school_type": 1001}, metadata(), "/school")
    assert dict(normalized.values) == {"name": "Riverside", "school_type": 1001}
    result = CheckResult("required", ObjectLocation().property("school_type"))
    assert retain_submitted_paths([result], normalized)[0].source_instance_path == "/school/school_type"

def test_rejects_unknown_and_collision():
    with pytest.raises(WireInputError) as unknown: normalize_wire_input({"not/known": 1}, metadata())
    assert (unknown.value.code, unknown.value.instance_path) == ("WIRE_UNKNOWN_FIELD", "/not~1known")
    with pytest.raises(WireInputError) as collision: normalize_wire_input({"schoolType": 1001, "school_type": 1002}, metadata())
    assert collision.value.code == "WIRE_FIELD_COLLISION"

def test_encodes_wire_output():
    assert dict(encode_wire_output({"school_type": 1001}, metadata())) == {"schoolType": 1001}
    with pytest.raises(ValueError, match="Unknown canonical"): encode_wire_output({"missing": 1}, metadata())

def test_parent_alias_never_truncates_descendant_provenance():
    meta = create_wire_entity_metadata("Order", ["order_item_list", "product_name"], aliases={"order_item_list": ["legacy/items"], "product_name": ["legacy~name"]})
    normalized = normalize_wire_input({"legacy/items": [], "legacy~name": None}, meta)
    location = ObjectLocation().property("order_item_list").index(2).property("product_name")
    exact = "/legacy~1items/2/legacy~0name"
    original = CheckResult("required", location, source_instance_path=exact)
    results = retain_submitted_paths([
        original, CheckResult("required", location),
        CheckResult("required", ObjectLocation().index(2).property("product_name")),
        CheckResult("required", ObjectLocation().property("order_item_list")),
    ], normalized)
    assert [r.source_instance_path for r in results] == [exact, None, None, "/legacy~1items"]
    assert results[0].location.instance_path == "/orderItemList/2/productName"
    assert original.source_instance_path == exact

@pytest.mark.parametrize("profile", [JsonFieldNamingProfile.CAMEL_CASE, JsonFieldNamingProfile.SNAKE_CASE, JsonFieldNamingProfile.PASCAL_CASE])
def test_standard_child_retains_ancestor_provenance(profile):
    parent = create_wire_entity_metadata("Order", ["order_item_list"], aliases={"order_item_list": ["legacy/items~"]})
    child = create_wire_entity_metadata("OrderItem", ["product_name", "unit_count"], profile)
    name = child.fields["product_name"].wire_name
    for value in (None, "submitted item"):
        child_object = {name: value}
        parent_input = normalize_wire_input({"legacy/items~": [{}, {}, child_object]}, parent)
        boundary = parent_input.source_instance_paths["order_item_list"] + "/2"
        normalized = normalize_wire_input(child_object, child, boundary)
        assert dict(normalized.values) == {"product_name": value}
        assert dict(normalized.source_instance_paths) == {"product_name": boundary + "/" + name}
        original = CheckResult("required", ObjectLocation().property("product_name"), entity_type="OrderItem")
        leaf = retain_submitted_paths([original], normalized)[0]
        location = ObjectLocation().property("order_item_list").index(2).property("product_name")
        prefixed = CheckResult(leaf.rule_id, location, entity_type=leaf.entity_type, source_instance_path=leaf.source_instance_path)
        actual = retain_submitted_paths([prefixed], parent_input)[0]
        assert actual.source_instance_path == "/legacy~1items~0/2/" + name
        assert actual.location == location
        assert original.source_instance_path is None
    assert dict(normalize_wire_input({name: None}, child).source_instance_paths) == {}
