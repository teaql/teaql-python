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
from models.order_item import OrderItem
from typing import Protocol

class QuerySelection(Protocol):
    query: SelectQuery

class OrderItemRequest:
    def __init__(self, minimal=False):
        self.query = SelectQuery("OrderItem")
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
        return ExecutableOrderItemRequest(self)

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
        self.query.project("id", "customer_order", "product_name", "quantity", "unit_price", "version")
        return self

    def select_id(self):
        self.query.project("id")
        return self


    def select_product_name(self):
        self.query.project("product_name")
        return self

    def select_quantity(self):
        self.query.project("quantity")
        return self

    def select_unit_price(self):
        self.query.project("unit_price")
        return self

    def select_version(self):
        self.query.project("version")
        return self

    def select_customer_order_with(self, child_request):
        self.query.project("customer_order")
        self.query.relation_query("customer_order", child_request.query,
            QueryOperation("relation-select", "select_customer_order_with", relation="customer_order"))
        return self
    def with_customer_order_matching(self, child_request):
        child_request.query.projection = ["id"]
        self.query.and_filter(in_subquery(column("customer_order"), "CustomerOrder", child_request.query))
        return self

    def without_customer_order_matching(self, child_request):
        child_request.query.projection = ["id"]
        self.query.and_filter(not_in_subquery(column("customer_order"), "CustomerOrder", child_request.query))
        return self

    def have_customer_order(self):
        self.query.and_filter(is_not_null(column("customer_order")))
        return self

    def have_no_customer_order(self):
        self.query.and_filter(is_null(column("customer_order")))
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

    def filter_by_customer_order(self, val):
        self.query.and_filter(eq("customer_order", val))
        return self

    def with_product_name_containing(self, val: str):
        self.query.and_filter(contain("product_name", val))
        return self

    def with_product_name_not_containing(self, val: str):
        self.query.and_filter(not_contain("product_name", val))
        return self

    def with_product_name_starting_with(self, val: str):
        self.query.and_filter(begin_with("product_name", val))
        return self

    def with_product_name_not_starting_with(self, val: str):
        self.query.and_filter(not_begin_with("product_name", val))
        return self

    def with_product_name_ending_with(self, val: str):
        self.query.and_filter(end_with("product_name", val))
        return self

    def with_product_name_not_ending_with(self, val: str):
        self.query.and_filter(not_end_with("product_name", val))
        return self

    def with_product_name_sounding_like(self, val: str):
        self.query.and_filter(sound_like("product_name", val))
        return self

    def with_product_name_is(self, val: str):
        self.query.and_filter(eq("product_name", val))
        return self
    def with_product_name_is_not(self, val):
        self.query.and_filter(ne("product_name", val))
        return self

    def with_product_name_in(self, *vals):
        self.query.and_filter(in_list("product_name", list(vals)))
        return self

    def with_product_name_not_in(self, *vals):
        self.query.and_filter(not_in_list("product_name", list(vals)))
        return self

    def with_product_name_greater_than(self, val):
        self.query.and_filter(gt("product_name", val))
        return self

    def with_product_name_greater_than_or_equal_to(self, val):
        self.query.and_filter(gte("product_name", val))
        return self

    def with_product_name_less_than(self, val):
        self.query.and_filter(lt("product_name", val))
        return self

    def with_product_name_less_than_or_equal_to(self, val):
        self.query.and_filter(lte("product_name", val))
        return self

    def with_product_name_between(self, lower, upper):
        self.query.and_filter(between(column("product_name"), value(lower), value(upper)))
        return self

    def with_product_name_is_known(self):
        self.query.and_filter(is_not_null(column("product_name")))
        return self

    def with_product_name_is_unknown(self):
        self.query.and_filter(is_null(column("product_name")))
        return self

    def with_quantity_is(self, val):
        self.query.and_filter(eq("quantity", val))
        return self

    def with_quantity_is_not(self, val):
        self.query.and_filter(ne("quantity", val))
        return self

    def with_quantity_in(self, *vals):
        self.query.and_filter(in_list("quantity", list(vals)))
        return self

    def with_quantity_not_in(self, *vals):
        self.query.and_filter(not_in_list("quantity", list(vals)))
        return self

    def with_quantity_greater_than(self, val):
        self.query.and_filter(gt("quantity", val))
        return self

    def with_quantity_greater_than_or_equal_to(self, val):
        self.query.and_filter(gte("quantity", val))
        return self

    def with_quantity_less_than(self, val):
        self.query.and_filter(lt("quantity", val))
        return self

    def with_quantity_less_than_or_equal_to(self, val):
        self.query.and_filter(lte("quantity", val))
        return self

    def with_quantity_between(self, lower, upper):
        self.query.and_filter(between(column("quantity"), value(lower), value(upper)))
        return self

    def with_quantity_is_known(self):
        self.query.and_filter(is_not_null(column("quantity")))
        return self

    def with_quantity_is_unknown(self):
        self.query.and_filter(is_null(column("quantity")))
        return self

    def with_unit_price_is(self, val):
        self.query.and_filter(eq("unit_price", val))
        return self

    def with_unit_price_is_not(self, val):
        self.query.and_filter(ne("unit_price", val))
        return self

    def with_unit_price_in(self, *vals):
        self.query.and_filter(in_list("unit_price", list(vals)))
        return self

    def with_unit_price_not_in(self, *vals):
        self.query.and_filter(not_in_list("unit_price", list(vals)))
        return self

    def with_unit_price_greater_than(self, val):
        self.query.and_filter(gt("unit_price", val))
        return self

    def with_unit_price_greater_than_or_equal_to(self, val):
        self.query.and_filter(gte("unit_price", val))
        return self

    def with_unit_price_less_than(self, val):
        self.query.and_filter(lt("unit_price", val))
        return self

    def with_unit_price_less_than_or_equal_to(self, val):
        self.query.and_filter(lte("unit_price", val))
        return self

    def with_unit_price_between(self, lower, upper):
        self.query.and_filter(between(column("unit_price"), value(lower), value(upper)))
        return self

    def with_unit_price_is_known(self):
        self.query.and_filter(is_not_null(column("unit_price")))
        return self

    def with_unit_price_is_unknown(self):
        self.query.and_filter(is_null(column("unit_price")))
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


    def order_by_product_name_ascending(self):
        self.query.order_by("product_name", "asc")
        return self

    def order_by_product_name_descending(self):
        self.query.order_by("product_name", "desc")
        return self

    def order_by_quantity_ascending(self):
        self.query.order_by("quantity", "asc")
        return self

    def order_by_quantity_descending(self):
        self.query.order_by("quantity", "desc")
        return self

    def order_by_unit_price_ascending(self):
        self.query.order_by("unit_price", "asc")
        return self

    def order_by_unit_price_descending(self):
        self.query.order_by("unit_price", "desc")
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

    def min_quantity(self):
        return self.min_quantity_as("minOfQuantity")

    def min_quantity_as(self, ret_name: str):
        self.query.min("quantity", ret_name)
        return self
    def max_quantity(self):
        return self.max_quantity_as("maxOfQuantity")

    def max_quantity_as(self, ret_name: str):
        self.query.max("quantity", ret_name)
        return self
    def sum_quantity(self):
        return self.sum_quantity_as("sumOfQuantity")

    def sum_quantity_as(self, ret_name: str):
        self.query.sum("quantity", ret_name)
        return self
    def avg_quantity(self):
        return self.avg_quantity_as("avgOfQuantity")

    def avg_quantity_as(self, ret_name: str):
        self.query.avg("quantity", ret_name)
        return self
    def standardDeviation_quantity(self):
        return self.standardDeviation_quantity_as("standardDeviationOfQuantity")

    def standardDeviation_quantity_as(self, ret_name: str):
        self.query.standardDeviation("quantity", ret_name)
        return self
    def squareRootOfPopulationStandardDeviation_quantity(self):
        return self.squareRootOfPopulationStandardDeviation_quantity_as("squareRootOfPopulationStandardDeviationOfQuantity")

    def squareRootOfPopulationStandardDeviation_quantity_as(self, ret_name: str):
        self.query.squareRootOfPopulationStandardDeviation("quantity", ret_name)
        return self
    def sampleVariance_quantity(self):
        return self.sampleVariance_quantity_as("sampleVarianceOfQuantity")

    def sampleVariance_quantity_as(self, ret_name: str):
        self.query.sampleVariance("quantity", ret_name)
        return self
    def samplePopulationVariance_quantity(self):
        return self.samplePopulationVariance_quantity_as("samplePopulationVarianceOfQuantity")

    def samplePopulationVariance_quantity_as(self, ret_name: str):
        self.query.samplePopulationVariance("quantity", ret_name)
        return self
    def min_unit_price(self):
        return self.min_unit_price_as("minOfUnitPrice")

    def min_unit_price_as(self, ret_name: str):
        self.query.min("unit_price", ret_name)
        return self
    def max_unit_price(self):
        return self.max_unit_price_as("maxOfUnitPrice")

    def max_unit_price_as(self, ret_name: str):
        self.query.max("unit_price", ret_name)
        return self
    def sum_unit_price(self):
        return self.sum_unit_price_as("sumOfUnitPrice")

    def sum_unit_price_as(self, ret_name: str):
        self.query.sum("unit_price", ret_name)
        return self
    def avg_unit_price(self):
        return self.avg_unit_price_as("avgOfUnitPrice")

    def avg_unit_price_as(self, ret_name: str):
        self.query.avg("unit_price", ret_name)
        return self
    def standardDeviation_unit_price(self):
        return self.standardDeviation_unit_price_as("standardDeviationOfUnitPrice")

    def standardDeviation_unit_price_as(self, ret_name: str):
        self.query.standardDeviation("unit_price", ret_name)
        return self
    def squareRootOfPopulationStandardDeviation_unit_price(self):
        return self.squareRootOfPopulationStandardDeviation_unit_price_as("squareRootOfPopulationStandardDeviationOfUnitPrice")

    def squareRootOfPopulationStandardDeviation_unit_price_as(self, ret_name: str):
        self.query.squareRootOfPopulationStandardDeviation("unit_price", ret_name)
        return self
    def sampleVariance_unit_price(self):
        return self.sampleVariance_unit_price_as("sampleVarianceOfUnitPrice")

    def sampleVariance_unit_price_as(self, ret_name: str):
        self.query.sampleVariance("unit_price", ret_name)
        return self
    def samplePopulationVariance_unit_price(self):
        return self.samplePopulationVariance_unit_price_as("samplePopulationVarianceOfUnitPrice")

    def samplePopulationVariance_unit_price_as(self, ret_name: str):
        self.query.samplePopulationVariance("unit_price", ret_name)
        return self
    def group_by_id(self):
        self.query.group_by("id")
        return self

    def group_by_id_as(self, ret_name: str):
        self.query.group_by("id")
        return self
    def group_by_customer_order(self):
        self.query.group_by("customer_order")
        return self

    def group_by_customer_order_as(self, ret_name: str):
        self.query.group_by("customer_order")
        return self
    def group_by_product_name(self):
        self.query.group_by("product_name")
        return self

    def group_by_product_name_as(self, ret_name: str):
        self.query.group_by("product_name")
        return self
    def group_by_quantity(self):
        self.query.group_by("quantity")
        return self

    def group_by_quantity_as(self, ret_name: str):
        self.query.group_by("quantity")
        return self
    def group_by_unit_price(self):
        self.query.group_by("unit_price")
        return self

    def group_by_unit_price_as(self, ret_name: str):
        self.query.group_by("unit_price")
        return self
    def group_by_version(self):
        self.query.group_by("version")
        return self

    def group_by_version_as(self, ret_name: str):
        self.query.group_by("version")
        return self
    def facet_by_customer_order_as(self, name: str, request: QuerySelection,
                                      include_all_facets: bool = True):
        self.query.facet_by(name, "customer_order", request.query, include_all_facets,
            QueryOperation("facet", "facet_by_customer_order_as", name, "customer_order"))
        return self


