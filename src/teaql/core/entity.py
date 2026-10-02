from dataclasses import dataclass
from copy import deepcopy
from threading import RLock
from typing import Dict, Optional, Any, Iterable, Mapping, Set, Tuple
from .value import Value


@dataclass(frozen=True, order=True)
class EntityKey:
    entity: str
    id: Any

    def __post_init__(self):
        if not self.entity or not self.entity.strip():
            raise ValueError("entity type is required")


class EntityChangeSet:
    """Final pending field values grouped by stable entity identity."""

    def __init__(self):
        self._changes: Dict[EntityKey, Dict[str, Any]] = {}

    def set(self, key: EntityKey, field: str, value: Any) -> None:
        if not field or not field.strip():
            raise ValueError("field is required")
        self._changes.setdefault(key, {})[field] = value

    def get(self, key: EntityKey, field: str) -> Any:
        return self._changes.get(key, {}).get(field)

    def changes(self) -> Iterable[Tuple[EntityKey, Mapping[str, Any]]]:
        return tuple((key, dict(values)) for key, values in self._changes.items())

    def clear_entity(self, key: EntityKey) -> None:
        self._changes.pop(key, None)

    def merge_from(self, other: 'EntityChangeSet') -> None:
        for key, values in other.changes():
            for field, value in values.items():
                self.set(key, field, value)

    def rekey(self, old_key: EntityKey, new_key: EntityKey) -> None:
        values = self._changes.pop(old_key, None)
        if values:
            self._changes.setdefault(new_key, {}).update(values)

    def is_empty(self) -> bool:
        return not self._changes


