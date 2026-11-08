"""Model-owned typed JSON, independent of persistence and transport authorization.

Generated schemas supply names, types and relation factories. Presence alone
restores a loaded field; a JSON null is never confused with an absent property.
This codec is not an HTTP authorization or context-bound reference adapter.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal, InvalidOperation
from functools import lru_cache
import json
import math
import re
from typing import Callable

from teaql.core.value import Timestamp, Value
from teaql.core.projection_properties import ProjectionProperties
from .i18n import JsonFieldNamingProfile, ObjectLocation
from .wire_fields import WireInputError, create_wire_entity_metadata

_KINDS = frozenset(("id", "version", "long", "integer", "text", "boolean", "decimal",
    "float", "double", "date", "time", "datetime", "json", "reference", "many", "business_id"))
_INTEGER = re.compile(r"-?(?:0|[1-9][0-9]*)\Z")
_DECIMAL = re.compile(r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?\Z")
_DATE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}\Z")
_TIME = re.compile(r"[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,6})?\Z")
_DATETIME = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}"
    r"(?:\.[0-9]{1,6})?(?:Z|[+-][0-9]{2}:[0-9]{2})\Z")
_MAX_TEXT = 4096
_MAX_JSON_BYTES = 1024 * 1024
_MAX_DEPTH = 64
_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)


class EntityJSONError(WireInputError):
    """Precise canonical and submitted paths, without echoing private values."""
    def __init__(self, code, location, instance_path, message):
        super().__init__(code, instance_path, message)
        self.location = location

    def to_wire(self):
        return {"code": self.code, "location": [
            {"kind": kind, "name" if kind == "property" else "index": value}
            for kind, value in self.location.segments],
            "instancePath": self.instance_path, "message": str(self)}


@dataclass(frozen=True)
class EntityJSONField:
    canonical_name: str
    native_name: str
    kind: str
    factory: Callable[[], type] | None = None
    loaded_name: str | None = None

    def __post_init__(self):
        if not self.canonical_name or not self.native_name or self.kind not in _KINDS:
            raise ValueError("Invalid generated JSON field metadata")
        if self.kind in ("reference", "many", "business_id") and self.factory is None:
            raise ValueError("Generated JSON field requires its model-owned factory")


class _ObjectPairs(list):
    """Retain duplicate names until the schema can attach their exact path."""


def _pointer(parent, name):
    return parent + "/" + str(name).replace("~", "~0").replace("/", "~1")


def _error(location, pointer, message="Expected the declared logical JSON type", code="WIRE_INVALID_TYPE"):
    raise EntityJSONError(code, location, pointer, message)


def _profile(value):
    if isinstance(value, JsonFieldNamingProfile):
        return value
    return JsonFieldNamingProfile.parse(value)


def _unwrap(value):
    return value.val if isinstance(value, Value) else value


def _text(value, location, pointer):
    if not isinstance(value, str):
        _error(location, pointer)
    try:
        value.encode("utf-8")
    except UnicodeError:
        _error(location, pointer, "Expected valid Unicode text", "WIRE_INVALID_TEXT")
    return value


def _integer(value, kind, decoding, location, pointer):
    if decoding and kind != "integer":
        if not isinstance(value, str) or len(value) > 21 or not _INTEGER.fullmatch(value):
            _error(location, pointer, "Expected an exact integer string")
        value = int(value)
    if type(value) is not int:
        _error(location, pointer)
    lower, upper = (-(2**31), 2**31 - 1) if kind == "integer" else (
        (0, 2**64 - 1) if kind in ("id", "reference") else (-(2**63), 2**63 - 1))
    if not lower <= value <= upper:
        _error(location, pointer, "Integer is outside the declared model range", "WIRE_INTEGER_RANGE")
    return value if decoding or kind == "integer" else str(value)


def _decimal(value, decoding, location, pointer):
    if decoding:
        if not isinstance(value, str) or len(value) > _MAX_TEXT or not _DECIMAL.fullmatch(value):
            _error(location, pointer, "Expected a bounded exact Decimal string")
        try:
            return Decimal(value)
        except InvalidOperation:
            _error(location, pointer)
    if not isinstance(value, Decimal) or not value.is_finite():
        _error(location, pointer, "Expected a finite native Decimal")
    sign, digits, exponent = value.as_tuple()
    # Bound expansion before format(); a tiny exponent-form Decimal must not
    # cause an unbounded allocation or silently round under a decimal context.
    if max(len(digits) + max(exponent, 0), max(-exponent, 0) + 2) + sign > _MAX_TEXT:
        _error(location, pointer, "Decimal exceeds the JSON precision profile", "WIRE_DECIMAL_LIMIT")
    result = format(value, "f")
    if len(result) > _MAX_TEXT:
        _error(location, pointer, "Decimal exceeds the JSON precision profile", "WIRE_DECIMAL_LIMIT")
    return result


def _temporal(value, kind, decoding, location, pointer):
    try:
        if decoding:
            if not isinstance(value, str):
                _error(location, pointer)
            pattern = {"date": _DATE, "time": _TIME, "datetime": _DATETIME}[kind]
            if not pattern.fullmatch(value):
                _error(location, pointer)
            value = {"date": date.fromisoformat, "time": time.fromisoformat,
                "datetime": datetime.fromisoformat}[kind](value.replace("Z", "+00:00"))
        if kind == "date":
            if type(value) is not date:
                _error(location, pointer)
            return value if decoding else value.isoformat()
        if kind == "time":
            if type(value) is not time or value.utcoffset() is not None:
                _error(location, pointer)
            return value if decoding else value.isoformat()
        if isinstance(value, Timestamp):
            value = _EPOCH + timedelta(milliseconds=value.millis)
        if not isinstance(value, datetime) or value.utcoffset() is None:
            _error(location, pointer, "Expected an offset-aware DateTime")
        if value.microsecond % 1000:
            _error(location, pointer, "DateTime requires millisecond resolution", "WIRE_TEMPORAL_PRECISION")
        value = value.astimezone(timezone.utc)
        return value if decoding else value.isoformat(timespec="milliseconds").replace("+00:00", "Z")
    except EntityJSONError:
        raise
    except (ValueError, OverflowError):
        _error(location, pointer)


def _json_value(value, location, pointer, depth):
    if depth > _MAX_DEPTH:
        _error(location, pointer, "JSON depth limit exceeded", "WIRE_JSON_LIMIT")
    value = _unwrap(value)
    if value is None or type(value) in (bool, int):
        return value
    if isinstance(value, str):
        return _text(value, location, pointer)
    if isinstance(value, float):
        if not math.isfinite(value):
            _error(location, pointer, "Expected a finite JSON number")
        return value
    if isinstance(value, (dict, _ObjectPairs)):
        result = {}
        pairs = value if isinstance(value, _ObjectPairs) else value.items()
        for key, child in pairs:
            _text(key, location, pointer)
            child_location, child_pointer = location.property(key), _pointer(pointer, key)
            if key in result:
                _error(child_location, child_pointer, "Duplicate JSON property", "WIRE_FIELD_COLLISION")
            result[key] = _json_value(child, child_location, child_pointer, depth + 1)
        return result
    if isinstance(value, list):
        return [_json_value(child, location.index(index), _pointer(pointer, index), depth + 1)
            for index, child in enumerate(value)]
    _error(location, pointer)


class EntityJSONSchema:
    """Reusable generated schema; per-object state is only read, never changed."""
    def __init__(self, entity_type, fields, *, profile=JsonFieldNamingProfile.CAMEL_CASE, max_json_bytes=_MAX_JSON_BYTES):
        self.entity_type, self.fields = entity_type, tuple(fields)
        self.profile = _profile(profile)
        if type(max_json_bytes) is not int or max_json_bytes <= 0:
            raise ValueError("JSON byte limit must be positive")
        self.max_json_bytes = max_json_bytes
        if len({field.canonical_name for field in self.fields}) != len(self.fields):
            raise ValueError("Duplicate generated JSON field")
        if len({field.native_name for field in self.fields}) != len(self.fields):
            raise ValueError("Duplicate generated JSON native attribute")

    @lru_cache(maxsize=512)
    def _wire(self, profile):
        return create_wire_entity_metadata(self.entity_type, [field.canonical_name for field in self.fields],
            profile, {field.canonical_name: (field.canonical_name,) for field in self.fields})

    @lru_cache(maxsize=512)
    def _query_reserved_names(self):
        return frozenset(name for field in self.fields for name in (
            field.canonical_name, field.native_name, field.loaded_name or field.native_name,
            *(profile.render(field.canonical_name) for profile in JsonFieldNamingProfile)))

    def dumps(self, entity, *, profile=None):
        value = self._encode_entity(entity, self.profile if profile is None else _profile(profile), ObjectLocation(), "", set(), 0)
        text = json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
        if len(text.encode("utf-8")) > self.max_json_bytes:
            _error(ObjectLocation(), "", "JSON byte limit exceeded", "WIRE_JSON_LIMIT")
        return text

    def loads(self, entity_class, text, *, profile=None):
        if not isinstance(text, (str, bytes, bytearray)) or len(text) > self.max_json_bytes:
            _error(ObjectLocation(), "", "Expected a bounded JSON object", "WIRE_JSON_LIMIT")
        def invalid_constant(_value):
            _error(ObjectLocation(), "", "Nonstandard JSON numbers are not allowed", "WIRE_INVALID_JSON")
        try:
            if isinstance(text, str) and len(text.encode("utf-8")) > self.max_json_bytes:
                _error(ObjectLocation(), "", "JSON byte limit exceeded", "WIRE_JSON_LIMIT")
            value = json.loads(text, object_pairs_hook=_ObjectPairs, parse_constant=invalid_constant)
        except EntityJSONError:
            raise
        except (ValueError, UnicodeError, RecursionError):
            _error(ObjectLocation(), "", "Invalid JSON document", "WIRE_INVALID_JSON")
        return self._decode_entity(entity_class, value, self.profile if profile is None else _profile(profile), ObjectLocation(), "", 0)

    def _encode_entity(self, entity, profile, location, pointer, active, depth):
        if depth > _MAX_DEPTH:
            _error(location, pointer, "JSON depth limit exceeded", "WIRE_JSON_LIMIT")
        if id(entity) in active:
            _error(location, pointer, "Cyclic entity graphs require an explicit reference adapter", "WIRE_ENTITY_CYCLE")
        loaded = getattr(entity, "_loaded_fields", None)
        if not isinstance(loaded, (set, frozenset)):
            _error(location, pointer, "Expected a generated entity with loaded-field state")
        active.add(id(entity))
        try:
            result = {}
            for field in self.fields:
                if (field.loaded_name or field.native_name) not in loaded:
                    continue
                wire_name = self._wire(profile).fields[field.canonical_name].wire_name
                result[wire_name] = self._convert(field, getattr(entity, field.native_name), False, profile,
                    location.property(field.canonical_name), _pointer(pointer, wire_name), active, depth + 1)
            properties = getattr(entity, "_projection_properties", None)
            if isinstance(properties, ProjectionProperties):
                for name, value in properties.selected_values().items():
                    child_location, child_pointer = location.property(name), _pointer(pointer, name)
                    if name in self._query_reserved_names():
                        _error(child_location, child_pointer, "Query alias conflicts with the model namespace",
                               "WIRE_QUERY_PROPERTY_COLLISION")
                    result[name] = self._query_property_value(value, child_location, child_pointer, depth + 1)
            return result
        finally:
            active.remove(id(entity))

    def _query_property_value(self, value, location, pointer, depth):
        if depth > _MAX_DEPTH:
            _error(location, pointer, "JSON depth limit exceeded", "WIRE_JSON_LIMIT")
        value = _unwrap(value)
        if value is None or type(value) is bool:
            return value
        if type(value) is int:
            if not -(2**63) <= value < 2**64:
                _error(location, pointer, "Query integer exceeds the native exact range", "WIRE_INTEGER_RANGE")
            return value if abs(value) <= 2**53 - 1 else str(value)
        if isinstance(value, Decimal):
            return _decimal(value, False, location, pointer)
        if type(value) is float:
            if not math.isfinite(value):
                _error(location, pointer, "Expected a finite query number")
            return value
        if isinstance(value, str):
            return _text(value, location, pointer)
        for native, kind in ((datetime, "datetime"), (date, "date"), (time, "time")):
            if isinstance(value, native):
                return _temporal(value, kind, False, location, pointer)
        if isinstance(value, (list, tuple)):
            return [self._query_property_value(item, location.index(index), _pointer(pointer, index), depth + 1)
                    for index, item in enumerate(value)]
        if isinstance(value, dict):
            if any(not isinstance(key, str) for key in value):
                _error(location, pointer, "Query object keys must be text")
            return {key: self._query_property_value(item, location.property(key), _pointer(pointer, key), depth + 1)
                    for key, item in sorted(value.items())}
        _error(location, pointer, "Unsupported query-property value")

    def _decode_entity(self, entity_class, value, profile, location, pointer, depth):
        if depth > _MAX_DEPTH:
            _error(location, pointer, "JSON depth limit exceeded", "WIRE_JSON_LIMIT")
        if not isinstance(value, (dict, _ObjectPairs)):
            _error(location, pointer, "Expected a JSON entity object", "WIRE_ENTITY_OBJECT_REQUIRED")
        metadata = self._wire(profile)
        names = {name: canonical for canonical, field in metadata.fields.items()
            for name in (field.wire_name, *field.aliases)}
        fields = {field.canonical_name: field for field in self.fields}
        seen, values = set(), {}
        pairs = value if isinstance(value, _ObjectPairs) else value.items()
        for submitted_name, raw in pairs:
            canonical = names.get(submitted_name)
            child_location, child_pointer = location.property(canonical or submitted_name), _pointer(pointer, submitted_name)
            if canonical is None:
                _error(child_location, child_pointer, "Unknown JSON entity property", "WIRE_UNKNOWN_FIELD")
            if canonical in seen:
                _error(child_location, child_pointer, "Multiple JSON properties name the same model field", "WIRE_FIELD_COLLISION")
            seen.add(canonical)
            field = fields[canonical]
            values[field.loaded_name or field.native_name] = self._convert(field, raw, True, profile,
                child_location, child_pointer, set(), depth + 1)
        hydrate = getattr(entity_class, "_teaql_from_record", None)
        # Generated models have a read-only hydration capability. Handwritten
        # adapters retain their constructor contract; never infer insert intent
        # from the presence or absence of an ID in a JSON document.
        return hydrate(**values) if callable(hydrate) else entity_class(**values)

    def _convert(self, field, value, decoding, profile, location, pointer, active, depth):
        value = _unwrap(value)
        if value is None:
            if field.kind == "many":
                _error(location, pointer, "Expected a loaded relation array, not null")
            return None
        kind = field.kind
        if kind in ("id", "version", "integer", "long"):
            return _integer(value, kind, decoding, location, pointer)
        if kind == "text":
            return _text(value, location, pointer)
        if kind == "boolean":
            if type(value) is not bool:
                _error(location, pointer)
            return value
        if kind in ("float", "double"):
            if type(value) not in (int, float) or (type(value) is int and abs(value) > 2**53) or not math.isfinite(value):
                _error(location, pointer, "Expected a finite exactly representable JSON number")
            return float(value)
        if kind == "decimal":
            return _decimal(value, decoding, location, pointer)
        if kind in ("date", "time", "datetime"):
            return _temporal(value, kind, decoding, location, pointer)
        if kind == "json":
            return _json_value(value, location, pointer, depth)
        if kind == "business_id":
            entity_class = field.factory()
            if decoding:
                return entity_class(_text(value, location, pointer))
            if not isinstance(value, entity_class):
                _error(location, pointer)
            return _text(value.value, location, pointer)
        entity_class = field.factory()
        if kind == "reference" and not isinstance(value, (dict, _ObjectPairs, entity_class)):
            return _integer(value, "reference", decoding, location, pointer)
        schema = entity_class._teaql_json_schema
        def convert_entity(child, child_location, child_pointer):
            if decoding:
                return schema._decode_entity(entity_class, child, profile, child_location, child_pointer, depth)
            if not isinstance(child, entity_class):
                _error(child_location, child_pointer)
            return schema._encode_entity(child, profile, child_location, child_pointer, active, depth)
        if kind == "many":
            if not isinstance(value, list) or isinstance(value, _ObjectPairs):
                _error(location, pointer)
            return [convert_entity(child, location.index(index), _pointer(pointer, index)) for index, child in enumerate(value)]
        return convert_entity(value, location, pointer)
