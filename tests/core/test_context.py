import pytest
from teaql.runtime.context import UserContext
from teaql.runtime.env import ServiceRuntimeFromEnv
import os

def test_user_context():
    context = UserContext.new()
    context.insert_resource("my_res", {"key": "value"})
    assert context.get_resource("my_res") == {"key": "value"}
    assert context.get_resource("missing") is None
    
    with pytest.raises(Exception):
        context.require_resource("missing")
        
    context.set_user_identifier("test_user")
    assert context.user_identifier() == "test_user"
    
def test_user_context_extensions():
    from teaql.runtime.context import SqlLogOptions, SqlLogOperation
    context = UserContext.new()
    
    # Logs
    context.set_sql_log_options(SqlLogOptions(select=True, mutation=True))
    assert context.sql_log_options() is not None
    context.disable_sql_log()
    assert len(context.sql_logs()) == 0
    
    # Metadata logs
    class MockMetadata:
        debug_query = "SELECT 1"
        operation = "Select"
        result_count = 1

    context.enable_all_sql_log()
    context.record_metadata_log(MockMetadata())
    assert len(context.sql_logs()) == 1
    assert context.sql_logs()[0].debug_sql == "SELECT 1"
    
    # SQL logs
    class MockQuery:
        sql = "INSERT INTO a"
        params = []
    
    # Needs re-enable since disable_sql_log disabled it
    context.set_sql_log_options(SqlLogOptions(select=True, mutation=True))
    context.record_sql_log(SqlLogOperation.Insert, MockQuery(), None, None, None, affected_rows=1)
    assert len(context.sql_logs()) == 2
    assert context.sql_logs()[1].result_summary == "1 rows affected"
    
    context.clear_sql_logs()
    assert len(context.sql_logs()) == 0

def test_service_runtime_from_env(monkeypatch):
    monkeypatch.setenv("TEAQL_USER", "env_user")
    context = ServiceRuntimeFromEnv.build_context()
    assert context.user_identifier() == "env_user"
