from typing import Dict, Optional, Any
from .value import Value

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
