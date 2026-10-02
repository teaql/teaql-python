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
from models.platform import Platform
from typing import Protocol

class QuerySelection(Protocol):
    query: SelectQuery

class PlatformRequest:
    def __init__(self, minimal=False):
        self.query = SelectQuery("Platform")
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
        return ExecutablePlatformRequest(self)

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
        self.query.project("id", "name", "founded", "user_email", "version")
        return self

    def select_id(self):
        self.query.project("id")
        return self

    def select_name(self):
        self.query.project("name")
        return self

    def select_founded(self):
        self.query.project("founded")
        return self

    def select_user_email(self):
        self.query.project("user_email")
        return self

    def select_version(self):
        self.query.project("version")
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

    def with_founded_is(self, val):
        self.query.and_filter(eq("founded", val))
        return self

    def with_founded_is_not(self, val):
        self.query.and_filter(ne("founded", val))
        return self

    def with_founded_in(self, *vals):
        self.query.and_filter(in_list("founded", list(vals)))
        return self

    def with_founded_not_in(self, *vals):
        self.query.and_filter(not_in_list("founded", list(vals)))
        return self

    def with_founded_greater_than(self, val):
        self.query.and_filter(gt("founded", val))
        return self

    def with_founded_greater_than_or_equal_to(self, val):
        self.query.and_filter(gte("founded", val))
        return self

    def with_founded_less_than(self, val):
        self.query.and_filter(lt("founded", val))
        return self

    def with_founded_less_than_or_equal_to(self, val):
        self.query.and_filter(lte("founded", val))
        return self

    def with_founded_between(self, lower, upper):
        self.query.and_filter(between(column("founded"), value(lower), value(upper)))
        return self

    def with_founded_is_known(self):
        self.query.and_filter(is_not_null(column("founded")))
        return self

    def with_founded_is_unknown(self):
        self.query.and_filter(is_null(column("founded")))
        return self

    def with_user_email_containing(self, val: str):
        self.query.and_filter(contain("user_email", val))
        return self

    def with_user_email_not_containing(self, val: str):
        self.query.and_filter(not_contain("user_email", val))
        return self

    def with_user_email_starting_with(self, val: str):
        self.query.and_filter(begin_with("user_email", val))
        return self

    def with_user_email_not_starting_with(self, val: str):
        self.query.and_filter(not_begin_with("user_email", val))
        return self

    def with_user_email_ending_with(self, val: str):
        self.query.and_filter(end_with("user_email", val))
        return self

    def with_user_email_not_ending_with(self, val: str):
        self.query.and_filter(not_end_with("user_email", val))
        return self

    def with_user_email_sounding_like(self, val: str):
        self.query.and_filter(sound_like("user_email", val))
        return self

    def with_user_email_is(self, val: str):
        self.query.and_filter(eq("user_email", val))
        return self
    def with_user_email_is_not(self, val):
        self.query.and_filter(ne("user_email", val))
        return self

    def with_user_email_in(self, *vals):
        self.query.and_filter(in_list("user_email", list(vals)))
        return self

    def with_user_email_not_in(self, *vals):
        self.query.and_filter(not_in_list("user_email", list(vals)))
        return self

    def with_user_email_greater_than(self, val):
        self.query.and_filter(gt("user_email", val))
        return self

    def with_user_email_greater_than_or_equal_to(self, val):
        self.query.and_filter(gte("user_email", val))
        return self

    def with_user_email_less_than(self, val):
        self.query.and_filter(lt("user_email", val))
        return self

    def with_user_email_less_than_or_equal_to(self, val):
        self.query.and_filter(lte("user_email", val))
        return self

    def with_user_email_between(self, lower, upper):
        self.query.and_filter(between(column("user_email"), value(lower), value(upper)))
        return self

    def with_user_email_is_known(self):
        self.query.and_filter(is_not_null(column("user_email")))
        return self

    def with_user_email_is_unknown(self):
        self.query.and_filter(is_null(column("user_email")))
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

    def order_by_founded_ascending(self):
        self.query.order_by("founded", "asc")
        return self

    def order_by_founded_descending(self):
        self.query.order_by("founded", "desc")
        return self

    def order_by_user_email_ascending(self):
        self.query.order_by("user_email", "asc")
        return self

    def order_by_user_email_descending(self):
        self.query.order_by("user_email", "desc")
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
    def group_by_founded(self):
        self.query.group_by("founded")
        return self

    def group_by_founded_as(self, ret_name: str):
        self.query.group_by("founded")
        return self
    def group_by_user_email(self):
        self.query.group_by("user_email")
        return self

    def group_by_user_email_as(self, ret_name: str):
        self.query.group_by("user_email")
        return self
    def group_by_version(self):
        self.query.group_by("version")
        return self

    def group_by_version_as(self, ret_name: str):
        self.query.group_by("version")
        return self
    def select_task_status_list(self):
        from requests.task_status_request import TaskStatusRequest
        return self.select_task_status_list_with(TaskStatusRequest())

    def select_task_status_list_with(self, child_request):
        self.query.relation_query("task_status_list", child_request.query)
        return self
    def select_task_list(self):
        from requests.task_request import TaskRequest
        return self.select_task_list_with(TaskRequest())

    def select_task_list_with(self, child_request):
        self.query.relation_query("task_list", child_request.query)
        return self
    def have_task_statuses(self):
        from requests.task_status_request import TaskStatusRequest
        return self.with_task_status_list_matching(TaskStatusRequest())

    def have_no_task_statuses(self):
        from requests.task_status_request import TaskStatusRequest
        return self.without_task_status_list_matching(TaskStatusRequest())

    def with_task_status_list_matching(self, child_request):
        child_request.query.projection = ["platform"]
        self.query.and_filter(in_subquery(column("id"), "TaskStatus", child_request.query))
        return self

    def without_task_status_list_matching(self, child_request):
        child_request.query.projection = ["platform"]
        self.query.and_filter(not_in_subquery(column("id"), "TaskStatus", child_request.query))
        return self
    def have_tasks(self):
        from requests.task_request import TaskRequest
        return self.with_task_list_matching(TaskRequest())

    def have_no_tasks(self):
        from requests.task_request import TaskRequest
        return self.without_task_list_matching(TaskRequest())

    def with_task_list_matching(self, child_request):
        child_request.query.projection = ["platform"]
        self.query.and_filter(in_subquery(column("id"), "Task", child_request.query))
        return self

    def without_task_list_matching(self, child_request):
        child_request.query.projection = ["platform"]
        self.query.and_filter(not_in_subquery(column("id"), "Task", child_request.query))
        return self
    def count_task_statuses(self):
        return self.count_task_statuses_as("count_task_statuses")

    def count_task_statuses_as(self, alias: str):
        from requests.task_status_request import TaskStatusRequest
        return self.count_task_statuses_with(alias, TaskStatusRequest())

    def count_task_statuses_with(self, alias: str, child_request):
        child_request.query.count_field("id", alias)
        self.query.relation_aggregates.append(
            RelationAggregate("task_status_list", alias, child_request.query, True)
        )
        return self

    def min_display_order_of_task_statuses(self):
        from requests.task_status_request import TaskStatusRequest
        return self.min_display_order_of_task_statuses_as(
            "min_display_order_of_task_statuses", TaskStatusRequest())

    def min_display_order_of_task_statuses_as(self, alias: str, child_request):
        child_request.query.min("display_order", "min_display_order")
        self.query.relation_aggregates.append(
            RelationAggregate("task_status_list", alias, child_request.query, True)
        )
        return self
    def max_display_order_of_task_statuses(self):
        from requests.task_status_request import TaskStatusRequest
        return self.max_display_order_of_task_statuses_as(
            "max_display_order_of_task_statuses", TaskStatusRequest())

    def max_display_order_of_task_statuses_as(self, alias: str, child_request):
        child_request.query.max("display_order", "max_display_order")
        self.query.relation_aggregates.append(
            RelationAggregate("task_status_list", alias, child_request.query, True)
        )
        return self
    def sum_display_order_of_task_statuses(self):
        from requests.task_status_request import TaskStatusRequest
        return self.sum_display_order_of_task_statuses_as(
            "sum_display_order_of_task_statuses", TaskStatusRequest())

    def sum_display_order_of_task_statuses_as(self, alias: str, child_request):
        child_request.query.sum("display_order", "sum_display_order")
        self.query.relation_aggregates.append(
            RelationAggregate("task_status_list", alias, child_request.query, True)
        )
        return self
    def avg_display_order_of_task_statuses(self):
        from requests.task_status_request import TaskStatusRequest
        return self.avg_display_order_of_task_statuses_as(
            "avg_display_order_of_task_statuses", TaskStatusRequest())

    def avg_display_order_of_task_statuses_as(self, alias: str, child_request):
        child_request.query.avg("display_order", "avg_display_order")
        self.query.relation_aggregates.append(
            RelationAggregate("task_status_list", alias, child_request.query, True)
        )
        return self
    def standardDeviation_display_order_of_task_statuses(self):
        from requests.task_status_request import TaskStatusRequest
        return self.standardDeviation_display_order_of_task_statuses_as(
            "standardDeviation_display_order_of_task_statuses", TaskStatusRequest())

    def standardDeviation_display_order_of_task_statuses_as(self, alias: str, child_request):
        child_request.query.standardDeviation("display_order", "standardDeviation_display_order")
        self.query.relation_aggregates.append(
            RelationAggregate("task_status_list", alias, child_request.query, True)
        )
        return self
    def squareRootOfPopulationStandardDeviation_display_order_of_task_statuses(self):
        from requests.task_status_request import TaskStatusRequest
        return self.squareRootOfPopulationStandardDeviation_display_order_of_task_statuses_as(
            "squareRootOfPopulationStandardDeviation_display_order_of_task_statuses", TaskStatusRequest())

    def squareRootOfPopulationStandardDeviation_display_order_of_task_statuses_as(self, alias: str, child_request):
        child_request.query.squareRootOfPopulationStandardDeviation("display_order", "squareRootOfPopulationStandardDeviation_display_order")
        self.query.relation_aggregates.append(
            RelationAggregate("task_status_list", alias, child_request.query, True)
        )
        return self
    def sampleVariance_display_order_of_task_statuses(self):
        from requests.task_status_request import TaskStatusRequest
        return self.sampleVariance_display_order_of_task_statuses_as(
            "sampleVariance_display_order_of_task_statuses", TaskStatusRequest())

    def sampleVariance_display_order_of_task_statuses_as(self, alias: str, child_request):
        child_request.query.sampleVariance("display_order", "sampleVariance_display_order")
        self.query.relation_aggregates.append(
            RelationAggregate("task_status_list", alias, child_request.query, True)
        )
        return self
    def samplePopulationVariance_display_order_of_task_statuses(self):
        from requests.task_status_request import TaskStatusRequest
        return self.samplePopulationVariance_display_order_of_task_statuses_as(
            "samplePopulationVariance_display_order_of_task_statuses", TaskStatusRequest())

    def samplePopulationVariance_display_order_of_task_statuses_as(self, alias: str, child_request):
        child_request.query.samplePopulationVariance("display_order", "samplePopulationVariance_display_order")
        self.query.relation_aggregates.append(
            RelationAggregate("task_status_list", alias, child_request.query, True)
        )
        return self
    def min_progress_of_task_statuses(self):
        from requests.task_status_request import TaskStatusRequest
        return self.min_progress_of_task_statuses_as(
            "min_progress_of_task_statuses", TaskStatusRequest())

    def min_progress_of_task_statuses_as(self, alias: str, child_request):
        child_request.query.min("progress", "min_progress")
        self.query.relation_aggregates.append(
            RelationAggregate("task_status_list", alias, child_request.query, True)
        )
        return self
    def max_progress_of_task_statuses(self):
        from requests.task_status_request import TaskStatusRequest
        return self.max_progress_of_task_statuses_as(
            "max_progress_of_task_statuses", TaskStatusRequest())

    def max_progress_of_task_statuses_as(self, alias: str, child_request):
        child_request.query.max("progress", "max_progress")
        self.query.relation_aggregates.append(
            RelationAggregate("task_status_list", alias, child_request.query, True)
        )
        return self
    def sum_progress_of_task_statuses(self):
        from requests.task_status_request import TaskStatusRequest
        return self.sum_progress_of_task_statuses_as(
            "sum_progress_of_task_statuses", TaskStatusRequest())

    def sum_progress_of_task_statuses_as(self, alias: str, child_request):
        child_request.query.sum("progress", "sum_progress")
        self.query.relation_aggregates.append(
            RelationAggregate("task_status_list", alias, child_request.query, True)
        )
        return self
    def avg_progress_of_task_statuses(self):
        from requests.task_status_request import TaskStatusRequest
        return self.avg_progress_of_task_statuses_as(
            "avg_progress_of_task_statuses", TaskStatusRequest())

    def avg_progress_of_task_statuses_as(self, alias: str, child_request):
        child_request.query.avg("progress", "avg_progress")
        self.query.relation_aggregates.append(
            RelationAggregate("task_status_list", alias, child_request.query, True)
        )
        return self
    def standardDeviation_progress_of_task_statuses(self):
        from requests.task_status_request import TaskStatusRequest
        return self.standardDeviation_progress_of_task_statuses_as(
            "standardDeviation_progress_of_task_statuses", TaskStatusRequest())

    def standardDeviation_progress_of_task_statuses_as(self, alias: str, child_request):
        child_request.query.standardDeviation("progress", "standardDeviation_progress")
        self.query.relation_aggregates.append(
            RelationAggregate("task_status_list", alias, child_request.query, True)
        )
        return self
    def squareRootOfPopulationStandardDeviation_progress_of_task_statuses(self):
        from requests.task_status_request import TaskStatusRequest
        return self.squareRootOfPopulationStandardDeviation_progress_of_task_statuses_as(
            "squareRootOfPopulationStandardDeviation_progress_of_task_statuses", TaskStatusRequest())

    def squareRootOfPopulationStandardDeviation_progress_of_task_statuses_as(self, alias: str, child_request):
        child_request.query.squareRootOfPopulationStandardDeviation("progress", "squareRootOfPopulationStandardDeviation_progress")
        self.query.relation_aggregates.append(
            RelationAggregate("task_status_list", alias, child_request.query, True)
        )
        return self
    def sampleVariance_progress_of_task_statuses(self):
        from requests.task_status_request import TaskStatusRequest
        return self.sampleVariance_progress_of_task_statuses_as(
            "sampleVariance_progress_of_task_statuses", TaskStatusRequest())

    def sampleVariance_progress_of_task_statuses_as(self, alias: str, child_request):
        child_request.query.sampleVariance("progress", "sampleVariance_progress")
        self.query.relation_aggregates.append(
            RelationAggregate("task_status_list", alias, child_request.query, True)
        )
        return self
    def samplePopulationVariance_progress_of_task_statuses(self):
        from requests.task_status_request import TaskStatusRequest
        return self.samplePopulationVariance_progress_of_task_statuses_as(
            "samplePopulationVariance_progress_of_task_statuses", TaskStatusRequest())

    def samplePopulationVariance_progress_of_task_statuses_as(self, alias: str, child_request):
        child_request.query.samplePopulationVariance("progress", "samplePopulationVariance_progress")
        self.query.relation_aggregates.append(
            RelationAggregate("task_status_list", alias, child_request.query, True)
        )
        return self
    def count_tasks(self):
        return self.count_tasks_as("count_tasks")

    def count_tasks_as(self, alias: str):
        from requests.task_request import TaskRequest
        return self.count_tasks_with(alias, TaskRequest())

    def count_tasks_with(self, alias: str, child_request):
        child_request.query.count_field("id", alias)
        self.query.relation_aggregates.append(
            RelationAggregate("task_list", alias, child_request.query, True)
        )
        return self



