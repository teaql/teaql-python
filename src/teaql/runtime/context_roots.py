"""Pure admission for generated, context-managed object references.

The declaration comes from the model, never from an incoming command. This is
not a tenant policy: applications decide what their active root represents.
Loaded ownership is checked even when the update changes a different field.
"""
from collections.abc import Mapping

from teaql.core.value import Value
from .i18n import CheckException, CheckResult, ObjectLocation


def _identity(value):
    raw = value.val if isinstance(value, Value) else value
    if isinstance(raw, Mapping):
        return raw.get("id")
    return getattr(raw, "id", raw)


def validate_input(context, entity, field, expected_type, action, original, current, pending):
    """Validate original and proposed references without allocation or I/O."""
    from .context import ContextRootError

    def reject(rule):
        # IDs are not needed in a diagnostic; retain neither raw root nor input.
        results = [CheckResult(rule, ObjectLocation().property(field), entity_type=entity)]
        context.translate_check_results(results)
        raise CheckException(results)

    try:
        root = context.require_active_root(expected_type)
    except ContextRootError:
        reject("context_root_missing")
    if type(root.id) is not int or root.id <= 0:
        reject("context_root_missing")
    seen = False
    for values in (original, current, pending):
        if not isinstance(values, Mapping) or field not in values:
            continue
        identity = _identity(values[field])
        if identity is None and action == "Create":
            continue  # The generated insert Fix will supply the trusted root.
        seen = True
        if type(identity) is not int or identity != root.id:
            reject("context_root_mismatch")
    if not seen and action != "Create":
        reject("context_root_missing")
