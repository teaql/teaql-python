from enum import Enum, auto
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Union
import json

class DataType(Enum):
    Bool = auto()
    I64 = auto()
    U64 = auto()
    F64 = auto()
    Decimal = auto()
    Text = auto()
    LargeText = auto()
    Json = auto()
    Date = auto()
    Timestamp = auto()

@dataclass
class Timestamp:
    millis: int

    def __eq__(self, other):
        if not isinstance(other, Timestamp):
            return False
        return self.millis == other.millis

class Value:
    # We use a single class to mimic the Rust enum for simplicity and type narrowing using .is_xxx() or match.
    def __init__(self, data: Any, type_hint: Optional[DataType] = None):
        self._data = data
        self._type_hint = type_hint

    @staticmethod
    def Null() -> 'Value':
        return Value(None)

    @staticmethod
    def Bool(v: bool) -> 'Value':
        return Value(v)

    @staticmethod
    def I64(v: int) -> 'Value':
        return Value(v, DataType.I64)

    @staticmethod
    def U64(v: int) -> 'Value':
        return Value(v, DataType.U64)

    @staticmethod
    def F64(v: float) -> 'Value':
        return Value(v)

    @staticmethod
    def Decimal(v: Decimal) -> 'Value':
        return Value(v)

    @staticmethod
    def Text(v: str) -> 'Value':
        return Value(v)

    @staticmethod
    def Json(v: Any) -> 'Value':
        return Value(v, DataType.Json)

    @staticmethod
    def Date(v: date) -> 'Value':
        return Value(v)

    @staticmethod
    def Timestamp(v: Timestamp) -> 'Value':
        return Value(v)

    @staticmethod
    def Object(v: Dict[str, 'Value']) -> 'Value':
        return Value(v, DataType.Json) # Or Object specific

    @staticmethod
    def List(v: List['Value']) -> 'Value':
        return Value(v, DataType.Json) # Or List specific

    @staticmethod
    def TypedNull(t: DataType) -> 'Value':
        return Value(None, t)

    def __eq__(self, other):
        if not isinstance(other, Value):
            return False
        return self._data == other._data and self._type_hint == other._type_hint

    @classmethod
    def from_any(cls, value: Any) -> 'Value':
        if isinstance(value, cls):
            return value
        if value is None:
            return cls.Null()
        if isinstance(value, bool):
            return cls.Bool(value)
        if isinstance(value, int):
            return cls.I64(value)
        if isinstance(value, float):
            return cls.F64(value)
        if isinstance(value, Decimal):
            return cls.Decimal(value)
        if isinstance(value, str):
            return cls.Text(value)
        if isinstance(value, date) and not isinstance(value, datetime):
            return cls.Date(value)
        if isinstance(value, Timestamp):
            return cls.Timestamp(value)
        if isinstance(value, datetime):
            return cls.Timestamp(Timestamp(int(value.timestamp() * 1000)))
        if isinstance(value, dict):
            return cls.Json(value)
        return cls.Text(str(value))

    def try_i64(self) -> Optional[int]:
        if self._data is None:
            return None
        if self._type_hint in (DataType.I64, DataType.U64) or isinstance(self._data, int) and not isinstance(self._data, bool):
            return int(self._data)
        if isinstance(self._data, Decimal):
            try:
                return int(self._data)
            except Exception:
                pass
        return None

    def try_u64(self) -> Optional[int]:
        val = self.try_i64()
        if val is not None and val >= 0:
            return val
        return None

    def try_decimal(self) -> Optional[Decimal]:
        if self._data is None:
            return None
        if isinstance(self._data, Decimal):
            return self._data
        if isinstance(self._data, int) and not isinstance(self._data, bool):
            return Decimal(self._data)
        if isinstance(self._data, str):
            try:
                return Decimal(self._data)
            except Exception:
                pass
        return None

    def try_f64(self) -> Optional[float]:
        if self._data is None:
            return None
        if isinstance(self._data, float):
            return self._data
        if isinstance(self._data, int) and not isinstance(self._data, bool):
            return float(self._data)
        if isinstance(self._data, Decimal):
            return float(self._data)
        return None

    def try_text(self) -> Optional[str]:
        if isinstance(self._data, str):
            return self._data
        return None

    def try_bool(self) -> Optional[bool]:
        if isinstance(self._data, bool):
            return self._data
        return None

    def try_date(self) -> Optional[date]:
        if isinstance(self._data, date) and not isinstance(self._data, datetime):
            return self._data
        if isinstance(self._data, str):
            try:
                return datetime.strptime(self._data, "%Y-%m-%d").date()
            except ValueError:
                pass
        if isinstance(self._data, int) and not isinstance(self._data, bool):
            try:
                return datetime.fromtimestamp(self._data / 1000.0, tz=timezone.utc).date()
            except Exception:
                pass
        return None

    def try_timestamp(self) -> Optional[Timestamp]:
        if isinstance(self._data, Timestamp):
            return self._data
        if isinstance(self._data, str):
            try:
                # ISO Format parsing, minimal implementation for RFC3339
                dt = datetime.fromisoformat(self._data.replace('Z', '+00:00'))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return Timestamp(int(dt.timestamp() * 1000))
            except Exception:
                pass
            try:
                dt = datetime.strptime(self._data, "%Y-%m-%d %H:%M:%S")
                dt = dt.replace(tzinfo=timezone.utc)
                return Timestamp(int(dt.timestamp() * 1000))
            except Exception:
                pass
            try:
                d = datetime.strptime(self._data, "%Y-%m-%d")
                d = d.replace(tzinfo=timezone.utc)
                return Timestamp(int(d.timestamp() * 1000))
            except Exception:
                pass
        if isinstance(self._data, int) and not isinstance(self._data, bool):
            return Timestamp(self._data)
        return None

    def to_json_value(self) -> Any:
        if self._data is None:
            return None
        if isinstance(self._data, (bool, int, float, str, dict, list)):
            return self._data
        if isinstance(self._data, Decimal):
            return str(self._data)
        if isinstance(self._data, date):
            return self._data.isoformat()
        if isinstance(self._data, Timestamp):
            return self._data.millis
        if isinstance(self._data, dict):
            # Object serialization
            return {k: v.to_json_value() if isinstance(v, Value) else v for k, v in self._data.items()}
        if isinstance(self._data, list):
            return [v.to_json_value() if isinstance(v, Value) else v for v in self._data]
        return None
    @classmethod
    def ValText(cls, v): return cls(v)
    @classmethod
    def val_u64(cls, v): return cls(v)
