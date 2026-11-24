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
from models.customer_order import _TeaqlFields, CustomerOrder
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
        self.query.project(_TeaqlFields.ID_PROPERTY_COLUMN, _TeaqlFields.ORDER_NUMBER_PROPERTY_COLUMN, _TeaqlFields.ORDER_DATE_PROPERTY_COLUMN, _TeaqlFields.TOTAL_AMOUNT_PROPERTY_COLUMN, _TeaqlFields.STATUS_PROPERTY_COLUMN, _TeaqlFields.CUSTOMER_PROPERTY_COLUMN, _TeaqlFields.COMMERCE_PLATFORM_PROPERTY_COLUMN, _TeaqlFields.CREATE_TIME_PROPERTY_COLUMN, _TeaqlFields.UPDATE_TIME_PROPERTY_COLUMN, _TeaqlFields.VERSION_PROPERTY_COLUMN)
        return self

    def select_id(self):
        self.query.project(_TeaqlFields.ID_PROPERTY_COLUMN)
        return self

    def select_order_number(self):
        self.query.project(_TeaqlFields.ORDER_NUMBER_PROPERTY_COLUMN)
        return self

    def select_order_date(self):
        self.query.project(_TeaqlFields.ORDER_DATE_PROPERTY_COLUMN)
        return self

    def select_total_amount(self):
        self.query.project(_TeaqlFields.TOTAL_AMOUNT_PROPERTY_COLUMN)
        return self




    def select_create_time(self):
        self.query.project(_TeaqlFields.CREATE_TIME_PROPERTY_COLUMN)
        return self

    def select_update_time(self):
        self.query.project(_TeaqlFields.UPDATE_TIME_PROPERTY_COLUMN)
        return self

    def select_version(self):
        self.query.project(_TeaqlFields.VERSION_PROPERTY_COLUMN)
        return self

    def select_status_with(self, child_request):
        self.query.project(_TeaqlFields.STATUS_PROPERTY_COLUMN)
        self.query.relation_query(_TeaqlFields.STATUS_PROPERTY_COLUMN, child_request.query,
            QueryOperation("relation-select", "select_status_with", relation=_TeaqlFields.STATUS_PROPERTY_COLUMN))
        return self
    def select_customer_with(self, child_request):
        self.query.project(_TeaqlFields.CUSTOMER_PROPERTY_COLUMN)
        self.query.relation_query(_TeaqlFields.CUSTOMER_PROPERTY_COLUMN, child_request.query,
            QueryOperation("relation-select", "select_customer_with", relation=_TeaqlFields.CUSTOMER_PROPERTY_COLUMN))
        return self
    def select_commerce_platform_with(self, child_request):
        self.query.project(_TeaqlFields.COMMERCE_PLATFORM_PROPERTY_COLUMN)
        self.query.relation_query(_TeaqlFields.COMMERCE_PLATFORM_PROPERTY_COLUMN, child_request.query,
            QueryOperation("relation-select", "select_commerce_platform_with", relation=_TeaqlFields.COMMERCE_PLATFORM_PROPERTY_COLUMN))
        return self
    def with_status_matching(self, child_request):
        child_request.query.projection = ["id"]
        self.query.and_filter(in_subquery(column(_TeaqlFields.STATUS_PROPERTY_COLUMN), "OrderStatus", child_request.query))
        return self

    def without_status_matching(self, child_request):
        child_request.query.projection = ["id"]
        self.query.and_filter(not_in_subquery(column(_TeaqlFields.STATUS_PROPERTY_COLUMN), "OrderStatus", child_request.query))
        return self

    def have_status(self):
        self.query.and_filter(is_not_null(column(_TeaqlFields.STATUS_PROPERTY_COLUMN)))
        return self

    def have_no_status(self):
        self.query.and_filter(is_null(column(_TeaqlFields.STATUS_PROPERTY_COLUMN)))
        return self
    def with_customer_matching(self, child_request):
        child_request.query.projection = ["id"]
        self.query.and_filter(in_subquery(column(_TeaqlFields.CUSTOMER_PROPERTY_COLUMN), "Customer", child_request.query))
        return self

    def without_customer_matching(self, child_request):
        child_request.query.projection = ["id"]
        self.query.and_filter(not_in_subquery(column(_TeaqlFields.CUSTOMER_PROPERTY_COLUMN), "Customer", child_request.query))
        return self

    def have_customer(self):
        self.query.and_filter(is_not_null(column(_TeaqlFields.CUSTOMER_PROPERTY_COLUMN)))
        return self

    def have_no_customer(self):
        self.query.and_filter(is_null(column(_TeaqlFields.CUSTOMER_PROPERTY_COLUMN)))
        return self
    def with_commerce_platform_matching(self, child_request):
        child_request.query.projection = ["id"]
        self.query.and_filter(in_subquery(column(_TeaqlFields.COMMERCE_PLATFORM_PROPERTY_COLUMN), "CommercePlatform", child_request.query))
        return self

    def without_commerce_platform_matching(self, child_request):
        child_request.query.projection = ["id"]
        self.query.and_filter(not_in_subquery(column(_TeaqlFields.COMMERCE_PLATFORM_PROPERTY_COLUMN), "CommercePlatform", child_request.query))
        return self

    def have_commerce_platform(self):
        self.query.and_filter(is_not_null(column(_TeaqlFields.COMMERCE_PLATFORM_PROPERTY_COLUMN)))
        return self

    def have_no_commerce_platform(self):
        self.query.and_filter(is_null(column(_TeaqlFields.COMMERCE_PLATFORM_PROPERTY_COLUMN)))
        return self

    def with_id_is(self, val):
        self.query.and_filter(eq(_TeaqlFields.ID_PROPERTY_COLUMN, val))
        return self

    def with_id_is_not(self, val):
        self.query.and_filter(ne(_TeaqlFields.ID_PROPERTY_COLUMN, val))
        return self

    def with_id_in(self, *vals):
        self.query.and_filter(in_list(_TeaqlFields.ID_PROPERTY_COLUMN, list(vals)))
        return self

    def with_id_not_in(self, *vals):
        self.query.and_filter(not_in_list(_TeaqlFields.ID_PROPERTY_COLUMN, list(vals)))
        return self

    def with_id_greater_than(self, val):
        self.query.and_filter(gt(_TeaqlFields.ID_PROPERTY_COLUMN, val))
        return self

    def with_id_greater_than_or_equal_to(self, val):
        self.query.and_filter(gte(_TeaqlFields.ID_PROPERTY_COLUMN, val))
        return self

    def with_id_less_than(self, val):
        self.query.and_filter(lt(_TeaqlFields.ID_PROPERTY_COLUMN, val))
        return self

    def with_id_less_than_or_equal_to(self, val):
        self.query.and_filter(lte(_TeaqlFields.ID_PROPERTY_COLUMN, val))
        return self

    def with_id_between(self, lower, upper):
        self.query.and_filter(between(column(_TeaqlFields.ID_PROPERTY_COLUMN), value(lower), value(upper)))
        return self

    def with_id_is_known(self):
        self.query.and_filter(is_not_null(column(_TeaqlFields.ID_PROPERTY_COLUMN)))
        return self

    def with_id_is_unknown(self):
        self.query.and_filter(is_null(column(_TeaqlFields.ID_PROPERTY_COLUMN)))
        return self

    def with_order_number_containing(self, val: str):
        self.query.and_filter(contain(_TeaqlFields.ORDER_NUMBER_PROPERTY_COLUMN, val))
        return self

    def with_order_number_not_containing(self, val: str):
        self.query.and_filter(not_contain(_TeaqlFields.ORDER_NUMBER_PROPERTY_COLUMN, val))
        return self

    def with_order_number_starting_with(self, val: str):
        self.query.and_filter(begin_with(_TeaqlFields.ORDER_NUMBER_PROPERTY_COLUMN, val))
        return self

    def with_order_number_not_starting_with(self, val: str):
        self.query.and_filter(not_begin_with(_TeaqlFields.ORDER_NUMBER_PROPERTY_COLUMN, val))
        return self

    def with_order_number_ending_with(self, val: str):
        self.query.and_filter(end_with(_TeaqlFields.ORDER_NUMBER_PROPERTY_COLUMN, val))
        return self

    def with_order_number_not_ending_with(self, val: str):
        self.query.and_filter(not_end_with(_TeaqlFields.ORDER_NUMBER_PROPERTY_COLUMN, val))
        return self

    def with_order_number_sounding_like(self, val: str):
        self.query.and_filter(sound_like(_TeaqlFields.ORDER_NUMBER_PROPERTY_COLUMN, val))
        return self

    def with_order_number_is(self, val: str):
        self.query.and_filter(eq(_TeaqlFields.ORDER_NUMBER_PROPERTY_COLUMN, val))
        return self
    def with_order_number_is_not(self, val):
        self.query.and_filter(ne(_TeaqlFields.ORDER_NUMBER_PROPERTY_COLUMN, val))
        return self

    def with_order_number_in(self, *vals):
        self.query.and_filter(in_list(_TeaqlFields.ORDER_NUMBER_PROPERTY_COLUMN, list(vals)))
        return self

    def with_order_number_not_in(self, *vals):
        self.query.and_filter(not_in_list(_TeaqlFields.ORDER_NUMBER_PROPERTY_COLUMN, list(vals)))
        return self

    def with_order_number_greater_than(self, val):
        self.query.and_filter(gt(_TeaqlFields.ORDER_NUMBER_PROPERTY_COLUMN, val))
        return self

    def with_order_number_greater_than_or_equal_to(self, val):
        self.query.and_filter(gte(_TeaqlFields.ORDER_NUMBER_PROPERTY_COLUMN, val))
        return self

    def with_order_number_less_than(self, val):
        self.query.and_filter(lt(_TeaqlFields.ORDER_NUMBER_PROPERTY_COLUMN, val))
        return self

    def with_order_number_less_than_or_equal_to(self, val):
        self.query.and_filter(lte(_TeaqlFields.ORDER_NUMBER_PROPERTY_COLUMN, val))
        return self

    def with_order_number_between(self, lower, upper):
        self.query.and_filter(between(column(_TeaqlFields.ORDER_NUMBER_PROPERTY_COLUMN), value(lower), value(upper)))
        return self

    def with_order_number_is_known(self):
        self.query.and_filter(is_not_null(column(_TeaqlFields.ORDER_NUMBER_PROPERTY_COLUMN)))
        return self

    def with_order_number_is_unknown(self):
        self.query.and_filter(is_null(column(_TeaqlFields.ORDER_NUMBER_PROPERTY_COLUMN)))
        return self

    def with_order_date_is(self, val):
        self.query.and_filter(eq(_TeaqlFields.ORDER_DATE_PROPERTY_COLUMN, val))
        return self

    def with_order_date_is_not(self, val):
        self.query.and_filter(ne(_TeaqlFields.ORDER_DATE_PROPERTY_COLUMN, val))
        return self

    def with_order_date_in(self, *vals):
        self.query.and_filter(in_list(_TeaqlFields.ORDER_DATE_PROPERTY_COLUMN, list(vals)))
        return self

    def with_order_date_not_in(self, *vals):
        self.query.and_filter(not_in_list(_TeaqlFields.ORDER_DATE_PROPERTY_COLUMN, list(vals)))
        return self

    def with_order_date_greater_than(self, val):
        self.query.and_filter(gt(_TeaqlFields.ORDER_DATE_PROPERTY_COLUMN, val))
        return self

    def with_order_date_greater_than_or_equal_to(self, val):
        self.query.and_filter(gte(_TeaqlFields.ORDER_DATE_PROPERTY_COLUMN, val))
        return self

    def with_order_date_less_than(self, val):
        self.query.and_filter(lt(_TeaqlFields.ORDER_DATE_PROPERTY_COLUMN, val))
        return self

    def with_order_date_less_than_or_equal_to(self, val):
        self.query.and_filter(lte(_TeaqlFields.ORDER_DATE_PROPERTY_COLUMN, val))
        return self

    def with_order_date_between(self, lower, upper):
        self.query.and_filter(between(column(_TeaqlFields.ORDER_DATE_PROPERTY_COLUMN), value(lower), value(upper)))
        return self

    def with_order_date_is_known(self):
        self.query.and_filter(is_not_null(column(_TeaqlFields.ORDER_DATE_PROPERTY_COLUMN)))
        return self

    def with_order_date_is_unknown(self):
        self.query.and_filter(is_null(column(_TeaqlFields.ORDER_DATE_PROPERTY_COLUMN)))
        return self

    def with_total_amount_is(self, val):
        self.query.and_filter(eq(_TeaqlFields.TOTAL_AMOUNT_PROPERTY_COLUMN, val))
        return self

    def with_total_amount_is_not(self, val):
        self.query.and_filter(ne(_TeaqlFields.TOTAL_AMOUNT_PROPERTY_COLUMN, val))
        return self

    def with_total_amount_in(self, *vals):
        self.query.and_filter(in_list(_TeaqlFields.TOTAL_AMOUNT_PROPERTY_COLUMN, list(vals)))
        return self

    def with_total_amount_not_in(self, *vals):
        self.query.and_filter(not_in_list(_TeaqlFields.TOTAL_AMOUNT_PROPERTY_COLUMN, list(vals)))
        return self

    def with_total_amount_greater_than(self, val):
        self.query.and_filter(gt(_TeaqlFields.TOTAL_AMOUNT_PROPERTY_COLUMN, val))
        return self

    def with_total_amount_greater_than_or_equal_to(self, val):
        self.query.and_filter(gte(_TeaqlFields.TOTAL_AMOUNT_PROPERTY_COLUMN, val))
        return self

    def with_total_amount_less_than(self, val):
        self.query.and_filter(lt(_TeaqlFields.TOTAL_AMOUNT_PROPERTY_COLUMN, val))
        return self

    def with_total_amount_less_than_or_equal_to(self, val):
        self.query.and_filter(lte(_TeaqlFields.TOTAL_AMOUNT_PROPERTY_COLUMN, val))
        return self

    def with_total_amount_between(self, lower, upper):
        self.query.and_filter(between(column(_TeaqlFields.TOTAL_AMOUNT_PROPERTY_COLUMN), value(lower), value(upper)))
        return self

    def with_total_amount_is_known(self):
        self.query.and_filter(is_not_null(column(_TeaqlFields.TOTAL_AMOUNT_PROPERTY_COLUMN)))
        return self

    def with_total_amount_is_unknown(self):
        self.query.and_filter(is_null(column(_TeaqlFields.TOTAL_AMOUNT_PROPERTY_COLUMN)))
        return self

    def filter_by_status(self, val):
        self.query.and_filter(eq(_TeaqlFields.STATUS_PROPERTY_COLUMN, val))
        return self
    def with_status_is_pending(self):
        self.query.and_filter(eq(_TeaqlFields.STATUS_PROPERTY_COLUMN, 1001))
        return self
    def with_status_is_confirmed(self):
        self.query.and_filter(eq(_TeaqlFields.STATUS_PROPERTY_COLUMN, 1002))
        return self

    def filter_by_customer(self, val):
        self.query.and_filter(eq(_TeaqlFields.CUSTOMER_PROPERTY_COLUMN, val))
        return self

    def filter_by_commerce_platform(self, val):
        self.query.and_filter(eq(_TeaqlFields.COMMERCE_PLATFORM_PROPERTY_COLUMN, val))
        return self

    def with_create_time_is(self, val):
        self.query.and_filter(eq(_TeaqlFields.CREATE_TIME_PROPERTY_COLUMN, val))
        return self

    def with_create_time_is_not(self, val):
        self.query.and_filter(ne(_TeaqlFields.CREATE_TIME_PROPERTY_COLUMN, val))
        return self

    def with_create_time_in(self, *vals):
        self.query.and_filter(in_list(_TeaqlFields.CREATE_TIME_PROPERTY_COLUMN, list(vals)))
        return self

    def with_create_time_not_in(self, *vals):
        self.query.and_filter(not_in_list(_TeaqlFields.CREATE_TIME_PROPERTY_COLUMN, list(vals)))
        return self

    def with_create_time_greater_than(self, val):
        self.query.and_filter(gt(_TeaqlFields.CREATE_TIME_PROPERTY_COLUMN, val))
        return self

    def with_create_time_greater_than_or_equal_to(self, val):
        self.query.and_filter(gte(_TeaqlFields.CREATE_TIME_PROPERTY_COLUMN, val))
        return self

    def with_create_time_less_than(self, val):
        self.query.and_filter(lt(_TeaqlFields.CREATE_TIME_PROPERTY_COLUMN, val))
        return self

    def with_create_time_less_than_or_equal_to(self, val):
        self.query.and_filter(lte(_TeaqlFields.CREATE_TIME_PROPERTY_COLUMN, val))
        return self

    def with_create_time_between(self, lower, upper):
        self.query.and_filter(between(column(_TeaqlFields.CREATE_TIME_PROPERTY_COLUMN), value(lower), value(upper)))
        return self

    def with_create_time_is_known(self):
        self.query.and_filter(is_not_null(column(_TeaqlFields.CREATE_TIME_PROPERTY_COLUMN)))
        return self

    def with_create_time_is_unknown(self):
        self.query.and_filter(is_null(column(_TeaqlFields.CREATE_TIME_PROPERTY_COLUMN)))
        return self

    def with_update_time_is(self, val):
        self.query.and_filter(eq(_TeaqlFields.UPDATE_TIME_PROPERTY_COLUMN, val))
        return self

    def with_update_time_is_not(self, val):
        self.query.and_filter(ne(_TeaqlFields.UPDATE_TIME_PROPERTY_COLUMN, val))
        return self

    def with_update_time_in(self, *vals):
        self.query.and_filter(in_list(_TeaqlFields.UPDATE_TIME_PROPERTY_COLUMN, list(vals)))
        return self

    def with_update_time_not_in(self, *vals):
        self.query.and_filter(not_in_list(_TeaqlFields.UPDATE_TIME_PROPERTY_COLUMN, list(vals)))
        return self

    def with_update_time_greater_than(self, val):
        self.query.and_filter(gt(_TeaqlFields.UPDATE_TIME_PROPERTY_COLUMN, val))
        return self

    def with_update_time_greater_than_or_equal_to(self, val):
        self.query.and_filter(gte(_TeaqlFields.UPDATE_TIME_PROPERTY_COLUMN, val))
        return self

    def with_update_time_less_than(self, val):
        self.query.and_filter(lt(_TeaqlFields.UPDATE_TIME_PROPERTY_COLUMN, val))
        return self

    def with_update_time_less_than_or_equal_to(self, val):
        self.query.and_filter(lte(_TeaqlFields.UPDATE_TIME_PROPERTY_COLUMN, val))
        return self

    def with_update_time_between(self, lower, upper):
        self.query.and_filter(between(column(_TeaqlFields.UPDATE_TIME_PROPERTY_COLUMN), value(lower), value(upper)))
        return self

    def with_update_time_is_known(self):
        self.query.and_filter(is_not_null(column(_TeaqlFields.UPDATE_TIME_PROPERTY_COLUMN)))
        return self

    def with_update_time_is_unknown(self):
        self.query.and_filter(is_null(column(_TeaqlFields.UPDATE_TIME_PROPERTY_COLUMN)))
        return self

    def with_version_is(self, val):
        self.query.and_filter(eq(_TeaqlFields.VERSION_PROPERTY_COLUMN, val))
        return self

    def with_version_is_not(self, val):
        self.query.and_filter(ne(_TeaqlFields.VERSION_PROPERTY_COLUMN, val))
        return self

    def with_version_in(self, *vals):
        self.query.and_filter(in_list(_TeaqlFields.VERSION_PROPERTY_COLUMN, list(vals)))
        return self

    def with_version_not_in(self, *vals):
        self.query.and_filter(not_in_list(_TeaqlFields.VERSION_PROPERTY_COLUMN, list(vals)))
        return self

    def with_version_greater_than(self, val):
        self.query.and_filter(gt(_TeaqlFields.VERSION_PROPERTY_COLUMN, val))
        return self

    def with_version_greater_than_or_equal_to(self, val):
        self.query.and_filter(gte(_TeaqlFields.VERSION_PROPERTY_COLUMN, val))
        return self

    def with_version_less_than(self, val):
        self.query.and_filter(lt(_TeaqlFields.VERSION_PROPERTY_COLUMN, val))
        return self

    def with_version_less_than_or_equal_to(self, val):
        self.query.and_filter(lte(_TeaqlFields.VERSION_PROPERTY_COLUMN, val))
        return self

    def with_version_between(self, lower, upper):
        self.query.and_filter(between(column(_TeaqlFields.VERSION_PROPERTY_COLUMN), value(lower), value(upper)))
        return self

    def with_version_is_known(self):
        self.query.and_filter(is_not_null(column(_TeaqlFields.VERSION_PROPERTY_COLUMN)))
        return self

    def with_version_is_unknown(self):
        self.query.and_filter(is_null(column(_TeaqlFields.VERSION_PROPERTY_COLUMN)))
        return self

    def order_by_id_ascending(self):
        self.query.order_by(_TeaqlFields.ID_PROPERTY_COLUMN, "asc")
        return self

    def order_by_id_descending(self):
        self.query.order_by(_TeaqlFields.ID_PROPERTY_COLUMN, "desc")
        return self

    def order_by_order_number_ascending(self):
        self.query.order_by(_TeaqlFields.ORDER_NUMBER_PROPERTY_COLUMN, "asc")
        return self

    def order_by_order_number_descending(self):
        self.query.order_by(_TeaqlFields.ORDER_NUMBER_PROPERTY_COLUMN, "desc")
        return self

    def order_by_order_date_ascending(self):
        self.query.order_by(_TeaqlFields.ORDER_DATE_PROPERTY_COLUMN, "asc")
        return self

    def order_by_order_date_descending(self):
        self.query.order_by(_TeaqlFields.ORDER_DATE_PROPERTY_COLUMN, "desc")
        return self

    def order_by_total_amount_ascending(self):
        self.query.order_by(_TeaqlFields.TOTAL_AMOUNT_PROPERTY_COLUMN, "asc")
        return self

    def order_by_total_amount_descending(self):
        self.query.order_by(_TeaqlFields.TOTAL_AMOUNT_PROPERTY_COLUMN, "desc")
        return self




    def order_by_create_time_ascending(self):
        self.query.order_by(_TeaqlFields.CREATE_TIME_PROPERTY_COLUMN, "asc")
        return self

    def order_by_create_time_descending(self):
        self.query.order_by(_TeaqlFields.CREATE_TIME_PROPERTY_COLUMN, "desc")
        return self

    def order_by_update_time_ascending(self):
        self.query.order_by(_TeaqlFields.UPDATE_TIME_PROPERTY_COLUMN, "asc")
        return self

    def order_by_update_time_descending(self):
        self.query.order_by(_TeaqlFields.UPDATE_TIME_PROPERTY_COLUMN, "desc")
        return self

    def order_by_version_ascending(self):
        self.query.order_by(_TeaqlFields.VERSION_PROPERTY_COLUMN, "asc")
        return self

    def order_by_version_descending(self):
        self.query.order_by(_TeaqlFields.VERSION_PROPERTY_COLUMN, "desc")
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
        self.query.min(_TeaqlFields.TOTAL_AMOUNT_PROPERTY_COLUMN, ret_name)
        return self
    def max_total_amount(self):
        return self.max_total_amount_as("maxOfTotalAmount")

    def max_total_amount_as(self, ret_name: str):
        self.query.max(_TeaqlFields.TOTAL_AMOUNT_PROPERTY_COLUMN, ret_name)
        return self
    def sum_total_amount(self):
        return self.sum_total_amount_as("sumOfTotalAmount")

    def sum_total_amount_as(self, ret_name: str):
        self.query.sum(_TeaqlFields.TOTAL_AMOUNT_PROPERTY_COLUMN, ret_name)
        return self
    def avg_total_amount(self):
        return self.avg_total_amount_as("avgOfTotalAmount")

    def avg_total_amount_as(self, ret_name: str):
        self.query.avg(_TeaqlFields.TOTAL_AMOUNT_PROPERTY_COLUMN, ret_name)
        return self
    def standardDeviation_total_amount(self):
        return self.standardDeviation_total_amount_as("standardDeviationOfTotalAmount")

    def standardDeviation_total_amount_as(self, ret_name: str):
        self.query.standardDeviation(_TeaqlFields.TOTAL_AMOUNT_PROPERTY_COLUMN, ret_name)
        return self
    def squareRootOfPopulationStandardDeviation_total_amount(self):
        return self.squareRootOfPopulationStandardDeviation_total_amount_as("squareRootOfPopulationStandardDeviationOfTotalAmount")

    def squareRootOfPopulationStandardDeviation_total_amount_as(self, ret_name: str):
        self.query.squareRootOfPopulationStandardDeviation(_TeaqlFields.TOTAL_AMOUNT_PROPERTY_COLUMN, ret_name)
        return self
    def sampleVariance_total_amount(self):
        return self.sampleVariance_total_amount_as("sampleVarianceOfTotalAmount")

    def sampleVariance_total_amount_as(self, ret_name: str):
        self.query.sampleVariance(_TeaqlFields.TOTAL_AMOUNT_PROPERTY_COLUMN, ret_name)
        return self
    def samplePopulationVariance_total_amount(self):
        return self.samplePopulationVariance_total_amount_as("samplePopulationVarianceOfTotalAmount")

    def samplePopulationVariance_total_amount_as(self, ret_name: str):
        self.query.samplePopulationVariance(_TeaqlFields.TOTAL_AMOUNT_PROPERTY_COLUMN, ret_name)
        return self
    def group_by_id(self):
        self.query.group_by(_TeaqlFields.ID_PROPERTY_COLUMN)
        return self

    def group_by_id_as(self, ret_name: str):
        self.query.group_by(_TeaqlFields.ID_PROPERTY_COLUMN)
        self.query.project_expr(ret_name, column(_TeaqlFields.ID_PROPERTY_COLUMN))
        return self
    def group_by_order_number(self):
        self.query.group_by(_TeaqlFields.ORDER_NUMBER_PROPERTY_COLUMN)
        return self

    def group_by_order_number_as(self, ret_name: str):
        self.query.group_by(_TeaqlFields.ORDER_NUMBER_PROPERTY_COLUMN)
        self.query.project_expr(ret_name, column(_TeaqlFields.ORDER_NUMBER_PROPERTY_COLUMN))
        return self
    def group_by_order_date(self):
        self.query.group_by(_TeaqlFields.ORDER_DATE_PROPERTY_COLUMN)
        return self

    def group_by_order_date_as(self, ret_name: str):
        self.query.group_by(_TeaqlFields.ORDER_DATE_PROPERTY_COLUMN)
        self.query.project_expr(ret_name, column(_TeaqlFields.ORDER_DATE_PROPERTY_COLUMN))
        return self
    def group_by_total_amount(self):
        self.query.group_by(_TeaqlFields.TOTAL_AMOUNT_PROPERTY_COLUMN)
        return self

    def group_by_total_amount_as(self, ret_name: str):
        self.query.group_by(_TeaqlFields.TOTAL_AMOUNT_PROPERTY_COLUMN)
        self.query.project_expr(ret_name, column(_TeaqlFields.TOTAL_AMOUNT_PROPERTY_COLUMN))
        return self
    def group_by_status(self):
        self.query.group_by(_TeaqlFields.STATUS_PROPERTY_COLUMN)
        return self

    def group_by_status_as(self, ret_name: str):
        self.query.group_by(_TeaqlFields.STATUS_PROPERTY_COLUMN)
        self.query.project_expr(ret_name, column(_TeaqlFields.STATUS_PROPERTY_COLUMN))
        return self
    def group_by_customer(self):
        self.query.group_by(_TeaqlFields.CUSTOMER_PROPERTY_COLUMN)
        return self

    def group_by_customer_as(self, ret_name: str):
        self.query.group_by(_TeaqlFields.CUSTOMER_PROPERTY_COLUMN)
        self.query.project_expr(ret_name, column(_TeaqlFields.CUSTOMER_PROPERTY_COLUMN))
        return self
    def group_by_commerce_platform(self):
        self.query.group_by(_TeaqlFields.COMMERCE_PLATFORM_PROPERTY_COLUMN)
        return self

    def group_by_commerce_platform_as(self, ret_name: str):
        self.query.group_by(_TeaqlFields.COMMERCE_PLATFORM_PROPERTY_COLUMN)
        self.query.project_expr(ret_name, column(_TeaqlFields.COMMERCE_PLATFORM_PROPERTY_COLUMN))
        return self
    def group_by_create_time(self):
        self.query.group_by(_TeaqlFields.CREATE_TIME_PROPERTY_COLUMN)
        return self

    def group_by_create_time_as(self, ret_name: str):
        self.query.group_by(_TeaqlFields.CREATE_TIME_PROPERTY_COLUMN)
        self.query.project_expr(ret_name, column(_TeaqlFields.CREATE_TIME_PROPERTY_COLUMN))
        return self
    def group_by_update_time(self):
        self.query.group_by(_TeaqlFields.UPDATE_TIME_PROPERTY_COLUMN)
        return self

    def group_by_update_time_as(self, ret_name: str):
        self.query.group_by(_TeaqlFields.UPDATE_TIME_PROPERTY_COLUMN)
        self.query.project_expr(ret_name, column(_TeaqlFields.UPDATE_TIME_PROPERTY_COLUMN))
        return self
    def group_by_version(self):
        self.query.group_by(_TeaqlFields.VERSION_PROPERTY_COLUMN)
        return self

    def group_by_version_as(self, ret_name: str):
        self.query.group_by(_TeaqlFields.VERSION_PROPERTY_COLUMN)
        self.query.project_expr(ret_name, column(_TeaqlFields.VERSION_PROPERTY_COLUMN))
        return self
    def select_order_line_list(self):
        from requests.order_line_request import OrderLineRequest
        return self.select_order_line_list_with(OrderLineRequest())

    def select_order_line_list_with(self, child_request):
        self.query.relation_query("order_line_list", child_request.query,
            QueryOperation("relation-select", "select_order_line_list_with", relation="order_line_list"))
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
        self.count_order_lines_with(alias, OrderLineRequest())
        self.query.relation_aggregates[-1].operation = QueryOperation(
            "relation-count", "count_order_lines_as", alias, "order_line_list")
        return self

    def count_order_lines_with(self, alias: str, child_request):
        query = deepcopy(child_request.query)
        query.aggregates = []
        query.count_field("id", alias)
        self.query.relation_aggregates.append(
            RelationAggregate("order_line_list", alias, query, True,
                QueryOperation("relation-count", "count_order_lines_with", alias, "order_line_list"))
        )
        return self

    def min_quantity_of_order_lines(self):
        from requests.order_line_request import OrderLineRequest
        return self.min_quantity_of_order_lines_as(
            "min_quantity_of_order_lines", OrderLineRequest())

    def min_quantity_of_order_lines_as(self, alias: str, child_request):
        query = deepcopy(child_request.query)
        query.aggregates = []
        query.min("quantity", alias)
        self.query.relation_aggregates.append(
            RelationAggregate("order_line_list", alias, query, True,
                QueryOperation("aggregate", "min_quantity_of_order_lines_as", alias, "order_line_list"))
        )
        return self
    def max_quantity_of_order_lines(self):
        from requests.order_line_request import OrderLineRequest
        return self.max_quantity_of_order_lines_as(
            "max_quantity_of_order_lines", OrderLineRequest())

    def max_quantity_of_order_lines_as(self, alias: str, child_request):
        query = deepcopy(child_request.query)
        query.aggregates = []
        query.max("quantity", alias)
        self.query.relation_aggregates.append(
            RelationAggregate("order_line_list", alias, query, True,
                QueryOperation("aggregate", "max_quantity_of_order_lines_as", alias, "order_line_list"))
        )
        return self
    def sum_quantity_of_order_lines(self):
        from requests.order_line_request import OrderLineRequest
        return self.sum_quantity_of_order_lines_as(
            "sum_quantity_of_order_lines", OrderLineRequest())

    def sum_quantity_of_order_lines_as(self, alias: str, child_request):
        query = deepcopy(child_request.query)
        query.aggregates = []
        query.sum("quantity", alias)
        self.query.relation_aggregates.append(
            RelationAggregate("order_line_list", alias, query, True,
                QueryOperation("aggregate", "sum_quantity_of_order_lines_as", alias, "order_line_list"))
        )
        return self
    def avg_quantity_of_order_lines(self):
        from requests.order_line_request import OrderLineRequest
        return self.avg_quantity_of_order_lines_as(
            "avg_quantity_of_order_lines", OrderLineRequest())

    def avg_quantity_of_order_lines_as(self, alias: str, child_request):
        query = deepcopy(child_request.query)
        query.aggregates = []
        query.avg("quantity", alias)
        self.query.relation_aggregates.append(
            RelationAggregate("order_line_list", alias, query, True,
                QueryOperation("aggregate", "avg_quantity_of_order_lines_as", alias, "order_line_list"))
        )
        return self
    def standardDeviation_quantity_of_order_lines(self):
        from requests.order_line_request import OrderLineRequest
        return self.standardDeviation_quantity_of_order_lines_as(
            "standardDeviation_quantity_of_order_lines", OrderLineRequest())

    def standardDeviation_quantity_of_order_lines_as(self, alias: str, child_request):
        query = deepcopy(child_request.query)
        query.aggregates = []
        query.standardDeviation("quantity", alias)
        self.query.relation_aggregates.append(
            RelationAggregate("order_line_list", alias, query, True,
                QueryOperation("aggregate", "standardDeviation_quantity_of_order_lines_as", alias, "order_line_list"))
        )
        return self
    def squareRootOfPopulationStandardDeviation_quantity_of_order_lines(self):
        from requests.order_line_request import OrderLineRequest
        return self.squareRootOfPopulationStandardDeviation_quantity_of_order_lines_as(
            "squareRootOfPopulationStandardDeviation_quantity_of_order_lines", OrderLineRequest())

    def squareRootOfPopulationStandardDeviation_quantity_of_order_lines_as(self, alias: str, child_request):
        query = deepcopy(child_request.query)
        query.aggregates = []
        query.squareRootOfPopulationStandardDeviation("quantity", alias)
        self.query.relation_aggregates.append(
            RelationAggregate("order_line_list", alias, query, True,
                QueryOperation("aggregate", "squareRootOfPopulationStandardDeviation_quantity_of_order_lines_as", alias, "order_line_list"))
        )
        return self
    def sampleVariance_quantity_of_order_lines(self):
        from requests.order_line_request import OrderLineRequest
        return self.sampleVariance_quantity_of_order_lines_as(
            "sampleVariance_quantity_of_order_lines", OrderLineRequest())

    def sampleVariance_quantity_of_order_lines_as(self, alias: str, child_request):
        query = deepcopy(child_request.query)
        query.aggregates = []
        query.sampleVariance("quantity", alias)
        self.query.relation_aggregates.append(
            RelationAggregate("order_line_list", alias, query, True,
                QueryOperation("aggregate", "sampleVariance_quantity_of_order_lines_as", alias, "order_line_list"))
        )
        return self
    def samplePopulationVariance_quantity_of_order_lines(self):
        from requests.order_line_request import OrderLineRequest
        return self.samplePopulationVariance_quantity_of_order_lines_as(
            "samplePopulationVariance_quantity_of_order_lines", OrderLineRequest())

    def samplePopulationVariance_quantity_of_order_lines_as(self, alias: str, child_request):
        query = deepcopy(child_request.query)
        query.aggregates = []
        query.samplePopulationVariance("quantity", alias)
        self.query.relation_aggregates.append(
            RelationAggregate("order_line_list", alias, query, True,
                QueryOperation("aggregate", "samplePopulationVariance_quantity_of_order_lines_as", alias, "order_line_list"))
        )
        return self
    def facet_by_status_as(self, name: str, request: QuerySelection,
                                      include_all_facets: bool = True):
        self.query.facet_by(name, _TeaqlFields.STATUS_PROPERTY_COLUMN, request.query, include_all_facets,
            QueryOperation("facet", "facet_by_status_as", name, _TeaqlFields.STATUS_PROPERTY_COLUMN))
        return self

    def facet_by_customer_as(self, name: str, request: QuerySelection,
                                      include_all_facets: bool = True):
        self.query.facet_by(name, _TeaqlFields.CUSTOMER_PROPERTY_COLUMN, request.query, include_all_facets,
            QueryOperation("facet", "facet_by_customer_as", name, _TeaqlFields.CUSTOMER_PROPERTY_COLUMN))
        return self

    def facet_by_commerce_platform_as(self, name: str, request: QuerySelection,
                                      include_all_facets: bool = True):
        self.query.facet_by(name, _TeaqlFields.COMMERCE_PLATFORM_PROPERTY_COLUMN, request.query, include_all_facets,
            QueryOperation("facet", "facet_by_commerce_platform_as", name, _TeaqlFields.COMMERCE_PLATFORM_PROPERTY_COLUMN))
        return self


class ExecutableCustomerOrderRequest:
    def __init__(self, request):
        self._request = request

    def comment(self, c: str):
        self._request.comment(c)
        return self

    async def new_entity(self, context) -> CustomerOrder:
        request = self._request
        QueryIntent(request._comment, request._purpose)
        identity = await context.next_id("CustomerOrder")
        entity = context.initialize_entity("CustomerOrder", CustomerOrder._teaql_from_reserved_id(identity))
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
            lambda row: CustomerOrder._teaql_from_record(_entity_root=EntityRoot(), **row),
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
        if root.query.aggregates or root.query.group_by_items or root.query.object_group_bys:
            raise ValueError("Entity streams require entity rows; use a record or aggregation query")
        from teaql.runtime.query_stream import execute_typed_stream
        return execute_typed_stream(context, root,
            lambda row: CustomerOrder._teaql_from_record(_entity_root=EntityRoot(), **row), chunk_size)
