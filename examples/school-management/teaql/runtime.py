from dataclasses import dataclass
from datetime import timedelta
from enum import Enum
import asyncio
import builtins
import contextvars
import time

_ID_SET_STORE = {}
_ID_SET_LOCKS = {}

_SCHEMA_INVOCATION = object()

_CHECK_MESSAGES = {
    "en": {
        "required": "{location} is required",
        "min": "{location} is below the minimum",
        "max": "{location} exceeds the maximum",
        "min_length": "{location} is too short",
        "max_length": "{location} is too long",
    },
    "zh-CN": {
        "required": "{location} 为必填项",
        "min": "{location} 小于最小值",
        "max": "{location} 超过最大值",
        "min_length": "{location} 长度不足",
        "max_length": "{location} 长度过长",
    },
}
_SUPPORTED_LOCALES = {"en", "zh-CN", "zh-TW", "ja", "ko", "de", "fr", "es", "pt", "ar", "th", "id", "fil", "uk", "vi"}
_LOCALE_ALIASES = {"zh": "zh-CN", "zh-hans": "zh-CN", "cn": "zh-CN", "zh-hant": "zh-TW", "tw": "zh-TW", "en-us": "en", "en-gb": "en"}

@dataclass(frozen=True)
class ObjectLocation:
    segments: tuple = ()

    @classmethod
    def root(cls):
        return cls()

    def property(self, name):
        if not isinstance(name, str) or not name:
            raise ValueError("A canonical KSML property name is required")
        return ObjectLocation(self.segments + (("property", name),))

    def index(self, value):
        if value < 0:
            raise ValueError("Object location index must not be negative")
        return ObjectLocation(self.segments + (("index", value),))

    def prefixed_by(self, prefix):
        return ObjectLocation(prefix.segments + self.segments)

    @builtins.property
    def model_path(self):
        result = ""
        for kind, value in self.segments:
            result += f"[{value}]" if kind == "index" else ("." if result else "") + value
        return result

    @builtins.property
    def native_path(self):
        # Python's generated API uses canonical snake_case property names.
        return self.model_path

    @builtins.property
    def instance_path(self):
        def lower_camel(value):
            parts = value.split("_")
            return parts[0] + "".join(part[:1].upper() + part[1:] for part in parts[1:])
        def escape(value):
            return str(value).replace("~", "~0").replace("/", "~1")
        return "".join("/" + escape(lower_camel(value) if kind == "property" else value)
                       for kind, value in self.segments)

    def __str__(self):
        return self.native_path

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

@dataclass(frozen=True)
class FixEvidence:
    entity_type: str
    model_path: str
    source: str
    source_label: str

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
    comment: object
    purpose: object
    audit_reason: object
    trace_path: tuple
    sql: str
    params: tuple
    debug_sql: str
    elapsed: timedelta
    result_count: object = None
    affected_rows: object = None
    result_summary: str = ""

class DiagnosticSqlLogSink:
    """Value-bearing diagnostic SQL destination; the text sink is installed by default."""
    def write(self, entry):
        raise NotImplementedError

class TextDiagnosticSqlLogSink(DiagnosticSqlLogSink):
    def __init__(self, writer=print): self._writer = writer
    def write(self, entry):
        trace = " -> ".join(f"{key}:{value}" for key, value in entry.trace_path)
        comment = "" if entry.comment is None else str(entry.comment)
        purpose = "" if entry.purpose is None else str(entry.purpose)
        audit_reason = "" if entry.audit_reason is None else str(entry.audit_reason)
        self._writer(
            f"[TeaQL SQL][{entry.operation.value}][{int(entry.elapsed.total_seconds() * 1000000)}us] "
            f"{entry.result_summary} comment={comment} purpose={purpose} "
            f"auditReason={audit_reason} tracePath=[{trace}]\n"
            f"Parameterized SQL: {entry.sql} params={entry.params!r}\n"
            f"Debug SQL: {entry.debug_sql}")

