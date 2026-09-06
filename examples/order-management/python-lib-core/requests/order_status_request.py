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
from models.order_status import OrderStatus
from typing import Protocol

class QuerySelection(Protocol):
    query: SelectQuery

class OrderStatusRequest:
    def __init__(self, minimal=False):
        self.query = SelectQuery("OrderStatus")
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
        return ExecutableOrderStatusRequest(self)

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
        self.query.project("id", "name", "code", "color", "display_order", "commerce_platform", "version")
        return self

    def select_id(self):
        self.query.project("id")
        return self

    def select_name(self):
        self.query.project("name")
        return self

    def select_code(self):
        self.query.project("code")
        return self

    def select_color(self):
        self.query.project("color")
        return self

    def select_display_order(self):
        self.query.project("display_order")
        return self


    def select_version(self):
        self.query.project("version")
        return self

    def select_commerce_platform_with(self, child_request):
        self.query.project("commerce_platform")
        self.query.relation_query("commerce_platform", child_request.query)
        return self
    def with_commerce_platform_matching(self, child_request):
        child_request.query._projection = ["id"]
        self.query.and_filter(in_subquery(column("commerce_platform"), "CommercePlatform", child_request.query))
        return self

    def without_commerce_platform_matching(self, child_request):
        child_request.query._projection = ["id"]
        self.query.and_filter(not_in_subquery(column("commerce_platform"), "CommercePlatform", child_request.query))
        return self

    def have_commerce_platform(self):
        self.query.and_filter(is_not_null(column("commerce_platform")))
        return self

    def have_no_commerce_platform(self):
        self.query.and_filter(is_null(column("commerce_platform")))
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

    def with_code_containing(self, val: str):
        self.query.and_filter(contain("code", val))
        return self

    def with_code_not_containing(self, val: str):
        self.query.and_filter(not_contain("code", val))
        return self

    def with_code_starting_with(self, val: str):
        self.query.and_filter(begin_with("code", val))
        return self

    def with_code_not_starting_with(self, val: str):
        self.query.and_filter(not_begin_with("code", val))
        return self

    def with_code_ending_with(self, val: str):
        self.query.and_filter(end_with("code", val))
        return self

    def with_code_not_ending_with(self, val: str):
        self.query.and_filter(not_end_with("code", val))
        return self

    def with_code_sounding_like(self, val: str):
        self.query.and_filter(sound_like("code", val))
        return self

    def with_code_is(self, val: str):
        self.query.and_filter(eq("code", val))
        return self
    def with_code_is_not(self, val):
        self.query.and_filter(ne("code", val))
        return self

    def with_code_in(self, *vals):
        self.query.and_filter(in_list("code", list(vals)))
        return self

    def with_code_not_in(self, *vals):
        self.query.and_filter(not_in_list("code", list(vals)))
        return self

    def with_code_greater_than(self, val):
        self.query.and_filter(gt("code", val))
        return self

    def with_code_greater_than_or_equal_to(self, val):
        self.query.and_filter(gte("code", val))
        return self

    def with_code_less_than(self, val):
        self.query.and_filter(lt("code", val))
        return self

    def with_code_less_than_or_equal_to(self, val):
        self.query.and_filter(lte("code", val))
        return self

    def with_code_between(self, lower, upper):
        self.query.and_filter(between(column("code"), value(lower), value(upper)))
        return self

    def with_code_is_known(self):
        self.query.and_filter(is_not_null(column("code")))
        return self

    def with_code_is_unknown(self):
        self.query.and_filter(is_null(column("code")))
        return self

    def with_color_containing(self, val: str):
        self.query.and_filter(contain("color", val))
        return self

    def with_color_not_containing(self, val: str):
        self.query.and_filter(not_contain("color", val))
        return self

    def with_color_starting_with(self, val: str):
        self.query.and_filter(begin_with("color", val))
        return self

    def with_color_not_starting_with(self, val: str):
        self.query.and_filter(not_begin_with("color", val))
        return self

    def with_color_ending_with(self, val: str):
        self.query.and_filter(end_with("color", val))
        return self

    def with_color_not_ending_with(self, val: str):
        self.query.and_filter(not_end_with("color", val))
        return self

    def with_color_sounding_like(self, val: str):
        self.query.and_filter(sound_like("color", val))
        return self

    def with_color_is(self, val: str):
        self.query.and_filter(eq("color", val))
        return self
    def with_color_is_not(self, val):
        self.query.and_filter(ne("color", val))
        return self

    def with_color_in(self, *vals):
        self.query.and_filter(in_list("color", list(vals)))
        return self

    def with_color_not_in(self, *vals):
        self.query.and_filter(not_in_list("color", list(vals)))
        return self

    def with_color_greater_than(self, val):
        self.query.and_filter(gt("color", val))
        return self

    def with_color_greater_than_or_equal_to(self, val):
        self.query.and_filter(gte("color", val))
        return self

    def with_color_less_than(self, val):
        self.query.and_filter(lt("color", val))
        return self

    def with_color_less_than_or_equal_to(self, val):
        self.query.and_filter(lte("color", val))
        return self

    def with_color_between(self, lower, upper):
        self.query.and_filter(between(column("color"), value(lower), value(upper)))
        return self

    def with_color_is_known(self):
        self.query.and_filter(is_not_null(column("color")))
        return self

    def with_color_is_unknown(self):
        self.query.and_filter(is_null(column("color")))
        return self

    def with_display_order_is(self, val):
        self.query.and_filter(eq("display_order", val))
        return self

    def with_display_order_is_not(self, val):
        self.query.and_filter(ne("display_order", val))
        return self

    def with_display_order_in(self, *vals):
        self.query.and_filter(in_list("display_order", list(vals)))
        return self

    def with_display_order_not_in(self, *vals):
        self.query.and_filter(not_in_list("display_order", list(vals)))
        return self

    def with_display_order_greater_than(self, val):
        self.query.and_filter(gt("display_order", val))
        return self

    def with_display_order_greater_than_or_equal_to(self, val):
        self.query.and_filter(gte("display_order", val))
        return self

    def with_display_order_less_than(self, val):
        self.query.and_filter(lt("display_order", val))
        return self

    def with_display_order_less_than_or_equal_to(self, val):
        self.query.and_filter(lte("display_order", val))
        return self

    def with_display_order_between(self, lower, upper):
        self.query.and_filter(between(column("display_order"), value(lower), value(upper)))
        return self

    def with_display_order_is_known(self):
        self.query.and_filter(is_not_null(column("display_order")))
        return self

    def with_display_order_is_unknown(self):
        self.query.and_filter(is_null(column("display_order")))
        return self

    def filter_by_commerce_platform(self, val):
        self.query.and_filter(eq("commerce_platform", val))
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

    def order_by_code_ascending(self):
        self.query.order_by("code", "asc")
        return self

    def order_by_code_descending(self):
        self.query.order_by("code", "desc")
        return self

    def order_by_color_ascending(self):
        self.query.order_by("color", "asc")
        return self

    def order_by_color_descending(self):
        self.query.order_by("color", "desc")
        return self

    def order_by_display_order_ascending(self):
        self.query.order_by("display_order", "asc")
        return self

    def order_by_display_order_descending(self):
        self.query.order_by("display_order", "desc")
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

    def min_display_order(self):
        return self.min_display_order_as("minOfDisplayOrder")

    def min_display_order_as(self, ret_name: str):
        self.query.aggregate("min", "display_order", ret_name)
        return self
    def max_display_order(self):
        return self.max_display_order_as("maxOfDisplayOrder")

    def max_display_order_as(self, ret_name: str):
        self.query.aggregate("max", "display_order", ret_name)
        return self
    def sum_display_order(self):
        return self.sum_display_order_as("sumOfDisplayOrder")

    def sum_display_order_as(self, ret_name: str):
        self.query.aggregate("sum", "display_order", ret_name)
        return self
    def avg_display_order(self):
        return self.avg_display_order_as("avgOfDisplayOrder")

    def avg_display_order_as(self, ret_name: str):
        self.query.aggregate("avg", "display_order", ret_name)
        return self
    def standardDeviation_display_order(self):
        return self.standardDeviation_display_order_as("standardDeviationOfDisplayOrder")

    def standardDeviation_display_order_as(self, ret_name: str):
        self.query.aggregate("stddev", "display_order", ret_name)
        return self
    def squareRootOfPopulationStandardDeviation_display_order(self):
        return self.squareRootOfPopulationStandardDeviation_display_order_as("squareRootOfPopulationStandardDeviationOfDisplayOrder")

    def squareRootOfPopulationStandardDeviation_display_order_as(self, ret_name: str):
        self.query.aggregate("stddev_pop", "display_order", ret_name)
        return self
    def sampleVariance_display_order(self):
        return self.sampleVariance_display_order_as("sampleVarianceOfDisplayOrder")

    def sampleVariance_display_order_as(self, ret_name: str):
        self.query.aggregate("var_samp", "display_order", ret_name)
        return self
    def samplePopulationVariance_display_order(self):
        return self.samplePopulationVariance_display_order_as("samplePopulationVarianceOfDisplayOrder")

    def samplePopulationVariance_display_order_as(self, ret_name: str):
        self.query.aggregate("var_pop", "display_order", ret_name)
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
    def group_by_code(self):
        self.query.group_by("code")
        return self

    def group_by_code_as(self, ret_name: str):
        self.query.group_by("code") 
        return self
    def group_by_color(self):
        self.query.group_by("color")
        return self

    def group_by_color_as(self, ret_name: str):
        self.query.group_by("color") 
        return self
    def group_by_display_order(self):
        self.query.group_by("display_order")
        return self

    def group_by_display_order_as(self, ret_name: str):
        self.query.group_by("display_order") 
        return self
    def group_by_commerce_platform(self):
        self.query.group_by("commerce_platform")
        return self

    def group_by_commerce_platform_as(self, ret_name: str):
        self.query.group_by("commerce_platform") 
        return self
    def group_by_version(self):
        self.query.group_by("version")
        return self

    def group_by_version_as(self, ret_name: str):
        self.query.group_by("version") 
        return self
    def select_customer_order_list(self):
        from requests.customer_order_request import CustomerOrderRequest
        return self.select_customer_order_list_with(CustomerOrderRequest())

    def select_customer_order_list_with(self, child_request):
        self.query.relation_query("customer_order_list", child_request.query)
        return self
    def have_customer_orders(self):
        from requests.customer_order_request import CustomerOrderRequest
        return self.with_customer_order_list_matching(CustomerOrderRequest())

    def have_no_customer_orders(self):
        from requests.customer_order_request import CustomerOrderRequest
        return self.without_customer_order_list_matching(CustomerOrderRequest())

    def with_customer_order_list_matching(self, child_request):
        self.query.and_filter(in_subquery(column("id"), "CustomerOrder", child_request.query))
        child_request.query._projection = ["status"]
        return self

    def without_customer_order_list_matching(self, child_request):
        self.query.and_filter(not_in_subquery(column("id"), "CustomerOrder", child_request.query))
        child_request.query._projection = ["status"]
        return self
    def count_customer_orders(self):
        return self.count_customer_orders_as("count_customer_orders")

    def count_customer_orders_as(self, alias: str):
        from requests.customer_order_request import CustomerOrderRequest
        return self.count_customer_orders_with(alias, CustomerOrderRequest())

    def count_customer_orders_with(self, alias: str, child_request):
        child_request.query.count_field("id", alias)
        self.query.relation_aggregate("customer_order_list", alias, child_request.query, True)
        return self

    def min_total_amount_of_customer_orders(self):
        from requests.customer_order_request import CustomerOrderRequest
        return self.min_total_amount_of_customer_orders_as(
            "min_total_amount_of_customer_orders", CustomerOrderRequest())

    def min_total_amount_of_customer_orders_as(self, alias: str, child_request):
        child_request.query.aggregate("min", "total_amount", "min_total_amount")
        self.query.relation_aggregate("customer_order_list", alias, child_request.query, True)
        return self
    def max_total_amount_of_customer_orders(self):
        from requests.customer_order_request import CustomerOrderRequest
        return self.max_total_amount_of_customer_orders_as(
            "max_total_amount_of_customer_orders", CustomerOrderRequest())

    def max_total_amount_of_customer_orders_as(self, alias: str, child_request):
        child_request.query.aggregate("max", "total_amount", "max_total_amount")
        self.query.relation_aggregate("customer_order_list", alias, child_request.query, True)
        return self
    def sum_total_amount_of_customer_orders(self):
        from requests.customer_order_request import CustomerOrderRequest
        return self.sum_total_amount_of_customer_orders_as(
            "sum_total_amount_of_customer_orders", CustomerOrderRequest())

    def sum_total_amount_of_customer_orders_as(self, alias: str, child_request):
        child_request.query.aggregate("sum", "total_amount", "sum_total_amount")
        self.query.relation_aggregate("customer_order_list", alias, child_request.query, True)
        return self
    def avg_total_amount_of_customer_orders(self):
        from requests.customer_order_request import CustomerOrderRequest
        return self.avg_total_amount_of_customer_orders_as(
            "avg_total_amount_of_customer_orders", CustomerOrderRequest())

    def avg_total_amount_of_customer_orders_as(self, alias: str, child_request):
        child_request.query.aggregate("avg", "total_amount", "avg_total_amount")
        self.query.relation_aggregate("customer_order_list", alias, child_request.query, True)
        return self
    def standardDeviation_total_amount_of_customer_orders(self):
        from requests.customer_order_request import CustomerOrderRequest
        return self.standardDeviation_total_amount_of_customer_orders_as(
            "standardDeviation_total_amount_of_customer_orders", CustomerOrderRequest())

    def standardDeviation_total_amount_of_customer_orders_as(self, alias: str, child_request):
        child_request.query.aggregate("stddev", "total_amount", "standardDeviation_total_amount")
        self.query.relation_aggregate("customer_order_list", alias, child_request.query, True)
        return self
    def squareRootOfPopulationStandardDeviation_total_amount_of_customer_orders(self):
        from requests.customer_order_request import CustomerOrderRequest
        return self.squareRootOfPopulationStandardDeviation_total_amount_of_customer_orders_as(
            "squareRootOfPopulationStandardDeviation_total_amount_of_customer_orders", CustomerOrderRequest())

    def squareRootOfPopulationStandardDeviation_total_amount_of_customer_orders_as(self, alias: str, child_request):
        child_request.query.aggregate("stddev_pop", "total_amount", "squareRootOfPopulationStandardDeviation_total_amount")
        self.query.relation_aggregate("customer_order_list", alias, child_request.query, True)
        return self
    def sampleVariance_total_amount_of_customer_orders(self):
        from requests.customer_order_request import CustomerOrderRequest
        return self.sampleVariance_total_amount_of_customer_orders_as(
            "sampleVariance_total_amount_of_customer_orders", CustomerOrderRequest())

    def sampleVariance_total_amount_of_customer_orders_as(self, alias: str, child_request):
        child_request.query.aggregate("var_samp", "total_amount", "sampleVariance_total_amount")
        self.query.relation_aggregate("customer_order_list", alias, child_request.query, True)
        return self
    def samplePopulationVariance_total_amount_of_customer_orders(self):
        from requests.customer_order_request import CustomerOrderRequest
        return self.samplePopulationVariance_total_amount_of_customer_orders_as(
            "samplePopulationVariance_total_amount_of_customer_orders", CustomerOrderRequest())

    def samplePopulationVariance_total_amount_of_customer_orders_as(self, alias: str, child_request):
        child_request.query.aggregate("var_pop", "total_amount", "samplePopulationVariance_total_amount")
        self.query.relation_aggregate("customer_order_list", alias, child_request.query, True)
        return self
    def facet_by_commerce_platform_as(self, name: str, request: QuerySelection,
                                      include_all_facets: bool = True):
        self.query.facet_by(name, "commerce_platform", request.query, include_all_facets)
        return self


class ExecutableOrderStatusRequest:
    def __init__(self, request):
        self._request = request

    def comment(self, c: str):
        self._request.comment(c)
        return self

    def new_entity(self, context) -> OrderStatus:
        request = self._request
        if not request._comment or not request._comment.strip() or not request._purpose or not request._purpose.strip():
            raise ValueError("Security audit failure: non-empty comment() and purpose() are required before new_entity()")
        entity = context.initialize_entity("OrderStatus", OrderStatus())
        if not isinstance(entity, OrderStatus):
            raise TypeError("entity initializer returned an incompatible OrderStatus")
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

    async def execute_for_list(self, context) -> SmartList[OrderStatus]:
        result = await self.execute_for_result(context)
        query_root = EntityRoot()
        return SmartList(
            (OrderStatus(_entity_root=query_root, **row) for row in result.rows),
            facets=result.facets)

    async def execute_for_page(self, context, offset: int, limit: int) -> TeaQLPage[OrderStatus]:
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
        data = SmartList(OrderStatus(_entity_root=query_root, **row) for row in row_result.rows)
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
                yield OrderStatus(_entity_root=query_root, **row)
