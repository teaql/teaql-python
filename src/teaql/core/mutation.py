from enum import Enum, auto
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from .value import Value

@dataclass
class TraceNode:
    entity_type: str
    entity_id: Optional[int] = None
    comment: str = ""

@dataclass
class InsertMutation:
    entity: str
    values: Dict[str, Value] = field(default_factory=dict)
    trace_chain: List[TraceNode] = field(default_factory=list)

    @classmethod
    def new(cls, entity: str) -> 'InsertMutation':
        return cls(entity=entity)

    def value(self, field_name: str, value: Any) -> 'InsertMutation':
        self.values[field_name] = Value.from_any(value)
        return self

@dataclass
class UpdateMutation:
    entity: str
    id: Value
    expected_version: Optional[int] = None
    values: Dict[str, Value] = field(default_factory=dict)
    trace_chain: List[TraceNode] = field(default_factory=list)
    old_values: Optional[Dict[str, Value]] = None

    @classmethod
    def new(cls, entity: str, id_val: Any) -> 'UpdateMutation':
        return cls(entity=entity, id=Value.from_any(id_val))

    def with_expected_version(self, version: int) -> 'UpdateMutation':
        self.expected_version = version
        return self

    def value(self, field_name: str, value: Any) -> 'UpdateMutation':
        self.values[field_name] = Value.from_any(value)
        return self

@dataclass
class BatchInsertMutation:
    entity: str
    batch_values: List[Dict[str, Value]] = field(default_factory=list)
    trace_chains: List[List[TraceNode]] = field(default_factory=list)

    @classmethod
    def new(cls, entity: str) -> 'BatchInsertMutation':
        return cls(entity=entity)

@dataclass
class BatchUpdateMutation:
    entity: str
    update_fields: List[str]
    batch_ids: List[Value] = field(default_factory=list)
    batch_expected_versions: List[Optional[int]] = field(default_factory=list)
    batch_values: List[Dict[str, Value]] = field(default_factory=list)
    trace_chains: List[List[TraceNode]] = field(default_factory=list)
    batch_old_values: List[Optional[Dict[str, Value]]] = field(default_factory=list)

    @classmethod
    def new(cls, entity: str, update_fields: List[str]) -> 'BatchUpdateMutation':
        return cls(entity=entity, update_fields=update_fields)

@dataclass
class DeleteMutation:
    entity: str
    id: Value
    expected_version: Optional[int] = None
    soft_delete: bool = True
    trace_chain: List[TraceNode] = field(default_factory=list)

    @classmethod
    def new(cls, entity: str, id_val: Any) -> 'DeleteMutation':
        return cls(entity=entity, id=Value.from_any(id_val))

    def with_expected_version(self, version: int) -> 'DeleteMutation':
        self.expected_version = version
        return self

    def hard_delete(self) -> 'DeleteMutation':
        self.soft_delete = False
        return self

@dataclass
class RecoverMutation:
    entity: str
    id: Value
    expected_version: int
    trace_chain: List[TraceNode] = field(default_factory=list)

    @classmethod
    def new(cls, entity: str, id_val: Any, expected_version: int) -> 'RecoverMutation':
        return cls(entity=entity, id=Value.from_any(id_val), expected_version=expected_version)

# Alias to match Rust code if needed
InsertCommand = InsertMutation
UpdateCommand = UpdateMutation
BatchInsertCommand = BatchInsertMutation
BatchUpdateCommand = BatchUpdateMutation
DeleteCommand = DeleteMutation
RecoverCommand = RecoverMutation

class MutationRequest:
    def __init__(self, data: Any):
        self._data = data

    def trace_chain(self) -> List[TraceNode]:
        if isinstance(self._data, list):
            return []
        return getattr(self._data, 'trace_chain', [])

    def comment(self) -> Optional[str]:
        if isinstance(self._data, list):
            return None
        traces = self.trace_chain()
        if traces:
            return traces[-1].comment
        return None

    @classmethod
    def Insert(cls, cmd: InsertMutation) -> 'MutationRequest':
        return cls(cmd)

    @classmethod
    def Update(cls, cmd: UpdateMutation) -> 'MutationRequest':
        return cls(cmd)

    @classmethod
    def Delete(cls, cmd: DeleteMutation) -> 'MutationRequest':
        return cls(cmd)

    @classmethod
    def Recover(cls, cmd: RecoverMutation) -> 'MutationRequest':
        return cls(cmd)
        
    @classmethod
    def Batch(cls, cmds: List['MutationRequest']) -> 'MutationRequest':
        return cls(cmds)

