import os
import pytest
from teaql.runtime import RuntimeModule, UserContext, TeaqlRuntime, ServiceRuntimeFromEnv

class DummyEntity:
    _name = "Dummy"

class DummyBehavior:
    pass

class DummyDependency:
    pass

def test_runtime_module_initialization():
    module = RuntimeModule.new()
    module.entity(DummyEntity)
    module.entity_with_behavior(DummyEntity, DummyBehavior())
    
    dep = DummyDependency()
    module.provide_custom_dependency("dummy_dep", dep)
    
    ctx = module.into_context()
    
    assert ctx.require_resource("dummy_dep") is dep
    
    entities = ctx.require_resource("entities")
    assert DummyEntity in entities
    
    behaviors = ctx.require_resource("behaviors")
    assert "Dummy" in behaviors
    assert isinstance(behaviors["Dummy"], DummyBehavior)

def test_runtime_module_composes_and_installs_without_schema_changes():
    first = RuntimeModule.new().entity(DummyEntity)
    second = RuntimeModule.new().provide_custom_dependency("dummy", DummyDependency())
    ctx = UserContext.new().install(first.and_module(second))
    assert DummyEntity in ctx.require_resource("entities")
    assert isinstance(ctx.require_resource("dummy"), DummyDependency)

@pytest.mark.asyncio
async def test_runtime_module_configure():
    module = RuntimeModule.new()
    ctx = await module.configure()
    assert isinstance(ctx, UserContext)

def test_service_runtime_from_env(monkeypatch):
    monkeypatch.setenv("TEAQL_USER", "test_user")
    monkeypatch.setenv("TEAQL_DB_URL", "sqlite://memory")
    
    ctx = ServiceRuntimeFromEnv.build_context()
    assert ctx.user_identifier() == "test_user"
    
    # Should instantiate sqlite service and store it in DataService
    data_service = ctx.require_resource("dataService")
    assert data_service is not None
    
    runtime = TeaqlRuntime(ctx)
    assert runtime.require_service("dataService") is data_service

def test_service_runtime_from_env_fallback(monkeypatch):
    monkeypatch.delenv("TEAQL_USER", raising=False)
    monkeypatch.delenv("TEAQL_DB_URL", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    
    ctx = ServiceRuntimeFromEnv.build_context()
    assert ctx.user_identifier() == ""
    assert ctx.get_resource("DataService") is None
