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
from models.purchase_order import PurchaseOrder
from typing import Protocol

class QuerySelection(Protocol):
    query: SelectQuery

class PurchaseOrderRequest:
    def __init__(self, minimal=False):
        self.query = SelectQuery("PurchaseOrder")
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
        return ExecutablePurchaseOrderRequest(self)

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
        self.query.project("id", "warehouse", "reference", "version")
        return self

    def select_id(self):
        self.query.project("id")
        return self


    def select_reference(self):
        self.query.project("reference")
        return self

    def select_version(self):
        self.query.project("version")
        return self

    def select_warehouse_with(self, child_request):
        self.query.project("warehouse")
        self.query.relation_query("warehouse", child_request.query,
            QueryOperation("relation-select", "select_warehouse_with", relation="warehouse"))
        return self
    def with_warehouse_matching(self, child_request):
        child_request.query.projection = ["id"]
        self.query.and_filter(in_subquery(column("warehouse"), "Warehouse", child_request.query))
        return self

    def without_warehouse_matching(self, child_request):
        child_request.query.projection = ["id"]
        self.query.and_filter(not_in_subquery(column("warehouse"), "Warehouse", child_request.query))
        return self

    def have_warehouse(self):
        self.query.and_filter(is_not_null(column("warehouse")))
        return self

    def have_no_warehouse(self):
        self.query.and_filter(is_null(column("warehouse")))
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

    def filter_by_warehouse(self, val):
        self.query.and_filter(eq("warehouse", val))
        return self

    def with_reference_containing(self, val: str):
        self.query.and_filter(contain("reference", val))
        return self

    def with_reference_not_containing(self, val: str):
        self.query.and_filter(not_contain("reference", val))
        return self

    def with_reference_starting_with(self, val: str):
        self.query.and_filter(begin_with("reference", val))
        return self

    def with_reference_not_starting_with(self, val: str):
        self.query.and_filter(not_begin_with("reference", val))
        return self

    def with_reference_ending_with(self, val: str):
        self.query.and_filter(end_with("reference", val))
        return self

    def with_reference_not_ending_with(self, val: str):
        self.query.and_filter(not_end_with("reference", val))
        return self

    def with_reference_sounding_like(self, val: str):
        self.query.and_filter(sound_like("reference", val))
        return self

    def with_reference_is(self, val: str):
        self.query.and_filter(eq("reference", val))
        return self
    def with_reference_is_not(self, val):
        self.query.and_filter(ne("reference", val))
        return self

    def with_reference_in(self, *vals):
        self.query.and_filter(in_list("reference", list(vals)))
        return self

    def with_reference_not_in(self, *vals):
        self.query.and_filter(not_in_list("reference", list(vals)))
        return self

    def with_reference_greater_than(self, val):
        self.query.and_filter(gt("reference", val))
        return self

    def with_reference_greater_than_or_equal_to(self, val):
        self.query.and_filter(gte("reference", val))
        return self

    def with_reference_less_than(self, val):
        self.query.and_filter(lt("reference", val))
        return self

    def with_reference_less_than_or_equal_to(self, val):
        self.query.and_filter(lte("reference", val))
        return self

    def with_reference_between(self, lower, upper):
        self.query.and_filter(between(column("reference"), value(lower), value(upper)))
        return self

    def with_reference_is_known(self):
        self.query.and_filter(is_not_null(column("reference")))
        return self

    def with_reference_is_unknown(self):
        self.query.and_filter(is_null(column("reference")))
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


    def order_by_reference_ascending(self):
        self.query.order_by("reference", "asc")
        return self

    def order_by_reference_descending(self):
        self.query.order_by("reference", "desc")
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
    def group_by_warehouse(self):
        self.query.group_by("warehouse")
        return self

    def group_by_warehouse_as(self, ret_name: str):
        self.query.group_by("warehouse")
        self.query.project_expr(ret_name, column("warehouse"))
        return self
    def group_by_reference(self):
        self.query.group_by("reference")
        return self

    def group_by_reference_as(self, ret_name: str):
        self.query.group_by("reference")
        self.query.project_expr(ret_name, column("reference"))
        return self
    def group_by_version(self):
        self.query.group_by("version")
        return self

    def group_by_version_as(self, ret_name: str):
        self.query.group_by("version")
        self.query.project_expr(ret_name, column("version"))
        return self
    def select_order_item_list(self):
        from requests.order_item_request import OrderItemRequest
        return self.select_order_item_list_with(OrderItemRequest())

    def select_order_item_list_with(self, child_request):
        self.query.relation_query("order_item_list", child_request.query,
            QueryOperation("relation-select", "select_order_item_list_with", relation="order_item_list"))
        return self
    def have_order_items(self):
        from requests.order_item_request import OrderItemRequest
        return self.with_order_item_list_matching(OrderItemRequest())

    def have_no_order_items(self):
        from requests.order_item_request import OrderItemRequest
        return self.without_order_item_list_matching(OrderItemRequest())

    def with_order_item_list_matching(self, child_request):
        child_request.query.projection = ["purchase_order"]
        self.query.and_filter(in_subquery(column("id"), "OrderItem", child_request.query))
        return self

    def without_order_item_list_matching(self, child_request):
        child_request.query.projection = ["purchase_order"]
        self.query.and_filter(not_in_subquery(column("id"), "OrderItem", child_request.query))
        return self
    def count_order_items(self):
        return self.count_order_items_as("count_order_items")

    def count_order_items_as(self, alias: str):
        from requests.order_item_request import OrderItemRequest
        self.count_order_items_with(alias, OrderItemRequest())
        self.query.relation_aggregates[-1].operation = QueryOperation(
            "relation-count", "count_order_items_as", alias, "order_item_list")
        return self

    def count_order_items_with(self, alias: str, child_request):
        query = deepcopy(child_request.query)
        query.aggregates = []
        query.count_field("id", alias)
        self.query.relation_aggregates.append(
            RelationAggregate("order_item_list", alias, query, True,
                QueryOperation("relation-count", "count_order_items_with", alias, "order_item_list"))
        )
        return self

    def min_quantity_of_order_items(self):
        from requests.order_item_request import OrderItemRequest
        return self.min_quantity_of_order_items_as(
            "min_quantity_of_order_items", OrderItemRequest())

    def min_quantity_of_order_items_as(self, alias: str, child_request):
        query = deepcopy(child_request.query)
        query.aggregates = []
        query.min("quantity", alias)
        self.query.relation_aggregates.append(
            RelationAggregate("order_item_list", alias, query, True,
                QueryOperation("aggregate", "min_quantity_of_order_items_as", alias, "order_item_list"))
        )
        return self
    def max_quantity_of_order_items(self):
        from requests.order_item_request import OrderItemRequest
        return self.max_quantity_of_order_items_as(
            "max_quantity_of_order_items", OrderItemRequest())

    def max_quantity_of_order_items_as(self, alias: str, child_request):
        query = deepcopy(child_request.query)
        query.aggregates = []
        query.max("quantity", alias)
        self.query.relation_aggregates.append(
            RelationAggregate("order_item_list", alias, query, True,
                QueryOperation("aggregate", "max_quantity_of_order_items_as", alias, "order_item_list"))
        )
        return self
    def sum_quantity_of_order_items(self):
        from requests.order_item_request import OrderItemRequest
        return self.sum_quantity_of_order_items_as(
            "sum_quantity_of_order_items", OrderItemRequest())

    def sum_quantity_of_order_items_as(self, alias: str, child_request):
        query = deepcopy(child_request.query)
        query.aggregates = []
        query.sum("quantity", alias)
        self.query.relation_aggregates.append(
            RelationAggregate("order_item_list", alias, query, True,
                QueryOperation("aggregate", "sum_quantity_of_order_items_as", alias, "order_item_list"))
        )
        return self
    def avg_quantity_of_order_items(self):
        from requests.order_item_request import OrderItemRequest
        return self.avg_quantity_of_order_items_as(
            "avg_quantity_of_order_items", OrderItemRequest())

    def avg_quantity_of_order_items_as(self, alias: str, child_request):
        query = deepcopy(child_request.query)
        query.aggregates = []
        query.avg("quantity", alias)
        self.query.relation_aggregates.append(
            RelationAggregate("order_item_list", alias, query, True,
                QueryOperation("aggregate", "avg_quantity_of_order_items_as", alias, "order_item_list"))
        )
        return self
    def standardDeviation_quantity_of_order_items(self):
        from requests.order_item_request import OrderItemRequest
        return self.standardDeviation_quantity_of_order_items_as(
            "standardDeviation_quantity_of_order_items", OrderItemRequest())

    def standardDeviation_quantity_of_order_items_as(self, alias: str, child_request):
        query = deepcopy(child_request.query)
        query.aggregates = []
        query.standardDeviation("quantity", alias)
        self.query.relation_aggregates.append(
            RelationAggregate("order_item_list", alias, query, True,
                QueryOperation("aggregate", "standardDeviation_quantity_of_order_items_as", alias, "order_item_list"))
        )
        return self
    def squareRootOfPopulationStandardDeviation_quantity_of_order_items(self):
        from requests.order_item_request import OrderItemRequest
        return self.squareRootOfPopulationStandardDeviation_quantity_of_order_items_as(
            "squareRootOfPopulationStandardDeviation_quantity_of_order_items", OrderItemRequest())

    def squareRootOfPopulationStandardDeviation_quantity_of_order_items_as(self, alias: str, child_request):
        query = deepcopy(child_request.query)
        query.aggregates = []
        query.squareRootOfPopulationStandardDeviation("quantity", alias)
        self.query.relation_aggregates.append(
            RelationAggregate("order_item_list", alias, query, True,
                QueryOperation("aggregate", "squareRootOfPopulationStandardDeviation_quantity_of_order_items_as", alias, "order_item_list"))
        )
        return self
    def sampleVariance_quantity_of_order_items(self):
        from requests.order_item_request import OrderItemRequest
        return self.sampleVariance_quantity_of_order_items_as(
            "sampleVariance_quantity_of_order_items", OrderItemRequest())

    def sampleVariance_quantity_of_order_items_as(self, alias: str, child_request):
        query = deepcopy(child_request.query)
        query.aggregates = []
        query.sampleVariance("quantity", alias)
        self.query.relation_aggregates.append(
            RelationAggregate("order_item_list", alias, query, True,
                QueryOperation("aggregate", "sampleVariance_quantity_of_order_items_as", alias, "order_item_list"))
        )
        return self
    def samplePopulationVariance_quantity_of_order_items(self):
        from requests.order_item_request import OrderItemRequest
        return self.samplePopulationVariance_quantity_of_order_items_as(
            "samplePopulationVariance_quantity_of_order_items", OrderItemRequest())

    def samplePopulationVariance_quantity_of_order_items_as(self, alias: str, child_request):
        query = deepcopy(child_request.query)
        query.aggregates = []
        query.samplePopulationVariance("quantity", alias)
        self.query.relation_aggregates.append(
            RelationAggregate("order_item_list", alias, query, True,
                QueryOperation("aggregate", "samplePopulationVariance_quantity_of_order_items_as", alias, "order_item_list"))
        )
        return self
    def facet_by_warehouse_as(self, name: str, request: QuerySelection,
                                      include_all_facets: bool = True):
        self.query.facet_by(name, "warehouse", request.query, include_all_facets,
            QueryOperation("facet", "facet_by_warehouse_as", name, "warehouse"))
        return self


