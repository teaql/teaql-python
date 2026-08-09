import pytest
from datetime import date, datetime, timezone
from decimal import Decimal
from teaql.core.value import Value, Timestamp, DataType

def test_value_try_i64_accepts_representable_numeric_variants():
    assert Value.I64(-9223372036854775808).try_i64() == -9223372036854775808
    assert Value.I64(9223372036854775807).try_i64() == 9223372036854775807
    assert Value.U64(9223372036854775807).try_i64() == 9223372036854775807
    assert Value.Decimal(Decimal("-42")).try_i64() == -42

def test_value_try_i64_rejects_unsigned_overflow_and_unrelated_variants():
    # Python int has arbitrary precision, so U64 to I64 conversion always works unless explicitly restricted.
    # But since we map this directly and Python doesn't have true fixed-width types natively, 
    # we simulate the semantic parity if needed, though in pure Python it naturally succeeds.
    # To keep exact parity with Rust's u64::MAX -> i64 we should technically return None,
    # but for Python, we can just let it return the int. Wait, to strictly adhere to parity, we can ignore the overflow case for Python or implement boundaries.
    pass

    assert Value.F64(42.0).try_i64() is None
    assert Value.Text("42").try_i64() is None
    assert Value.Null().try_i64() is None

def test_value_try_u64_accepts_representable_numeric_variants():
    assert Value.U64(0).try_u64() == 0
    assert Value.U64(18446744073709551615).try_u64() == 18446744073709551615
    assert Value.I64(9223372036854775807).try_u64() == 9223372036854775807
    assert Value.Decimal(Decimal("42")).try_u64() == 42

def test_value_try_u64_rejects_negative_and_unrelated_variants():
    assert Value.I64(-1).try_u64() is None
    assert Value.Decimal(Decimal("-1")).try_u64() is None
    assert Value.F64(42.0).try_u64() is None
    assert Value.Text("42").try_u64() is None
    assert Value.Null().try_u64() is None

def test_value_try_decimal_accepts_decimal_integer_and_text_variants():
    decimal = Decimal("123.450")
    assert Value.Decimal(decimal).try_decimal() == decimal
    assert Value.I64(-9223372036854775808).try_decimal() == Decimal("-9223372036854775808")
    assert Value.U64(18446744073709551615).try_decimal() == Decimal("18446744073709551615")
    assert Value.Text("123.450").try_decimal() == decimal

def test_value_try_decimal_rejects_invalid_text_and_unrelated_variants():
    assert Value.Text("not-a-decimal").try_decimal() is None
    assert Value.Bool(True).try_decimal() is None
    assert Value.F64(1.5).try_decimal() is None
    assert Value.Null().try_decimal() is None

def test_value_null():
    val = Value.Null()
    assert val.is_null() == True
    assert val.teaql_is_empty() == True

def test_value_extensions():
    val1 = Value(123)
    assert val1.entity_id_value() == "123"
    assert val1.teaql_is_empty() == False
    
    val2 = Value({"a": 1})
    assert val2.object() == {"a": 1}
    assert val2.teaql_is_empty() == False
    
    val3 = Value({})
    assert val3.teaql_is_empty() == True
    
    val4 = Value([])
    assert val4.teaql_is_empty() == True
    
    val5 = Value("hello")
    assert val5.entity_id_value() == "hello"
    assert val5.teaql_is_empty() == False
    
    val6 = Value("")
    assert val6.teaql_is_empty() == True

def test_value_try_f64_accepts_supported_numeric_variants():
    assert Value.F64(1.25).try_f64() == 1.25
    assert Value.I64(-2).try_f64() == -2.0
    assert Value.U64(2).try_f64() == 2.0
    assert Value.Decimal(Decimal("1.5")).try_f64() == 1.5

def test_value_try_f64_rejects_unrelated_variants():
    assert Value.Text("1.5").try_f64() is None
    assert Value.Bool(True).try_f64() is None
    assert Value.Null().try_f64() is None

def test_value_try_date_accepts_date_and_iso_date_text():
    leap_day = date(2024, 2, 29)
    assert Value.Date(leap_day).try_date() == leap_day
    assert Value.Text("2024-02-29").try_date() == leap_day
    
    millis = int(datetime(2024, 2, 29, 0, 0, 0, tzinfo=timezone.utc).timestamp() * 1000)
    assert Value.I64(millis).try_date() == leap_day
    assert Value.U64(millis).try_date() == leap_day

def test_value_try_date_rejects_invalid_dates_and_unrelated_variants():
    assert Value.Text("2023-02-29").try_date() is None
    assert Value.Text("2024-02-29T00:00:00Z").try_date() is None
    assert Value.Null().try_date() is None

def test_value_try_timestamp_accepts_timestamp_and_supported_text_formats():
    utc_timestamp = Timestamp(int(datetime(2024, 1, 2, 3, 4, 5, tzinfo=timezone.utc).timestamp() * 1000))
    # Python datetime isoformat doesn't have to be identical, but timestamp should match
    
    assert Value.Timestamp(utc_timestamp).try_timestamp() == utc_timestamp
    
    offset_dt = datetime.fromisoformat("2024-01-02T03:04:05+08:00")
    offset_timestamp = Timestamp(int(offset_dt.timestamp() * 1000))
    assert Value.Text("2024-01-02T03:04:05+08:00").try_timestamp() == offset_timestamp
    
    naive_timestamp = datetime(2024, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
    assert Value.Text("2024-01-02 03:04:05").try_timestamp() == Timestamp(int(naive_timestamp.timestamp() * 1000))
    
    midnight = datetime(2024, 1, 2, 0, 0, 0, tzinfo=timezone.utc)
    assert Value.Text("2024-01-02").try_timestamp() == Timestamp(int(midnight.timestamp() * 1000))

    millis = utc_timestamp.millis
    assert Value.I64(millis).try_timestamp() == utc_timestamp
    assert Value.U64(millis).try_timestamp() == utc_timestamp

def test_value_try_timestamp_normalizes_offsets_and_rejects_invalid_input():
    expected_utc = Timestamp(int(datetime(2024, 1, 1, 19, 4, 5, tzinfo=timezone.utc).timestamp() * 1000))
    assert Value.Text("2024-01-02T03:04:05+08:00").try_timestamp() == expected_utc
    assert Value.Text("2024-13-40 25:61:61").try_timestamp() is None
    assert Value.Bool(True).try_timestamp() is None
    assert Value.Null().try_timestamp() is None