class ExecutableOrderItemRequest:
    def __init__(self, request):
        self._request = request

    def comment(self, c: str):
        self._request.comment(c)
        return self

    def new_entity(self, context) -> OrderItem:
        request = self._request
        if not request._comment or not request._comment.strip() or not request._purpose or not request._purpose.strip():
            raise ValueError("Security audit failure: non-empty comment() and purpose() are required before new_entity()")
        entity = context.initialize_entity("OrderItem", OrderItem())
        if not isinstance(entity, OrderItem):
            raise TypeError("entity initializer returned an incompatible OrderItem")
        return entity

    async def execute_for_result(self, context):
        self = self._request
        if not self._purpose or not self._purpose.strip() or not self._comment or not self._comment.strip():
            raise Exception("Security audit failure: comment() and purpose() must be called before execute_for_rows()")
        service = context.require_resource("dataService")
        req = QueryRequest(context.prepare_query(self.query), _comment=self._comment, _purpose=self._purpose)
        return await service.query(context, req)

    async def execute_for_rows(self, context):
        return (await self.execute_for_result(context)).rows

    async def execute_for_list(self, context) -> SmartList[OrderItem]:
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
            lambda row: OrderItem(_entity_root=EntityRoot(), **row),
            count_operation=operation, count_alias=request._page_count_alias)

    async def execute_for_one(self, context):
        request = deepcopy(self._request)
        request.limit(1)
        entities = await ExecutableOrderItemRequest(request).execute_for_list(context)
        return entities[0] if entities else None

    def execute_for_stream(self, context, chunk_size: int = 1000):
        """Yield entity chunks lazily from the provider cursor."""
        request = deepcopy(self._request)
        QueryIntent(request._comment, request._purpose)
        service = context.require_resource("dataService")
        if not hasattr(service, "query_stream"):
            raise RuntimeError("dataService does not implement query_stream")
        root = QueryRequest(context.prepare_query(request.query), _comment=request._comment, _purpose=request._purpose)
        from teaql.runtime.query_stream import execute_typed_stream
        return execute_typed_stream(context, root,
            lambda row: OrderItem(_entity_root=EntityRoot(), **row), chunk_size)
