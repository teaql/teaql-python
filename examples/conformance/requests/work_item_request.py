from teaql.core.query import SelectQuery
from teaql.core.list import SmartList, TeaQLPage
from teaql.data_service import QueryRequest
from teaql.core.expr import eq, contain, gte, lte
from models.work_item import WorkItem

class WorkItemRequest:
    def __init__(self, minimal=False):
        self.query = SelectQuery("WorkItem")
        self._purpose = None
        self._comment = None
        self.query.and_filter(gte("version", 1))
        if minimal:
            self.select_id()
            self.select_version()
        else:
            self.select_self_fields()

    def comment(self, c: str):
        self.query.comment(c)
        self._comment = c
        return self

    def purpose(self, p: str):
        self.query.purpose(p)
        self._purpose = p
        return ExecutableWorkItemRequest(self)

    def optimize_for_continuous_page_fetch(self):
        self.query.optimize_for_continuous_page_fetch()
        return self

    def optimize_for_continuous_page_fetch_with(self, namespace: str, ttl_seconds: int):
        self.query.optimize_for_continuous_page_fetch_with(namespace, ttl_seconds)
        return self

    def limit(self, n: int):
        self.query.limit(n)
        return self

    def offset(self, n: int):
        self.query.offset(n)
        return self

    def with_deleted_rows(self):
        self.query._filters = [
            expression for expression in self.query._filters
            if expression.get("field") != "version"
        ]
        return self

    def deleted_rows_only(self):
        self.with_deleted_rows()
        self.query.and_filter(lte("version", -1))
        return self

    def select_self_fields(self):
        self.query.project("id", "title", "description", "platform", "version")
        return self

    def select_id(self):
        self.query.project("id")
        return self

    def select_title(self):
        self.query.project("title")
        return self

    def select_description(self):
        self.query.project("description")
        return self


    def select_version(self):
        self.query.project("version")
        return self

    def select_platform_with(self, child_request):
        self.query.project("platform")
        self.query.relation_query("platform", child_request.query)
        return self

    def with_id_is(self, val):
        self.query.and_filter(eq("id", val))
        return self

    def with_title_containing(self, val: str):
        self.query.and_filter(contain("title", val))
        return self

    def with_title_is(self, val: str):
        self.query.and_filter(eq("title", val))
        return self

    def with_description_containing(self, val: str):
        self.query.and_filter(contain("description", val))
        return self

    def with_description_is(self, val: str):
        self.query.and_filter(eq("description", val))
        return self

    def filter_by_platform(self, val):
        self.query.and_filter(eq("platform", val))
        return self

    def with_version_is(self, val):
        self.query.and_filter(eq("version", val))
        return self

    def order_by_id_ascending(self):
        self.query.order_by("id", "asc")
        return self

    def order_by_id_descending(self):
        self.query.order_by("id", "desc")
        return self

    def order_by_title_ascending(self):
        self.query.order_by("title", "asc")
        return self

    def order_by_title_descending(self):
        self.query.order_by("title", "desc")
        return self

    def order_by_description_ascending(self):
        self.query.order_by("description", "asc")
        return self

    def order_by_description_descending(self):
        self.query.order_by("description", "desc")
        return self


    def order_by_version_ascending(self):
        self.query.order_by("version", "asc")
        return self

    def order_by_version_descending(self):
        self.query.order_by("version", "desc")
        return self


    def count(self):
        self.query.count_field("id", "count")
        return self

    def count_as(self, ret_name: str):
        self.query.count_field("id", ret_name)
        return self

    def group_by_id(self):
        self.query.group_by("id")
        return self

    def group_by_id_as(self, ret_name: str):
        self.query.group_by("id") 
        return self
    def group_by_title(self):
        self.query.group_by("title")
        return self

    def group_by_title_as(self, ret_name: str):
        self.query.group_by("title") 
        return self
    def group_by_description(self):
        self.query.group_by("description")
        return self

    def group_by_description_as(self, ret_name: str):
        self.query.group_by("description") 
        return self
    def group_by_platform(self):
        self.query.group_by("platform")
        return self

    def group_by_platform_as(self, ret_name: str):
        self.query.group_by("platform") 
        return self
    def group_by_version(self):
        self.query.group_by("version")
        return self

    def group_by_version_as(self, ret_name: str):
        self.query.group_by("version") 
        return self

class ExecutableWorkItemRequest:
    def __init__(self, request):
        self._request = request

    def comment(self, c: str):
        self._request.comment(c)
        return self

    def new_entity(self, context) -> WorkItem:
        request = self._request
        if not request._comment or not request._comment.strip() or not request._purpose or not request._purpose.strip():
            raise ValueError("Security audit failure: non-empty comment() and purpose() are required before new_entity()")
        entity = context.initialize_entity("WorkItem", WorkItem(_entity_root=context.entity_root()))
        if not isinstance(entity, WorkItem):
            raise TypeError("entity initializer returned an incompatible WorkItem")
        return entity

    async def execute_for_rows(self, context):
        self = self._request
        if not self._purpose or not self._purpose.strip() or not self._comment or not self._comment.strip():
            raise Exception("Security audit failure: comment() and purpose() must be called before execute_for_rows()")
        service = context.require_resource("dataService")
        req = QueryRequest(context.prepare_query(self.query))
        res = await service.query(context, req)
        return res.rows

    async def execute_for_list(self, context) -> SmartList[WorkItem]:
        rows = await self.execute_for_rows(context)
        return SmartList(WorkItem(_entity_root=context.entity_root(), **row) for row in rows)

    async def execute_for_page(self, context, offset: int, limit: int) -> TeaQLPage[WorkItem]:
        request = self._request
        if not request._purpose or not request._purpose.strip() or not request._comment or not request._comment.strip():
            raise ValueError("Security audit failure: comment() and purpose() must be called before execute_for_page()")
        request.query.offset(offset).limit(limit)
        authorized = context.prepare_query(request.query)
        service = context.require_resource("dataService")
        alias = "__teaql_total"
        count_result = await service.query(context, QueryRequest(authorized.for_exact_count(alias)))
        if not count_result.rows or not isinstance(count_result.rows[0].get(alias), (int, float)):
            raise RuntimeError("dataService did not return an exact page count")
        row_result = await service.query(context, QueryRequest(authorized))
        data = SmartList(WorkItem(_entity_root=context.entity_root(), **row) for row in row_result.rows)
        return TeaQLPage(data=data, total_count=int(count_result.rows[0][alias]), offset=offset, limit=limit)

    async def execute_for_one(self, context):
        self._request.limit(1)
        entities = await self.execute_for_list(context)
        return entities[0] if entities else None

    async def execute_for_stream(self, context, chunk_size: int = 1000):
        """Yield entity chunks lazily from the provider cursor."""
        request = self._request
        if not request._purpose or not request._purpose.strip() or not request._comment or not request._comment.strip():
            raise Exception("Security audit failure: comment() and purpose() must be called before execute_for_stream()")
        service = context.require_resource("dataService")
        if not hasattr(service, "query_stream"):
            raise RuntimeError("dataService does not implement query_stream")
        async for chunk in service.query_stream(context, QueryRequest(request.query), chunk_size):
            for row in chunk.rows:
                yield WorkItem(_entity_root=context.entity_root(), **row)
