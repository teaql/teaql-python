"""Trusted model vocabulary at mutation admission; never a wire-name converter."""
from collections.abc import Mapping

from .i18n import CheckException, CheckResult, ObjectLocation


def canonical_field_results(descriptor, record, location=None):
    properties = getattr(descriptor, "properties", ())
    if not properties or not isinstance(record, Mapping):
        # Legacy/manual entities without field metadata do not supply a model
        # vocabulary. Generated entities always declare their fixed fields.
        return []
    allowed = {prop.name for prop in properties}
    prefix = location or ObjectLocation()
    if isinstance(prefix, str):
        prefix = ObjectLocation.from_model_path(prefix)
    return [CheckResult("unknown_field", prefix.property(field) if isinstance(field, str) else prefix,
                        entity_type=descriptor._name)
            for field in record if not isinstance(field, str) or field not in allowed]


def validate_canonical_fields(context, entity, record, location=None):
    lookup = getattr(context, "entity", None)
    descriptor = lookup(entity) if callable(lookup) else None
    results = canonical_field_results(descriptor, record, location)
    if results:
        context.translate_check_results(results)
        raise CheckException(results)
