from typing import Dict, Any, Optional, List, Callable, TypeVar


TEntity = TypeVar("TEntity")
EntityInitializer = Callable[["UserContext", Any], None]

import threading
import time


_local_cache = {}
_local_cache_lock = threading.RLock()
_local_locks = {}
_local_lock_condition = threading.Condition(threading.RLock())


class UserContext:
    def __init__(self):
        self._resources: Dict[str, Any] = {}
        self._metadata: Optional[Any] = None
        self._user_identifier: str = ""
        self._entities: List[Any] = []
        self._initial_graphs: List[Any] = []
        self._standard_audit_sink: Optional[Any] = None
        self._app_audit_sink: Optional[Any] = None
        self._entity_initializers: Dict[str, List[EntityInitializer]] = {}
        self._managed_entities: List[Any] = []
        from .telemetry import NOOP_RUNTIME_TELEMETRY
        self._runtime_telemetry = NOOP_RUNTIME_TELEMETRY

    @classmethod
    def new(cls) -> 'UserContext':
        return cls()

    def entity_root(self) -> Any:
        return self.get_resource("entity_root")

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
        
    def all_entities(self) -> List[Any]:
        return self._entities
        
    def add_initial_graph(self, graph_node: Any):
        self._initial_graphs.append(graph_node)
        
    def initial_graphs(self) -> List[Any]:
        return self._initial_graphs

    def with_metadata(self, metadata: Any) -> 'UserContext':
        self._metadata = metadata
        return self

    def insert_resource(self, resource_type: str, resource: Any):
        self._resources[resource_type] = resource
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
            await provider.ensure_schema(self)
        else:
            raise Exception("missing schema provider")

    def with_language(self, language: Any) -> 'UserContext':
        self.insert_resource("language", language)
        return self

    def set_language(self, language: Any):
        self.insert_resource("language", language)

    def set_language_code(self, code: str):
        self.insert_resource("language_code", code)

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
            raise Exception(f"Check failed: {results}")

    def translate_check_results(self, results: Any):
        # Python naive translation stub based on rust translate_check_results
        lang = self.language()
        for r in results:
            if hasattr(r, 'message'):
                r.message = getattr(r, 'message', str(r))

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

    def sql_logs(self) -> List['SqlLogEntry']:
        return self._resources.get("sql_logs", [])

    def clear_sql_logs(self):
        self._resources["sql_logs"] = []

    async def commit_changes_internal(self):
        root = self.entity_root()
        if not root or not hasattr(root, 'current_change_set'):
            return
            
        change_set = root.current_change_set()
        if not change_set or not hasattr(change_set, 'changes'):
            return
            
        executor = self.get_resource("executor")
        if not executor:
            raise Exception("cannot commit changes without executor")
            
        from teaql.core.mutation import UpdateCommand, MutationRequest
        
        for key, changes in change_set.changes():
            if not changes:
                continue
            
            command = UpdateCommand(getattr(key, 'entity', ''), getattr(key, 'id', None))
            for field, val in changes.items():
                command.value(field, val)
                
            request = MutationRequest(command)
            await executor.mutate(request)

    def data_service_internal(self, entity: str) -> Any:
        # Returns internal data service for entity
        registry = self.get_resource("entity_registry")
        if registry and hasattr(registry, "get_internal_service"):
            return registry.get_internal_service(entity)
        return None

    def entity_data_service(self, entity: str) -> Any:
        return self.data_service_internal(entity)

    def language(self) -> Any:
        return self.get_resource("language")

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
        expires_at = (
            time.monotonic() + time_to_live_in_seconds
            if time_to_live_in_seconds is not None and time_to_live_in_seconds > 0
            else None
        )
        with _local_cache_lock:
            _local_cache[key] = (value, expires_at)

    def get_from_local_cache(self, key: str, clazz: Any = None) -> Optional[Any]:
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

    def remove_from_local_cache(self, key: str):
        with _local_cache_lock:
            _local_cache.pop(key, None)

    # ==========================================
    # Remote Cache
    # ==========================================
    def put_to_remote_cache(self, key: str, value: Any, time_to_live_in_seconds: Optional[int] = None):
        provider = self.get_resource("RemoteCacheProvider")
        if provider and hasattr(provider, 'put_to_remote_cache'):
            provider.put_to_remote_cache(key, value, time_to_live_in_seconds)

    def get_from_remote_cache(self, key: str, clazz: Any = None) -> Optional[Any]:
        provider = self.get_resource("RemoteCacheProvider")
        if provider and hasattr(provider, 'get_from_remote_cache'):
            return provider.get_from_remote_cache(key, clazz)
        return None

    def remove_from_remote_cache(self, key: str):
        provider = self.get_resource("RemoteCacheProvider")
        if provider and hasattr(provider, 'remove_from_remote_cache'):
            provider.remove_from_remote_cache(key)

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
    select: bool = False
    mutation: bool = False

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
    async def ensure_schema(self, context: 'UserContext') -> None:
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
