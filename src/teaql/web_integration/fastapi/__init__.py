from typing import Generic, TypeVar, List, Optional, Dict, Any
from pydantic import BaseModel, Field
import json
from teaql.core.list import SmartList
from teaql.runtime.context import UserContext

T = TypeVar('T')

class WebResponse(BaseModel, Generic[T]):
    data: List[T] = Field(default_factory=list)
    resultCode: int = 0
    status: str = "YES"
    message: Optional[str] = None
    recordCount: int = 0
    facets: Optional[Dict[str, Any]] = None
    version: str = "1.001"
    traceId: Optional[str] = None

    @classmethod
    def success(cls) -> 'WebResponse[T]':
        return cls()

    @classmethod
    def fail(cls, message: str) -> 'WebResponse[T]':
        return cls(resultCode=1, status="NO", message=message)

    def with_trace_id(self, trace_id: str) -> 'WebResponse[T]':
        self.traceId = trace_id
        return self

    def with_facets(self, facets: Dict[str, Any]) -> 'WebResponse[T]':
        self.facets = facets
        return self

    def with_record_count(self, count: int) -> 'WebResponse[T]':
        self.recordCount = count
        return self

    @classmethod
    def of_single(cls, entity: T) -> 'WebResponse[T]':
        return cls(data=[entity], recordCount=1)

    @classmethod
    def of_list(cls, data_list: List[T]) -> 'WebResponse[T]':
        return cls(data=data_list, recordCount=len(data_list))

    @classmethod
    def from_smart_list(cls, smart_list: 'SmartList') -> 'WebResponse':
        count = smart_list.total_count
        facets = {}
        for key, facet_list in (smart_list.facets or {}).items():
            facets[key] = [item for item in facet_list]
            
        resp = cls.of_list(list(smart_list))
        resp.recordCount = count
        if facets:
            resp = resp.with_facets(facets)
        return resp

class WebRequestInfo:
    def __init__(self, client_ip: Optional[str], user_agent: Optional[str], request_uri: str, method: str):
        self.client_ip = client_ip
        self.user_agent = user_agent
        self.request_uri = request_uri
        self.method = method

# Optional Dependency for FastAPI
def get_tea_context(request) -> UserContext:
    from teaql.runtime.env import ServiceRuntimeFromEnv
    ctx = ServiceRuntimeFromEnv.build_context()
    
    user_id = request.headers.get("X-User-Id")
    if user_id:
        ctx.set_user_identifier(user_id)
        
    trace_id = request.headers.get("X-Trace-Id")
    if trace_id and hasattr(ctx, 'set_trace_id'):
        ctx.set_trace_id(trace_id)
        
    forwarded = request.headers.get("X-Forwarded-For")
    client_ip = forwarded.split(",")[0].strip() if forwarded else None
    
    user_agent = request.headers.get("User-Agent")
    
    web_info = WebRequestInfo(
        client_ip=client_ip,
        user_agent=user_agent,
        request_uri=str(request.url),
        method=request.method
    )
    
    ctx.insert_resource("WebRequestInfo", web_info)
    return ctx
