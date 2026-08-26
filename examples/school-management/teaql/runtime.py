from dataclasses import dataclass
from datetime import timedelta
from enum import Enum

_SCHEMA_INVOCATION = object()

@dataclass
class CheckResult:
    rule_id: str
    location: object
    input_value: object = None
    system_value: object = None
    message: str = None

class CheckException(Exception):
    def __init__(self, violations):
        self.violations = list(violations)
        super().__init__("Check failed: " + "; ".join(
            result.message or f"{result.rule_id}:{result.location}"
            for result in self.violations))

@dataclass(frozen=True)
class ContextEntityRef:
    entity: str
    id: int

class ContextRootError(Exception):
    def __init__(self, reason, expected_type, active_root=None):
        self.reason, self.expected_type, self.active_root = reason, expected_type, active_root
        super().__init__(f"context root {reason}: expected {expected_type}")

@dataclass(frozen=True, order=True)
class EntityKey:
    entity: str
    id: object

class EntityChangeSet:
    def __init__(self): self._changes = {}
    def set(self, key, field, value): self._changes.setdefault(key, {})[field] = value
    def changes(self): return tuple((key, dict(values)) for key, values in self._changes.items())
    def clear_entity(self, key): self._changes.pop(key, None)
    def merge_from(self, other):
        for key, values in other.changes():
            for field, value in values.items(): self.set(key, field, value)
    def rekey(self, old_key, new_key):
        values = self._changes.pop(old_key, None)
        if values: self._changes.setdefault(new_key, {}).update(values)

class EntityRoot:
    def __init__(self):
        self._changes = EntityChangeSet(); self._versions = {}; self._new = set(); self._deleted = set()
    def current_change_set(self): return self._changes
    def set(self, key, field, value): self._changes.set(key, field, value)
    def mark_as_new(self, key): self._new.add(key)
    def mark_as_deleted(self, key): self._changes.clear_entity(key); self._deleted.add(key)
    def set_original_version(self, key, version): self._versions[key] = version
    def original_version(self, key): return self._versions.get(key)
    def merge_from(self, other):
        if other is self: return
        self._changes.merge_from(other._changes); self._versions.update(other._versions)
        self._new.update(other._new); self._deleted.update(other._deleted)
    def rekey(self, old_key, new_key):
        self._changes.rekey(old_key, new_key)
        if old_key in self._versions: self._versions[new_key] = self._versions.pop(old_key)
        if old_key in self._new: self._new.remove(old_key); self._new.add(new_key)
        if old_key in self._deleted: self._deleted.remove(old_key); self._deleted.add(new_key)
    def clear_entity(self, key):
        self._changes.clear_entity(key); self._new.discard(key); self._deleted.discard(key)

class SqlLogOperation(str, Enum):
    Select = "select"
    Insert = "insert"
    Update = "update"
    Delete = "delete"

