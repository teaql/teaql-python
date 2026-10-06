"""Persistent, invocation-owned graph lineage, independent of SQL routes."""

from dataclasses import dataclass
from typing import Optional

from .entity import EntityKey
from .mutation import TraceNode


@dataclass(frozen=True)
class _AuditReason:
    entity: str
    entity_id: int
    reason: str


@dataclass(frozen=True)
class TraceScope:
    """O(1) immutable branch token; recover owned nodes only at a boundary."""

    _owner: object
    _node: _AuditReason
    _parent: Optional['TraceScope'] = None

    @classmethod
    def root(cls, owner: object, key: EntityKey, reason: str) -> 'TraceScope':
        from .request_intent import MutationIntent
        intent = MutationIntent(reason)
        cls._require_assigned(key)
        return cls(owner, _AuditReason(key.entity, key.id, intent.comment))

    def child(self, key: EntityKey, reason: Optional[str]) -> 'TraceScope':
        from .request_intent import MutationIntent, _white_space
        self._require_assigned(key)
        # Match the public intent contract (Unicode White_Space), not Python
        # strip(), which also discards the valid U+001C..U+001F separators.
        if reason is None or (isinstance(reason, str) and all(_white_space(c) for c in reason)):
            return self
        intent = MutationIntent(reason)
        return TraceScope(self._owner, _AuditReason(key.entity, key.id, intent.comment), self)

    def recover(self) -> tuple[TraceNode, ...]:
        nodes = []
        scope = self
        while scope is not None:
            node = scope._node
            nodes.append(TraceNode(entity_type=node.entity, entity_id=node.entity_id,
                                   comment=node.reason, kind='auditReason', name=node.entity))
            scope = scope._parent
        nodes.reverse()
        return tuple(nodes)

    @staticmethod
    def _require_assigned(key: EntityKey) -> None:
        if not isinstance(key, EntityKey) or not isinstance(key.id, int) \
                or isinstance(key.id, bool) or key.id <= 0:
            raise ValueError('graph trace scope requires an assigned typed entity ID')
