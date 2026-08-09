import pytest
from teaql.runtime.context import UserContext
from teaql.runtime.env import ServiceRuntimeFromEnv
import os

def test_user_context():
    ctx = UserContext.new()
    ctx.insert_resource("my_res", {"key": "value"})
    assert ctx.get_resource("my_res") == {"key": "value"}
    assert ctx.get_resource("missing") is None
    
    with pytest.raises(Exception):
        ctx.require_resource("missing")
        
    ctx.set_user_identifier("test_user")
    assert ctx.user_identifier() == "test_user"

def test_service_runtime_from_env(monkeypatch):
    monkeypatch.setenv("TEAQL_USER", "env_user")
    ctx = ServiceRuntimeFromEnv.build_context()
    assert ctx.user_identifier() == "env_user"
