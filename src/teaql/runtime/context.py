from typing import Dict, Any, Optional, List, Callable, TypeVar
import asyncio
import contextvars
from dataclasses import dataclass
from array import array


TEntity = TypeVar("TEntity")
EntityInitializer = Callable[["UserContext", Any], None]

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
    def __init__(self, reason: str, expected_type: str, active_root: Optional[ContextEntityRef] = None):
        self.reason = reason
        self.expected_type = expected_type
        self.active_root = active_root
        super().__init__(f"context root {reason}: expected {expected_type}")

import threading
import time


_local_cache = {}
_local_cache_lock = threading.RLock()
_local_locks = {}
_local_lock_condition = threading.Condition(threading.RLock())

@dataclass(frozen=True)
class RetainedIdSet:
    query_key: str
    ids: array
    expires_at: float

class InMemoryIdSetStore:
    def __init__(self, max_entries: int = 64, max_bytes: int = 256 << 20):
        self._lock = threading.RLock()
        self._sets: Dict[str, RetainedIdSet] = {}
        self._max_entries = max_entries
        self._max_bytes = max_bytes

    def get(self, query_key: str) -> Optional[RetainedIdSet]:
        with self._lock:
            retained = self._sets.get(query_key)
            if retained is not None and retained.expires_at <= time.time():
                self._sets.pop(query_key, None)
                return None
            return retained

    def put(self, retained: RetainedIdSet) -> None:
        size = len(retained.ids) * retained.ids.itemsize
        if size > self._max_bytes:
            raise ValueError("retained ID set exceeds store memory ceiling")
        with self._lock:
            while self._sets and (len(self._sets) >= self._max_entries or
                                  sum(len(value.ids) * value.ids.itemsize for value in self._sets.values()) + size > self._max_bytes):
                oldest = min(self._sets, key=lambda key: self._sets[key].expires_at)
                self._sets.pop(oldest, None)
            self._sets[retained.query_key] = retained

    def invalidate(self, query_key: str) -> None:
        with self._lock:
            self._sets.pop(query_key, None)

_default_id_set_store = InMemoryIdSetStore()


