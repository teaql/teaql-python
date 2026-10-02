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
from models.customer_order import CustomerOrder
from typing import Protocol

class QuerySelection(Protocol):
    query: SelectQuery

class CustomerOrderRequest:
    def __init__(self, minimal=False):
        self.query = SelectQuery("CustomerOrder")
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
        self.query.project("id", "order_number", "order_date", "total_amount", "status", "customer", "commerce_platform", "create_time", "update_time", "version")
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




    def select_create_time(self):
        self.query.project("create_time")
        return self

    def select_update_time(self):
        self.query.project("update_time")
        return self

    def select_version(self):
        self.query.project("version")
        return self

    def select_status_with(self, child_request):
        self.query.project("status")
        self.query.relation_query("status", child_request.query)
        return self
    def select_customer_with(self, child_request):
        self.query.project("customer")
        self.query.relation_query("customer", child_request.query)
        return self
    def select_commerce_platform_with(self, child_request):
        self.query.project("commerce_platform")
        self.query.relation_query("commerce_platform", child_request.query)
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
    def with_commerce_platform_matching(self, child_request):
        child_request.query.projection = ["id"]
        self.query.and_filter(in_subquery(column("commerce_platform"), "CommercePlatform", child_request.query))
        return self

    def without_commerce_platform_matching(self, child_request):
        child_request.query.projection = ["id"]
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

    def filter_by_status(self, val):
        self.query.and_filter(eq("status", val))
        return self
    def with_status_is_pending(self):
        self.query.and_filter(eq("status", 1001))
        return self
    def with_status_is_confirmed(self):
        self.query.and_filter(eq("status", 1002))
        return self

    def filter_by_customer(self, val):
        self.query.and_filter(eq("customer", val))
        return self

    def filter_by_commerce_platform(self, val):
        self.query.and_filter(eq("commerce_platform", val))
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
    def group_by_status(self):
        self.query.group_by("status")
        return self

    def group_by_status_as(self, ret_name: str):
        self.query.group_by("status")
        return self
    def group_by_customer(self):
        self.query.group_by("customer")
        return self

    def group_by_customer_as(self, ret_name: str):
        self.query.group_by("customer")
        return self
    def group_by_commerce_platform(self):
        self.query.group_by("commerce_platform")
        return self

    def group_by_commerce_platform_as(self, ret_name: str):
        self.query.group_by("commerce_platform")
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
    def select_order_line_list(self):
        from requests.order_line_request import OrderLineRequest
        return self.select_order_line_list_with(OrderLineRequest())

    def select_order_line_list_with(self, child_request):
        self.query.relation_query("order_line_list", child_request.query)
        return self
    def have_order_lines(self):
        from requests.order_line_request import OrderLineRequest
        return self.with_order_line_list_matching(OrderLineRequest())

    def have_no_order_lines(self):
        from requests.order_line_request import OrderLineRequest
        return self.without_order_line_list_matching(OrderLineRequest())

    def with_order_line_list_matching(self, child_request):
        child_request.query.projection = ["customer_order"]
        self.query.and_filter(in_subquery(column("id"), "OrderLine", child_request.query))
        return self

    def without_order_line_list_matching(self, child_request):
        child_request.query.projection = ["customer_order"]
        self.query.and_filter(not_in_subquery(column("id"), "OrderLine", child_request.query))
        return self
    def count_order_lines(self):
        return self.count_order_lines_as("count_order_lines")

    def count_order_lines_as(self, alias: str):
        from requests.order_line_request import OrderLineRequest
        return self.count_order_lines_with(alias, OrderLineRequest())

    def count_order_lines_with(self, alias: str, child_request):
        child_request.query.count_field("id", alias)
        self.query.relation_aggregates.append(
            RelationAggregate("order_line_list", alias, child_request.query, True)
        )
        return self

    def min_quantity_of_order_lines(self):
        from requests.order_line_request import OrderLineRequest
        return self.min_quantity_of_order_lines_as(
            "min_quantity_of_order_lines", OrderLineRequest())

    def min_quantity_of_order_lines_as(self, alias: str, child_request):
        child_request.query.min("quantity", "min_quantity")
        self.query.relation_aggregates.append(
            RelationAggregate("order_line_list", alias, child_request.query, True)
        )
        return self
    def max_quantity_of_order_lines(self):
        from requests.order_line_request import OrderLineRequest
        return self.max_quantity_of_order_lines_as(
            "max_quantity_of_order_lines", OrderLineRequest())

    def max_quantity_of_order_lines_as(self, alias: str, child_request):
        child_request.query.max("quantity", "max_quantity")
        self.query.relation_aggregates.append(
            RelationAggregate("order_line_list", alias, child_request.query, True)
        )
        return self
    def sum_quantity_of_order_lines(self):
        from requests.order_line_request import OrderLineRequest
        return self.sum_quantity_of_order_lines_as(
            "sum_quantity_of_order_lines", OrderLineRequest())

    def sum_quantity_of_order_lines_as(self, alias: str, child_request):
        child_request.query.sum("quantity", "sum_quantity")
        self.query.relation_aggregates.append(
            RelationAggregate("order_line_list", alias, child_request.query, True)
        )
        return self
    def avg_quantity_of_order_lines(self):
        from requests.order_line_request import OrderLineRequest
        return self.avg_quantity_of_order_lines_as(
            "avg_quantity_of_order_lines", OrderLineRequest())

    def avg_quantity_of_order_lines_as(self, alias: str, child_request):
        child_request.query.avg("quantity", "avg_quantity")
        self.query.relation_aggregates.append(
            RelationAggregate("order_line_list", alias, child_request.query, True)
        )
        return self
    def standardDeviation_quantity_of_order_lines(self):
        from requests.order_line_request import OrderLineRequest
        return self.standardDeviation_quantity_of_order_lines_as(
            "standardDeviation_quantity_of_order_lines", OrderLineRequest())

    def standardDeviation_quantity_of_order_lines_as(self, alias: str, child_request):
        child_request.query.standardDeviation("quantity", "standardDeviation_quantity")
        self.query.relation_aggregates.append(
            RelationAggregate("order_line_list", alias, child_request.query, True)
        )
        return self
    def squareRootOfPopulationStandardDeviation_quantity_of_order_lines(self):
        from requests.order_line_request import OrderLineRequest
        return self.squareRootOfPopulationStandardDeviation_quantity_of_order_lines_as(
            "squareRootOfPopulationStandardDeviation_quantity_of_order_lines", OrderLineRequest())

    def squareRootOfPopulationStandardDeviation_quantity_of_order_lines_as(self, alias: str, child_request):
        child_request.query.squareRootOfPopulationStandardDeviation("quantity", "squareRootOfPopulationStandardDeviation_quantity")
        self.query.relation_aggregates.append(
            RelationAggregate("order_line_list", alias, child_request.query, True)
        )
        return self
    def sampleVariance_quantity_of_order_lines(self):
        from requests.order_line_request import OrderLineRequest
        return self.sampleVariance_quantity_of_order_lines_as(
            "sampleVariance_quantity_of_order_lines", OrderLineRequest())

    def sampleVariance_quantity_of_order_lines_as(self, alias: str, child_request):
        child_request.query.sampleVariance("quantity", "sampleVariance_quantity")
        self.query.relation_aggregates.append(
            RelationAggregate("order_line_list", alias, child_request.query, True)
        )
        return self
    def samplePopulationVariance_quantity_of_order_lines(self):
        from requests.order_line_request import OrderLineRequest
        return self.samplePopulationVariance_quantity_of_order_lines_as(
            "samplePopulationVariance_quantity_of_order_lines", OrderLineRequest())

    def samplePopulationVariance_quantity_of_order_lines_as(self, alias: str, child_request):
        child_request.query.samplePopulationVariance("quantity", "samplePopulationVariance_quantity")
        self.query.relation_aggregates.append(
            RelationAggregate("order_line_list", alias, child_request.query, True)
        )
        return self
    def facet_by_status_as(self, name: str, request: QuerySelection,
                                      include_all_facets: bool = True):
        self.query.facet_by(name, "status", request.query, include_all_facets)
        return self

    def facet_by_customer_as(self, name: str, request: QuerySelection,
                                      include_all_facets: bool = True):
        self.query.facet_by(name, "customer", request.query, include_all_facets)
        return self

    def facet_by_commerce_platform_as(self, name: str, request: QuerySelection,
                                      include_all_facets: bool = True):
        self.query.facet_by(name, "commerce_platform", request.query, include_all_facets)
        return self