@dataclass(frozen=True)
class SqlLogEntry:
    operation: SqlLogOperation
    sql: str
    params: tuple
    elapsed: timedelta
    result_count: object = None
    affected_rows: object = None
    result_summary: str = ""

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
        self._entity_root = EntityRoot()
        self._standard_audit_sink = None
        self._app_audit_sink = None
        self._audit_policies = {}
        self._entity_initializers = {}
        self._managed_entities = []
        self._continuous_page_cursors = {}
        self._continuous_page_plan = "DISABLED"
        self._continuous_page_cursor_id = None
        self._sql_log_mode = "all"
        self._sql_logs = []
        self._checker_registry = {}
        self._checked_mutations = set()

    @classmethod
    def new(cls):
        return cls()

    def entity_root(self):
        return self._entity_root

    def insert_resource(self, resource_type, resource):
        self._resources[resource_type] = resource
        return self

    def install(self, module):
        """Install a passive metadata manifest; this never changes a database schema."""
        module.apply_to(self)
        return self

    def check_and_fix_mutation(self, mutation):
        checker = self._checker_registry.get(getattr(mutation, "entity", None))
        if checker is None:
            return
        raw_record = getattr(mutation, "payload", getattr(mutation, "values", None))
        if raw_record is None:
            return
        from datetime import datetime
        from teaql.core.value import Value
        record = {name: Value.from_any(value) for name, value in raw_record.items()}
        self.insert_resource("fix_time", datetime.now())
        self.insert_resource("fix_operation", "insert" if hasattr(mutation, "payload") else "update")
        results = []
        try:
            checker.check_and_fix(self, record, None, results)
        finally:
            self._resources.pop("fix_time", None)
            self._resources.pop("fix_operation", None)
        if results:
            raise CheckException(results)
        raw_record.clear()
        raw_record.update({name: getattr(value, "val", value) for name, value in record.items()})

    def mark_mutation_checked(self, mutation):
        self._checked_mutations.add(id(mutation))

    def consume_mutation_checked(self, mutation):
        key = id(mutation)
        if key not in self._checked_mutations:
            return False
        self._checked_mutations.remove(key)
        return True

    def get_resource(self, resource_type):
        return self._resources.get(resource_type)

    def require_resource(self, resource_type):
        resource = self.get_resource(resource_type)
        if resource is None:
            raise RuntimeError(f"Required UserContext resource is missing: {resource_type}")
        return resource

    async def ensure_schema(self):
        """Reconcile schema through this context's configured data service."""
        await self.require_resource("dataService")._ensure_schema(self, _SCHEMA_INVOCATION)

    def with_active_root(self, root):
        if not isinstance(root, ContextEntityRef):
            raise TypeError("active root must be ContextEntityRef")
        return self.insert_resource("active_root", root)

    def require_active_root(self, expected_type):
        root = self.get_resource("active_root")
        if not isinstance(root, ContextEntityRef):
            raise ContextRootError("missing", expected_type)
        if root.entity != expected_type:
            raise ContextRootError("type_mismatch", expected_type, root)
        return root

    def with_request_policy(self, policy):
        self.insert_resource("request_policy", policy)
        return self

    def prepare_query(self, query):
        policy = self.get_resource("request_policy")
        if policy is None: return query
        if callable(policy): prepared = policy(query)
        elif hasattr(policy, "apply"): prepared = policy.apply(query)
        else: raise TypeError("request_policy must be callable or expose apply(query)")
        return query if prepared is None else prepared

    def register_entity_initializer(self, entity_name, initializer):
        if not isinstance(entity_name, str) or not entity_name.strip() or not callable(initializer):
            raise ValueError("entity_name and callable initializer are required")
        self._entity_initializers.setdefault(entity_name, []).append(initializer)
        return self

    def initialize_entity(self, entity_name, entity):
        if not isinstance(entity_name, str) or not entity_name.strip() or entity is None:
            raise ValueError("entity_name and entity are required")
        for initializer in self._entity_initializers.get("*", ()):
            initializer(self, entity)
        for initializer in self._entity_initializers.get(entity_name, ()):
            initializer(self, entity)
        self._managed_entities.append(entity)
        return entity

    def managed_entities(self):
        return list(self._managed_entities)

    def continuous_page_cursor(self, query_key, offset):
        cursor = self._continuous_page_cursors.get((query_key, offset))
        if cursor is not None and cursor["expires_at"] <= __import__("time").time():
            self._continuous_page_cursors.pop((query_key, offset), None)
            return None
        return cursor

    def put_continuous_page_cursor(self, query_key, offset, cursor):
        if len(self._continuous_page_cursors) >= 4096:
            oldest = min(self._continuous_page_cursors,
                         key=lambda key: self._continuous_page_cursors[key]["expires_at"])
            self._continuous_page_cursors.pop(oldest, None)
        self._continuous_page_cursors[(query_key, offset)] = cursor

    def observe_continuous_page(self, plan, cursor_id=None):
        self._continuous_page_plan = plan
        self._continuous_page_cursor_id = cursor_id

    def continuous_page_plan(self): return self._continuous_page_plan
    def continuous_page_cursor_id(self): return self._continuous_page_cursor_id

    def _set_sql_log_mode(self, mode):
        self._sql_log_mode = mode
        self._sql_logs = []
        return self

    def enable_all_sql_log(self): return self._set_sql_log_mode("all")
    def enable_select_sql_log(self): return self._set_sql_log_mode("select")
    def enable_mutation_sql_log(self): return self._set_sql_log_mode("mutation")
    def disable_sql_log(self): return self._set_sql_log_mode("disabled")
    def clear_sql_logs(self): self._sql_logs = []
    def sql_logs(self): return list(self._sql_logs)

    def record_sql_evidence(self, operation, sql, params, elapsed_micros,
                            result_count=None, affected_rows=None):
        is_select = operation == SqlLogOperation.Select
        if (self._sql_log_mode == "disabled"
                or (self._sql_log_mode == "select" and not is_select)
                or (self._sql_log_mode == "mutation" and is_select)):
            return
        summary = (f"{result_count} rows returned" if result_count is not None
                   else f"{affected_rows} rows affected")
        self._sql_logs.append(SqlLogEntry(
            operation, sql, tuple(params), timedelta(microseconds=elapsed_micros),
            result_count, affected_rows, summary))

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

class RuntimeModule:
    """Immutable generated runtime manifest."""
    def __init__(self, entities=(), schemas=None, checkers=None, root_graphs=(), initial_graphs=()):
        self.entities = tuple(entities)
        self.schemas = dict(schemas or {})
        self.checkers = dict(checkers or {})
        self.root_graphs = tuple(root_graphs)
        self.initial_graphs = tuple(initial_graphs)

    def entity(self, entity):
        self.entities = (*self.entities, entity)
        return self

    def checker(self, entity, checker):
        self.checkers[entity] = checker
        return self

    def root_graph(self, graph):
        self.root_graphs = (*self.root_graphs, graph)
        return self

    def initial_graph(self, graph):
        self.initial_graphs = (*self.initial_graphs, graph)
        return self

    def and_module(self, other):
        return RuntimeModule(self.entities + other.entities,
                             {**self.schemas, **other.schemas},
                             {**self.checkers, **other.checkers},
                             self.root_graphs + other.root_graphs,
                             self.initial_graphs + other.initial_graphs)

    def apply_to(self, context):
        context.insert_resource("entities", self.entities)
        context.insert_resource("entity_schemas", dict(self.schemas))
        context._checker_registry.update(self.checkers)
        context.insert_resource("root_graphs", self.root_graphs)
        context.insert_resource("initial_graphs", self.initial_graphs)
