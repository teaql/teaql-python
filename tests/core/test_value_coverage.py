import pytest
from teaql.core.value import Value, DataType, Timestamp
from datetime import date, datetime, timezone
from decimal import Decimal

def test_value_types():
    assert Value.Null().is_null()
    assert Value.Bool(True).val is True
    assert Value.I64(1).val == 1
    assert Value.U64(1).val == 1
    assert Value.F64(1.5).val == 1.5
    assert Value.Decimal(Decimal("1.5")).val == Decimal("1.5")
    assert Value.Text("A").val == "A"
    assert Value.Json({"a": 1}).val == {"a": 1}
    assert Value.Date(date(2020, 1, 1)).val == date(2020, 1, 1)
    
    t = Timestamp(1000)
    assert Value.Timestamp(t).val == t
    
    assert Value.Object({"a": Value.I64(1)}).val == {"a": Value.I64(1)}
    assert Value.List([Value.I64(1)]).val == [Value.I64(1)]
    assert Value.TypedNull(DataType.I64).is_null()

def test_value_methods():
    v = Value.I64(123)
    assert v.entity_id_value() == "123"
    assert Value.Json({"a": 1}).object() == {"a": 1}
    
    assert Value.Null().teaql_is_empty() is True
    assert Value.Text("").teaql_is_empty() is True
    assert Value.Text("A").teaql_is_empty() is False
    assert Value.Json({}).teaql_is_empty() is True
    assert Value.List([]).teaql_is_empty() is True

def test_value_from_any():
    assert Value.from_any(None).is_null()
    assert Value.from_any(True).val is True
    assert Value.from_any(1).val == 1
    assert Value.from_any(1.5).val == 1.5
    assert Value.from_any(Decimal("1.5")).val == Decimal("1.5")
    assert Value.from_any("A").val == "A"
    assert Value.from_any(date(2020, 1, 1)).val == date(2020, 1, 1)
    assert Value.from_any(Timestamp(1000)).val == Timestamp(1000)
    
    dt = datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    assert isinstance(Value.from_any(dt).val, Timestamp)
    
    assert Value.from_any({"a": 1}).val == {"a": 1}
    
    v = Value.I64(1)
    assert Value.from_any(v) == v

def test_value_try_methods():
    assert Value.from_any(1).try_i64() == 1
    assert Value.from_any("1").try_i64() is None
    
    assert Value.from_any(1).try_u64() == 1
    assert Value.from_any(-1).try_u64() is None
    
    assert Value.from_any(1).try_decimal() == Decimal("1")
    assert Value.from_any(1.5).try_f64() == 1.5
    assert Value.from_any("A").try_text() == "A"
    assert Value.from_any(True).try_bool() is True
    
    assert Value.from_any(date(2020, 1, 1)).try_date() == date(2020, 1, 1)
    assert Value.from_any("2020-01-01").try_date() == date(2020, 1, 1)
    
    assert Value.from_any(Timestamp(1000)).try_timestamp() == Timestamp(1000)
    assert Value.from_any("2020-01-01 00:00:00").try_timestamp() is not None

def test_to_json_value():
    assert Value.from_any(1).to_json_value() == 1
    assert Value.from_any(Decimal("1.5")).to_json_value() == "1.5"
    assert Value.from_any(date(2020, 1, 1)).to_json_value() == "2020-01-01"
    assert Value.from_any(Timestamp(1000)).to_json_value() == 1000
    assert Value.from_any({"a": Value.I64(1)}).to_json_value() == {"a": 1}
    assert Value.from_any([Value.I64(1)]).to_json_value() == [1]

def test_class_methods():
    assert Value.ValText("a").val == "a"
    assert Value.val_u64(1).val == 1
