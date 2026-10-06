from teaql.core.query import RelationAggregate, SelectQuery
from teaql.core.list import SmartList, TeaQLPage
from teaql.data_service import QueryRequest
from teaql.core import QueryIntent
from copy import deepcopy
from teaql.core.expr import (
    begin_with, between, column, contain, end_with, eq, gt, gte,
    in_list, in_subquery, is_not_null, is_null, lt, lte, ne, not_begin_with,
    not_contain, not_end_with, not_in_list, not_in_subquery, value,
    sound_like,
)
from models.task import Task
from typing import Protocol

class QuerySelection(Protocol):
    query: SelectQuery

class TaskRequest:
    def __init__(self, minimal=False):
        self.query = SelectQuery("Task")
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
        return ExecutableTaskRequest(self)

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
        self.query.with_deleted_rows()
        return self

    def deleted_rows_only(self):
        self.query.deleted_rows_only()
        return self

    def select_self_fields(self):
        self.query.project("id", "name", "status", "platform", "version")
        return self

    def select_id(self):
        self.query.project("id")
        return self

    def select_name(self):
        self.query.project("name")
        return self



    def select_version(self):
        self.query.project("version")
        return self

    def select_status_with(self, child_request):
        self.query.project("status")
        self.query.relation_query("status", child_request.query)
        return self
    def select_platform_with(self, child_request):
        self.query.project("platform")
        self.query.relation_query("platform", child_request.query)
        return self
    def with_status_matching(self, child_request):
        child_request.query.projection = ["id"]
        self.query.and_filter(in_subquery(column("status"), "TaskStatus", child_request.query))
        return self

    def without_status_matching(self, child_request):
        child_request.query.projection = ["id"]
        self.query.and_filter(not_in_subquery(column("status"), "TaskStatus", child_request.query))
        return self

    def have_status(self):
        self.query.and_filter(is_not_null(column("status")))
        return self

    def have_no_status(self):
        self.query.and_filter(is_null(column("status")))
        return self
    def with_platform_matching(self, child_request):
        child_request.query.projection = ["id"]
        self.query.and_filter(in_subquery(column("platform"), "Platform", child_request.query))
        return self

    def without_platform_matching(self, child_request):
        child_request.query.projection = ["id"]
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

    def with_name_containing(self, val: str):
        self.query.and_filter(contain("name", val))
        return self

    def with_name_not_containing(self, val: str):
        self.query.and_filter(not_contain("name", val))
        return self

    def with_name_starting_with(self, val: str):
        self.query.and_filter(begin_with("name", val))
        return self

    def with_name_not_starting_with(self, val: str):
        self.query.and_filter(not_begin_with("name", val))
        return self

    def with_name_ending_with(self, val: str):
        self.query.and_filter(end_with("name", val))
        return self

    def with_name_not_ending_with(self, val: str):
        self.query.and_filter(not_end_with("name", val))
        return self

    def with_name_sounding_like(self, val: str):
        self.query.and_filter(sound_like("name", val))
        return self

    def with_name_is(self, val: str):
        self.query.and_filter(eq("name", val))
        return self
    def with_name_is_not(self, val):
        self.query.and_filter(ne("name", val))
        return self

    def with_name_in(self, *vals):
        self.query.and_filter(in_list("name", list(vals)))
        return self

    def with_name_not_in(self, *vals):
        self.query.and_filter(not_in_list("name", list(vals)))
        return self

    def with_name_greater_than(self, val):
        self.query.and_filter(gt("name", val))
        return self

    def with_name_greater_than_or_equal_to(self, val):
        self.query.and_filter(gte("name", val))
        return self

    def with_name_less_than(self, val):
        self.query.and_filter(lt("name", val))
        return self

    def with_name_less_than_or_equal_to(self, val):
        self.query.and_filter(lte("name", val))
        return self

    def with_name_between(self, lower, upper):
        self.query.and_filter(between(column("name"), value(lower), value(upper)))
        return self

    def with_name_is_known(self):
        self.query.and_filter(is_not_null(column("name")))
        return self

    def with_name_is_unknown(self):
        self.query.and_filter(is_null(column("name")))
        return self

    def filter_by_status(self, val):
        self.query.and_filter(eq("status", val))
        return self
    def with_status_is_planned(self):
        self.query.and_filter(eq("status", 1001))
        return self
    def with_status_is_ready(self):
        self.query.and_filter(eq("status", 1002))
        return self
    def with_status_is_executing(self):
        self.query.and_filter(eq("status", 1003))
        return self
    def with_status_is_verified(self):
        self.query.and_filter(eq("status", 1004))
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

    def order_by_name_ascending(self):
        self.query.order_by("name", "asc")
        return self

    def order_by_name_descending(self):
        self.query.order_by("name", "desc")
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
    def group_by_name(self):
        self.query.group_by("name")
        return self

    def group_by_name_as(self, ret_name: str):
        self.query.group_by("name")
        return self
    def group_by_status(self):
        self.query.group_by("status")
        return self

    def group_by_status_as(self, ret_name: str):
        self.query.group_by("status")
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
    def select_task_execution_log_list(self):
        from requests.task_execution_log_request import TaskExecutionLogRequest
        return self.select_task_execution_log_list_with(TaskExecutionLogRequest())

    def select_task_execution_log_list_with(self, child_request):
        self.query.relation_query("task_execution_log_list", child_request.query)
        return self
    def have_task_execution_logs(self):
        from requests.task_execution_log_request import TaskExecutionLogRequest
        return self.with_task_execution_log_list_matching(TaskExecutionLogRequest())

    def have_no_task_execution_logs(self):
        from requests.task_execution_log_request import TaskExecutionLogRequest
        return self.without_task_execution_log_list_matching(TaskExecutionLogRequest())

    def with_task_execution_log_list_matching(self, child_request):
        child_request.query.projection = ["task"]
        self.query.and_filter(in_subquery(column("id"), "TaskExecutionLog", child_request.query))
        return self

    def without_task_execution_log_list_matching(self, child_request):
        child_request.query.projection = ["task"]
        self.query.and_filter(not_in_subquery(column("id"), "TaskExecutionLog", child_request.query))
        return self
    def count_task_execution_logs(self):
        return self.count_task_execution_logs_as("count_task_execution_logs")

    def count_task_execution_logs_as(self, alias: str):
        from requests.task_execution_log_request import TaskExecutionLogRequest
        return self.count_task_execution_logs_with(alias, TaskExecutionLogRequest())

    def count_task_execution_logs_with(self, alias: str, child_request):
        child_request.query.count_field("id", alias)
        self.query.relation_aggregates.append(
            RelationAggregate("task_execution_log_list", alias, child_request.query, True)
        )
        return self


    def facet_by_status_as(self, name: str, request: QuerySelection,
                                      include_all_facets: bool = True):
        self.query.facet_by(name, "status", request.query, include_all_facets)
        return self

    def facet_by_platform_as(self, name: str, request: QuerySelection,
                                      include_all_facets: bool = True):
        self.query.facet_by(name, "platform", request.query, include_all_facets)
        return self


