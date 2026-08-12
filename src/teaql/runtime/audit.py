from dataclasses import dataclass, field
from enum import Enum
from inspect import isawaitable
from typing import Any, List, Optional


class MutationAuditKind(Enum):
    CREATED = "created"
    UPDATED = "updated"
    DELETED = "deleted"
    RECOVERED = "recovered"


@dataclass(frozen=True)
class AuditFieldChange:
    field: str
    old_value: Any = None
    new_value: Any = None


@dataclass(frozen=True)
class RawAuditEvent:
    kind: MutationAuditKind
    entity: str
    entity_id: Any
    changes: tuple[AuditFieldChange, ...]
    trace_chain: tuple[Any, ...] = field(default_factory=tuple)

    def safe(self, mask_fields: List[str], max_length: Optional[int]) -> "SafeAuditEvent":
        fields = []
        for change in self.changes:
            value = None if change.new_value is None else str(getattr(change.new_value, "val", change.new_value))
            masked = change.field in mask_fields
            if value is not None and masked:
                value = _mask(value)
            truncated = value is not None and max_length is not None and len(value) > max_length
            if truncated:
                value = "*" * max_length if max_length <= 3 else value[:max_length - 3] + "..."
            fields.append(SafeAuditField(change.field, value, masked, truncated))
        return SafeAuditEvent(self.kind, self.entity, self.entity_id, tuple(fields), self.trace_chain)


@dataclass(frozen=True)
class SafeAuditField:
    field: str
    value: Optional[str]
    masked: bool
    truncated: bool


@dataclass(frozen=True)
class SafeAuditEvent:
    kind: MutationAuditKind
    entity: str
    entity_id: Any
    fields: tuple[SafeAuditField, ...]
    trace_chain: tuple[Any, ...] = field(default_factory=tuple)


def _mask(value: str) -> str:
    if len(value) < 8:
        return "*" * len(value)
    return value[:2] + "*" * (len(value) - 4) + value[-2:]


async def deliver(sink: Any, method: str, context: Any, event: Any) -> None:
    callback = getattr(sink, method)
    result = callback(context, event)
    if isawaitable(result):
        await result
