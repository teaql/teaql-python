import os
import pytest
from teaql.runtime import CheckException, CheckResult, RuntimeModule, UserContext, TeaqlRuntime, ServiceRuntimeFromEnv
from teaql.core.mutation import InsertCommand

class DummyEntity:
    _name = "Dummy"

class DummyBehavior:
    pass

class DummyDependency:
    pass

class RequiredNameChecker:
    def __init__(self):
        self.calls = 0

    def check_and_fix(self, context, record, location, results):
        self.calls += 1
        assert context.get_resource("fix_time") is not None
        if "name" not in record:
            results.append(CheckResult("REQUIRED", "name"))

class DummyCheckerRegistry:
    def __init__(self, checker):
        self.value = checker

    def checker(self, entity):
        return self.value if entity == "Dummy" else None

def test_check_and_fix_mutation_is_typed_and_save_scoped():
    checker = RequiredNameChecker()
    context = UserContext.new().with_checker_registry(DummyCheckerRegistry(checker))
    command = InsertCommand.new("Dummy")

    for _ in range(2):
        with pytest.raises(CheckException) as failure:
            context.check_and_fix_mutation(command)
        assert failure.value.violations[0].location == "name"

    assert checker.calls == 2
    assert context.get_resource("fix_time") is None

def test_runtime_module_initialization():
    module = RuntimeModule.new()
    module.entity(DummyEntity)
    module.entity_with_behavior(DummyEntity, DummyBehavior())
    
    dep = DummyDependency()
    module.provide_custom_dependency("dummy_dep", dep)
    
    context = module.into_context()
    
    assert context.require_resource("dummy_dep") is dep
    
    entities = context.require_resource("entities")
    assert DummyEntity in entities
    
    behaviors = context.require_resource("behaviors")
    assert "Dummy" in behaviors
    assert isinstance(behaviors["Dummy"], DummyBehavior)

def test_runtime_module_composes_and_installs_without_schema_changes():
    first = RuntimeModule.new().entity(DummyEntity)
    second = RuntimeModule.new().provide_custom_dependency("dummy", DummyDependency())
    context = UserContext.new().install(first.and_module(second))
    assert DummyEntity in context.require_resource("entities")
    assert isinstance(context.require_resource("dummy"), DummyDependency)

@pytest.mark.asyncio
async def test_runtime_module_configure():
    module = RuntimeModule.new()
    context = await module.configure()
    assert isinstance(context, UserContext)

def test_service_runtime_from_env(monkeypatch):
    monkeypatch.setenv("TEAQL_USER", "test_user")
    monkeypatch.setenv("TEAQL_DB_URL", "sqlite://memory")
    
    context = ServiceRuntimeFromEnv.build_context()
    assert context.user_identifier() == "test_user"
    
    # Should instantiate sqlite service and store it in DataService
    data_service = context.require_resource("dataService")
    assert data_service is not None
    
    runtime = TeaqlRuntime(context)
    assert runtime.require_service("dataService") is data_service

def test_service_runtime_from_env_fallback(monkeypatch):
    monkeypatch.delenv("TEAQL_USER", raising=False)
    monkeypatch.delenv("TEAQL_DB_URL", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    
    context = ServiceRuntimeFromEnv.build_context()
    assert context.user_identifier() == ""
    assert context.get_resource("DataService") is None