class ExecutablePurchaseOrderRequest:
    def __init__(self, request):
        self._request = request

    def comment(self, c: str):
        self._request.comment(c)
        return self

    async def new_entity(self, context) -> PurchaseOrder:
        request = self._request
        QueryIntent(request._comment, request._purpose)
        identity = await context.next_id("PurchaseOrder")
        entity = context.initialize_entity("PurchaseOrder", PurchaseOrder._teaql_from_reserved_id(identity))
        if not isinstance(entity, PurchaseOrder):
            raise TypeError("entity initializer returned an incompatible PurchaseOrder")
        return entity

    async def execute_for_result(self, context):
        self = self._request
        req = QueryRequest(self.query, _comment=self._comment, _purpose=self._purpose)
        req = context.prepare_query_request(req)
        service = context.require_resource("dataService")
        return await service.query(context, req)

    async def execute_for_rows(self, context):
        return (await self.execute_for_result(context)).rows

    async def execute_for_list(self, context) -> SmartList[PurchaseOrder]:
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
            lambda row: PurchaseOrder._teaql_from_record(_entity_root=EntityRoot(), **row),
            count_operation=operation, count_alias=request._page_count_alias)

    async def execute_for_one(self, context):
        request = deepcopy(self._request)
        request.limit(1)
        entities = await ExecutablePurchaseOrderRequest(request).execute_for_list(context)
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
            lambda row: PurchaseOrder._teaql_from_record(_entity_root=EntityRoot(), **row), chunk_size)
