import pytest
from teaql.web_integration.fastapi import WebResponse, WebRequestInfo, get_tea_context
from teaql.core.list import SmartList

def test_web_response_success():
    resp = WebResponse.success()
    assert resp.resultCode == 0
    assert resp.status == "YES"

def test_web_response_from_smart_list():
    lst = SmartList([1, 2, 3])
    lst.total_count = 10
    
    resp = WebResponse.from_smart_list(lst)
    assert resp.recordCount == 10
    assert resp.data == [1, 2, 3]

class MockRequest:
    def __init__(self):
        self.headers = {
            "X-User-Id": "user123",
            "X-Forwarded-For": "192.168.1.1, 10.0.0.1",
            "User-Agent": "TestAgent/1.0"
        }
        self.url = "/api/test"
        self.method = "POST"

def test_get_tea_context():
    req = MockRequest()
    ctx = get_tea_context(req)
    
    assert ctx.user_identifier() == "user123"
    
    web_info = ctx.get_resource("WebRequestInfo")
    assert web_info is not None
    assert web_info.client_ip == "192.168.1.1"
    assert web_info.user_agent == "TestAgent/1.0"
    assert web_info.request_uri == "/api/test"
    assert web_info.method == "POST"