class ExecutableCustomerOrderRequest:
    def __init__(self, request):
        self._request = request

    def comment(self, c: str):
        self._request.comment(c)
        return self

    def new_entity(self, context) -> CustomerOrder:
        request = self._request
        QueryIntent(request._comment, request._purpose)
        entity = context.initialize_entity("CustomerOrder", CustomerOrder())
        if not isinstance(entity, CustomerOrder):
            raise TypeError("entity initializer returned an incompatible CustomerOrder")
        return entity

    async def execute_for_result(self, context):
        self = self._request
        req = QueryRequest(self.query, _comment=self._comment, _purpose=self._purpose)
        req = context.prepare_query_request(req)
        service = context.require_resource("dataService")
        return await service.query(context, req)

    async def execute_for_rows(self, context):
        return (await self.execute_for_result(context)).rows

    async def execute_for_list(self, context) -> SmartList[CustomerOrder]:
        result = await self.execute_for_result(context)
        return SmartList(
            (CustomerOrder(**row) for row in result.rows),
            facets=result.facets)

    async def execute_for_page(self, context, offset: int, limit: int) -> TeaQLPage[CustomerOrder]:
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
        data = SmartList(CustomerOrder(**row) for row in row_result.rows)
        return TeaQLPage(data=data, total_count=total_count, offset=offset, limit=limit)

    async def execute_for_one(self, context):
        request = deepcopy(self._request)
        request.limit(1)
        entities = await ExecutableCustomerOrderRequest(request).execute_for_list(context)
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
                        yield CustomerOrder(**row)
            finally:
                close = getattr(stream, "aclose", None)
                if close is not None:
                    await close()
        return entities()
