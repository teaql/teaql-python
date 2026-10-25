"""Final trusted-metadata admission, after the configured Checker/Fix."""
from collections.abc import Mapping
from math import isfinite

from teaql.core.value import DataType, Value
from .i18n import CheckResult, ObjectLocation


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