class UserContext:
    def __init__(self):
        self._resources: Dict[str, Any] = {}
        self._resources["sql_log_options"] = SqlLogOptions.all()
        self._resources["diagnostic_sql_log_sink"] = TextDiagnosticSqlLogSink()
        self._metadata: Optional[Any] = None
        self._user_identifier: str = ""
        self._entities: List[Any] = []
        self._initial_graphs: List[Any] = []
        self._root_graphs: List[Any] = []
        self._standard_audit_sink: Optional[Any] = None
        self._app_audit_sink: Optional[Any] = None
        self._entity_initializers: Dict[str, List[EntityInitializer]] = {}
        self._managed_entities: List[Any] = []
        from .telemetry import NOOP_RUNTIME_TELEMETRY
        self._runtime_telemetry = NOOP_RUNTIME_TELEMETRY
        self._id_set_store = _default_id_set_store
        self._id_set_plan = "ID_SET_DISABLED"
        self._id_set_count = 0
        self._id_set_count_accuracy = "UNKNOWN"
        self._graph_save_active = False
        self._graph_save_lock = asyncio.Lock()
        self._graph_save_owner = contextvars.ContextVar(
            f"teaql_graph_save_owner_{id(self)}", default=None
        )
        self._graph_commit_actions: List[Any] = []
        self._graph_rollback_actions: List[Any] = []
        self._fix_evidence_current: List[FixEvidence] = []
        self._fix_evidence_last: List[FixEvidence] = []
        self._checked_mutations = set()

    def begin_fix_evidence(self):
        self._fix_evidence_current = []
        return self

    def record_fix_evidence(self, entity_type: str, model_path: str, source: str, source_label: str):
        normalized = source_label.lower()
        if not entity_type or not model_path or source not in ("clock", "context") or not source_label \
                or "authorization" in normalized or "cookie" in normalized or "token=" in normalized:
            raise ValueError("Fix evidence must contain only safe framework provenance labels")
        self._fix_evidence_current.append(FixEvidence(entity_type, model_path, source, source_label))
        return self

    def finish_fix_evidence(self):
        self._fix_evidence_last = list(self._fix_evidence_current)
        self._fix_evidence_current = []
        return self

    def last_fix_evidence(self):
        return tuple(self._fix_evidence_last)

    @classmethod
    def new(cls) -> 'UserContext':
        return cls()

    def with_active_root(self, root: ContextEntityRef) -> 'UserContext':
        if not isinstance(root, ContextEntityRef):
            raise TypeError("active root must be ContextEntityRef")
        self.insert_resource("active_root", root)
        return self

    def require_active_root(self, expected_type: str) -> ContextEntityRef:
        root = self.get_resource("active_root")
        if not isinstance(root, ContextEntityRef):
            raise ContextRootError("missing", expected_type)
        if root.entity != expected_type:
            raise ContextRootError("type_mismatch", expected_type, root)
        return root

    async def execute_graph_save(self, work):
        """Run one generated entity graph in one provider transaction."""
        if self._graph_save_owner.get() is not None:
            return await work()
        async with self._graph_save_lock:
            provider = self.require_resource("dataService")
            begin = getattr(provider, "begin", None)
            if not callable(begin):
                raise RuntimeError("Configured dataService does not support graph transactions")
            try:
                transaction = await begin(self)
            except TypeError:
                transaction = await begin()
            owner_token = self._graph_save_owner.set(object())
            self._graph_save_active = True
            self._graph_commit_actions = []
            self._graph_rollback_actions = []
            self.insert_resource("fix_time", datetime.now())
            self.begin_fix_evidence()
            self.insert_resource("dataService", transaction)
            try:
                result = await work()
            except BaseException:
                try:
                    await self._finish_graph_transaction(transaction, "rollback")
                finally:
                    for action in reversed(self._graph_rollback_actions):
                        action()
                raise
            else:
                try:
                    await self._finish_graph_transaction(transaction, "commit")
                except BaseException:
                    try:
                        await self._finish_graph_transaction(transaction, "rollback")
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

    async def _finish_graph_transaction(self, transaction, operation: str) -> None:
        finish = getattr(transaction, operation)
        try:
            await finish(self)
        except TypeError:
            await finish()

    def after_graph_commit(self, work) -> None:
        if not self._graph_save_active:
            raise RuntimeError("No graph save is active")
        self._graph_commit_actions.append(work)

    def after_graph_rollback(self, work) -> None:
        if not self._graph_save_active:
            raise RuntimeError("No graph save is active")
        self._graph_rollback_actions.append(work)

    async def get_in_store(self, key: str) -> Optional[Any]:
        store = self.get_resource("data_store")
        if store and hasattr(store, "get"):
            return await store.get(key)
        return None

    async def put_in_store(self, key: str, value: Any, timeout_seconds: Optional[int] = None):
        store = self.get_resource("data_store")
        if store and hasattr(store, "put"):
            await store.put(key, value, timeout_seconds)

    async def clear_in_store(self, key: str):
        store = self.get_resource("data_store")
        if store and hasattr(store, "remove"):
            await store.remove(key)
        
    def register_entity(self, entity_desc: Any):
        self._entities.append(entity_desc)

    def register_entity_initializer(
        self, entity_name: str, initializer: EntityInitializer
    ) -> "UserContext":
        """Register a trusted initializer; use ``*`` for every entity type."""
        if not isinstance(entity_name, str) or not entity_name.strip() or not callable(initializer):
            raise ValueError("entity_name and callable initializer are required")
        self._entity_initializers.setdefault(entity_name, []).append(initializer)
        return self

    def initialize_entity(self, entity_name: str, entity: TEntity) -> TEntity:
        """Apply trusted initializers and bring a new entity into managed scope."""
        if not isinstance(entity_name, str) or not entity_name.strip() or entity is None:
            raise ValueError("entity_name and entity are required")
        for initializer in self._entity_initializers.get("*", []):
            initializer(self, entity)
        for initializer in self._entity_initializers.get(entity_name, []):
            initializer(self, entity)
        self._managed_entities.append(entity)
        return entity

    def managed_entities(self) -> List[Any]:
        return list(self._managed_entities)

    def with_runtime_telemetry(self, telemetry: Any) -> "UserContext":
        self._runtime_telemetry = telemetry
        return self

    def set_runtime_telemetry(self, telemetry: Any) -> None:
        self._runtime_telemetry = telemetry

    def runtime_telemetry(self) -> Any:
        return self._runtime_telemetry

    def set_id_set_store(self, store: Any) -> None:
        if store is None:
            raise ValueError("ID set store must not be None")
        self._id_set_store = store

    def id_set_store(self) -> Any:
        return self._id_set_store

    def observe_id_set(self, plan: str, accuracy: str = "UNKNOWN", count: int = 0) -> None:
        self._id_set_plan = plan
        self._id_set_count_accuracy = accuracy
        self._id_set_count = count

    def id_set_plan(self) -> str:
        return self._id_set_plan

    def id_set_count(self) -> tuple[int, str]:
        return self._id_set_count, self._id_set_count_accuracy
        
    def all_entities(self) -> List[Any]:
        return self._entities
        
    def add_initial_graph(self, graph_node: Any):
        self._initial_graphs.append(graph_node)
        
    def initial_graphs(self) -> List[Any]:
        return self._initial_graphs

    def add_root_graph(self, graph_node: Any):
        self._root_graphs.append(graph_node)

    def root_graphs(self) -> List[Any]:
        return self._root_graphs

    def with_metadata(self, metadata: Any) -> 'UserContext':
        self._metadata = metadata
        return self

    def insert_resource(self, resource_type: str, resource: Any):
        self._resources[resource_type] = resource
        if resource_type == "dataService" and hasattr(resource, "_ensure_schema"):
            self._resources["schema_provider"] = resource
        return self

    def get_resource(self, resource_type: str) -> Optional[Any]:
        return self._resources.get(resource_type)
        
    def require_resource(self, resource_type: str) -> Any:
        res = self._resources.get(resource_type)
        if res is None:
            raise Exception(f"Resource {resource_type} not found")
        return res

    def prepare_query(self, query: Any) -> Any:
        """Apply trusted request policy exactly once before execution."""
        policy = self.get_resource("request_policy")
        if policy is None:
            return query
        if callable(policy):
            prepared = policy(query)
        elif hasattr(policy, "apply"):
            prepared = policy.apply(query)
        else:
            raise TypeError("request_policy must be callable or expose apply(query)")
        return query if prepared is None else prepared

    def set_user_identifier(self, identifier: str):
        self._user_identifier = identifier

    def user_identifier(self) -> str:
        return self._user_identifier

    def with_user_identifier(self, identifier: str) -> 'UserContext':
        self._user_identifier = identifier
        return self

    def set_user_identifier_option(self, identifier: Optional[str]):
        if identifier is not None:
            self._user_identifier = identifier
        else:
            self._user_identifier = ""

    def with_user_identifier_option(self, identifier: Optional[str]) -> 'UserContext':
        self.set_user_identifier_option(identifier)
        return self

    def timezone(self) -> Optional[str]:
        return self.get_resource("timezone")

    def set_timezone(self, tz: str):
        self.insert_resource("timezone", tz)

    def with_timezone(self, tz: str) -> 'UserContext':
        self.set_timezone(tz)
        return self

    def trace_id(self) -> Optional[str]:
        return self.get_resource("trace_id")

    def set_trace_id(self, trace_id: str):
        self.insert_resource("trace_id", trace_id)

    def with_trace_id(self, trace_id: str) -> 'UserContext':
        self.set_trace_id(trace_id)
        return self

    def with_module(self, module: Any) -> 'UserContext':
        if hasattr(module, 'apply_to'):
            module.apply_to(self)
        return self

    def install(self, module: Any) -> 'UserContext':
        """Install a passive runtime manifest without changing database schemas."""
        return self.with_module(module)

    def set_initial_graphs(self, graphs: List[Any]):
        self._initial_graphs = graphs

    def set_metadata(self, metadata: Any):
        self._metadata = metadata

    def with_entity_registry(self, registry: Any) -> 'UserContext':
        self.insert_resource("entity_registry", registry)
        return self

    def set_entity_registry(self, registry: Any):
        self.insert_resource("entity_registry", registry)

    def with_entity_data_service_behavior_registry(self, registry: Any) -> 'UserContext':
        self.insert_resource("entity_data_service_behavior_registry", registry)
        return self

    def set_entity_data_service_behavior_registry(self, registry: Any):
        self.insert_resource("entity_data_service_behavior_registry", registry)

    def with_request_policy(self, policy: Any) -> 'UserContext':
        self.insert_resource("request_policy", policy)
        return self

    def set_request_policy(self, policy: Any):
        self.insert_resource("request_policy", policy)

    def clear_request_policy(self):
        self._resources.pop("request_policy", None)

    def with_checker_registry(self, registry: Any) -> 'UserContext':
        self.insert_resource("checker_registry", registry)
        return self

    def set_checker_registry(self, registry: Any):
        self.insert_resource("checker_registry", registry)

    def with_custom_event_sink(self, sink: Any) -> 'UserContext':
        self._app_audit_sink = sink
        return self

    def set_custom_event_sink(self, sink: Any):
        self._app_audit_sink = sink

    def initialize_audit(self, raw_sink: Any, app_sink: Any = None) -> 'UserContext':
        """Compatibility entry point for generated applications."""
        self._set_standard_audit_sink(raw_sink)
        self._app_audit_sink = app_sink
        return self

    def configure_audit_policy(self, entity: str, mask_fields: List[str],
                               value_max_len: Optional[int] = None) -> 'UserContext':
        descriptor = self.entity(entity)
        if descriptor is not None:
            descriptor.audit_mask_fields(mask_fields)
            descriptor.audit_value_max_len(value_max_len)
        return self

    def with_internal_id_generator(self, gen: Any) -> 'UserContext':
        self.insert_resource("internal_id_generator", gen)
        return self

    def set_internal_id_generator(self, gen: Any):
        self.insert_resource("internal_id_generator", gen)

    def with_schema_provider(self, provider: Any) -> 'UserContext':
        self.insert_resource("schema_provider", provider)
        return self

    def set_schema_provider(self, provider: Any):
        self.insert_resource("schema_provider", provider)

    async def ensure_schema(self):
        provider = self.get_resource("schema_provider")
        if provider:
            from ._schema_capability import SCHEMA_CAPABILITY
            await provider._ensure_schema(self, SCHEMA_CAPABILITY)
            for bootstrap in self.get_resource("_teaql_generated_bootstraps") or ():
                await bootstrap(self)
        else:
            raise Exception("missing schema provider")

    def with_language(self, language: Any) -> 'UserContext':
        self.set_locale_code(language)
        return self

    def set_language(self, language: Any):
        self.set_locale_code(language)

    def set_language_code(self, code: str):
        self.set_locale_code(code)

    def set_locale_code(self, code: str):
        from .i18n import Locale
        locale = Locale.parse(code)
        self.insert_resource("locale", locale)
        return self

    def install_i18n_catalog(self, catalog: Any):
        if catalog is None: raise ValueError("catalog is required")
        self.insert_resource("i18n_catalog", catalog)
        return self

    def i18n_catalog(self):
        from .i18n import I18nCatalog
        return self.get_resource("i18n_catalog") or I18nCatalog.builtin()

    def generate_id(self, entity: str) -> Optional[int]:
        gen = self.get_resource("internal_id_generator")
        if gen and hasattr(gen, "generate_id"):
            return gen.generate_id(entity)
        return None

    def next_id(self, entity: str) -> int:
        gen_id = self.generate_id(entity)
        if gen_id is not None:
            return gen_id
        # Simple fallback
        return int(datetime.now().timestamp() * 1000)

    def entity(self, name: str) -> Optional[Any]:
        if self._metadata and hasattr(self._metadata, "entity"):
            return self._metadata.entity(name)
        for e in self._entities:
            if getattr(e, "_name", None) == name:
                return e
        return None

    def require_entity(self, name: str) -> Any:
        e = self.entity(name)
        if e is None:
            raise Exception(f"MissingEntity: {name}")
        return e

    def insert_named_resource(self, name: str, resource: Any):
        if "named_resources" not in self._resources:
            self._resources["named_resources"] = {}
        self._resources["named_resources"][name] = resource

    def get_named_resource(self, name: str) -> Optional[Any]:
        return self._resources.get("named_resources", {}).get(name)

    def require_named_resource(self, name: str) -> Any:
        res = self.get_named_resource(name)
        if res is None:
            raise Exception(f"MissingResource: {name}")
        return res

    def put_local(self, key: str, value: Any):
        if "locals" not in self._resources:
            self._resources["locals"] = {}
        self._resources["locals"][key] = value

    def local(self, key: str) -> Optional[Any]:
        return self._resources.get("locals", {}).get(key)

    def remove_local(self, key: str) -> Optional[Any]:
        return self._resources.get("locals", {}).pop(key, None)

    def has_entity_data_service(self, entity: str) -> bool:
        registry = self.get_resource("entity_registry")
        in_registry = registry and hasattr(registry, "contains") and registry.contains(entity)
        return bool(in_registry or self.entity(entity))

    def entity_data_service_behavior(self, entity: str) -> Optional[Any]:
        registry = self.get_resource("entity_data_service_behavior_registry")
        if registry and hasattr(registry, "behavior"):
            return registry.behavior(entity)
        return None

    def has_checker(self, entity: str) -> bool:
        registry = self.get_resource("checker_registry")
        return bool(registry and hasattr(registry, "checker") and registry.checker(entity))

    def check_and_fix_record(self, entity: str, record: Any):
        self.check_and_fix_record_at(entity, record, None)

    def check_and_fix_record_at(self, entity: str, record: Any, location: Any):
        registry = self.get_resource("checker_registry")
        if not registry or not hasattr(registry, "checker"):
            return
            
        checker = registry.checker(entity)
        if not checker:
            return
            
        results = []
        if hasattr(checker, "check_and_fix"):
            checker.check_and_fix(self, record, location, results)
            
        if results:
            self.translate_check_results(results)
            from .i18n import CheckException
            raise CheckException(results)

    def check_and_fix_mutation(self, mutation: Any):
        """Run generated fixes and checks before a mutation reaches a provider."""
        entity = getattr(mutation, "entity", None)
        record = getattr(mutation, "values", None)
        if not entity or record is None:
            return
        from datetime import datetime
        owns_fix_time = self.get_resource("fix_time") is None
        if owns_fix_time:
            self.insert_resource("fix_time", datetime.now())
            self.begin_fix_evidence()
        self.insert_resource("fix_operation", type(mutation).__name__.replace("Command", "").lower())
        try:
            self.check_and_fix_record(entity, record)
        finally:
            if owns_fix_time:
                self._resources.pop("fix_time", None)
                self.finish_fix_evidence()
            self._resources.pop("fix_operation", None)

    def mark_mutation_checked(self, mutation: Any) -> None:
        self._checked_mutations.add(id(mutation))

    def consume_mutation_checked(self, mutation: Any) -> bool:
        key = id(mutation)
        if key not in self._checked_mutations:
            return False
        self._checked_mutations.remove(key)
        return True

    def translate_check_results(self, results: Any):
        for r in results:
            self.i18n_catalog().translate_check_result(r, self.language())
        return results

    async def send_audit_event(self, event: Any):
        from .audit import deliver
        from .telemetry import RuntimeOperation, start_runtime_operation
        scope = start_runtime_operation(self._runtime_telemetry, RuntimeOperation(
            "audit", f"{event.entity}.audit", {
                "teaql.entity.type": event.entity,
                "teaql.mutation.kind": event.kind.value,
                "teaql.audit.changed_field_count": len(event.changes),
            },
        ))
        try:
            if self._standard_audit_sink is not None:
                await deliver(self._standard_audit_sink, "on_event", self, event)
            if self._app_audit_sink is not None:
                descriptor = self.entity(event.entity)
                mask_fields = getattr(descriptor, "audit_mask_fields_val", []) if descriptor else []
                max_len = getattr(descriptor, "audit_value_max_len_val", None) if descriptor else None
                await deliver(self._app_audit_sink, "on_safe_event", self, event.safe(mask_fields, max_len))
            scope.success()
        except BaseException as error:
            scope.failure(error)
            raise

    def _set_standard_audit_sink(self, sink: Any):
        self._standard_audit_sink = sink

    def with_app_audit_event_sink(self, sink: Any) -> 'UserContext':
        self._app_audit_sink = sink
        return self

    def with_sql_log_options(self, options: 'SqlLogOptions') -> 'UserContext':
        self.insert_resource("sql_log_options", options)
        return self

    def set_sql_log_options(self, options: 'SqlLogOptions'):
        self.insert_resource("sql_log_options", options)

    def sql_log_options(self) -> 'SqlLogOptions':
        opts = self.get_resource("sql_log_options")
        if not opts:
            opts = SqlLogOptions.all()
            self.insert_resource("sql_log_options", opts)
        return opts

    def with_diagnostic_sql_log_sink(self, sink: 'DiagnosticSqlLogSink') -> 'UserContext':
        self.insert_resource("diagnostic_sql_log_sink", sink)
        return self

    def set_diagnostic_sql_log_sink(self, sink: Optional['DiagnosticSqlLogSink']):
        self.insert_resource("diagnostic_sql_log_sink", sink)

    def enable_select_sql_log(self):
        self.set_sql_log_options(SqlLogOptions.select_only())
        self.clear_sql_logs()

    def enable_mutation_sql_log(self):
        self.set_sql_log_options(SqlLogOptions.mutation_only())
        self.clear_sql_logs()

    def enable_all_sql_log(self):
        self.set_sql_log_options(SqlLogOptions.all())
        self.clear_sql_logs()

    def disable_sql_log(self):
        self.set_sql_log_options(SqlLogOptions.disabled())
        self.clear_sql_logs()

    def disable_select_sql_log(self):
        options = self.sql_log_options()
        self.set_sql_log_options(SqlLogOptions(False, options.mutation))

    def disable_mutation_sql_log(self):
        options = self.sql_log_options()
        self.set_sql_log_options(SqlLogOptions(options.select, False))

    def sql_logs(self) -> List['SqlLogEntry']:
        return self._resources.get("sql_logs", [])

    def clear_sql_logs(self):
        self._resources["sql_logs"] = []

    def data_service_internal(self, entity: str) -> Any:
        # Returns internal data service for entity
        registry = self.get_resource("entity_registry")
        if registry and hasattr(registry, "get_internal_service"):
            return registry.get_internal_service(entity)
        return None

    def entity_data_service(self, entity: str) -> Any:
        return self.data_service_internal(entity)

    def language(self) -> Any:
        from .i18n import Locale
        return self.get_resource("locale") or Locale.ENGLISH

    def record_metadata_log(self, metadata: Any):
        op = SqlLogOperation.Select
        op_str = str(getattr(metadata, 'operation', '')).lower()
        if 'insert' in op_str: op = SqlLogOperation.Insert
        elif 'update' in op_str: op = SqlLogOperation.Update
        elif 'delete' in op_str: op = SqlLogOperation.Delete
        elif 'recover' in op_str: op = SqlLogOperation.Recover
        if not self.sql_log_options().enabled_for(op):
            return

        started_at = getattr(metadata, 'started_at', datetime.now())
        ended_at = getattr(metadata, 'ended_at', started_at)
        entry = SqlLogEntry(
            operation=op,
            comment=getattr(metadata, 'comment', None),
            purpose=getattr(metadata, 'purpose', None),
            audit_reason=getattr(metadata, 'audit_reason', None),
            trace_path=list(getattr(metadata, 'trace_chain', [])),
            sql=getattr(metadata, 'parameterized_sql', ''),
            params=list(getattr(metadata, 'parameters', [])),
            debug_sql=getattr(metadata, 'debug_query', '') or '',
            pretty_sql=getattr(metadata, 'debug_query', '') or '',
            started_at=started_at,
            ended_at=ended_at,
            elapsed=ended_at - started_at,
            result_count=getattr(metadata, 'result_count', None),
            result_type=None,
            affected_rows=getattr(metadata, 'affected_rows', None),
            result_summary=""
        )
        if entry.result_count is not None:
            entry.result_summary = f"{entry.result_count} rows returned"
        elif entry.affected_rows is not None:
            entry.result_summary = f"{entry.affected_rows} rows affected"

        logs = self.sql_logs()
        logs.append(entry)
        self._resources["sql_logs"] = logs
        sink = self.get_resource("diagnostic_sql_log_sink")
        if sink is not None:
            sink.write(entry)
        buf = self.get_resource("UnifiedLogBuffer")
        if buf:
            buf.entries.append(UnifiedLogEntry(
                timestamp=entry.started_at,
                user_identifier=self.user_identifier(),
                trace_chain=getattr(metadata, 'trace_chain', []),
                payload=LogPayload.Sql(entry)
            ))

    def record_sql_log(self, operation: Any, query: Any, started_at: Any, ended_at: Any, elapsed: Any, result_count: Any = None, affected_rows: Any = None):
        if not self.sql_log_options().enabled_for(operation):
            return
            
        debug_sql = getattr(query, 'debug_sql', lambda *args: "")() if hasattr(query, 'debug_sql') else getattr(query, 'sql', "")
        
        entry = SqlLogEntry(
            operation=operation,
            comment=None,
            purpose=None,
            audit_reason=None,
            trace_path=[],
            sql=getattr(query, 'sql', ""),
            params=getattr(query, 'params', []),
            debug_sql=debug_sql,
            pretty_sql=debug_sql,
            started_at=started_at,
            ended_at=ended_at,
            elapsed=elapsed,
            result_count=result_count,
            result_type=None,
            affected_rows=affected_rows,
            result_summary=""
        )
        
        if result_count is not None:
            entry.result_summary = f"{result_count} rows returned"
        elif affected_rows is not None:
            entry.result_summary = f"{affected_rows} rows affected"

        logs = self.sql_logs()
        logs.append(entry)
        self._resources["sql_logs"] = logs
        sink = self.get_resource("diagnostic_sql_log_sink")
        if sink is not None:
            sink.write(entry)
        
        buf = self.get_resource("UnifiedLogBuffer")
        if buf:
            buf.entries.append(UnifiedLogEntry(
                timestamp=started_at,
                user_identifier=self.user_identifier(),
                trace_chain=[],
                payload=LogPayload.Sql(entry)
            ))

    def register_executor(self, executor: Any):
        self.insert_resource("executor", executor)

    def set_event_sink(self, sink: Any):
        self._app_audit_sink = sink

    def with_event_sink(self, sink: Any) -> 'UserContext':
        self.set_event_sink(sink)
        return self

    # ==========================================
    # Context Attribute
    # ==========================================
    def put_attribute(self, key: str, value: Any):
        pass

    def get_attribute(self, key: str, clazz: Any = None) -> Optional[Any]:
        return None

    # ==========================================
    # Local Cache
    # ==========================================
    def put_to_local_cache(self, key: str, value: Any, time_to_live_in_seconds: Optional[int] = None):
        def put():
            expires_at = (
                time.monotonic() + time_to_live_in_seconds
                if time_to_live_in_seconds is not None and time_to_live_in_seconds > 0
                else None
            )
            with _local_cache_lock:
                _local_cache[key] = (value, expires_at)

        self._observe_cache("local.put", "put", put, lambda _: {"teaql.cache.result": "stored"})

    def get_from_local_cache(self, key: str, clazz: Any = None) -> Optional[Any]:
        def get():
            with _local_cache_lock:
                entry = _local_cache.get(key)
                if entry is None:
                    return None
                value, expires_at = entry
                if expires_at is not None and time.monotonic() >= expires_at:
                    _local_cache.pop(key, None)
                    return None
                if clazz is not None and not isinstance(value, clazz):
                    return None
                return value

        return self._observe_cache(
            "local.get", "get", get,
            lambda value: {"teaql.cache.result": "miss" if value is None else "hit"},
        )

    def remove_from_local_cache(self, key: str):
        def remove():
            with _local_cache_lock:
                _local_cache.pop(key, None)

        self._observe_cache(
            "local.remove", "remove", remove,
            lambda _: {"teaql.cache.result": "removed"},
        )

    # ==========================================
    # Remote Cache
    # ==========================================
    def put_to_remote_cache(self, key: str, value: Any, time_to_live_in_seconds: Optional[int] = None):
        def put():
            provider = self.get_resource("RemoteCacheProvider")
            if provider and hasattr(provider, 'put_to_remote_cache'):
                provider.put_to_remote_cache(key, value, time_to_live_in_seconds)

        self._observe_cache("remote.put", "put", put, lambda _: {"teaql.cache.result": "stored"})

    def get_from_remote_cache(self, key: str, clazz: Any = None) -> Optional[Any]:
        def get():
            provider = self.get_resource("RemoteCacheProvider")
            if provider and hasattr(provider, 'get_from_remote_cache'):
                return provider.get_from_remote_cache(key, clazz)
            return None

        return self._observe_cache(
            "remote.get", "get", get,
            lambda value: {"teaql.cache.result": "miss" if value is None else "hit"},
        )

    def remove_from_remote_cache(self, key: str):
        def remove():
            provider = self.get_resource("RemoteCacheProvider")
            if provider and hasattr(provider, 'remove_from_remote_cache'):
                provider.remove_from_remote_cache(key)

        self._observe_cache(
            "remote.remove", "remove", remove,
            lambda _: {"teaql.cache.result": "removed"},
        )

    def _observe_cache(self, name: str, operation: str, work: Callable, completion: Callable):
        from .telemetry import RuntimeOperation, observe_runtime_operation_sync

        return observe_runtime_operation_sync(
            self.runtime_telemetry(),
            RuntimeOperation("cache", name, {"teaql.cache.operation": operation}),
            work,
            completion,
        )

    # ==========================================
    # Local Lock
    # ==========================================
    def try_local_lock(self, key: str, timeout_millis: int, expire_millis: int) -> bool:
        owner = id(self)
        deadline = time.monotonic() + max(timeout_millis, 0) / 1000
        with _local_lock_condition:
            while True:
                now = time.monotonic()
                current = _local_locks.get(key)
                if current is None or (current[1] is not None and now >= current[1]):
                    expires_at = now + expire_millis / 1000 if expire_millis > 0 else None
                    _local_locks[key] = (owner, expires_at)
                    return True
                if current[0] == owner:
                    expires_at = now + expire_millis / 1000 if expire_millis > 0 else None
                    _local_locks[key] = (owner, expires_at)
                    return True
                remaining = deadline - now
                if remaining <= 0:
                    return False
                lease_remaining = current[1] - now if current[1] is not None else remaining
                _local_lock_condition.wait(min(remaining, max(lease_remaining, 0.001)))

    def unlock_local(self, key: str):
        owner = id(self)
        with _local_lock_condition:
            current = _local_locks.get(key)
            if current is not None and current[0] == owner:
                _local_locks.pop(key, None)
                _local_lock_condition.notify_all()

    # ==========================================
    # Remote Lock
    # ==========================================
    def try_remote_lock(self, key: str, timeout_millis: int, expire_millis: int) -> bool:
        provider = self.get_resource("RemoteLockProvider")
        if provider and hasattr(provider, 'try_remote_lock'):
            return provider.try_remote_lock(key, timeout_millis, expire_millis)
        return True

    def unlock_remote(self, key: str):
        provider = self.get_resource("RemoteLockProvider")
        if provider and hasattr(provider, 'unlock_remote'):
            provider.unlock_remote(key)


