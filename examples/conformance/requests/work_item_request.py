from teaql.core.query import SelectQuery
from teaql.core.list import SmartList, TeaQLPage
from teaql.runtime import EntityRoot
from teaql.data_service import QueryRequest
from teaql.core.expr import (
    begin_with, between, column, contain, end_with, eq, gt, gte,
    in_list, in_subquery, is_not_null, is_null, lt, lte, ne, not_begin_with,
    not_contain, not_end_with, not_in_list, not_in_subquery, value,
    sound_like,
)
from models.work_item import WorkItem
from typing import Protocol

class QuerySelection(Protocol):
    query: SelectQuery

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

    def optimize_pagination_with_id_set(self):
        self.query.optimize_pagination_with_id_set()
        return self

    def optimize_pagination_with_id_set_config(self, namespace: str, ttl_seconds: int, max_ids: int):
        self.query.optimize_pagination_with_id_set_config(namespace, ttl_seconds, max_ids)
        return self

    def top_n_probe_parent_threshold(self, threshold: int):
        self.query.top_n_probe_parent_threshold(threshold)
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
    def with_platform_matching(self, child_request):
        child_request.query._projection = ["id"]
        self.query.and_filter(in_subquery(column("platform"), "Platform", child_request.query))
        return self

    def without_platform_matching(self, child_request):
        child_request.query._projection = ["id"]
        self.query.and_filter(not_in_subquery(column("platform"), "Platform", child_request.query))
        return self

    def have_platform(self):
        self.query.and_filter(is_not_null(column("platform")))
        return self

    def have_no_platform(self):
        self.query.and_filter(is_null(column("platform")))
        return self

    def with_id_is(self, val):
        self.query.and_filter(eq("id", val))
        return self

    def with_id_is_not(self, val):
        self.query.and_filter(ne("id", val))
        return self

    def with_id_in(self, *vals):
        self.query.and_filter(in_list("id", list(vals)))
        return self

    def with_id_not_in(self, *vals):
        self.query.and_filter(not_in_list("id", list(vals)))
        return self

    def with_id_greater_than(self, val):
        self.query.and_filter(gt("id", val))
        return self

    def with_id_greater_than_or_equal_to(self, val):
        self.query.and_filter(gte("id", val))
        return self

    def with_id_less_than(self, val):
        self.query.and_filter(lt("id", val))
        return self

    def with_id_less_than_or_equal_to(self, val):
        self.query.and_filter(lte("id", val))
        return self

    def with_id_between(self, lower, upper):
        self.query.and_filter(between(column("id"), value(lower), value(upper)))
        return self

    def with_id_is_known(self):
        self.query.and_filter(is_not_null(column("id")))
        return self

    def with_id_is_unknown(self):
        self.query.and_filter(is_null(column("id")))
        return self

    def with_title_containing(self, val: str):
        self.query.and_filter(contain("title", val))
        return self

    def with_title_not_containing(self, val: str):
        self.query.and_filter(not_contain("title", val))
        return self

    def with_title_starting_with(self, val: str):
        self.query.and_filter(begin_with("title", val))
        return self

    def with_title_not_starting_with(self, val: str):
        self.query.and_filter(not_begin_with("title", val))
        return self

    def with_title_ending_with(self, val: str):
        self.query.and_filter(end_with("title", val))
        return self

    def with_title_not_ending_with(self, val: str):
        self.query.and_filter(not_end_with("title", val))
        return self

    def with_title_sounding_like(self, val: str):
        self.query.and_filter(sound_like("title", val))
        return self

    def with_title_is(self, val: str):
        self.query.and_filter(eq("title", val))
        return self
    def with_title_is_not(self, val):
        self.query.and_filter(ne("title", val))
        return self

    def with_title_in(self, *vals):
        self.query.and_filter(in_list("title", list(vals)))
        return self

    def with_title_not_in(self, *vals):
        self.query.and_filter(not_in_list("title", list(vals)))
        return self

    def with_title_greater_than(self, val):
        self.query.and_filter(gt("title", val))
        return self

    def with_title_greater_than_or_equal_to(self, val):
        self.query.and_filter(gte("title", val))
        return self

    def with_title_less_than(self, val):
        self.query.and_filter(lt("title", val))
        return self

    def with_title_less_than_or_equal_to(self, val):
        self.query.and_filter(lte("title", val))
        return self

    def with_title_between(self, lower, upper):
        self.query.and_filter(between(column("title"), value(lower), value(upper)))
        return self

    def with_title_is_known(self):
        self.query.and_filter(is_not_null(column("title")))
        return self

    def with_title_is_unknown(self):
        self.query.and_filter(is_null(column("title")))
        return self

    def with_description_containing(self, val: str):
        self.query.and_filter(contain("description", val))
        return self

    def with_description_not_containing(self, val: str):
        self.query.and_filter(not_contain("description", val))
        return self

    def with_description_starting_with(self, val: str):
        self.query.and_filter(begin_with("description", val))
        return self

    def with_description_not_starting_with(self, val: str):
        self.query.and_filter(not_begin_with("description", val))
        return self

    def with_description_ending_with(self, val: str):
        self.query.and_filter(end_with("description", val))
        return self

    def with_description_not_ending_with(self, val: str):
        self.query.and_filter(not_end_with("description", val))
        return self

    def with_description_sounding_like(self, val: str):
        self.query.and_filter(sound_like("description", val))
        return self

    def with_description_is(self, val: str):
        self.query.and_filter(eq("description", val))
        return self
    def with_description_is_not(self, val):
        self.query.and_filter(ne("description", val))
        return self

    def with_description_in(self, *vals):
        self.query.and_filter(in_list("description", list(vals)))
        return self

    def with_description_not_in(self, *vals):
        self.query.and_filter(not_in_list("description", list(vals)))
        return self

    def with_description_greater_than(self, val):
        self.query.and_filter(gt("description", val))
        return self

    def with_description_greater_than_or_equal_to(self, val):
        self.query.and_filter(gte("description", val))
        return self

    def with_description_less_than(self, val):
        self.query.and_filter(lt("description", val))
        return self

    def with_description_less_than_or_equal_to(self, val):
        self.query.and_filter(lte("description", val))
        return self

    def with_description_between(self, lower, upper):
        self.query.and_filter(between(column("description"), value(lower), value(upper)))
        return self

    def with_description_is_known(self):
        self.query.and_filter(is_not_null(column("description")))
        return self

    def with_description_is_unknown(self):
        self.query.and_filter(is_null(column("description")))
        return self

    def filter_by_platform(self, val):
        self.query.and_filter(eq("platform", val))
        return self

    def with_version_is(self, val):
        self.query.and_filter(eq("version", val))
        return self

    def with_version_is_not(self, val):
        self.query.and_filter(ne("version", val))
        return self

    def with_version_in(self, *vals):
        self.query.and_filter(in_list("version", list(vals)))
        return self

    def with_version_not_in(self, *vals):
        self.query.and_filter(not_in_list("version", list(vals)))
        return self

    def with_version_greater_than(self, val):
        self.query.and_filter(gt("version", val))
        return self

    def with_version_greater_than_or_equal_to(self, val):
        self.query.and_filter(gte("version", val))
        return self

    def with_version_less_than(self, val):
        self.query.and_filter(lt("version", val))
        return self

    def with_version_less_than_or_equal_to(self, val):
        self.query.and_filter(lte("version", val))
        return self

    def with_version_between(self, lower, upper):
        self.query.and_filter(between(column("version"), value(lower), value(upper)))
        return self

    def with_version_is_known(self):
        self.query.and_filter(is_not_null(column("version")))
        return self

    def with_version_is_unknown(self):
        self.query.and_filter(is_null(column("version")))
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
    def facet_by_platform_as(self, name: str, request: QuerySelection,
                                      include_all_facets: bool = True):
        self.query.facet_by(name, "platform", request.query, include_all_facets)
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
        entity = context.initialize_entity("WorkItem", WorkItem())
        if not isinstance(entity, WorkItem):
            raise TypeError("entity initializer returned an incompatible WorkItem")
        return entity

    async def execute_for_result(self, context):
        self = self._request
        if not self._purpose or not self._purpose.strip() or not self._comment or not self._comment.strip():
            raise Exception("Security audit failure: comment() and purpose() must be called before execute_for_rows()")
        service = context.require_resource("dataService")
        req = QueryRequest(context.prepare_query(self.query))
        return await service.query(context, req)

    async def execute_for_rows(self, context):
        return (await self.execute_for_result(context)).rows

    async def execute_for_list(self, context) -> SmartList[WorkItem]:
        result = await self.execute_for_result(context)
        query_root = EntityRoot()
        return SmartList(
            (WorkItem(_entity_root=query_root, **row) for row in result.rows),
            facets=result.facets)

    async def execute_for_page(self, context, offset: int, limit: int) -> TeaQLPage[WorkItem]:
        request = self._request
        if not request._purpose or not request._purpose.strip() or not request._comment or not request._comment.strip():
            raise ValueError("Security audit failure: comment() and purpose() must be called before execute_for_page()")
        request.query.offset(offset).limit(limit)
        authorized = context.prepare_query(request.query)
        service = context.require_resource("dataService")
        alias = "__teaql_total"
        if authorized.id_set_pagination is not None:
            row_result = await service.query(context, QueryRequest(authorized))
            retained_count, accuracy = context.id_set_count()
            if accuracy == "EXACT":
                total_count = retained_count
            else:
                count_result = await service.query(context, QueryRequest(authorized.for_exact_count(alias)))
                if not count_result.rows or not isinstance(count_result.rows[0].get(alias), (int, float)):
                    raise RuntimeError("dataService did not return an exact page count")
                total_count = int(count_result.rows[0][alias])
        else:
            count_result = await service.query(context, QueryRequest(authorized.for_exact_count(alias)))
            if not count_result.rows or not isinstance(count_result.rows[0].get(alias), (int, float)):
                raise RuntimeError("dataService did not return an exact page count")
            total_count = int(count_result.rows[0][alias])
            row_result = await service.query(context, QueryRequest(authorized))
        query_root = EntityRoot()
        data = SmartList(WorkItem(_entity_root=query_root, **row) for row in row_result.rows)
        return TeaQLPage(data=data, total_count=total_count, offset=offset, limit=limit)

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
        query_root = EntityRoot()
        async for chunk in service.query_stream(context, QueryRequest(request.query), chunk_size):
            for row in chunk.rows:
                yield WorkItem(_entity_root=query_root, **row)
