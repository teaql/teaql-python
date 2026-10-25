from datetime import date, datetime, time, timezone
from decimal import Decimal
import json
import math

import pytest

from teaql.runtime.entity_json import EntityJSONError, EntityJSONField, EntityJSONSchema
from teaql.runtime.i18n import JsonFieldNamingProfile


class Node:
    def __init__(self, **values):
        self._loaded_fields = set(values)
        self._children = values.pop("children", [])
        self.__dict__.update(values)
        self._entity_root = object()


FIELDS = (
    EntityJSONField("id", "id", "id"),
    EntityJSONField("version", "version", "version"),
    EntityJSONField("display_name", "displayName", "text"),
    EntityJSONField("active", "active", "boolean"),
    EntityJSONField("count_value", "countValue", "integer"),
    EntityJSONField("long_value", "longValue", "long"),
    EntityJSONField("amount", "amount", "decimal"),
    EntityJSONField("float_value", "floatValue", "float"),
    EntityJSONField("double_value", "doubleValue", "double"),
    EntityJSONField("calendar_date", "calendarDate", "date"),
    EntityJSONField("wall_time", "wallTime", "time"),
    EntityJSONField("occurred_at", "occurredAt", "datetime"),
    EntityJSONField("payload", "payload", "json"),
    EntityJSONField("parent", "parent", "reference", factory=lambda: Node),
    EntityJSONField("children", "_children", "many", factory=lambda: Node, loaded_name="children"),
)
Node._teaql_json_schema = SCHEMA = EntityJSONSchema("Node", FIELDS)


def populated():
    return Node(id=7, version=2, displayName="", active=False, countValue=-(2**31), longValue=2**63 - 1,
        amount=Decimal("123456789012.3456789"), floatValue=1.25, doubleValue=-0.125,
        calendarDate=date(2024, 2, 29), wallTime=time(23, 59, 59, 123456),
        occurredAt=datetime(2024, 2, 29, 12, 34, 56, 789000, timezone.utc),
        payload={"nested": [0, False, None, "Unicode 精确值"]}, parent=1, children=[])


@pytest.mark.parametrize("profile", list(JsonFieldNamingProfile))
def test_exact_scalars_and_presence_roundtrip_in_all_profiles(profile):
    original = populated()
    wire = SCHEMA.dumps(original, profile=profile)
    values = json.loads(wire)
    assert values[profile.render("long_value")] == "9223372036854775807"
    assert values[profile.render("amount")] == "123456789012.3456789"
    assert values[profile.render("id")] == "7" and values[profile.render("version")] == "2"
    assert values[profile.render("count_value")] == -(2**31)
    assert values[profile.render("display_name")] == ""
    assert values[profile.render("active")] is False
    assert not any(key.startswith("_") for key in values)
    decoded = SCHEMA.loads(Node, wire, profile=profile)
    assert decoded._loaded_fields == original._loaded_fields
    for field in FIELDS:
        expected = getattr(original, field.native_name)
        actual = getattr(decoded, field.native_name)
        assert type(actual) is type(expected) and actual == expected, field
    assert decoded._entity_root is not original._entity_root


def test_loaded_null_and_not_loaded_are_distinct_without_touching_unselected_attributes():
    class Sparse:
        _loaded_fields = {"id", "displayName"}
        id = 1
        displayName = None
        @property
        def amount(self):
            pytest.fail("serializer accessed an unselected field")
    wire = SCHEMA.dumps(Sparse())
    assert json.loads(wire) == {"id": "1", "displayName": None}
    decoded = SCHEMA.loads(Node, wire)
    assert decoded._loaded_fields == {"id", "displayName"}
    assert decoded.displayName is None and not hasattr(decoded, "amount")


def test_nested_trees_and_empty_relations_preserve_loaded_state_and_types():
    child = populated()
    child.id = 8
    child._loaded_fields.discard("parent")
    original = Node(id=1, version=3, parent=Node(id=2, displayName=None), children=[child])
    decoded = SCHEMA.loads(Node, SCHEMA.dumps(original))
    assert isinstance(decoded.parent, Node) and decoded.parent.id == 2
    assert decoded.parent._loaded_fields == {"id", "displayName"}
    assert decoded.parent.displayName is None
    assert len(decoded._children) == 1 and decoded._children[0].id == 8
    assert decoded._children[0].amount == child.amount
    assert "parent" not in decoded._children[0]._loaded_fields
    assert "children" in decoded._children[0]._loaded_fields and decoded._children[0]._children == []


@pytest.mark.parametrize("field,value", [
    ("active", 1), ("countValue", True), ("countValue", 1.5), ("countValue", 2**31),
    ("longValue", 9007199254740993), ("longValue", "9223372036854775808"),
    ("longValue", " 1"), ("longValue", "01"), ("longValue", "+1"),
    ("id", "-1"), ("id", "18446744073709551616"), ("version", "9223372036854775808"),
    ("amount", 1.25), ("amount", "NaN"), ("amount", "Infinity"), ("amount", "1e999999"),
    ("displayName", 3), ("doubleValue", "1.0"),
    ("calendarDate", "2024-02-30"), ("calendarDate", "2024-W09-4"),
    ("wallTime", "24:00:00"), ("wallTime", "12:00:00Z"), ("wallTime", "12:00:00.1234567"),
    ("occurredAt", "2024-01-01T00:00:00"), ("occurredAt", "2024-01-01T00:00:00.123456Z"),
    ("parent", 4), ("children", {}), ("children", None),
])
def test_invalid_wire_scalars_are_precise_errors_not_silent_coercions(field, value):
    with pytest.raises(EntityJSONError) as error:
        SCHEMA.loads(Node, json.dumps({field: value}))
    assert error.value.instance_path == "/" + field
    assert error.value.code.startswith("WIRE_")
    assert str(value) not in str(error.value)