class TeaqlRuntime:
    def __init__(self, context: UserContext):
        self._ctx = context

    @property
    def context(self) -> UserContext:
        return self._ctx

    def get_service(self, name: str) -> Optional[Any]:
        return self._ctx.get_resource(name)

    def require_service(self, name: str) -> Any:
        return self._ctx.require_resource(name)

    def install(self, module: Any) -> 'TeaqlRuntime':
        self._ctx.install(module)
        return self

from enum import Enum, auto
from dataclasses import dataclass, field
from datetime import datetime, timedelta

class SqlLogOperation(Enum):
    Select = auto()
    Insert = auto()
    Update = auto()
    Delete = auto()
    Recover = auto()

    def is_select(self) -> bool:
        return self == SqlLogOperation.Select

    def is_mutation(self) -> bool:
        return not self.is_select()

@dataclass
class SqlLogOptions:
    select: bool = True
    mutation: bool = True

    @classmethod
    def disabled(cls) -> 'SqlLogOptions':
        return cls(False, False)

    @classmethod
    def select_only(cls) -> 'SqlLogOptions':
        return cls(True, False)

    @classmethod
    def mutation_only(cls) -> 'SqlLogOptions':
        return cls(False, True)

    @classmethod
    def all(cls) -> 'SqlLogOptions':
        return cls(True, True)

    def enabled_for(self, operation: SqlLogOperation) -> bool:
        return self.select if operation.is_select() else self.mutation

