"""Final trusted-metadata admission, after the configured Checker/Fix."""
from collections.abc import Mapping
from math import isfinite

from teaql.core.value import DataType, Value
from .i18n import CheckResult, ObjectLocation


def pending_reference_values(context, descriptor, record):
    """Freeze only pre-existing typed, ledger-owned new graph references.

    No negative number or arbitrary object is a deferred-FK capability. A Fix
    cannot introduce a new object and thereby bypass integer validation.
    """
    session = getattr(context, "_graph_session", None)
    if descriptor is None or not isinstance(record, Mapping) or not (
            session and session._active and session._preparing):
        return {}
    from teaql.core.entity import EntityRoot
    classes = context.get_resource("entity_classes") or ()
    result = {}
    for relation in descriptor.relations:
        if relation.is_many or relation.local_key not in record:
            continue
        value = record[relation.local_key]
        raw = value.val if isinstance(value, Value) else value
        candidates = [cls for cls in classes if isinstance(cls, type)
                      and cls.__name__ == relation.target_entity]
        if type(raw) not in candidates or getattr(raw, "id", None) is not None:
            continue
        ledger = getattr(raw, "_entity_root", None)
        key_fn = getattr(raw, "_teaql_entity_key", None)
        if not isinstance(ledger, EntityRoot) or not callable(key_fn):
            continue
        key = key_fn()
        if key.entity == relation.target_entity and key in ledger.new_keys():
            result[relation.local_key] = raw
    return result


def integral_scalar_results(descriptor, record, location=None, *, pending_references=None):
    if descriptor is None or not isinstance(record, Mapping):
        return []
    prefix = location or ObjectLocation()
    if isinstance(prefix, str):
        prefix = ObjectLocation.from_model_path(prefix)
    references = {relation.local_key for relation in getattr(descriptor, "relations", ())
                  if not relation.is_many}
    pending_references = pending_references or {}
    results = []
    for prop in getattr(descriptor, "properties", ()):
        kind = prop.property_type
        unsigned = kind == DataType.U64 or str(kind).lower() == "u64"
        if not unsigned and kind != DataType.I64 and str(kind).lower() not in ("i64", "integer", "long"):
            continue
        if prop.name not in record:
            continue
        value = Value.from_any(record[prop.name])
        if value.is_null():
            continue
        # No coercion or replacement: the command retains the exact Fix output.
        integer = value.try_u64() if unsigned else (
            value.try_i32() if prop._is_int32 or str(kind).lower() == "integer" else value.try_i64())
        if prop.name in references and prop.name in pending_references and value.val is pending_references[prop.name]:
            continue
        if integer is None or ((prop.name in references or prop._is_id) and integer < 0):
            results.append(CheckResult("invalid_type", prefix.property(prop.name), entity_type=descriptor._name))
    return results


def finite_scalar_results(descriptor, record, location=None):
    if descriptor is None or not isinstance(record, Mapping):
        return []
    prefix = location or ObjectLocation()
    if isinstance(prefix, str):
        prefix = ObjectLocation.from_model_path(prefix)
    results = []
    for prop in getattr(descriptor, "properties", ()):
        if prop.property_type != DataType.F64 and str(prop.property_type).lower() not in ("f64", "float", "double"):
            continue
        if prop.name not in record:
            continue  # NotLoaded is not a null or a fabricated scalar value.
        value = record[prop.name]
        raw = value.val if isinstance(value, Value) else value
        if raw is None:
            continue  # Required/null checks are owned by the Checker contract.
        try:
            valid = type(raw) in (int, float) and isfinite(raw)
        except OverflowError:
            valid = False
        if not valid:
            # NaN/Infinity are not JSON values. Do not echo sensitive numeric
            # text, or replace the original invalid input with a fake JSON null.
            results.append(CheckResult("invalid_type", prefix.property(prop.name),
                                       entity_type=descriptor._name))
    return results
