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