@dataclass
class SqlLogEntry:
    operation: SqlLogOperation
    comment: Optional[str]
    purpose: Optional[str]
    audit_reason: Optional[str]
    trace_path: List[Any]
    sql: str
    params: List[Any]
    debug_sql: str
    pretty_sql: str
    started_at: datetime
    ended_at: datetime
    elapsed: timedelta
    result_count: Optional[int]
    result_type: Optional[str]
    affected_rows: Optional[int]
    result_summary: str

class DiagnosticSqlLogSink:
    """Value-bearing diagnostic SQL destination; the text sink is installed by default."""
    def write(self, entry: SqlLogEntry) -> None:
        raise NotImplementedError

class TextDiagnosticSqlLogSink(DiagnosticSqlLogSink):
    def __init__(self, writer=print):
        self._writer = writer

    def write(self, entry: SqlLogEntry) -> None:
        elapsed_us = int(entry.elapsed.total_seconds() * 1_000_000) if entry.elapsed else 0
        self._writer(
            f"[TeaQL SQL][{entry.operation.name.lower()}][{elapsed_us}us] "
            f"{entry.result_summary} comment={entry.comment!r} purpose={entry.purpose!r} "
            f"auditReason={entry.audit_reason!r} tracePath={entry.trace_path!r}\n"
            f"Parameterized SQL: {entry.sql} params={entry.params!r}\n"
            f"Debug SQL: {entry.debug_sql}"
        )

