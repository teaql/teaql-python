"""Trusted Context extension registration rejects broken capabilities early."""

import pytest

from teaql.core.meta import EntityDescriptor, PropertyDescriptor
from teaql.core.mutation import InsertCommand, MutationRequest
from teaql.core.query import SelectQuery
from teaql.core.value import DataType
from teaql.data_service import QueryRequest
from teaql.provider.sqlite import SimpleSchemaProvider, create_sqlite_service
from teaql.runtime import (
    CheckerRegistry, InternalIdAllocator, RequestPolicy, RuntimeModule,
    RuntimeTelemetryAdapter, SafeAuditEventSink, SchemaCapability, UserContext,
)
from teaql.runtime.audit import MutationAuditKind, RawAuditEvent


def test_public_protocols_and_bad_installations_fail_before_business_execution():
    class Valid:
        def apply(self, query): return query
        def checker(self, entity): return None
        async def _ensure_schema(self, context, capability): pass
        def on_safe_event(self, context, event): pass
        def start(self, operation): return None
        async def next_id(self, entity): return 1
        async def ensure_id_floor(self, entity, floor): pass

    valid = Valid()
    for protocol in (RequestPolicy, CheckerRegistry, SchemaCapability,
                     SafeAuditEventSink, RuntimeTelemetryAdapter, InternalIdAllocator):
        assert isinstance(valid, protocol)
    context = UserContext()
    bad = object()
    methods = (
        (context.with_request_policy, "request policy"),
        (context.with_checker_registry, "checker registry"),
        (context.with_schema_provider, "schema capability"),
        (context.with_app_audit_event_sink, "application audit sink"),
        (context.with_runtime_telemetry, "runtime telemetry"),
        (context.with_internal_id_allocator, "internal ID allocator"),
    )
    for install, message in methods:
        with pytest.raises(TypeError, match=message):
            install(bad)
    with pytest.raises(TypeError, match="schema capability"):
        context.with_schema_provider(type("SyncSchema", (), {"_ensure_schema": lambda *_: None})())
    with pytest.raises(TypeError, match="request policy"):
        context.insert_resource("request_policy", bad)
    with pytest.raises(TypeError, match="checker registry"):
        context.insert_resource("checker_registry", bad)
    with pytest.raises(TypeError, match="schema capability"):
        context.insert_resource("schema_provider", bad)
    with pytest.raises(TypeError, match="application audit sink"):
        context.initialize_audit(valid, bad)
    assert context._standard_audit_sink is None


@pytest.mark.asyncio
async def test_schema_only_capability_is_independent_and_preserves_bootstrap_order():
    events = []

    class SchemaOnly:
        async def _ensure_schema(self, context, capability):
            events.append("schema")

    async def bootstrap(context):
        events.append("bootstrap")

    schema = SchemaOnly()
    assert isinstance(schema, SchemaCapability)
    assert not hasattr(schema, "query") and not hasattr(schema, "mutate")
    context = RuntimeModule.new().generated_bootstrap(bootstrap).into_context()
    context.with_schema_provider(schema)
    await context.ensure_schema()
    await context.ensure_schema()
    assert events == ["schema", "bootstrap", "schema", "bootstrap"]

    class CombinedService:
        async def _ensure_schema(self, context, capability):
            raise AssertionError("explicit schema provider must not be replaced")

    context.with_schema_provider(schema).insert_resource("dataService", CombinedService())
    await context.ensure_schema()
    assert events[-2:] == ["schema", "bootstrap"]

    inferred = UserContext().insert_resource("dataService", CombinedService())
    assert isinstance(inferred.get_resource("schema_provider"), CombinedService)
    inferred.insert_resource("dataService", object())
    assert inferred.get_resource("schema_provider") is None


async def school_fixture(path):
    school = (EntityDescriptor("School").table_name("school_data")
              .property(PropertyDescriptor("id", DataType.I64).is_id())
              .property(PropertyDescriptor("version", DataType.I64).is_version())
              .property(PropertyDescriptor("name", DataType.Text)))
    provider = SimpleSchemaProvider()
    provider.register_entity(school)
    service = create_sqlite_service(str(path), provider)
    context = (RuntimeModule.new().entity(school).into_context()
               .with_schema_provider(service).insert_resource("dataService", service))
    context.disable_sql_log()
    await context.ensure_schema()
    return context, service


