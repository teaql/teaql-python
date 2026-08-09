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
    
def test_user_context_extensions():
    from teaql.runtime.context import SqlLogOptions, SqlLogOperation
    ctx = UserContext.new()
    
    # Logs
    ctx.set_sql_log_options(SqlLogOptions(select=True, mutation=True))
    assert ctx.sql_log_options() is not None
    ctx.disable_sql_log()
    assert len(ctx.sql_logs()) == 0
    
    # Metadata logs
    class MockMetadata:
        debug_query = "SELECT 1"
        operation = "Select"
        result_count = 1
        
    ctx.record_metadata_log(MockMetadata())
    assert len(ctx.sql_logs()) == 1
    assert ctx.sql_logs()[0].debug_sql == "SELECT 1"
    
    # SQL logs
    class MockQuery:
        sql = "INSERT INTO a"
        params = []
    
    # Needs re-enable since disable_sql_log disabled it
    ctx.set_sql_log_options(SqlLogOptions(select=True, mutation=True))
    ctx.record_sql_log(SqlLogOperation.Insert, MockQuery(), None, None, None, affected_rows=1)
    assert len(ctx.sql_logs()) == 2
    assert ctx.sql_logs()[1].result_summary == "1 rows affected"
    
    ctx.clear_sql_logs()
    assert len(ctx.sql_logs()) == 0

def test_service_runtime_from_env(monkeypatch):
    monkeypatch.setenv("TEAQL_USER", "env_user")
    ctx = ServiceRuntimeFromEnv.build_context()
    assert ctx.user_identifier() == "env_user"