@dataclass
class InfoLogEntry:
    message: str

class LogPayload:
    def __init__(self, data: Any):
        self._data = data

    @classmethod
    def Sql(cls, entry: SqlLogEntry) -> 'LogPayload':
        return cls(entry)

    @classmethod
    def Info(cls, entry: InfoLogEntry) -> 'LogPayload':
        return cls(entry)

@dataclass
class UnifiedLogEntry:
    timestamp: datetime
    user_identifier: Optional[str]
    trace_chain: List[Any]
    payload: LogPayload

class UnifiedLogBuffer:
    def __init__(self):
        self.entries: List[UnifiedLogEntry] = []

from abc import ABC, abstractmethod

class SchemaProvider(ABC):
    @abstractmethod
    async def _ensure_schema(self, context: 'UserContext', capability: object) -> None:
        pass

class DataStore(ABC):
    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        pass
    
    @abstractmethod
    async def put(self, key: str, value: Any, timeout_seconds: Optional[int]) -> None:
        pass
        
    @abstractmethod
    async def remove(self, key: str) -> None:
        pass

class InMemoryDataStore(DataStore):
    def __init__(self):
        self.cache: Dict[str, Any] = {}

    async def get(self, key: str) -> Optional[Any]:
        if key in self.cache:
            val, expires_at = self.cache[key]
            if expires_at and datetime.now() > expires_at:
                del self.cache[key]
                return None
            return val
        return None

    async def put(self, key: str, value: Any, timeout_seconds: Optional[int]) -> None:
        expires_at = datetime.now() + timedelta(seconds=timeout_seconds) if timeout_seconds else None
        self.cache[key] = (value, expires_at)

    async def remove(self, key: str) -> None:
        self.cache.pop(key, None)
