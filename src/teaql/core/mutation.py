from enum import Enum, auto
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from copy import deepcopy
from .value import Value
from .request_intent import MutationIntent

@dataclass
class TraceNode:
    entity_type: str = ""
    entity_id: Optional[int] = None
    comment: str = ""
    kind: str = "entity"
    name: str = ""

@dataclass
class InsertCommand:
    entity: str
    values: Dict[str, Value] = field(default_factory=dict)
    trace_chain: List[TraceNode] = field(default_factory=list)

    @classmethod
    def new(cls, entity: str) -> 'InsertCommand':
        return cls(entity=entity)

    def value(self, field_name: str, value: Any) -> 'InsertCommand':
        self.values[field_name] = Value.from_any(value)
        return self

@dataclass
class UpdateCommand:
    entity: str
    id: Value
    expected_version_val: Optional[int] = None
    values: Dict[str, Value] = field(default_factory=dict)
    trace_chain: List[TraceNode] = field(default_factory=list)
    old_values: Optional[Dict[str, Value]] = None

    @classmethod
    def new(cls, entity: str, id_val: Any) -> 'UpdateCommand':
        return cls(entity=entity, id=Value.from_any(id_val))

    def expected_version(self, version: int) -> 'UpdateCommand':
        self.expected_version_val = version
        return self

    def value(self, field_name: str, value: Any) -> 'UpdateCommand':
        self.values[field_name] = Value.from_any(value)
        return self

@dataclass
class BatchInsertCommand:
    entity: str
    batch_values: List[Dict[str, Value]] = field(default_factory=list)
    trace_chains: List[List[TraceNode]] = field(default_factory=list)

    @classmethod
    def new(cls, entity: str) -> 'BatchInsertCommand':
        return cls(entity=entity)

@dataclass
class BatchUpdateCommand:
    entity: str
    update_fields: List[str]
    batch_ids: List[Value] = field(default_factory=list)
    batch_expected_versions: List[Optional[int]] = field(default_factory=list)
    batch_values: List[Dict[str, Value]] = field(default_factory=list)
    trace_chains: List[List[TraceNode]] = field(default_factory=list)
    batch_old_values: List[Optional[Dict[str, Value]]] = field(default_factory=list)

    @classmethod
    def new(cls, entity: str, update_fields: List[str]) -> 'BatchUpdateCommand':
        return cls(entity=entity, update_fields=update_fields)

@dataclass
class DeleteCommand:
    entity: str
    id: Value
    expected_version_val: Optional[int] = None
    soft_delete: bool = True
    trace_chain: List[TraceNode] = field(default_factory=list)
    old_values: Optional[Dict[str, Value]] = field(default=None, repr=False)

    @classmethod
    def new(cls, entity: str, id_val: Any) -> 'DeleteCommand':
        return cls(entity=entity, id=Value.from_any(id_val))

    def expected_version(self, version: int) -> 'DeleteCommand':
        self.expected_version_val = version
        return self

    def hard_delete(self) -> 'DeleteCommand':
        self.soft_delete = False
        return self

@dataclass
class RecoverCommand:
    entity: str
    id: Value
    expected_version_val: int
    trace_chain: List[TraceNode] = field(default_factory=list)
    old_values: Optional[Dict[str, Value]] = field(default=None, repr=False)

    @classmethod
    def new(cls, entity: str, id_val: Any, expected_version: int) -> 'RecoverCommand':
        return cls(entity=entity, id=Value.from_any(id_val), expected_version_val=expected_version)

    def expected_version(self, version: int) -> 'RecoverCommand':
        self.expected_version_val = version
        return self

class MutationKind(Enum):
    INSERT = auto()
    UPDATE = auto()
    DELETE = auto()
    RECOVER = auto()
    BATCH = auto()

class MutationRequest:
    __slots__ = ('_data', '__intent', '__mutation_lineage')

    def __init__(self, data: Any, comment: Optional[str] = None):
        self.__intent = MutationIntent(comment)
        self._data = data
        self.__mutation_lineage = ()

    @property
    def mutation_lineage(self) -> tuple[TraceNode, ...]:
        """Detached business lineage, never the physical SQL trace path."""
        return deepcopy(self.__mutation_lineage)

    def with_mutation_lineage(self, chain) -> 'MutationRequest':
        nodes = tuple(chain)
        if any(not isinstance(node, TraceNode) or node.kind != 'auditReason' for node in nodes):
            raise TypeError('mutation lineage must contain typed AuditReason nodes')
        result = MutationRequest(self._data, comment=self.intent.comment)
        result.__mutation_lineage = deepcopy(nodes)
        return result

    @property
    def intent(self) -> MutationIntent:
        return self.__intent

    def validate(self) -> None:
        MutationIntent(getattr(getattr(self, '_MutationRequest__intent', None), 'comment', None))
        if any(not isinstance(node, TraceNode) for node in self.trace_chain()):
            raise TypeError('MutationRequest trace must contain typed TraceNode values')

    def with_root_intent(self, intent: MutationIntent) -> 'MutationRequest':
        return MutationRequest(self._data, comment=intent.comment).with_mutation_lineage(self.mutation_lineage)

    def trace_chain(self) -> List[TraceNode]:
        if isinstance(self._data, list):
            return []
        return getattr(self._data, 'trace_chain', [])

    def comment(self) -> str:
        return self.intent.comment

    @classmethod
    def Insert(cls, cmd: InsertCommand, comment: Optional[str] = None) -> 'MutationRequest':
        return cls(cmd, comment)

    @classmethod
    def Update(cls, cmd: UpdateCommand, comment: Optional[str] = None) -> 'MutationRequest':
        return cls(cmd, comment)

    @classmethod
    def Delete(cls, cmd: DeleteCommand, comment: Optional[str] = None) -> 'MutationRequest':
        return cls(cmd, comment)

    @classmethod
    def Recover(cls, cmd: RecoverCommand, comment: Optional[str] = None) -> 'MutationRequest':
        return cls(cmd, comment)
        
    @classmethod
    def Batch(cls, cmds: List['MutationRequest'], comment: Optional[str] = None) -> 'MutationRequest':
        return cls(cmds, comment)
