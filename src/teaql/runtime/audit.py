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
    actor: Optional[str] = None
    category: Optional[str] = None

    def safe(self, mask_fields: List[str], max_length: Optional[int]) -> "SafeAuditEvent":
        from .log_privacy import REDACTED, credential_name, payload_has_credentials, plaintext_enabled, scrub, value_strings
        allow = plaintext_enabled()
        secrets = []
        fields = []
        for change in self.changes:
            value = None if change.new_value is None else str(getattr(change.new_value, "val", change.new_value))
            masked = (credential_name(change.field)
                      or payload_has_credentials(change.new_value)
                      or payload_has_credentials(change.old_value)
                      or (change.field in mask_fields and not allow))
            if masked:
                secrets.extend(value_strings(change.old_value))
                secrets.extend(value_strings(change.new_value))
            if value is not None and masked:
                value = REDACTED
            truncated = value is not None and max_length is not None and len(value) > max_length
            if truncated:
                value = "*" * max_length if max_length <= 3 else value[:max_length - 3] + "..."
            fields.append(SafeAuditField(change.field, value, masked, truncated))
        return SafeAuditEvent(
            self.kind, self.entity, self.entity_id, scrub(tuple(fields), secrets), scrub(self.trace_chain, secrets),
            scrub(self.actor, secrets), self.category,
        )


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
    actor: Optional[str] = None
    category: Optional[str] = None


def _mask(value: str) -> str:
    if len(value) < 8:
        return "*" * len(value)
    return value[:2] + "*" * (len(value) - 4) + value[-2:]


async def deliver(sink: Any, method: str, context: Any, event: Any) -> None:
    callback = getattr(sink, method)
    result = callback(context, event)
    if isawaitable(result):
        await result