def _diagnostic_sql_literal(value):
    if value is None: return "NULL"
    if isinstance(value, bool): return "1" if value else "0"
    if isinstance(value, (int, float)): return str(value)
    if isinstance(value, (bytes, bytearray)): return "X'" + bytes(value).hex().upper() + "'"
    return "'" + str(value).replace("'", "''") + "'"

def _render_diagnostic_sql(sql, params):
    rendered = sql
    for value in params:
        rendered = rendered.replace("?", _diagnostic_sql_literal(value), 1)
    return rendered

@dataclass(frozen=True)
class RawAuditEvent:
    kind: str
    entity: str
    entity_id: object
    reason: str
    changes: tuple
    actor: str = ""
    category: str = ""

@dataclass(frozen=True)
class SafeAuditEvent:
    kind: str
    entity: str
    entity_id: object
    reason: str
    fields: tuple
    actor: str = ""
    category: str = ""

class UserContext:
    """Runtime dependencies and trusted request state initialized by the server."""

    def __init__(self):
        self._resources = {}
        self._user_identifier = ""
        self._entity_root = EntityRoot()
        self._standard_audit_sink = None
        self._app_audit_sink = None
        self._audit_policies = {}
        self._entity_initializers = {}
        self._managed_entities = []
        self._continuous_page_cursors = {}
        self._continuous_page_plan = "DISABLED"
        self._continuous_page_cursor_id = None
        self._id_set_plan = "ID_SET_DISABLED"
        self._id_set_count = 0
        self._id_set_count_accuracy = "UNKNOWN"
        self._query_sql_log_enabled = True
        self._mutation_sql_log_enabled = True
        self._sql_logs = []
        self._resources["diagnostic_sql_log_sink"] = TextDiagnosticSqlLogSink()
        self._checker_registry = {}
        self._checked_mutations = set()
        self._graph_save_active = False
        self._graph_save_lock = asyncio.Lock()
        self._graph_save_owner = contextvars.ContextVar(
            f"teaql_graph_save_owner_{id(self)}", default=None)
        self._graph_commit_actions = []
        self._graph_rollback_actions = []

    def begin_fix_evidence(self):
        self._resources["fix_evidence_current"] = []
        return self

    def record_fix_evidence(self, entity_type, model_path, source, source_label):
        normalized = str(source_label).lower()
        if not entity_type or not model_path or source not in ("clock", "context") or not source_label or "authorization" in normalized or "cookie" in normalized or "token=" in normalized:
            raise ValueError("Fix evidence must contain only safe framework provenance labels")
        self._resources.setdefault("fix_evidence_current", []).append(FixEvidence(entity_type, model_path, source, source_label))
        return self

    def finish_fix_evidence(self):
        self._resources["fix_evidence_last"] = tuple(self._resources.get("fix_evidence_current", ()))
        self._resources.pop("fix_evidence_current", None)
        return self

    def last_fix_evidence(self):
        return self._resources.get("fix_evidence_last", ())

    @classmethod
    def new(cls):
        return cls()

    def entity_root(self):
        return self._entity_root

    def insert_resource(self, resource_type, resource):
        self._resources[resource_type] = resource
        return self

    def set_user_identifier(self, identifier):
        self._user_identifier = "" if identifier is None else str(identifier)

    def user_identifier(self):
        return self._user_identifier

    def set_locale_code(self, code):
        if not isinstance(code, str) or not code.strip():
            raise ValueError(f"Unsupported locale: {code}")
        normalized = code.strip().replace("_", "-")
        canonical = next((value for value in _SUPPORTED_LOCALES if value.lower() == normalized.lower()), None)
        canonical = canonical or _LOCALE_ALIASES.get(normalized.lower())
        if canonical is None:
            raise ValueError(f"Unsupported locale: {code}")
        self.insert_resource("locale", canonical)
        return self

    def set_language_code(self, code):
        return self.set_locale_code(code)

    def _translate_check_results(self, results):
        locale = self.get_resource("locale") or "en"
        messages = _CHECK_MESSAGES.get(locale, _CHECK_MESSAGES["en"])
        for result in results:
            key = str(result.rule_id).lower()
            if key == "min_str_len": key = "min_length"
            if key == "max_str_len": key = "max_length"
            template = messages.get(key) or _CHECK_MESSAGES["en"].get(key) or f"checker.{key}"
            location = getattr(result.location, "native_path", str(result.location))
            result.message = template.replace("{location}", location)
        return results

    async def execute_graph_save(self, work):
        if self._graph_save_owner.get() is not None:
            return await work()
        async with self._graph_save_lock:
            provider = self.require_resource("dataService")
            begin = getattr(provider, "begin", None)
            if not callable(begin):
                raise RuntimeError("Configured dataService does not support graph transactions")
            transaction = await begin(self)
            owner_token = self._graph_save_owner.set(object())
            self._graph_save_active = True
            self._graph_commit_actions = []
            self._graph_rollback_actions = []
            from datetime import datetime
            self.insert_resource("fix_time", datetime.now())
            self.begin_fix_evidence()
            self.insert_resource("dataService", transaction)
            try:
                result = await work()
            except BaseException:
                try:
                    await transaction.rollback(self)
                finally:
                    for action in reversed(self._graph_rollback_actions):
                        action()
                raise
            else:
                try:
                    await transaction.commit(self)
                except BaseException:
                    try:
                        await transaction.rollback(self)
                    finally:
                        for action in reversed(self._graph_rollback_actions):
                            action()
                    raise
                for action in self._graph_commit_actions:
                    action()
                return result
            finally:
                self.insert_resource("dataService", provider)
                self._graph_save_active = False
                self._graph_commit_actions = []
                self._graph_rollback_actions = []
                self._resources.pop("fix_time", None)
                self.finish_fix_evidence()
                self._graph_save_owner.reset(owner_token)

    def after_graph_commit(self, work):
        if not self._graph_save_active:
            raise RuntimeError("No graph save is active")
        self._graph_commit_actions.append(work)

    def after_graph_rollback(self, work):
        if not self._graph_save_active:
            raise RuntimeError("No graph save is active")
        self._graph_rollback_actions.append(work)

    def install(self, module):
        """Install a passive metadata manifest; this never changes a database schema."""
        module.apply_to(self)
        return self

    async def ensure_schema(self):
        """Explicitly reconcile schema and generated bootstrap data."""
        provider = self.require_resource("dataService")
        await provider._ensure_schema(self, _SCHEMA_INVOCATION)
        for bootstrap in self.get_resource("_teaql_generated_bootstraps") or ():
            await bootstrap(self)

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
        owns_fix_time = self._resources.get("fix_time") is None
        if owns_fix_time:
            self.insert_resource("fix_time", datetime.now())
            self.begin_fix_evidence()
        self.insert_resource("fix_operation", "insert" if hasattr(mutation, "payload") else "update")
        results = []
        try:
            checker.check_and_fix(self, record, None, results)
        finally:
            if owns_fix_time:
                self._resources.pop("fix_time", None)
                self.finish_fix_evidence()
            self._resources.pop("fix_operation", None)
        if results:
            self._translate_check_results(results)
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

    def id_set_get(self, key):
        retained = _ID_SET_STORE.get(key)
        if retained is not None and retained["expires_at"] <= time.time():
            _ID_SET_STORE.pop(key, None)
            return None
        return retained

    def id_set_put(self, key, ids, ttl_seconds):
        if len(ids) * 8 > 256 * 1024 * 1024:
            raise ValueError("retained ID set exceeds store memory ceiling")
        while len(_ID_SET_STORE) >= 64:
            oldest = min(_ID_SET_STORE, key=lambda item: _ID_SET_STORE[item]["expires_at"])
            _ID_SET_STORE.pop(oldest, None)
        _ID_SET_STORE[key] = {"ids": tuple(ids), "expires_at": time.time() + ttl_seconds}

    def id_set_lock(self, key):
        return _ID_SET_LOCKS.setdefault((id(asyncio.get_running_loop()), key), asyncio.Lock())

    def observe_id_set(self, plan, accuracy="UNKNOWN", count=0):
        self._id_set_plan, self._id_set_count_accuracy, self._id_set_count = plan, accuracy, count

    def id_set_plan(self): return self._id_set_plan
    def id_set_count(self): return self._id_set_count, self._id_set_count_accuracy

    def _set_sql_log_mode(self, mode):
        self._query_sql_log_enabled = mode in ("all", "select")
        self._mutation_sql_log_enabled = mode in ("all", "mutation")
        self._sql_logs = []
        return self

    def enable_all_sql_log(self): return self._set_sql_log_mode("all")
    def enable_select_sql_log(self): return self._set_sql_log_mode("select")
    def enable_mutation_sql_log(self): return self._set_sql_log_mode("mutation")
    def disable_sql_log(self): return self._set_sql_log_mode("disabled")
    def disable_select_sql_log(self):
        self._query_sql_log_enabled = False
        return self
    def disable_mutation_sql_log(self):
        self._mutation_sql_log_enabled = False
        return self
    def clear_sql_logs(self): self._sql_logs = []
    def sql_logs(self): return list(self._sql_logs)
    def with_diagnostic_sql_log_sink(self, sink):
        self._resources["diagnostic_sql_log_sink"] = sink
        return self
    def set_diagnostic_sql_log_sink(self, sink):
        self._resources["diagnostic_sql_log_sink"] = sink

    def record_sql_evidence(self, operation, sql, params, elapsed_micros,
                            result_count=None, affected_rows=None, comment=None,
                            purpose=None, audit_reason=None, trace_path=()):
        is_select = operation == SqlLogOperation.Select
        if ((is_select and not self._query_sql_log_enabled)
                or (not is_select and not self._mutation_sql_log_enabled)):
            return
        summary = (f"{result_count} rows returned" if result_count is not None
                   else f"{affected_rows} rows affected")
        entry = SqlLogEntry(operation, comment, purpose, audit_reason, tuple(trace_path),
                            sql, tuple(params), _render_diagnostic_sql(sql, params),
                            timedelta(microseconds=elapsed_micros), result_count, affected_rows, summary)
        self._sql_logs.append(entry)
        sink = self._resources.get("diagnostic_sql_log_sink")
        if sink is not None: sink.write(entry)

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
        raw = RawAuditEvent(
            kind, command.entity, result.get("id"), req.comment,
            tuple((name, None, value) for name, value in values.items()),
            self.user_identifier(), self.get_resource("bootstrapCategory") or "",
        )
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
            safe = SafeAuditEvent(
                kind, command.entity, result.get("id"), req.comment, tuple(fields),
                raw.actor, raw.category,
            )
            emitted = self._app_audit_sink.on_safe_event(self, safe)
            if hasattr(emitted, "__await__"): await emitted

