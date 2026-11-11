"""Original loaded scalars owned by runtime, not serialized entity state."""
from copy import deepcopy
from datetime import date, datetime, time
from decimal import Decimal
from math import isfinite
from struct import pack
from weakref import WeakKeyDictionary

from teaql.core.value import Timestamp, Value
from teaql.core.entity_creation import EntityCreationState


def _same_representation(left, right, depth=0):
    """Conservative exact equality; never numeric/string coercion or NaN."""
    if depth > 64:
        return False
    if isinstance(left, Value) and isinstance(right, Value):
        if left.is_null() and right.is_null():
            return True
        return left._type_hint == right._type_hint and _same_representation(left.val, right.val, depth + 1)
    if type(left) is not type(right):
        return False
    if left is None or type(left) in (str, bool, int, date, time, datetime):
        return left == right
    if isinstance(left, Decimal):
        return left.is_finite() and right.is_finite() and left.as_tuple() == right.as_tuple()
    if type(left) is float:
        return isfinite(left) and isfinite(right) and pack('!d', left) == pack('!d', right)
    if isinstance(left, Timestamp):
        return type(left.millis) is int and type(right.millis) is int and left.millis == right.millis
    if type(left) is list:
        return len(left) == len(right) and all(_same_representation(a, b, depth + 1) for a, b in zip(left, right))
    if type(left) is dict:
        return (left.keys() == right.keys() and all(type(key) is str for key in left)
                and all(_same_representation(value, right[key], depth + 1) for key, value in left.items()))
    return False


class LoadedScalarSnapshots:
    _values = WeakKeyDictionary()
    _owners = WeakKeyDictionary()
    _origins = WeakKeyDictionary()
    same_value = staticmethod(_same_representation)

    @classmethod
    def capture(cls, entity, values, *, origin=EntityCreationState.HYDRATED):
        if not isinstance(origin, EntityCreationState):
            raise TypeError('Snapshot origin must be process-local creation provenance')
        cls._values[entity] = deepcopy(values)
        cls._origins[entity] = origin
        key = getattr(entity, '_teaql_entity_key', None)
        cls._owners[entity] = key() if callable(key) else None

    @classmethod
    def values(cls, entity):
        return deepcopy(cls._values.get(entity, {}))

    @classmethod
    def origin(cls, entity):
        return cls._origins.get(entity, EntityCreationState.UNMANAGED)

    @classmethod
    def persisted_version(cls, entity):
        """Read admission provenance, never a later mutable carrier value."""
        if cls.origin(entity) is not EntityCreationState.HYDRATED:
            return None
        value = cls._values.get(entity, {}).get('version')
        return value.val if isinstance(value, Value) and type(value.val) is int else None

    @classmethod
    def restore(cls, entity, values, *, origin=EntityCreationState.HYDRATED):
        cls.capture(entity, values, origin=origin)

    @classmethod
    def discard_restored_fields(cls, entity, context):
        """Generated plumbing: normalize only admitted, known persisted fields.

        Raw ledger set stays lossless. Identity/version, lifecycle, immutable
        projection state and lineage are never cleared by a field restoration.
        """
        from teaql.core.entity import EntityKey, EntityRoot
        ledger = getattr(entity, '_entity_root', None)
        key_fn = getattr(entity, '_teaql_entity_key', None)
        if not isinstance(ledger, EntityRoot) or not callable(key_fn):
            return ()
        key = key_fn()
        if not isinstance(key, EntityKey):
            raise ValueError('ENTITY_BASELINE_OWNER: invalid typed entity identity')
        pending = ledger._pending_values(key)
        context._validate_mutation_fields(key.entity, pending)
        if getattr(entity, '_action', None) != 'Update' or key in ledger.new_keys() or key in ledger.deleted_keys():
            return ()
        if cls.origin(entity) is not EntityCreationState.HYDRATED:
            return ()
        baseline = cls._values.get(entity)
        owner = cls._owners.get(entity)
        if baseline is None or owner is None:
            return ()
        if key != owner or type(key.id) is not type(owner.id):
            raise ValueError('ENTITY_BASELINE_OWNER: persisted snapshot belongs to another typed entity')
        identity, version = baseline.get('id'), baseline.get('version')
        if not isinstance(identity, Value) or not isinstance(version, Value):
            return ()
        if (type(identity.val) is not int or type(version.val) is not int
                or identity.val != key.id or version.val != ledger.original_version(key)):
            raise ValueError('ENTITY_BASELINE_OWNER: persisted identity or version changed')
        descriptor = context.entity(key.entity)
        fields = {prop.name for prop in getattr(descriptor, 'properties', ()) if not prop._is_id and not prop._is_version}
        restored = tuple(field for field, value in pending.items()
                         if field in fields and field in baseline and _same_representation(baseline[field], value))
        # Generated native-member mapping, not JSON serialization or inferred
        # casing. The callback changes values only; it never loads or saves.
        restore_values = getattr(entity, '_teaql_restore_fixed_values', None)
        if restored and callable(restore_values):
            restore_values({field: deepcopy(baseline[field]) for field in restored})
        ledger._discard_fields(key, restored)
        return restored
