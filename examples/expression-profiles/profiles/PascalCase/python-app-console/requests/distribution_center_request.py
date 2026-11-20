from teaql.core.query import AggregateFunction, RelationAggregate, SelectQuery
from teaql.core.request_tree import QueryOperation
from teaql.core.dynamic_search import merge_generated_scalar_search
from generated_search_models import GENERATED_SEARCH_MODELS
from teaql.core.list import SmartList
from teaql.core.request_intent import QueryIntent
from teaql.runtime import EntityRoot
from teaql.data_service import QueryRequest
from copy import deepcopy
from teaql.core.expr import (
    begin_with, between, column, contain, end_with, eq, gt, gte,
    in_list, in_subquery, is_not_null, is_null, lt, lte, ne, not_begin_with,
    not_contain, not_end_with, not_in_list, not_in_subquery, value,
    sound_like,
)
from models.distribution_center import DistributionCenter
from typing import Protocol

class QuerySelection(Protocol):
    query: SelectQuery

class DistributionCenterRequest:
    def __init__(self, minimal=False):
        self.query = SelectQuery("DistributionCenter")
        self._purpose = None
        self._comment = None
        self._page_count_alias = None
        self._page_count_method = None
        self._dynamic_search_warnings = []
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

    def filter_by_json(self, source, warn=None):
        kwargs = {} if warn is None else {"warn": warn}
        query, warnings = merge_generated_scalar_search(self.query, source, GENERATED_SEARCH_MODELS, **kwargs)
        self.query = query
        self._dynamic_search_warnings.extend(warnings)
        return self

    @property
    def dynamic_search_warnings(self):
        return tuple(dict(warning) for warning in self._dynamic_search_warnings)

    def purpose(self, p: str):
        self.query.purpose(p)
        self._purpose = p
        return ExecutableDistributionCenterRequest(self)

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
        self.query.project("id", "dock_name", "version")
        return self

    def select_id(self):
        self.query.project("id")
        return self

    def select_dock_name(self):
        self.query.project("dock_name")
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

    def with_dock_name_containing(self, val: str):
        self.query.and_filter(contain("dock_name", val))
        return self

    def with_dock_name_not_containing(self, val: str):
        self.query.and_filter(not_contain("dock_name", val))
        return self

    def with_dock_name_starting_with(self, val: str):
        self.query.and_filter(begin_with("dock_name", val))
        return self

    def with_dock_name_not_starting_with(self, val: str):
        self.query.and_filter(not_begin_with("dock_name", val))
        return self

    def with_dock_name_ending_with(self, val: str):
        self.query.and_filter(end_with("dock_name", val))
        return self

    def with_dock_name_not_ending_with(self, val: str):
        self.query.and_filter(not_end_with("dock_name", val))
        return self

    def with_dock_name_sounding_like(self, val: str):
        self.query.and_filter(sound_like("dock_name", val))
        return self

    def with_dock_name_is(self, val: str):
        self.query.and_filter(eq("dock_name", val))
        return self
    def with_dock_name_is_not(self, val):
        self.query.and_filter(ne("dock_name", val))
        return self

    def with_dock_name_in(self, *vals):
        self.query.and_filter(in_list("dock_name", list(vals)))
        return self

    def with_dock_name_not_in(self, *vals):
        self.query.and_filter(not_in_list("dock_name", list(vals)))
        return self

    def with_dock_name_greater_than(self, val):
        self.query.and_filter(gt("dock_name", val))
        return self

    def with_dock_name_greater_than_or_equal_to(self, val):
        self.query.and_filter(gte("dock_name", val))
        return self

    def with_dock_name_less_than(self, val):
        self.query.and_filter(lt("dock_name", val))
        return self

    def with_dock_name_less_than_or_equal_to(self, val):
        self.query.and_filter(lte("dock_name", val))
        return self

    def with_dock_name_between(self, lower, upper):
        self.query.and_filter(between(column("dock_name"), value(lower), value(upper)))
        return self

    def with_dock_name_is_known(self):
        self.query.and_filter(is_not_null(column("dock_name")))
        return self

    def with_dock_name_is_unknown(self):
        self.query.and_filter(is_null(column("dock_name")))
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

    def order_by_dock_name_ascending(self):
        self.query.order_by("dock_name", "asc")
        return self

    def order_by_dock_name_descending(self):
        self.query.order_by("dock_name", "desc")
        return self

    def order_by_version_ascending(self):
        self.query.order_by("version", "asc")
        return self

    def order_by_version_descending(self):
        self.query.order_by("version", "desc")
        return self


    def count(self):
        self.query.count_field("id", "count")
        self._page_count_alias = "count"
        self._page_count_method = "count"
        return self

    def count_as(self, ret_name: str):
        self.query.count_field("id", ret_name)
        self._page_count_alias = ret_name
        self._page_count_method = "count_as"
        return self

    def group_by_id(self):
        self.query.group_by("id")
        return self

    def group_by_id_as(self, ret_name: str):
        self.query.group_by("id")
        self.query.project_expr(ret_name, column("id"))
        return self
    def group_by_dock_name(self):
        self.query.group_by("dock_name")
        return self

    def group_by_dock_name_as(self, ret_name: str):
        self.query.group_by("dock_name")
        self.query.project_expr(ret_name, column("dock_name"))
        return self
    def group_by_version(self):
        self.query.group_by("version")
        return self

    def group_by_version_as(self, ret_name: str):
        self.query.group_by("version")
        self.query.project_expr(ret_name, column("version"))
        return self
    def select_dispatch_order_list(self):
        from requests.dispatch_order_request import DispatchOrderRequest
        return self.select_dispatch_order_list_with(DispatchOrderRequest())

    def select_dispatch_order_list_with(self, child_request):
        self.query.relation_query("dispatch_order_list", child_request.query,
            QueryOperation("relation-select", "select_dispatch_order_list_with", relation="dispatch_order_list"))
        return self
    def have_dispatch_orders(self):
        from requests.dispatch_order_request import DispatchOrderRequest
        return self.with_dispatch_order_list_matching(DispatchOrderRequest())

    def have_no_dispatch_orders(self):
        from requests.dispatch_order_request import DispatchOrderRequest
        return self.without_dispatch_order_list_matching(DispatchOrderRequest())

    def with_dispatch_order_list_matching(self, child_request):
        child_request.query.projection = ["distribution_center"]
        self.query.and_filter(in_subquery(column("id"), "DispatchOrder", child_request.query))
        return self

    def without_dispatch_order_list_matching(self, child_request):
        child_request.query.projection = ["distribution_center"]
        self.query.and_filter(not_in_subquery(column("id"), "DispatchOrder", child_request.query))
        return self
    def count_dispatch_orders(self):
        return self.count_dispatch_orders_as("count_dispatch_orders")

    def count_dispatch_orders_as(self, alias: str):
        from requests.dispatch_order_request import DispatchOrderRequest
        self.count_dispatch_orders_with(alias, DispatchOrderRequest())
        self.query.relation_aggregates[-1].operation = QueryOperation(
            "relation-count", "count_dispatch_orders_as", alias, "dispatch_order_list")
        return self

    def count_dispatch_orders_with(self, alias: str, child_request):
        query = deepcopy(child_request.query)
        query.aggregates = []
        query.count_field("id", alias)
        self.query.relation_aggregates.append(
            RelationAggregate("dispatch_order_list", alias, query, True,
                QueryOperation("relation-count", "count_dispatch_orders_with", alias, "dispatch_order_list"))
        )
        return self



