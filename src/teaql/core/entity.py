from dataclasses import dataclass
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
            self._original_versions[key] = version

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