class ExecutableTaskRequest:
    def __init__(self, request):
        self._request = request

    def comment(self, c: str):
        self._request.comment(c)
        return self

    def new_entity(self, context) -> Task:
        request = self._request
        QueryIntent(request._comment, request._purpose)
        entity = context.initialize_entity("Task", Task())
        if not isinstance(entity, Task):
            raise TypeError("entity initializer returned an incompatible Task")
        return entity

    async def execute_for_result(self, context):
        self = self._request
        req = QueryRequest(self.query, _comment=self._comment, _purpose=self._purpose)
        req = context.prepare_query_request(req)
        service = context.require_resource("dataService")
        return await service.query(context, req)

    async def execute_for_rows(self, context):
        return (await self.execute_for_result(context)).rows

    async def execute_for_list(self, context) -> SmartList[Task]:
        result = await self.execute_for_result(context)
        return SmartList(
            (Task(**row) for row in result.rows),
            facets=result.facets)

    async def execute_for_page(self, context, offset: int, limit: int) -> TeaQLPage[Task]:
        request = self._request
        intent = QueryIntent(request._comment, request._purpose)
        query = deepcopy(request.query)
        query.offset(offset).limit(limit)
        authorized = context.prepare_query_request(QueryRequest(query, _comment=intent.comment, _purpose=intent.purpose))
        service = context.require_resource("dataService")
        alias = "__teaql_total"
        if authorized.query.id_set_pagination is not None:
            row_result = await service.query(context, authorized)
            retained_count, accuracy = context.id_set_count()
            if accuracy == "EXACT":
                total_count = retained_count
            else:
                count_result = await service.query(context, authorized.with_query(authorized.query.for_exact_count(alias)))
                if not count_result.rows or not isinstance(count_result.rows[0].get(alias), (int, float)):
                    raise RuntimeError("dataService did not return an exact page count")
                total_count = int(count_result.rows[0][alias])
        else:
            count_result = await service.query(context, authorized.with_query(authorized.query.for_exact_count(alias)))
            if not count_result.rows or not isinstance(count_result.rows[0].get(alias), (int, float)):
                raise RuntimeError("dataService did not return an exact page count")
            total_count = int(count_result.rows[0][alias])
            row_result = await service.query(context, authorized)
        data = SmartList(Task(**row) for row in row_result.rows)
        return TeaQLPage(data=data, total_count=total_count, offset=offset, limit=limit)

    async def execute_for_one(self, context):
        request = deepcopy(self._request)
        request.limit(1)
        entities = await ExecutableTaskRequest(request).execute_for_list(context)
        return entities[0] if entities else None

    def execute_for_stream(self, context, chunk_size: int = 1000):
        """Yield entity chunks lazily from the provider cursor."""
        request = self._request
        req = QueryRequest(request.query, _comment=request._comment, _purpose=request._purpose)
        req = context.prepare_query_request(req)
        service = context.require_resource("dataService")
        if not hasattr(service, "query_stream"):
            raise RuntimeError("dataService does not implement query_stream")
        stream = service.query_stream(context, req, chunk_size)
        async def entities():
            try:
                async for chunk in stream:
                    for row in chunk.rows:
                        yield Task(**row)
            finally:
                close = getattr(stream, "aclose", None)
                if close is not None:
                    await close()
        return entities()
