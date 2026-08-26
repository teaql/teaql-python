from dataclasses import dataclass

@dataclass(frozen=True)
class RawAuditEvent:
    kind: str
    entity: str
    entity_id: object
    reason: str
    changes: tuple

@dataclass(frozen=True)
class SafeAuditEvent:
    kind: str
    entity: str
    entity_id: object
    reason: str
    fields: tuple

class UserContext:
    """Runtime dependencies and trusted request state initialized by the server."""

    def __init__(self):
        self._resources = {}
        self._standard_audit_sink = None
        self._app_audit_sink = None
        self._audit_policies = {}

    @classmethod
    def new(cls):
        return cls()

    def insert_resource(self, resource_type, resource):
        self._resources[resource_type] = resource
        return self

    def get_resource(self, resource_type):
        return self._resources.get(resource_type)

    def require_resource(self, resource_type):
        resource = self.get_resource(resource_type)
        if resource is None:
            raise RuntimeError(f"Required UserContext resource is missing: {resource_type}")
        return resource

    async def ensure_schema(self):
        """Reconcile schema through this context's configured data service."""
        await self.require_resource("dataService").ensure_schema(self)

    def initialize_audit(self, standard_sink, app_sink=None):
        self._standard_audit_sink = standard_sink
        self._app_audit_sink = app_sink
        return self

    def configure_audit_policy(self, entity, mask_fields=(), max_length=None):
        self._audit_policies[entity] = (frozenset(mask_fields), max_length)
        return self

    async def emit_mutation_audit(self, req, result):
        command = req.cmd
        values = getattr(command, "payload", getattr(command, "values", {}))
        kind = "created" if hasattr(command, "payload") else "updated" if hasattr(command, "values") else "deleted"
        raw = RawAuditEvent(kind, command.entity, result.get("id"), req.comment,
                            tuple((name, None, value) for name, value in values.items()))
        if self._standard_audit_sink is not None:
            emitted = self._standard_audit_sink.on_event(self, raw)
            if hasattr(emitted, "__await__"): await emitted
        if self._app_audit_sink is not None:
            masks, limit = self._audit_policies.get(command.entity, (frozenset(), None))
            fields = []
            for name, _, raw_value in raw.changes:
                value = None if raw_value is None else str(raw_value)
                masked = name in masks
                if value is not None and masked:
                    value = "*" * len(value) if len(value) < 8 else value[:2] + "*" * (len(value) - 4) + value[-2:]
                truncated = value is not None and limit is not None and len(value) > limit
                if truncated: value = "*" * limit if limit <= 3 else value[:limit - 3] + "..."
                fields.append((name, value, masked, truncated))
            safe = SafeAuditEvent(kind, command.entity, result.get("id"), req.comment, tuple(fields))
            emitted = self._app_audit_sink.on_safe_event(self, safe)
            if hasattr(emitted, "__await__"): await emitted
