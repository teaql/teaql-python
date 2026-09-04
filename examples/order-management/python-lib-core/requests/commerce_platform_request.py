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
from models.commerce_platform import CommercePlatform
from typing import Protocol

class QuerySelection(Protocol):
    query: SelectQuery

class CommercePlatformRequest:
    def __init__(self, minimal=False):
        self.query = SelectQuery("CommercePlatform")
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
        return ExecutableCommercePlatformRequest(self)

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
        self.query.project("id", "name", "create_time", "update_time", "version")
        return self

    def select_id(self):
        self.query.project("id")
        return self

    def select_name(self):
        self.query.project("name")
        return self

    def select_create_time(self):
        self.query.project("create_time")
        return self

    def select_update_time(self):
        self.query.project("update_time")
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

    def with_create_time_is(self, val):
        self.query.and_filter(eq("create_time", val))
        return self

    def with_create_time_is_not(self, val):
        self.query.and_filter(ne("create_time", val))
        return self

    def with_create_time_in(self, *vals):
        self.query.and_filter(in_list("create_time", list(vals)))
        return self

    def with_create_time_not_in(self, *vals):
        self.query.and_filter(not_in_list("create_time", list(vals)))
        return self

    def with_create_time_greater_than(self, val):
        self.query.and_filter(gt("create_time", val))
        return self

    def with_create_time_greater_than_or_equal_to(self, val):
        self.query.and_filter(gte("create_time", val))
        return self

    def with_create_time_less_than(self, val):
        self.query.and_filter(lt("create_time", val))
        return self

    def with_create_time_less_than_or_equal_to(self, val):
        self.query.and_filter(lte("create_time", val))
        return self

    def with_create_time_between(self, lower, upper):
        self.query.and_filter(between(column("create_time"), value(lower), value(upper)))
        return self

    def with_create_time_is_known(self):
        self.query.and_filter(is_not_null(column("create_time")))
        return self

    def with_create_time_is_unknown(self):
        self.query.and_filter(is_null(column("create_time")))
        return self

    def with_update_time_is(self, val):
        self.query.and_filter(eq("update_time", val))
        return self

    def with_update_time_is_not(self, val):
        self.query.and_filter(ne("update_time", val))
        return self

    def with_update_time_in(self, *vals):
        self.query.and_filter(in_list("update_time", list(vals)))
        return self

    def with_update_time_not_in(self, *vals):
        self.query.and_filter(not_in_list("update_time", list(vals)))
        return self

    def with_update_time_greater_than(self, val):
        self.query.and_filter(gt("update_time", val))
        return self

    def with_update_time_greater_than_or_equal_to(self, val):
        self.query.and_filter(gte("update_time", val))
        return self

    def with_update_time_less_than(self, val):
        self.query.and_filter(lt("update_time", val))
        return self

    def with_update_time_less_than_or_equal_to(self, val):
        self.query.and_filter(lte("update_time", val))
        return self

    def with_update_time_between(self, lower, upper):
        self.query.and_filter(between(column("update_time"), value(lower), value(upper)))
        return self

    def with_update_time_is_known(self):
        self.query.and_filter(is_not_null(column("update_time")))
        return self

    def with_update_time_is_unknown(self):
        self.query.and_filter(is_null(column("update_time")))
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

    def order_by_create_time_ascending(self):
        self.query.order_by("create_time", "asc")
        return self

    def order_by_create_time_descending(self):
        self.query.order_by("create_time", "desc")
        return self

    def order_by_update_time_ascending(self):
        self.query.order_by("update_time", "asc")
        return self

    def order_by_update_time_descending(self):
        self.query.order_by("update_time", "desc")
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
    def group_by_create_time(self):
        self.query.group_by("create_time")
        return self

    def group_by_create_time_as(self, ret_name: str):
        self.query.group_by("create_time") 
        return self
    def group_by_update_time(self):
        self.query.group_by("update_time")
        return self

    def group_by_update_time_as(self, ret_name: str):
        self.query.group_by("update_time") 
        return self
    def group_by_version(self):
        self.query.group_by("version")
        return self

    def group_by_version_as(self, ret_name: str):
        self.query.group_by("version") 
        return self
    def select_customer_list(self):
        from requests.customer_request import CustomerRequest
        return self.select_customer_list_with(CustomerRequest())

    def select_customer_list_with(self, child_request):
        self.query.relation_query("customer_list", child_request.query)
        return self
    def select_order_status_list(self):
        from requests.order_status_request import OrderStatusRequest
        return self.select_order_status_list_with(OrderStatusRequest())

    def select_order_status_list_with(self, child_request):
        self.query.relation_query("order_status_list", child_request.query)
        return self
    def select_customer_order_list(self):
        from requests.customer_order_request import CustomerOrderRequest
        return self.select_customer_order_list_with(CustomerOrderRequest())

    def select_customer_order_list_with(self, child_request):
        self.query.relation_query("customer_order_list", child_request.query)
        return self
    def select_product_list(self):
        from requests.product_request import ProductRequest
        return self.select_product_list_with(ProductRequest())

    def select_product_list_with(self, child_request):
        self.query.relation_query("product_list", child_request.query)
        return self
    def select_order_line_list(self):
        from requests.order_line_request import OrderLineRequest
        return self.select_order_line_list_with(OrderLineRequest())

    def select_order_line_list_with(self, child_request):
        self.query.relation_query("order_line_list", child_request.query)
        return self
    def select_order_search_preset_list(self):
        from requests.order_search_preset_request import OrderSearchPresetRequest
        return self.select_order_search_preset_list_with(OrderSearchPresetRequest())

    def select_order_search_preset_list_with(self, child_request):
        self.query.relation_query("order_search_preset_list", child_request.query)
        return self
    def have_customers(self):
        from requests.customer_request import CustomerRequest
        return self.with_customer_list_matching(CustomerRequest())

    def have_no_customers(self):
        from requests.customer_request import CustomerRequest
        return self.without_customer_list_matching(CustomerRequest())

    def with_customer_list_matching(self, child_request):
        self.query.and_filter(in_subquery(column("id"), "Customer", child_request.query))
        child_request.query._projection = ["commerce_platform"]
        return self

    def without_customer_list_matching(self, child_request):
        self.query.and_filter(not_in_subquery(column("id"), "Customer", child_request.query))
        child_request.query._projection = ["commerce_platform"]
        return self
    def have_order_statuses(self):
        from requests.order_status_request import OrderStatusRequest
        return self.with_order_status_list_matching(OrderStatusRequest())

    def have_no_order_statuses(self):
        from requests.order_status_request import OrderStatusRequest
        return self.without_order_status_list_matching(OrderStatusRequest())

    def with_order_status_list_matching(self, child_request):
        self.query.and_filter(in_subquery(column("id"), "OrderStatus", child_request.query))
        child_request.query._projection = ["commerce_platform"]
        return self

    def without_order_status_list_matching(self, child_request):
        self.query.and_filter(not_in_subquery(column("id"), "OrderStatus", child_request.query))
        child_request.query._projection = ["commerce_platform"]
        return self
    def have_customer_orders(self):
        from requests.customer_order_request import CustomerOrderRequest
        return self.with_customer_order_list_matching(CustomerOrderRequest())

    def have_no_customer_orders(self):
        from requests.customer_order_request import CustomerOrderRequest
        return self.without_customer_order_list_matching(CustomerOrderRequest())

    def with_customer_order_list_matching(self, child_request):
        self.query.and_filter(in_subquery(column("id"), "CustomerOrder", child_request.query))
        child_request.query._projection = ["commerce_platform"]
        return self

    def without_customer_order_list_matching(self, child_request):
        self.query.and_filter(not_in_subquery(column("id"), "CustomerOrder", child_request.query))
        child_request.query._projection = ["commerce_platform"]
        return self
    def have_products(self):
        from requests.product_request import ProductRequest
        return self.with_product_list_matching(ProductRequest())

    def have_no_products(self):
        from requests.product_request import ProductRequest
        return self.without_product_list_matching(ProductRequest())

    def with_product_list_matching(self, child_request):
        self.query.and_filter(in_subquery(column("id"), "Product", child_request.query))
        child_request.query._projection = ["commerce_platform"]
        return self

    def without_product_list_matching(self, child_request):
        self.query.and_filter(not_in_subquery(column("id"), "Product", child_request.query))
        child_request.query._projection = ["commerce_platform"]
        return self
    def have_order_lines(self):
        from requests.order_line_request import OrderLineRequest
        return self.with_order_line_list_matching(OrderLineRequest())

    def have_no_order_lines(self):
        from requests.order_line_request import OrderLineRequest
        return self.without_order_line_list_matching(OrderLineRequest())

    def with_order_line_list_matching(self, child_request):
        self.query.and_filter(in_subquery(column("id"), "OrderLine", child_request.query))
        child_request.query._projection = ["commerce_platform"]
        return self

    def without_order_line_list_matching(self, child_request):
        self.query.and_filter(not_in_subquery(column("id"), "OrderLine", child_request.query))
        child_request.query._projection = ["commerce_platform"]
        return self
    def have_order_search_presets(self):
        from requests.order_search_preset_request import OrderSearchPresetRequest
        return self.with_order_search_preset_list_matching(OrderSearchPresetRequest())

    def have_no_order_search_presets(self):
        from requests.order_search_preset_request import OrderSearchPresetRequest
        return self.without_order_search_preset_list_matching(OrderSearchPresetRequest())

    def with_order_search_preset_list_matching(self, child_request):
        self.query.and_filter(in_subquery(column("id"), "OrderSearchPreset", child_request.query))
        child_request.query._projection = ["commerce_platform"]
        return self

    def without_order_search_preset_list_matching(self, child_request):
        self.query.and_filter(not_in_subquery(column("id"), "OrderSearchPreset", child_request.query))
        child_request.query._projection = ["commerce_platform"]
        return self
    def count_customers(self):
        return self.count_customers_as("count_customers")

    def count_customers_as(self, alias: str):
        from requests.customer_request import CustomerRequest
        return self.count_customers_with(alias, CustomerRequest())

    def count_customers_with(self, alias: str, child_request):
        child_request.query.count_field("id", alias)
        self.query.relation_aggregate("customer_list", alias, child_request.query, True)
        return self


    def count_order_statuses(self):
        return self.count_order_statuses_as("count_order_statuses")

    def count_order_statuses_as(self, alias: str):
        from requests.order_status_request import OrderStatusRequest
        return self.count_order_statuses_with(alias, OrderStatusRequest())

    def count_order_statuses_with(self, alias: str, child_request):
        child_request.query.count_field("id", alias)
        self.query.relation_aggregate("order_status_list", alias, child_request.query, True)
        return self

    def min_display_order_of_order_statuses(self):
        from requests.order_status_request import OrderStatusRequest
        return self.min_display_order_of_order_statuses_as(
            "min_display_order_of_order_statuses", OrderStatusRequest())

    def min_display_order_of_order_statuses_as(self, alias: str, child_request):
        child_request.query.aggregate("min", "display_order", "min_display_order")
        self.query.relation_aggregate("order_status_list", alias, child_request.query, True)
        return self
    def max_display_order_of_order_statuses(self):
        from requests.order_status_request import OrderStatusRequest
        return self.max_display_order_of_order_statuses_as(
            "max_display_order_of_order_statuses", OrderStatusRequest())

    def max_display_order_of_order_statuses_as(self, alias: str, child_request):
        child_request.query.aggregate("max", "display_order", "max_display_order")
        self.query.relation_aggregate("order_status_list", alias, child_request.query, True)
        return self
    def sum_display_order_of_order_statuses(self):
        from requests.order_status_request import OrderStatusRequest
        return self.sum_display_order_of_order_statuses_as(
            "sum_display_order_of_order_statuses", OrderStatusRequest())

    def sum_display_order_of_order_statuses_as(self, alias: str, child_request):
        child_request.query.aggregate("sum", "display_order", "sum_display_order")
        self.query.relation_aggregate("order_status_list", alias, child_request.query, True)
        return self
    def avg_display_order_of_order_statuses(self):
        from requests.order_status_request import OrderStatusRequest
        return self.avg_display_order_of_order_statuses_as(
            "avg_display_order_of_order_statuses", OrderStatusRequest())

    def avg_display_order_of_order_statuses_as(self, alias: str, child_request):
        child_request.query.aggregate("avg", "display_order", "avg_display_order")
        self.query.relation_aggregate("order_status_list", alias, child_request.query, True)
        return self
    def standardDeviation_display_order_of_order_statuses(self):
        from requests.order_status_request import OrderStatusRequest
        return self.standardDeviation_display_order_of_order_statuses_as(
            "standardDeviation_display_order_of_order_statuses", OrderStatusRequest())

    def standardDeviation_display_order_of_order_statuses_as(self, alias: str, child_request):
        child_request.query.aggregate("stddev", "display_order", "standardDeviation_display_order")
        self.query.relation_aggregate("order_status_list", alias, child_request.query, True)
        return self
    def squareRootOfPopulationStandardDeviation_display_order_of_order_statuses(self):
        from requests.order_status_request import OrderStatusRequest
        return self.squareRootOfPopulationStandardDeviation_display_order_of_order_statuses_as(
            "squareRootOfPopulationStandardDeviation_display_order_of_order_statuses", OrderStatusRequest())

    def squareRootOfPopulationStandardDeviation_display_order_of_order_statuses_as(self, alias: str, child_request):
        child_request.query.aggregate("stddev_pop", "display_order", "squareRootOfPopulationStandardDeviation_display_order")
        self.query.relation_aggregate("order_status_list", alias, child_request.query, True)
        return self
    def sampleVariance_display_order_of_order_statuses(self):
        from requests.order_status_request import OrderStatusRequest
        return self.sampleVariance_display_order_of_order_statuses_as(
            "sampleVariance_display_order_of_order_statuses", OrderStatusRequest())

    def sampleVariance_display_order_of_order_statuses_as(self, alias: str, child_request):
        child_request.query.aggregate("var_samp", "display_order", "sampleVariance_display_order")
        self.query.relation_aggregate("order_status_list", alias, child_request.query, True)
        return self
    def samplePopulationVariance_display_order_of_order_statuses(self):
        from requests.order_status_request import OrderStatusRequest
        return self.samplePopulationVariance_display_order_of_order_statuses_as(
            "samplePopulationVariance_display_order_of_order_statuses", OrderStatusRequest())

    def samplePopulationVariance_display_order_of_order_statuses_as(self, alias: str, child_request):
        child_request.query.aggregate("var_pop", "display_order", "samplePopulationVariance_display_order")
        self.query.relation_aggregate("order_status_list", alias, child_request.query, True)
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
    def count_products(self):
        return self.count_products_as("count_products")

    def count_products_as(self, alias: str):
        from requests.product_request import ProductRequest
        return self.count_products_with(alias, ProductRequest())

    def count_products_with(self, alias: str, child_request):
        child_request.query.count_field("id", alias)
        self.query.relation_aggregate("product_list", alias, child_request.query, True)
        return self


    def count_order_lines(self):
        return self.count_order_lines_as("count_order_lines")

    def count_order_lines_as(self, alias: str):
        from requests.order_line_request import OrderLineRequest
        return self.count_order_lines_with(alias, OrderLineRequest())

    def count_order_lines_with(self, alias: str, child_request):
        child_request.query.count_field("id", alias)
        self.query.relation_aggregate("order_line_list", alias, child_request.query, True)
        return self

    def min_quantity_of_order_lines(self):
        from requests.order_line_request import OrderLineRequest
        return self.min_quantity_of_order_lines_as(
            "min_quantity_of_order_lines", OrderLineRequest())

    def min_quantity_of_order_lines_as(self, alias: str, child_request):
        child_request.query.aggregate("min", "quantity", "min_quantity")
        self.query.relation_aggregate("order_line_list", alias, child_request.query, True)
        return self
    def max_quantity_of_order_lines(self):
        from requests.order_line_request import OrderLineRequest
        return self.max_quantity_of_order_lines_as(
            "max_quantity_of_order_lines", OrderLineRequest())

    def max_quantity_of_order_lines_as(self, alias: str, child_request):
        child_request.query.aggregate("max", "quantity", "max_quantity")
        self.query.relation_aggregate("order_line_list", alias, child_request.query, True)
        return self
    def sum_quantity_of_order_lines(self):
        from requests.order_line_request import OrderLineRequest
        return self.sum_quantity_of_order_lines_as(
            "sum_quantity_of_order_lines", OrderLineRequest())

    def sum_quantity_of_order_lines_as(self, alias: str, child_request):
        child_request.query.aggregate("sum", "quantity", "sum_quantity")
        self.query.relation_aggregate("order_line_list", alias, child_request.query, True)
        return self
    def avg_quantity_of_order_lines(self):
        from requests.order_line_request import OrderLineRequest
        return self.avg_quantity_of_order_lines_as(
            "avg_quantity_of_order_lines", OrderLineRequest())

    def avg_quantity_of_order_lines_as(self, alias: str, child_request):
        child_request.query.aggregate("avg", "quantity", "avg_quantity")
        self.query.relation_aggregate("order_line_list", alias, child_request.query, True)
        return self
    def standardDeviation_quantity_of_order_lines(self):
        from requests.order_line_request import OrderLineRequest
        return self.standardDeviation_quantity_of_order_lines_as(
            "standardDeviation_quantity_of_order_lines", OrderLineRequest())

    def standardDeviation_quantity_of_order_lines_as(self, alias: str, child_request):
        child_request.query.aggregate("stddev", "quantity", "standardDeviation_quantity")
        self.query.relation_aggregate("order_line_list", alias, child_request.query, True)
        return self
    def squareRootOfPopulationStandardDeviation_quantity_of_order_lines(self):
        from requests.order_line_request import OrderLineRequest
        return self.squareRootOfPopulationStandardDeviation_quantity_of_order_lines_as(
            "squareRootOfPopulationStandardDeviation_quantity_of_order_lines", OrderLineRequest())

    def squareRootOfPopulationStandardDeviation_quantity_of_order_lines_as(self, alias: str, child_request):
        child_request.query.aggregate("stddev_pop", "quantity", "squareRootOfPopulationStandardDeviation_quantity")
        self.query.relation_aggregate("order_line_list", alias, child_request.query, True)
        return self
    def sampleVariance_quantity_of_order_lines(self):
        from requests.order_line_request import OrderLineRequest
        return self.sampleVariance_quantity_of_order_lines_as(
            "sampleVariance_quantity_of_order_lines", OrderLineRequest())

    def sampleVariance_quantity_of_order_lines_as(self, alias: str, child_request):
        child_request.query.aggregate("var_samp", "quantity", "sampleVariance_quantity")
        self.query.relation_aggregate("order_line_list", alias, child_request.query, True)
        return self
    def samplePopulationVariance_quantity_of_order_lines(self):
        from requests.order_line_request import OrderLineRequest
        return self.samplePopulationVariance_quantity_of_order_lines_as(
            "samplePopulationVariance_quantity_of_order_lines", OrderLineRequest())

    def samplePopulationVariance_quantity_of_order_lines_as(self, alias: str, child_request):
        child_request.query.aggregate("var_pop", "quantity", "samplePopulationVariance_quantity")
        self.query.relation_aggregate("order_line_list", alias, child_request.query, True)
        return self
    def count_order_search_presets(self):
        return self.count_order_search_presets_as("count_order_search_presets")

    def count_order_search_presets_as(self, alias: str):
        from requests.order_search_preset_request import OrderSearchPresetRequest
        return self.count_order_search_presets_with(alias, OrderSearchPresetRequest())

    def count_order_search_presets_with(self, alias: str, child_request):
        child_request.query.count_field("id", alias)
        self.query.relation_aggregate("order_search_preset_list", alias, child_request.query, True)
        return self



class ExecutableCommercePlatformRequest:
    def __init__(self, request):
        self._request = request

    def comment(self, c: str):
        self._request.comment(c)
        return self

    def new_entity(self, context) -> CommercePlatform:
        request = self._request
        if not request._comment or not request._comment.strip() or not request._purpose or not request._purpose.strip():
            raise ValueError("Security audit failure: non-empty comment() and purpose() are required before new_entity()")
        entity = context.initialize_entity("CommercePlatform", CommercePlatform())
        if not isinstance(entity, CommercePlatform):
            raise TypeError("entity initializer returned an incompatible CommercePlatform")
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

    async def execute_for_list(self, context) -> SmartList[CommercePlatform]:
        result = await self.execute_for_result(context)
        query_root = EntityRoot()
        return SmartList(
            (CommercePlatform(_entity_root=query_root, **row) for row in result.rows),
            facets=result.facets)

    async def execute_for_page(self, context, offset: int, limit: int) -> TeaQLPage[CommercePlatform]:
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
        data = SmartList(CommercePlatform(_entity_root=query_root, **row) for row in row_result.rows)
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
                yield CommercePlatform(_entity_root=query_root, **row)