@pytest.mark.parametrize("kind", ["float", "double"])
@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
def test_nonfinite_values_cannot_be_encoded(kind, value):
    native = kind + "Value"
    with pytest.raises(EntityJSONError) as error:
        SCHEMA.dumps(Node(**{native: value}))
    assert error.value.instance_path == "/" + native


@pytest.mark.parametrize("wire", [
    '{"displayName":"a","displayName":"b"}',
    '{"displayName":"a","display_name":"b"}',
    '{"payload":{"a":1,"a":2}}',
    '{"_entity_root":{}}', '{"unknownField":1}',
    '{"floatValue":NaN}', '{"doubleValue":Infinity}', '{"doubleValue":1e9999}',
    '[]', 'null', 'true', '1',
])
def test_ambiguous_private_nonstandard_or_nonobject_inputs_fail_closed(wire):
    with pytest.raises(EntityJSONError):
        SCHEMA.loads(Node, wire)


def test_nested_error_retains_canonical_location_and_actual_json_pointer():
    with pytest.raises(EntityJSONError) as error:
        SCHEMA.loads(Node, '{"children":[{"countValue":true}]}')
    assert error.value.location.model_path == "children[0].count_value"
    assert error.value.instance_path == "/children/0/countValue"
    assert error.value.to_wire()["instancePath"] == "/children/0/countValue"


def test_cycles_fail_explicitly_and_do_not_turn_into_hidden_reference_or_database_lookups():
    original = Node(id=1)
    original.parent = original
    original._loaded_fields.add("parent")
    with pytest.raises(EntityJSONError) as error:
        SCHEMA.dumps(original)
    assert error.value.code == "WIRE_ENTITY_CYCLE" and error.value.instance_path == "/parent"


def test_exact_decimal_scale_and_negative_zero_are_preserved():
    for value in [Decimal("3.50"), Decimal("-0.00"), Decimal("1e-1000"), Decimal("1e1000")]:
        decoded = SCHEMA.loads(Node, SCHEMA.dumps(Node(amount=value))).amount
        assert decoded.as_tuple() == value.as_tuple() or (decoded == value and value.as_tuple().exponent > 0)
    for value in [Decimal("NaN"), Decimal("Infinity"), Decimal("1e100000000")]:
        with pytest.raises(EntityJSONError):
            SCHEMA.dumps(Node(amount=value))


def test_timestamp_roundtrip_is_utc_and_rejects_native_precision_loss():
    from datetime import timedelta
    value = datetime(2024, 2, 29, 20, 34, 56, 789000, timezone(timedelta(hours=8)))
    wire = SCHEMA.dumps(Node(occurredAt=value))
    assert json.loads(wire)["occurredAt"] == "2024-02-29T12:34:56.789Z"
    assert SCHEMA.loads(Node, wire).occurredAt == value
    for bad in [value.replace(tzinfo=None), value.replace(microsecond=789001)]:
        with pytest.raises(EntityJSONError):
            SCHEMA.dumps(Node(occurredAt=bad))


def test_model_profile_can_be_overridden_without_changing_native_attributes():
    schema = EntityJSONSchema("SnakeNode", FIELDS, profile=JsonFieldNamingProfile.SNAKE_CASE)
    assert json.loads(schema.dumps(Node(displayName="example"))) == {"display_name": "example"}
    assert schema.loads(Node, '{"display_name":"example"}').displayName == "example"
    assert json.loads(schema.dumps(Node(displayName="example"), profile="PascalCase")) == {"DisplayName": "example"}


def test_profile_limits_and_text_errors_fail_explicitly_in_both_directions():
    schema = EntityJSONSchema("Small", FIELDS, max_json_bytes=64)
    for text in ["a" * 80, "精" * 20]:
        with pytest.raises(EntityJSONError) as error:
            schema.dumps(Node(displayName=text))
        assert error.value.code == "WIRE_JSON_LIMIT"
        with pytest.raises(EntityJSONError):
            schema.loads(Node, json.dumps({"displayName": text}, ensure_ascii=False))
    with pytest.raises(EntityJSONError) as error:
        SCHEMA.dumps(Node(displayName="\ud800"))
    assert error.value.code == "WIRE_INVALID_TEXT"


def test_full_identity_and_version_ranges_do_not_go_through_binary_float():
    original = Node(id=2**64 - 1, version=-(2**63), longValue=-(2**63))
    wire = SCHEMA.dumps(original)
    assert json.loads(wire) == {"id": "18446744073709551615", "version": "-9223372036854775808",
        "longValue": "-9223372036854775808"}
    decoded = SCHEMA.loads(Node, wire)
    assert decoded.id == original.id and decoded.version == original.version and decoded.longValue == original.longValue


def test_business_id_factory_and_temporal_precision_error_are_preserved():
    from dataclasses import dataclass
    @dataclass(frozen=True)
    class BusinessID:
        value: str
    schema = EntityJSONSchema("BusinessNode", (EntityJSONField("order_number", "orderNumber", "business_id", factory=lambda: BusinessID),))
    decoded = schema.loads(Node, schema.dumps(Node(orderNumber=BusinessID("ORD-X4K2P9"))))
    assert type(decoded.orderNumber) is BusinessID and decoded.orderNumber.value == "ORD-X4K2P9"
    with pytest.raises(EntityJSONError) as error:
        SCHEMA.loads(Node, '{"occurredAt":"2024-01-01T00:00:00.000001Z"}')
    assert error.value.code == "WIRE_TEMPORAL_PRECISION"
