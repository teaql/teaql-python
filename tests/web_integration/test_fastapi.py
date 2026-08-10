import pytest
from unittest.mock import MagicMock, patch
from teaql.web_integration.fastapi import WebResponse, WebRequestInfo, get_tea_context
from teaql.core.list import SmartList

def test_web_response_success():
    resp = WebResponse.success()
    assert resp.resultCode == 0
    assert resp.status == "YES"
    assert resp.data == []

def test_web_response_fail():
    resp = WebResponse.fail("error")
    assert resp.resultCode == 1
    assert resp.status == "NO"
    assert resp.message == "error"

def test_web_response_with_methods():
    resp = WebResponse.success()
    resp = resp.with_trace_id("123").with_facets({"a": 1}).with_record_count(5)
    assert resp.traceId == "123"
    assert resp.facets == {"a": 1}
    assert resp.recordCount == 5

def test_web_response_of_single():
    resp = WebResponse.of_single({"name": "a"})
    assert resp.data == [{"name": "a"}]
    assert resp.recordCount == 1

def test_web_response_of_list():
    resp = WebResponse.of_list([1, 2])
    assert resp.data == [1, 2]
    assert resp.recordCount == 2

def test_web_response_from_smart_list():
    sl = SmartList([1, 2])
    sl.total_count = 10
    sl.facets = {"f1": [3, 4]}
    
    resp = WebResponse.from_smart_list(sl)
    assert resp.data == [1, 2]
    assert resp.recordCount == 10
    assert resp.facets == {"f1": [3, 4]}

@patch('teaql.runtime.env.ServiceRuntimeFromEnv.build_context')
def test_get_tea_context(mock_build):
    mock_ctx = MagicMock()
    mock_build.return_value = mock_ctx
    
    request = MagicMock()
    request.headers = {
        "X-User-Id": "u1",
        "X-Trace-Id": "t1",
        "X-Forwarded-For": "1.2.3.4, 5.6.7.8",
        "User-Agent": "agent"
    }
    request.url = "http://test"
    request.method = "GET"
    
    ctx = get_tea_context(request)
    assert ctx == mock_ctx
    mock_ctx.set_user_identifier.assert_called_with("u1")
    mock_ctx.set_trace_id.assert_called_with("t1")
    
    mock_ctx.insert_resource.assert_called_once()
    args, _ = mock_ctx.insert_resource.call_args
    assert args[0] == "WebRequestInfo"
    info = args[1]
    assert isinstance(info, WebRequestInfo)
    assert info.client_ip == "1.2.3.4"
    assert info.user_agent == "agent"
    assert info.request_uri == "http://test"
    assert info.method == "GET"
