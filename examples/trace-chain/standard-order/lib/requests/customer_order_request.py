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
from models.customer_order import CustomerOrder
from typing import Protocol

class QuerySelection(Protocol):
    query: SelectQuery

class CustomerOrderRequest:
    def __init__(self, minimal=False):
        self.query = SelectQuery("CustomerOrder")
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
        return ExecutableCustomerOrderRequest(self)

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
        self.query.project("id", "customer", "status", "order_number", "order_date", "total_amount", "version")
        return self

    def select_id(self):
        self.query.project("id")
        return self



    def select_order_number(self):
        self.query.project("order_number")
        return self

    def select_order_date(self):
        self.query.project("order_date")
        return self

    def select_total_amount(self):
        self.query.project("total_amount")
        return self

    def select_version(self):
        self.query.project("version")
        return self

    def select_customer_with(self, child_request):
        self.query.project("customer")
        self.query.relation_query("customer", child_request.query,
            QueryOperation("relation-select", "select_customer_with", relation="customer"))
        return self
    def select_status_with(self, child_request):
        self.query.project("status")
        self.query.relation_query("status", child_request.query,
            QueryOperation("relation-select", "select_status_with", relation="status"))
        return self
    def with_customer_matching(self, child_request):
        child_request.query.projection = ["id"]
        self.query.and_filter(in_subquery(column("customer"), "Customer", child_request.query))
        return self

    def without_customer_matching(self, child_request):
        child_request.query.projection = ["id"]
        self.query.and_filter(not_in_subquery(column("customer"), "Customer", child_request.query))
        return self

    def have_customer(self):
        self.query.and_filter(is_not_null(column("customer")))
        return self

    def have_no_customer(self):
        self.query.and_filter(is_null(column("customer")))
        return self
    def with_status_matching(self, child_request):
        child_request.query.projection = ["id"]
        self.query.and_filter(in_subquery(column("status"), "OrderStatus", child_request.query))
        return self

    def without_status_matching(self, child_request):
        child_request.query.projection = ["id"]
        self.query.and_filter(not_in_subquery(column("status"), "OrderStatus", child_request.query))
        return self

    def have_status(self):
        self.query.and_filter(is_not_null(column("status")))
        return self

    def have_no_status(self):
        self.query.and_filter(is_null(column("status")))
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

    def filter_by_customer(self, val):
        self.query.and_filter(eq("customer", val))
        return self

    def filter_by_status(self, val):
        self.query.and_filter(eq("status", val))
        return self
    def with_status_is_new(self):
        self.query.and_filter(eq("status", 1001))
        return self
    def with_status_is_paid(self):
        self.query.and_filter(eq("status", 1002))
        return self
    def with_status_is_cancelled(self):
        self.query.and_filter(eq("status", 1003))
        return self

    def with_order_number_containing(self, val: str):
        self.query.and_filter(contain("order_number", val))
        return self

    def with_order_number_not_containing(self, val: str):
        self.query.and_filter(not_contain("order_number", val))
        return self

    def with_order_number_starting_with(self, val: str):
        self.query.and_filter(begin_with("order_number", val))
        return self

    def with_order_number_not_starting_with(self, val: str):
        self.query.and_filter(not_begin_with("order_number", val))
        return self

    def with_order_number_ending_with(self, val: str):
        self.query.and_filter(end_with("order_number", val))
        return self

    def with_order_number_not_ending_with(self, val: str):
        self.query.and_filter(not_end_with("order_number", val))
        return self

    def with_order_number_sounding_like(self, val: str):
        self.query.and_filter(sound_like("order_number", val))
        return self

    def with_order_number_is(self, val: str):
        self.query.and_filter(eq("order_number", val))
        return self
    def with_order_number_is_not(self, val):
        self.query.and_filter(ne("order_number", val))
        return self

    def with_order_number_in(self, *vals):
        self.query.and_filter(in_list("order_number", list(vals)))
        return self

    def with_order_number_not_in(self, *vals):
        self.query.and_filter(not_in_list("order_number", list(vals)))
        return self

    def with_order_number_greater_than(self, val):
        self.query.and_filter(gt("order_number", val))
        return self

    def with_order_number_greater_than_or_equal_to(self, val):
        self.query.and_filter(gte("order_number", val))
        return self

    def with_order_number_less_than(self, val):
        self.query.and_filter(lt("order_number", val))
        return self

    def with_order_number_less_than_or_equal_to(self, val):
        self.query.and_filter(lte("order_number", val))
        return self

    def with_order_number_between(self, lower, upper):
        self.query.and_filter(between(column("order_number"), value(lower), value(upper)))
        return self

    def with_order_number_is_known(self):
        self.query.and_filter(is_not_null(column("order_number")))
        return self

    def with_order_number_is_unknown(self):
        self.query.and_filter(is_null(column("order_number")))
        return self

    def with_order_date_is(self, val):
        self.query.and_filter(eq("order_date", val))
        return self

    def with_order_date_is_not(self, val):
        self.query.and_filter(ne("order_date", val))
        return self

    def with_order_date_in(self, *vals):
        self.query.and_filter(in_list("order_date", list(vals)))
        return self

    def with_order_date_not_in(self, *vals):
        self.query.and_filter(not_in_list("order_date", list(vals)))
        return self

    def with_order_date_greater_than(self, val):
        self.query.and_filter(gt("order_date", val))
        return self

    def with_order_date_greater_than_or_equal_to(self, val):
        self.query.and_filter(gte("order_date", val))
        return self

    def with_order_date_less_than(self, val):
        self.query.and_filter(lt("order_date", val))
        return self

    def with_order_date_less_than_or_equal_to(self, val):
        self.query.and_filter(lte("order_date", val))
        return self

    def with_order_date_between(self, lower, upper):
        self.query.and_filter(between(column("order_date"), value(lower), value(upper)))
        return self

    def with_order_date_is_known(self):
        self.query.and_filter(is_not_null(column("order_date")))
        return self

    def with_order_date_is_unknown(self):
        self.query.and_filter(is_null(column("order_date")))
        return self

    def with_total_amount_is(self, val):
        self.query.and_filter(eq("total_amount", val))
        return self

    def with_total_amount_is_not(self, val):
        self.query.and_filter(ne("total_amount", val))
        return self

    def with_total_amount_in(self, *vals):
        self.query.and_filter(in_list("total_amount", list(vals)))
        return self

    def with_total_amount_not_in(self, *vals):
        self.query.and_filter(not_in_list("total_amount", list(vals)))
        return self

    def with_total_amount_greater_than(self, val):
        self.query.and_filter(gt("total_amount", val))
        return self

    def with_total_amount_greater_than_or_equal_to(self, val):
        self.query.and_filter(gte("total_amount", val))
        return self

    def with_total_amount_less_than(self, val):
        self.query.and_filter(lt("total_amount", val))
        return self

    def with_total_amount_less_than_or_equal_to(self, val):
        self.query.and_filter(lte("total_amount", val))
        return self

    def with_total_amount_between(self, lower, upper):
        self.query.and_filter(between(column("total_amount"), value(lower), value(upper)))
        return self

    def with_total_amount_is_known(self):
        self.query.and_filter(is_not_null(column("total_amount")))
        return self

    def with_total_amount_is_unknown(self):
        self.query.and_filter(is_null(column("total_amount")))
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



    def order_by_order_number_ascending(self):
        self.query.order_by("order_number", "asc")
        return self

    def order_by_order_number_descending(self):
        self.query.order_by("order_number", "desc")
        return self

    def order_by_order_date_ascending(self):
        self.query.order_by("order_date", "asc")
        return self

    def order_by_order_date_descending(self):
        self.query.order_by("order_date", "desc")
        return self

    def order_by_total_amount_ascending(self):
        self.query.order_by("total_amount", "asc")
        return self

    def order_by_total_amount_descending(self):
        self.query.order_by("total_amount", "desc")
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

    def min_total_amount(self):
        return self.min_total_amount_as("minOfTotalAmount")

    def min_total_amount_as(self, ret_name: str):
        self.query.min("total_amount", ret_name)
        return self
    def max_total_amount(self):
        return self.max_total_amount_as("maxOfTotalAmount")

    def max_total_amount_as(self, ret_name: str):
        self.query.max("total_amount", ret_name)
        return self
    def sum_total_amount(self):
        return self.sum_total_amount_as("sumOfTotalAmount")

    def sum_total_amount_as(self, ret_name: str):
        self.query.sum("total_amount", ret_name)
        return self
    def avg_total_amount(self):
        return self.avg_total_amount_as("avgOfTotalAmount")

    def avg_total_amount_as(self, ret_name: str):
        self.query.avg("total_amount", ret_name)
        return self
    def standardDeviation_total_amount(self):
        return self.standardDeviation_total_amount_as("standardDeviationOfTotalAmount")

    def standardDeviation_total_amount_as(self, ret_name: str):
        self.query.standardDeviation("total_amount", ret_name)
        return self
    def squareRootOfPopulationStandardDeviation_total_amount(self):
        return self.squareRootOfPopulationStandardDeviation_total_amount_as("squareRootOfPopulationStandardDeviationOfTotalAmount")

    def squareRootOfPopulationStandardDeviation_total_amount_as(self, ret_name: str):
        self.query.squareRootOfPopulationStandardDeviation("total_amount", ret_name)
        return self
    def sampleVariance_total_amount(self):
        return self.sampleVariance_total_amount_as("sampleVarianceOfTotalAmount")

    def sampleVariance_total_amount_as(self, ret_name: str):
        self.query.sampleVariance("total_amount", ret_name)
        return self
    def samplePopulationVariance_total_amount(self):
        return self.samplePopulationVariance_total_amount_as("samplePopulationVarianceOfTotalAmount")

    def samplePopulationVariance_total_amount_as(self, ret_name: str):
        self.query.samplePopulationVariance("total_amount", ret_name)
        return self
    def group_by_id(self):
        self.query.group_by("id")
        return self

    def group_by_id_as(self, ret_name: str):
        self.query.group_by("id")
        return self
    def group_by_customer(self):
        self.query.group_by("customer")
        return self

    def group_by_customer_as(self, ret_name: str):
        self.query.group_by("customer")
        return self
    def group_by_status(self):
        self.query.group_by("status")
        return self

    def group_by_status_as(self, ret_name: str):
        self.query.group_by("status")
        return self
    def group_by_order_number(self):
        self.query.group_by("order_number")
        return self

    def group_by_order_number_as(self, ret_name: str):
        self.query.group_by("order_number")
        return self
    def group_by_order_date(self):
        self.query.group_by("order_date")
        return self

    def group_by_order_date_as(self, ret_name: str):
        self.query.group_by("order_date")
        return self
    def group_by_total_amount(self):
        self.query.group_by("total_amount")
        return self

    def group_by_total_amount_as(self, ret_name: str):
        self.query.group_by("total_amount")
        return self
    def group_by_version(self):
        self.query.group_by("version")
        return self

    def group_by_version_as(self, ret_name: str):
        self.query.group_by("version")
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
        child_request.query.projection = ["customer_order"]
        self.query.and_filter(in_subquery(column("id"), "OrderItem", child_request.query))
        return self

    def without_order_item_list_matching(self, child_request):
        child_request.query.projection = ["customer_order"]
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
    def min_unit_price_of_order_items(self):
        from requests.order_item_request import OrderItemRequest
        return self.min_unit_price_of_order_items_as(
            "min_unit_price_of_order_items", OrderItemRequest())

    def min_unit_price_of_order_items_as(self, alias: str, child_request):
        query = deepcopy(child_request.query)
        query.aggregates = []
        query.min("unit_price", alias)
        self.query.relation_aggregates.append(
            RelationAggregate("order_item_list", alias, query, True,
                QueryOperation("aggregate", "min_unit_price_of_order_items_as", alias, "order_item_list"))
        )
        return self
    def max_unit_price_of_order_items(self):
        from requests.order_item_request import OrderItemRequest
        return self.max_unit_price_of_order_items_as(
            "max_unit_price_of_order_items", OrderItemRequest())

    def max_unit_price_of_order_items_as(self, alias: str, child_request):
        query = deepcopy(child_request.query)
        query.aggregates = []
        query.max("unit_price", alias)
        self.query.relation_aggregates.append(
            RelationAggregate("order_item_list", alias, query, True,
                QueryOperation("aggregate", "max_unit_price_of_order_items_as", alias, "order_item_list"))
        )
        return self
    def sum_unit_price_of_order_items(self):
        from requests.order_item_request import OrderItemRequest
        return self.sum_unit_price_of_order_items_as(
            "sum_unit_price_of_order_items", OrderItemRequest())

    def sum_unit_price_of_order_items_as(self, alias: str, child_request):
        query = deepcopy(child_request.query)
        query.aggregates = []
        query.sum("unit_price", alias)
        self.query.relation_aggregates.append(
            RelationAggregate("order_item_list", alias, query, True,
                QueryOperation("aggregate", "sum_unit_price_of_order_items_as", alias, "order_item_list"))
        )
        return self
    def avg_unit_price_of_order_items(self):
        from requests.order_item_request import OrderItemRequest
        return self.avg_unit_price_of_order_items_as(
            "avg_unit_price_of_order_items", OrderItemRequest())

    def avg_unit_price_of_order_items_as(self, alias: str, child_request):
        query = deepcopy(child_request.query)
        query.aggregates = []
        query.avg("unit_price", alias)
        self.query.relation_aggregates.append(
            RelationAggregate("order_item_list", alias, query, True,
                QueryOperation("aggregate", "avg_unit_price_of_order_items_as", alias, "order_item_list"))
        )
        return self
    def standardDeviation_unit_price_of_order_items(self):
        from requests.order_item_request import OrderItemRequest
        return self.standardDeviation_unit_price_of_order_items_as(
            "standardDeviation_unit_price_of_order_items", OrderItemRequest())

    def standardDeviation_unit_price_of_order_items_as(self, alias: str, child_request):
        query = deepcopy(child_request.query)
        query.aggregates = []
        query.standardDeviation("unit_price", alias)
        self.query.relation_aggregates.append(
            RelationAggregate("order_item_list", alias, query, True,
                QueryOperation("aggregate", "standardDeviation_unit_price_of_order_items_as", alias, "order_item_list"))
        )
        return self
    def squareRootOfPopulationStandardDeviation_unit_price_of_order_items(self):
        from requests.order_item_request import OrderItemRequest
        return self.squareRootOfPopulationStandardDeviation_unit_price_of_order_items_as(
            "squareRootOfPopulationStandardDeviation_unit_price_of_order_items", OrderItemRequest())

    def squareRootOfPopulationStandardDeviation_unit_price_of_order_items_as(self, alias: str, child_request):
        query = deepcopy(child_request.query)
        query.aggregates = []
        query.squareRootOfPopulationStandardDeviation("unit_price", alias)
        self.query.relation_aggregates.append(
            RelationAggregate("order_item_list", alias, query, True,
                QueryOperation("aggregate", "squareRootOfPopulationStandardDeviation_unit_price_of_order_items_as", alias, "order_item_list"))
        )
        return self
    def sampleVariance_unit_price_of_order_items(self):
        from requests.order_item_request import OrderItemRequest
        return self.sampleVariance_unit_price_of_order_items_as(
            "sampleVariance_unit_price_of_order_items", OrderItemRequest())

    def sampleVariance_unit_price_of_order_items_as(self, alias: str, child_request):
        query = deepcopy(child_request.query)
        query.aggregates = []
        query.sampleVariance("unit_price", alias)
        self.query.relation_aggregates.append(
            RelationAggregate("order_item_list", alias, query, True,
                QueryOperation("aggregate", "sampleVariance_unit_price_of_order_items_as", alias, "order_item_list"))
        )
        return self
    def samplePopulationVariance_unit_price_of_order_items(self):
        from requests.order_item_request import OrderItemRequest
        return self.samplePopulationVariance_unit_price_of_order_items_as(
            "samplePopulationVariance_unit_price_of_order_items", OrderItemRequest())

    def samplePopulationVariance_unit_price_of_order_items_as(self, alias: str, child_request):
        query = deepcopy(child_request.query)
        query.aggregates = []
        query.samplePopulationVariance("unit_price", alias)
        self.query.relation_aggregates.append(
            RelationAggregate("order_item_list", alias, query, True,
                QueryOperation("aggregate", "samplePopulationVariance_unit_price_of_order_items_as", alias, "order_item_list"))
        )
        return self
    def facet_by_customer_as(self, name: str, request: QuerySelection,
                                      include_all_facets: bool = True):
        self.query.facet_by(name, "customer", request.query, include_all_facets,
            QueryOperation("facet", "facet_by_customer_as", name, "customer"))
        return self

    def facet_by_status_as(self, name: str, request: QuerySelection,
                                      include_all_facets: bool = True):
        self.query.facet_by(name, "status", request.query, include_all_facets,
            QueryOperation("facet", "facet_by_status_as", name, "status"))
        return self


class ExecutableCustomerOrderRequest:
    def __init__(self, request):
        self._request = request

    def comment(self, c: str):
        self._request.comment(c)
        return self

    def new_entity(self, context) -> CustomerOrder:
        request = self._request
        if not request._comment or not request._comment.strip() or not request._purpose or not request._purpose.strip():
            raise ValueError("Security audit failure: non-empty comment() and purpose() are required before new_entity()")
        entity = context.initialize_entity("CustomerOrder", CustomerOrder())
        if not isinstance(entity, CustomerOrder):
            raise TypeError("entity initializer returned an incompatible CustomerOrder")
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

    async def execute_for_list(self, context) -> SmartList[CustomerOrder]:
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
            lambda row: CustomerOrder(_entity_root=EntityRoot(), **row),
            count_operation=operation, count_alias=request._page_count_alias)

    async def execute_for_one(self, context):
        request = deepcopy(self._request)
        request.limit(1)
        entities = await ExecutableCustomerOrderRequest(request).execute_for_list(context)
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
            lambda row: CustomerOrder(_entity_root=EntityRoot(), **row), chunk_size)