class RuntimeModule:
    """Immutable generated runtime manifest."""
    def __init__(self, entities=(), schemas=None, checkers=None, root_graphs=(), initial_graphs=(), generated_bootstraps=()):
        self.entities = tuple(entities)
        self.schemas = dict(schemas or {})
        self.checkers = dict(checkers or {})
        self.root_graphs = tuple(root_graphs)
        self.initial_graphs = tuple(initial_graphs)
        self.generated_bootstraps = tuple(generated_bootstraps)

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

    def generated_bootstrap(self, bootstrap):
        self.generated_bootstraps = (*self.generated_bootstraps, bootstrap)
        return self

    def and_module(self, other):
        return RuntimeModule(self.entities + other.entities,
                             {**self.schemas, **other.schemas},
                             {**self.checkers, **other.checkers},
                             self.root_graphs + other.root_graphs,
                             self.initial_graphs + other.initial_graphs,
                             self.generated_bootstraps + other.generated_bootstraps)

    def apply_to(self, context):
        context.insert_resource("entities", self.entities)
        context.insert_resource("entity_schemas", dict(self.schemas))
        context._checker_registry.update(self.checkers)
        context.insert_resource("root_graphs", self.root_graphs)
        context.insert_resource("initial_graphs", self.initial_graphs)
        context.insert_resource("_teaql_generated_bootstraps", self.generated_bootstraps)