@pytest.mark.asyncio
async def test_object_policy_denies_query_before_sql_provider(tmp_path, monkeypatch):
    context, service = await school_fixture(tmp_path / "policy.db")
    called = []

    async def forbidden_fetch(*args):
        called.append("provider")
        raise AssertionError("query provider must not be called")

    monkeypatch.setattr(service.transport, "fetch_all_sql", forbidden_fetch)

    class DenySchool:
        def apply(self, query):
            raise PermissionError("school query denied")

    context.with_request_policy(DenySchool())
    query = SelectQuery("School").project("id")
    with pytest.raises(PermissionError, match="school query denied"):
        prepared = context.prepare_query_request(
            QueryRequest(query, _comment="load schools", _purpose="check policy"))
        await service.query(context, prepared)
    assert called == []
    await service.close()


@pytest.mark.asyncio
async def test_checker_failure_rejects_write_before_sql_provider(tmp_path, monkeypatch):
    context, service = await school_fixture(tmp_path / "checker.db")
    called = []

    async def forbidden_execute(*args):
        called.append("provider")
        raise AssertionError("write provider must not be called")

    monkeypatch.setattr(service.transport, "execute_sql", forbidden_execute)

    class DenyChecker:
        def check_and_fix(self, context, record, location, results):
            raise ValueError("school name rejected")

    class Registry:
        def checker(self, entity):
            return DenyChecker() if entity == "School" else None

    context.with_checker_registry(Registry())
    request = MutationRequest(InsertCommand.new("School").value("name", "Rejected"),
                              comment="create rejected school")
    with pytest.raises(ValueError, match="school name rejected"):
        await service.mutate(context, request)
    assert called == []
    await service.close()


@pytest.mark.asyncio
async def test_safe_audit_sink_and_telemetry_lifecycle_composed():
    events = []

    class Provider:
        async def begin(self, context):
            events.append("begin")
            return self

        async def commit(self, context): events.append("commit")
        async def rollback(self, context): events.append("rollback")

    class Sink:
        def on_safe_event(self, context, event):
            events.append(("audit", event.entity))

    class Telemetry:
        def start(self, operation):
            events.append(("start", operation.name))

            class Scope:
                def success(self, attributes=None): events.append(("success", operation.name))
                def failure(self, error): events.append(("failure", operation.name))

            return Scope()

    context = (UserContext().insert_resource("dataService", Provider())
               .with_app_audit_event_sink(Sink()).with_runtime_telemetry(Telemetry()))

    async def save(graph):
        await graph.context.send_audit_event(
            RawAuditEvent(MutationAuditKind.CREATED, "School", 1, ()))

    await context.execute_graph_save(save, comment="create school")
    assert events[0] == ("start", "graph.save")
    assert events.index("begin") < events.index("commit") < events.index(("audit", "School"))
    assert events[-1] == ("success", "graph.save")

    class BrokenTelemetry:
        def start(self, operation):
            raise RuntimeError("optional adapter is unavailable")

    context.with_runtime_telemetry(BrokenTelemetry())
    await context.execute_graph_save(save, comment="retry school")
    assert events[-3:] == ["begin", "commit", ("audit", "School")]


def test_all_six_context_extensions_can_be_installed_together():
    class Extensions:
        def apply(self, query): return query
        def checker(self, entity): return None
        async def _ensure_schema(self, context, capability): pass
        def on_safe_event(self, context, event): pass
        def start(self, operation): return None
        async def next_id(self, entity): return 1
        async def ensure_id_floor(self, entity, floor): pass

    extension = Extensions()
    context = (UserContext().with_request_policy(extension)
               .with_checker_registry(extension)
               .with_schema_provider(extension)
               .with_app_audit_event_sink(extension)
               .with_runtime_telemetry(extension)
               .with_internal_id_allocator(extension))
    assert context.runtime_telemetry() is extension
    assert context.internal_id_allocator() is extension
    assert context.get_resource("schema_provider") is extension
    assert context.get_resource("checker_registry") is extension
    assert context.get_resource("request_policy") is extension