class EntityRoot:
    """Shared pending mutation ledger for one generated entity graph."""

    def __init__(self):
        self._lock = RLock()
        self._change_sets = [EntityChangeSet()]
        self._original_versions: Dict[EntityKey, int] = {}
        self._new_keys: Set[EntityKey] = set()
        self._deleted_keys: Set[EntityKey] = set()
        self._trace_chains: Dict[EntityKey, tuple] = {}

    def set_trace_chain(self, key: EntityKey, chain) -> None:
        """Store a complete per-entity replacement, not an appended fragment."""
        from .mutation import TraceNode
        nodes = tuple(chain)
        if any(not isinstance(node, TraceNode) or node.kind != 'auditReason' for node in nodes):
            raise TypeError('ledger lineage must contain typed AuditReason nodes')
        with self._lock:
            self._trace_chains[key] = deepcopy(nodes)

    def trace_chain(self, key: EntityKey) -> tuple:
        with self._lock:
            return deepcopy(self._trace_chains.get(key, ()))

    def push_change_set(self) -> None:
        with self._lock:
            self._change_sets.append(EntityChangeSet())

    def pop_change_set(self) -> EntityChangeSet:
        with self._lock:
            if len(self._change_sets) == 1:
                raise RuntimeError("cannot pop the root change set")
            return self._change_sets.pop()

    def current_change_set(self) -> EntityChangeSet:
        with self._lock:
            return self._change_sets[-1]

    def set(self, key: EntityKey, field: str, value: Any) -> None:
        with self._lock:
            self._change_sets[-1].set(key, field, value)

    def get(self, key: EntityKey, field: str) -> Any:
        with self._lock:
            for change_set in reversed(self._change_sets):
                value = change_set.get(key, field)
                if value is not None:
                    return value
            return None

    def mark_as_new(self, key: EntityKey) -> None:
        with self._lock:
            self._new_keys.add(key)

    def mark_as_deleted(self, key: EntityKey) -> None:
        with self._lock:
            for change_set in self._change_sets:
                change_set.clear_entity(key)
            self._deleted_keys.add(key)

    def set_original_version(self, key: EntityKey, version: int) -> None:
        with self._lock:
            self._validate_version(key, version)
            self._original_versions[key] = version

    def accept_committed_version(self, key: EntityKey, version: int) -> None:
        """Advance authoritative state only after this key's changes clear."""
        with self._lock:
            if self.has_pending(key):
                raise ValueError('ENTITY_PENDING_CHANGES: clear committed changes before accepting a version')
            self._original_versions[key] = version

    def has_pending(self, key: EntityKey) -> bool:
        with self._lock:
            return (key in self._new_keys or key in self._deleted_keys or
                    any(key in change_set._changes for change_set in self._change_sets))

    def original_version(self, key: EntityKey) -> Optional[int]:
        with self._lock:
            return self._original_versions.get(key)

    def new_keys(self) -> Set[EntityKey]:
        with self._lock:
            return set(self._new_keys)

    def deleted_keys(self) -> Set[EntityKey]:
        with self._lock:
            return set(self._deleted_keys)

    def clear_committed(self) -> None:
        with self._lock:
            self._change_sets[-1] = EntityChangeSet()
            self._new_keys.clear()
            self._deleted_keys.clear()
            self._trace_chains.clear()

    def merge_from(self, other: 'EntityRoot') -> None:
        if other is self:
            return
        # Release the source lock before acquiring the target: opposing imports
        # must not hold both graph locks in opposite order.
        with other._lock:
            keys = (set(other._original_versions) | other._new_keys | other._deleted_keys |
                    set(other._trace_chains) | set(other._change_sets[-1]._changes))
            entries = [other._snapshot(key) for key in keys]
        with self._lock:
            for key, _, version, _, _, _ in entries:
                self._validate_version(key, version)
            for entry in entries:
                self._import(entry)

    def merge_entity_from(self, other: 'EntityRoot', key: EntityKey) -> None:
        """Copy one reached typed key without draining its source graph."""
        if other is self:
            return
        entry = other._snapshot(key)
        with self._lock:
            self._validate_version(key, entry[2])
            self._import(entry)

    def _snapshot(self, key):
        with self._lock:
            return (key, dict(self._change_sets[-1]._changes.get(key, {})),
                    self._original_versions.get(key), key in self._new_keys,
                    key in self._deleted_keys, deepcopy(self._trace_chains.get(key)))

    def _validate_version(self, key, incoming):
        original = self._original_versions.get(key)
        if incoming is not None and original is not None and incoming != original:
            raise ValueError(f'ENTITY_VERSION_CONFLICT: {key.entity} has loaded versions {original} and {incoming}')

    def _import(self, entry):
        key, values, version, added, removed, trace = entry
        for field, value in values.items():
            self._change_sets[-1].set(key, field, value)
        if version is not None:
            self._original_versions[key] = version
        if added:
            self._new_keys.add(key)
        if removed:
            self.mark_as_deleted(key)
        if trace is not None:
            self._trace_chains[key] = trace

    def rekey(self, old_key: EntityKey, new_key: EntityKey) -> None:
        if old_key == new_key:
            return
        with self._lock:
            self._validate_version(new_key, self._original_versions.get(old_key))
            for change_set in self._change_sets:
                change_set.rekey(old_key, new_key)
            if old_key in self._original_versions:
                self._original_versions[new_key] = self._original_versions.pop(old_key)
            if old_key in self._new_keys:
                self._new_keys.remove(old_key)
                self._new_keys.add(new_key)
            if old_key in self._deleted_keys:
                self._deleted_keys.remove(old_key)
                self._deleted_keys.add(new_key)
            if old_key in self._trace_chains:
                self._trace_chains[new_key] = self._trace_chains.pop(old_key)
            for chain in self._trace_chains.values():
                for node in chain:
                    if (node.name or node.entity_type, node.entity_id) == (old_key.entity, old_key.id):
                        node.entity_id = new_key.id

    def clear_entity(self, key: EntityKey) -> None:
        with self._lock:
            for change_set in self._change_sets:
                change_set.clear_entity(key)
            self._new_keys.discard(key)
            self._deleted_keys.discard(key)
            self._trace_chains.pop(key, None)

class BaseEntityData:
    def __init__(self, id: int = 0, version: int = 0, dynamic: Optional[Dict[str, Value]] = None):
        self.id = id
        self.version = version
        self.dynamic = dynamic or {}

    @classmethod
    def new(cls) -> 'BaseEntityData':
        return cls()

    def with_id(self, id: int) -> 'BaseEntityData':
        self.id = id
        return self

    def with_version(self, version: int) -> 'BaseEntityData':
        self.version = version
        return self

    def with_dynamic(self, key: str, value: Any) -> 'BaseEntityData':
        self.dynamic[key] = Value.from_any(value)
        return self

    def to_record(self) -> Dict[str, Any]:
        rec = {"id": self.id, "version": self.version}
        if self.dynamic:
            for k, v in self.dynamic.items():
                rec[k] = v.to_json_value()
        return rec
    def get_dynamic(self, key: str) -> Optional[Value]:
        return self.dynamic.get(key)
    def put_dynamic(self, key, value):
        self.dynamic[key] = value