class ExecutablePlatformRequest:
    def __init__(self, request):
        self._request = request

    def comment(self, c: str):
        self._request.comment(c)
        return self

    def new_entity(self, context) -> Platform:
        request = self._request
        QueryIntent(request._comment, request._purpose)
        entity = context.initialize_entity("Platform", Platform())
        if not isinstance(entity, Platform):
            raise TypeError("entity initializer returned an incompatible Platform")
        return entity

    async def execute_for_result(self, context):
        self = self._request
        req = QueryRequest(self.query, _comment=self._comment, _purpose=self._purpose)
        req = context.prepare_query_request(req)
        service = context.require_resource("dataService")
        return await service.query(context, req)

    async def execute_for_rows(self, context):
        return (await self.execute_for_result(context)).rows

    async def execute_for_list(self, context) -> SmartList[Platform]:
        result = await self.execute_for_result(context)
        return SmartList(
            (Platform(**row) for row in result.rows),
            facets=result.facets)

    async def execute_for_page(self, context, offset: int, limit: int) -> TeaQLPage[Platform]:
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
        data = SmartList(Platform(**row) for row in row_result.rows)
        return TeaQLPage(data=data, total_count=total_count, offset=offset, limit=limit)

    async def execute_for_one(self, context):
        request = deepcopy(self._request)
        request.limit(1)
        entities = await ExecutablePlatformRequest(request).execute_for_list(context)
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
                        yield Platform(**row)
            finally:
                close = getattr(stream, "aclose", None)
                if close is not None:
                    await close()
        return entities()