class ExecutableDistributionCenterRequest:
    def __init__(self, request):
        self._request = request

    def comment(self, c: str):
        self._request.comment(c)
        return self

    async def new_entity(self, context) -> DistributionCenter:
        request = self._request
        QueryIntent(request._comment, request._purpose)
        identity = await context.next_id("DistributionCenter")
        entity = context.initialize_entity("DistributionCenter", DistributionCenter._teaql_from_reserved_id(identity))
        if not isinstance(entity, DistributionCenter):
            raise TypeError("entity initializer returned an incompatible DistributionCenter")
        return entity

    async def execute_for_result(self, context):
        self = self._request
        req = QueryRequest(self.query, _comment=self._comment, _purpose=self._purpose)
        req = context.prepare_query_request(req)
        service = context.require_resource("dataService")
        return await service.query(context, req)

    async def execute_for_rows(self, context):
        return (await self.execute_for_result(context)).rows

    async def execute_for_list(self, context) -> SmartList[DistributionCenter]:
        from teaql.runtime.query_list import execute_typed_list
        request = self._request
        QueryIntent(request._comment, request._purpose)
        query = deepcopy(request.query)
        authorized = context.prepare_query(query)
        root = QueryRequest(authorized, _comment=request._comment, _purpose=request._purpose)
        operation = (QueryOperation("named-count", request._page_count_method or "count",
            request._page_count_alias if request._page_count_method == "count_as" else None)
            if request._page_count_alias is not None else None)
        return await execute_typed_list(context, root,
            lambda row: DistributionCenter._teaql_from_record(_entity_root=EntityRoot(), **row),
            count_operation=operation, count_alias=request._page_count_alias)

    async def execute_for_one(self, context):
        request = deepcopy(self._request)
        request.limit(1)
        entities = await ExecutableDistributionCenterRequest(request).execute_for_list(context)
        return entities[0] if entities else None

    def execute_for_stream(self, context, chunk_size: int = 1000):
        """Yield entity chunks lazily from the provider cursor."""
        request = deepcopy(self._request)
        QueryIntent(request._comment, request._purpose)
        service = context.require_resource("dataService")
        if not hasattr(service, "query_stream"):
            raise RuntimeError("dataService does not implement query_stream")
        root = QueryRequest(context.prepare_query(request.query), _comment=request._comment, _purpose=request._purpose)
        if root.query.aggregates or root.query.group_by_items or root.query.object_group_bys:
            raise ValueError("Entity streams require entity rows; use a record or aggregation query")
        from teaql.runtime.query_stream import execute_typed_stream
        return execute_typed_stream(context, root,
            lambda row: DistributionCenter._teaql_from_record(_entity_root=EntityRoot(), **row), chunk_size)
