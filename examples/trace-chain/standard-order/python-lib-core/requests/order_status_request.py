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
from models.order_status import _TeaqlFields, OrderStatus
from typing import Protocol

class QuerySelection(Protocol):
    query: SelectQuery

class OrderStatusRequest:
    def __init__(self, minimal=False):
        self.query = SelectQuery("OrderStatus")
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
        self.query.with_deleted_rows()
        return self

    def deleted_rows_only(self):
        self.query.deleted_rows_only()
        return self

    def select_self_fields(self):
        self.query.project(_TeaqlFields.PLATFORM_PROPERTY_COLUMN, _TeaqlFields.ID_PROPERTY_COLUMN, _TeaqlFields.NAME_PROPERTY_COLUMN, _TeaqlFields.CODE_PROPERTY_COLUMN, _TeaqlFields.COLOR_PROPERTY_COLUMN, _TeaqlFields.DISPLAY_ORDER_PROPERTY_COLUMN, _TeaqlFields.VERSION_PROPERTY_COLUMN)
        return self

    def select_id(self):
        self.query.project(_TeaqlFields.ID_PROPERTY_COLUMN)
        return self

    def select_name(self):
        self.query.project(_TeaqlFields.NAME_PROPERTY_COLUMN)
        return self

    def select_code(self):
        self.query.project(_TeaqlFields.CODE_PROPERTY_COLUMN)
        return self

    def select_color(self):
        self.query.project(_TeaqlFields.COLOR_PROPERTY_COLUMN)
        return self

    def select_display_order(self):
        self.query.project(_TeaqlFields.DISPLAY_ORDER_PROPERTY_COLUMN)
        return self

    def select_version(self):
        self.query.project(_TeaqlFields.VERSION_PROPERTY_COLUMN)
        return self

    def select_platform_with(self, child_request):
        self.query.project(_TeaqlFields.PLATFORM_PROPERTY_COLUMN)
        self.query.relation_query(_TeaqlFields.PLATFORM_PROPERTY_COLUMN, child_request.query,
            QueryOperation("relation-select", "select_platform_with", relation=_TeaqlFields.PLATFORM_PROPERTY_COLUMN))
        return self
    def with_platform_matching(self, child_request):
        child_request.query.projection = ["id"]
        self.query.and_filter(in_subquery(column(_TeaqlFields.PLATFORM_PROPERTY_COLUMN), "Platform", child_request.query))
        return self

    def without_platform_matching(self, child_request):
        child_request.query.projection = ["id"]
        self.query.and_filter(not_in_subquery(column(_TeaqlFields.PLATFORM_PROPERTY_COLUMN), "Platform", child_request.query))
        return self

    def have_platform(self):
        self.query.and_filter(is_not_null(column(_TeaqlFields.PLATFORM_PROPERTY_COLUMN)))
        return self

    def have_no_platform(self):
        self.query.and_filter(is_null(column(_TeaqlFields.PLATFORM_PROPERTY_COLUMN)))
        return self

    def filter_by_platform(self, val):
        self.query.and_filter(eq(_TeaqlFields.PLATFORM_PROPERTY_COLUMN, val))
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

    def with_name_containing(self, val: str):
        self.query.and_filter(contain(_TeaqlFields.NAME_PROPERTY_COLUMN, val))
        return self

    def with_name_not_containing(self, val: str):
        self.query.and_filter(not_contain(_TeaqlFields.NAME_PROPERTY_COLUMN, val))
        return self

    def with_name_starting_with(self, val: str):
        self.query.and_filter(begin_with(_TeaqlFields.NAME_PROPERTY_COLUMN, val))
        return self

    def with_name_not_starting_with(self, val: str):
        self.query.and_filter(not_begin_with(_TeaqlFields.NAME_PROPERTY_COLUMN, val))
        return self

    def with_name_ending_with(self, val: str):
        self.query.and_filter(end_with(_TeaqlFields.NAME_PROPERTY_COLUMN, val))
        return self

    def with_name_not_ending_with(self, val: str):
        self.query.and_filter(not_end_with(_TeaqlFields.NAME_PROPERTY_COLUMN, val))
        return self

    def with_name_sounding_like(self, val: str):
        self.query.and_filter(sound_like(_TeaqlFields.NAME_PROPERTY_COLUMN, val))
        return self

    def with_name_is(self, val: str):
        self.query.and_filter(eq(_TeaqlFields.NAME_PROPERTY_COLUMN, val))
        return self
    def with_name_is_not(self, val):
        self.query.and_filter(ne(_TeaqlFields.NAME_PROPERTY_COLUMN, val))
        return self

    def with_name_in(self, *vals):
        self.query.and_filter(in_list(_TeaqlFields.NAME_PROPERTY_COLUMN, list(vals)))
        return self

    def with_name_not_in(self, *vals):
        self.query.and_filter(not_in_list(_TeaqlFields.NAME_PROPERTY_COLUMN, list(vals)))
        return self

    def with_name_greater_than(self, val):
        self.query.and_filter(gt(_TeaqlFields.NAME_PROPERTY_COLUMN, val))
        return self

    def with_name_greater_than_or_equal_to(self, val):
        self.query.and_filter(gte(_TeaqlFields.NAME_PROPERTY_COLUMN, val))
        return self

    def with_name_less_than(self, val):
        self.query.and_filter(lt(_TeaqlFields.NAME_PROPERTY_COLUMN, val))
        return self

    def with_name_less_than_or_equal_to(self, val):
        self.query.and_filter(lte(_TeaqlFields.NAME_PROPERTY_COLUMN, val))
        return self

    def with_name_between(self, lower, upper):
        self.query.and_filter(between(column(_TeaqlFields.NAME_PROPERTY_COLUMN), value(lower), value(upper)))
        return self

    def with_name_is_known(self):
        self.query.and_filter(is_not_null(column(_TeaqlFields.NAME_PROPERTY_COLUMN)))
        return self

    def with_name_is_unknown(self):
        self.query.and_filter(is_null(column(_TeaqlFields.NAME_PROPERTY_COLUMN)))
        return self

    def with_code_containing(self, val: str):
        self.query.and_filter(contain(_TeaqlFields.CODE_PROPERTY_COLUMN, val))
        return self

    def with_code_not_containing(self, val: str):
        self.query.and_filter(not_contain(_TeaqlFields.CODE_PROPERTY_COLUMN, val))
        return self

    def with_code_starting_with(self, val: str):
        self.query.and_filter(begin_with(_TeaqlFields.CODE_PROPERTY_COLUMN, val))
        return self

    def with_code_not_starting_with(self, val: str):
        self.query.and_filter(not_begin_with(_TeaqlFields.CODE_PROPERTY_COLUMN, val))
        return self

    def with_code_ending_with(self, val: str):
        self.query.and_filter(end_with(_TeaqlFields.CODE_PROPERTY_COLUMN, val))
        return self

    def with_code_not_ending_with(self, val: str):
        self.query.and_filter(not_end_with(_TeaqlFields.CODE_PROPERTY_COLUMN, val))
        return self

    def with_code_sounding_like(self, val: str):
        self.query.and_filter(sound_like(_TeaqlFields.CODE_PROPERTY_COLUMN, val))
        return self

    def with_code_is(self, val: str):
        self.query.and_filter(eq(_TeaqlFields.CODE_PROPERTY_COLUMN, val))
        return self
    def with_code_is_not(self, val):
        self.query.and_filter(ne(_TeaqlFields.CODE_PROPERTY_COLUMN, val))
        return self

    def with_code_in(self, *vals):
        self.query.and_filter(in_list(_TeaqlFields.CODE_PROPERTY_COLUMN, list(vals)))
        return self

    def with_code_not_in(self, *vals):
        self.query.and_filter(not_in_list(_TeaqlFields.CODE_PROPERTY_COLUMN, list(vals)))
        return self

    def with_code_greater_than(self, val):
        self.query.and_filter(gt(_TeaqlFields.CODE_PROPERTY_COLUMN, val))
        return self

    def with_code_greater_than_or_equal_to(self, val):
        self.query.and_filter(gte(_TeaqlFields.CODE_PROPERTY_COLUMN, val))
        return self

    def with_code_less_than(self, val):
        self.query.and_filter(lt(_TeaqlFields.CODE_PROPERTY_COLUMN, val))
        return self

    def with_code_less_than_or_equal_to(self, val):
        self.query.and_filter(lte(_TeaqlFields.CODE_PROPERTY_COLUMN, val))
        return self

    def with_code_between(self, lower, upper):
        self.query.and_filter(between(column(_TeaqlFields.CODE_PROPERTY_COLUMN), value(lower), value(upper)))
        return self

    def with_code_is_known(self):
        self.query.and_filter(is_not_null(column(_TeaqlFields.CODE_PROPERTY_COLUMN)))
        return self

    def with_code_is_unknown(self):
        self.query.and_filter(is_null(column(_TeaqlFields.CODE_PROPERTY_COLUMN)))
        return self

    def with_color_containing(self, val: str):
        self.query.and_filter(contain(_TeaqlFields.COLOR_PROPERTY_COLUMN, val))
        return self

    def with_color_not_containing(self, val: str):
        self.query.and_filter(not_contain(_TeaqlFields.COLOR_PROPERTY_COLUMN, val))
        return self

    def with_color_starting_with(self, val: str):
        self.query.and_filter(begin_with(_TeaqlFields.COLOR_PROPERTY_COLUMN, val))
        return self

    def with_color_not_starting_with(self, val: str):
        self.query.and_filter(not_begin_with(_TeaqlFields.COLOR_PROPERTY_COLUMN, val))
        return self

    def with_color_ending_with(self, val: str):
        self.query.and_filter(end_with(_TeaqlFields.COLOR_PROPERTY_COLUMN, val))
        return self

    def with_color_not_ending_with(self, val: str):
        self.query.and_filter(not_end_with(_TeaqlFields.COLOR_PROPERTY_COLUMN, val))
        return self

    def with_color_sounding_like(self, val: str):
        self.query.and_filter(sound_like(_TeaqlFields.COLOR_PROPERTY_COLUMN, val))
        return self

    def with_color_is(self, val: str):
        self.query.and_filter(eq(_TeaqlFields.COLOR_PROPERTY_COLUMN, val))
        return self
    def with_color_is_not(self, val):
        self.query.and_filter(ne(_TeaqlFields.COLOR_PROPERTY_COLUMN, val))
        return self

    def with_color_in(self, *vals):
        self.query.and_filter(in_list(_TeaqlFields.COLOR_PROPERTY_COLUMN, list(vals)))
        return self

    def with_color_not_in(self, *vals):
        self.query.and_filter(not_in_list(_TeaqlFields.COLOR_PROPERTY_COLUMN, list(vals)))
        return self

    def with_color_greater_than(self, val):
        self.query.and_filter(gt(_TeaqlFields.COLOR_PROPERTY_COLUMN, val))
        return self

    def with_color_greater_than_or_equal_to(self, val):
        self.query.and_filter(gte(_TeaqlFields.COLOR_PROPERTY_COLUMN, val))
        return self

    def with_color_less_than(self, val):
        self.query.and_filter(lt(_TeaqlFields.COLOR_PROPERTY_COLUMN, val))
        return self

    def with_color_less_than_or_equal_to(self, val):
        self.query.and_filter(lte(_TeaqlFields.COLOR_PROPERTY_COLUMN, val))
        return self

    def with_color_between(self, lower, upper):
        self.query.and_filter(between(column(_TeaqlFields.COLOR_PROPERTY_COLUMN), value(lower), value(upper)))
        return self

    def with_color_is_known(self):
        self.query.and_filter(is_not_null(column(_TeaqlFields.COLOR_PROPERTY_COLUMN)))
        return self

    def with_color_is_unknown(self):
        self.query.and_filter(is_null(column(_TeaqlFields.COLOR_PROPERTY_COLUMN)))
        return self

    def with_display_order_is(self, val):
        self.query.and_filter(eq(_TeaqlFields.DISPLAY_ORDER_PROPERTY_COLUMN, val))
        return self

    def with_display_order_is_not(self, val):
        self.query.and_filter(ne(_TeaqlFields.DISPLAY_ORDER_PROPERTY_COLUMN, val))
        return self

    def with_display_order_in(self, *vals):
        self.query.and_filter(in_list(_TeaqlFields.DISPLAY_ORDER_PROPERTY_COLUMN, list(vals)))
        return self

    def with_display_order_not_in(self, *vals):
        self.query.and_filter(not_in_list(_TeaqlFields.DISPLAY_ORDER_PROPERTY_COLUMN, list(vals)))
        return self

    def with_display_order_greater_than(self, val):
        self.query.and_filter(gt(_TeaqlFields.DISPLAY_ORDER_PROPERTY_COLUMN, val))
        return self

    def with_display_order_greater_than_or_equal_to(self, val):
        self.query.and_filter(gte(_TeaqlFields.DISPLAY_ORDER_PROPERTY_COLUMN, val))
        return self

    def with_display_order_less_than(self, val):
        self.query.and_filter(lt(_TeaqlFields.DISPLAY_ORDER_PROPERTY_COLUMN, val))
        return self

    def with_display_order_less_than_or_equal_to(self, val):
        self.query.and_filter(lte(_TeaqlFields.DISPLAY_ORDER_PROPERTY_COLUMN, val))
        return self

    def with_display_order_between(self, lower, upper):
        self.query.and_filter(between(column(_TeaqlFields.DISPLAY_ORDER_PROPERTY_COLUMN), value(lower), value(upper)))
        return self

    def with_display_order_is_known(self):
        self.query.and_filter(is_not_null(column(_TeaqlFields.DISPLAY_ORDER_PROPERTY_COLUMN)))
        return self

    def with_display_order_is_unknown(self):
        self.query.and_filter(is_null(column(_TeaqlFields.DISPLAY_ORDER_PROPERTY_COLUMN)))
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

    def order_by_name_ascending(self):
        self.query.order_by(_TeaqlFields.NAME_PROPERTY_COLUMN, "asc")
        return self

    def order_by_name_descending(self):
        self.query.order_by(_TeaqlFields.NAME_PROPERTY_COLUMN, "desc")
        return self

    def order_by_code_ascending(self):
        self.query.order_by(_TeaqlFields.CODE_PROPERTY_COLUMN, "asc")
        return self

    def order_by_code_descending(self):
        self.query.order_by(_TeaqlFields.CODE_PROPERTY_COLUMN, "desc")
        return self

    def order_by_color_ascending(self):
        self.query.order_by(_TeaqlFields.COLOR_PROPERTY_COLUMN, "asc")
        return self

    def order_by_color_descending(self):
        self.query.order_by(_TeaqlFields.COLOR_PROPERTY_COLUMN, "desc")
        return self

    def order_by_display_order_ascending(self):
        self.query.order_by(_TeaqlFields.DISPLAY_ORDER_PROPERTY_COLUMN, "asc")
        return self

    def order_by_display_order_descending(self):
        self.query.order_by(_TeaqlFields.DISPLAY_ORDER_PROPERTY_COLUMN, "desc")
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

    def min_display_order(self):
        return self.min_display_order_as("minOfDisplayOrder")

    def min_display_order_as(self, ret_name: str):
        self.query.min(_TeaqlFields.DISPLAY_ORDER_PROPERTY_COLUMN, ret_name)
        return self
    def max_display_order(self):
        return self.max_display_order_as("maxOfDisplayOrder")

    def max_display_order_as(self, ret_name: str):
        self.query.max(_TeaqlFields.DISPLAY_ORDER_PROPERTY_COLUMN, ret_name)
        return self
    def sum_display_order(self):
        return self.sum_display_order_as("sumOfDisplayOrder")

    def sum_display_order_as(self, ret_name: str):
        self.query.sum(_TeaqlFields.DISPLAY_ORDER_PROPERTY_COLUMN, ret_name)
        return self
    def avg_display_order(self):
        return self.avg_display_order_as("avgOfDisplayOrder")

    def avg_display_order_as(self, ret_name: str):
        self.query.avg(_TeaqlFields.DISPLAY_ORDER_PROPERTY_COLUMN, ret_name)
        return self
    def standardDeviation_display_order(self):
        return self.standardDeviation_display_order_as("standardDeviationOfDisplayOrder")

    def standardDeviation_display_order_as(self, ret_name: str):
        self.query.standardDeviation(_TeaqlFields.DISPLAY_ORDER_PROPERTY_COLUMN, ret_name)
        return self
    def squareRootOfPopulationStandardDeviation_display_order(self):
        return self.squareRootOfPopulationStandardDeviation_display_order_as("squareRootOfPopulationStandardDeviationOfDisplayOrder")

    def squareRootOfPopulationStandardDeviation_display_order_as(self, ret_name: str):
        self.query.squareRootOfPopulationStandardDeviation(_TeaqlFields.DISPLAY_ORDER_PROPERTY_COLUMN, ret_name)
        return self
    def sampleVariance_display_order(self):
        return self.sampleVariance_display_order_as("sampleVarianceOfDisplayOrder")

    def sampleVariance_display_order_as(self, ret_name: str):
        self.query.sampleVariance(_TeaqlFields.DISPLAY_ORDER_PROPERTY_COLUMN, ret_name)
        return self
    def samplePopulationVariance_display_order(self):
        return self.samplePopulationVariance_display_order_as("samplePopulationVarianceOfDisplayOrder")

    def samplePopulationVariance_display_order_as(self, ret_name: str):
        self.query.samplePopulationVariance(_TeaqlFields.DISPLAY_ORDER_PROPERTY_COLUMN, ret_name)
        return self
    def group_by_platform(self):
        self.query.group_by(_TeaqlFields.PLATFORM_PROPERTY_COLUMN)
        return self

    def group_by_platform_as(self, ret_name: str):
        self.query.group_by(_TeaqlFields.PLATFORM_PROPERTY_COLUMN)
        self.query.project_expr(ret_name, column(_TeaqlFields.PLATFORM_PROPERTY_COLUMN))
        return self
    def group_by_id(self):
        self.query.group_by(_TeaqlFields.ID_PROPERTY_COLUMN)
        return self

    def group_by_id_as(self, ret_name: str):
        self.query.group_by(_TeaqlFields.ID_PROPERTY_COLUMN)
        self.query.project_expr(ret_name, column(_TeaqlFields.ID_PROPERTY_COLUMN))
        return self
    def group_by_name(self):
        self.query.group_by(_TeaqlFields.NAME_PROPERTY_COLUMN)
        return self

    def group_by_name_as(self, ret_name: str):
        self.query.group_by(_TeaqlFields.NAME_PROPERTY_COLUMN)
        self.query.project_expr(ret_name, column(_TeaqlFields.NAME_PROPERTY_COLUMN))
        return self
    def group_by_code(self):
        self.query.group_by(_TeaqlFields.CODE_PROPERTY_COLUMN)
        return self

    def group_by_code_as(self, ret_name: str):
        self.query.group_by(_TeaqlFields.CODE_PROPERTY_COLUMN)
        self.query.project_expr(ret_name, column(_TeaqlFields.CODE_PROPERTY_COLUMN))
        return self
    def group_by_color(self):
        self.query.group_by(_TeaqlFields.COLOR_PROPERTY_COLUMN)
        return self

    def group_by_color_as(self, ret_name: str):
        self.query.group_by(_TeaqlFields.COLOR_PROPERTY_COLUMN)
        self.query.project_expr(ret_name, column(_TeaqlFields.COLOR_PROPERTY_COLUMN))
        return self
    def group_by_display_order(self):
        self.query.group_by(_TeaqlFields.DISPLAY_ORDER_PROPERTY_COLUMN)
        return self

    def group_by_display_order_as(self, ret_name: str):
        self.query.group_by(_TeaqlFields.DISPLAY_ORDER_PROPERTY_COLUMN)
        self.query.project_expr(ret_name, column(_TeaqlFields.DISPLAY_ORDER_PROPERTY_COLUMN))
        return self
    def group_by_version(self):
        self.query.group_by(_TeaqlFields.VERSION_PROPERTY_COLUMN)
        return self

    def group_by_version_as(self, ret_name: str):
        self.query.group_by(_TeaqlFields.VERSION_PROPERTY_COLUMN)
        self.query.project_expr(ret_name, column(_TeaqlFields.VERSION_PROPERTY_COLUMN))
        return self
    def select_customer_order_list(self):
        from requests.customer_order_request import CustomerOrderRequest
        return self.select_customer_order_list_with(CustomerOrderRequest())

    def select_customer_order_list_with(self, child_request):
        self.query.relation_query("customer_order_list", child_request.query,
            QueryOperation("relation-select", "select_customer_order_list_with", relation="customer_order_list"))
        return self
    def have_customer_orders(self):
        from requests.customer_order_request import CustomerOrderRequest
        return self.with_customer_order_list_matching(CustomerOrderRequest())

    def have_no_customer_orders(self):
        from requests.customer_order_request import CustomerOrderRequest
        return self.without_customer_order_list_matching(CustomerOrderRequest())

    def with_customer_order_list_matching(self, child_request):
        child_request.query.projection = ["status"]
        self.query.and_filter(in_subquery(column("id"), "CustomerOrder", child_request.query))
        return self

    def without_customer_order_list_matching(self, child_request):
        child_request.query.projection = ["status"]
        self.query.and_filter(not_in_subquery(column("id"), "CustomerOrder", child_request.query))
        return self
    def count_customer_orders(self):
        return self.count_customer_orders_as("count_customer_orders")

    def count_customer_orders_as(self, alias: str):
        from requests.customer_order_request import CustomerOrderRequest
        self.count_customer_orders_with(alias, CustomerOrderRequest())
        self.query.relation_aggregates[-1].operation = QueryOperation(
            "relation-count", "count_customer_orders_as", alias, "customer_order_list")
        return self

    def count_customer_orders_with(self, alias: str, child_request):
        query = deepcopy(child_request.query)
        query.aggregates = []
        query.count_field("id", alias)
        self.query.relation_aggregates.append(
            RelationAggregate("customer_order_list", alias, query, True,
                QueryOperation("relation-count", "count_customer_orders_with", alias, "customer_order_list"))
        )
        return self

    def min_total_amount_of_customer_orders(self):
        from requests.customer_order_request import CustomerOrderRequest
        return self.min_total_amount_of_customer_orders_as(
            "min_total_amount_of_customer_orders", CustomerOrderRequest())

    def min_total_amount_of_customer_orders_as(self, alias: str, child_request):
        query = deepcopy(child_request.query)
        query.aggregates = []
        query.min("total_amount", alias)
        self.query.relation_aggregates.append(
            RelationAggregate("customer_order_list", alias, query, True,
                QueryOperation("aggregate", "min_total_amount_of_customer_orders_as", alias, "customer_order_list"))
        )
        return self
    def max_total_amount_of_customer_orders(self):
        from requests.customer_order_request import CustomerOrderRequest
        return self.max_total_amount_of_customer_orders_as(
            "max_total_amount_of_customer_orders", CustomerOrderRequest())

    def max_total_amount_of_customer_orders_as(self, alias: str, child_request):
        query = deepcopy(child_request.query)
        query.aggregates = []
        query.max("total_amount", alias)
        self.query.relation_aggregates.append(
            RelationAggregate("customer_order_list", alias, query, True,
                QueryOperation("aggregate", "max_total_amount_of_customer_orders_as", alias, "customer_order_list"))
        )
        return self
    def sum_total_amount_of_customer_orders(self):
        from requests.customer_order_request import CustomerOrderRequest
        return self.sum_total_amount_of_customer_orders_as(
            "sum_total_amount_of_customer_orders", CustomerOrderRequest())

    def sum_total_amount_of_customer_orders_as(self, alias: str, child_request):
        query = deepcopy(child_request.query)
        query.aggregates = []
        query.sum("total_amount", alias)
        self.query.relation_aggregates.append(
            RelationAggregate("customer_order_list", alias, query, True,
                QueryOperation("aggregate", "sum_total_amount_of_customer_orders_as", alias, "customer_order_list"))
        )
        return self
    def avg_total_amount_of_customer_orders(self):
        from requests.customer_order_request import CustomerOrderRequest
        return self.avg_total_amount_of_customer_orders_as(
            "avg_total_amount_of_customer_orders", CustomerOrderRequest())

    def avg_total_amount_of_customer_orders_as(self, alias: str, child_request):
        query = deepcopy(child_request.query)
        query.aggregates = []
        query.avg("total_amount", alias)
        self.query.relation_aggregates.append(
            RelationAggregate("customer_order_list", alias, query, True,
                QueryOperation("aggregate", "avg_total_amount_of_customer_orders_as", alias, "customer_order_list"))
        )
        return self
    def standardDeviation_total_amount_of_customer_orders(self):
        from requests.customer_order_request import CustomerOrderRequest
        return self.standardDeviation_total_amount_of_customer_orders_as(
            "standardDeviation_total_amount_of_customer_orders", CustomerOrderRequest())

    def standardDeviation_total_amount_of_customer_orders_as(self, alias: str, child_request):
        query = deepcopy(child_request.query)
        query.aggregates = []
        query.standardDeviation("total_amount", alias)
        self.query.relation_aggregates.append(
            RelationAggregate("customer_order_list", alias, query, True,
                QueryOperation("aggregate", "standardDeviation_total_amount_of_customer_orders_as", alias, "customer_order_list"))
        )
        return self
    def squareRootOfPopulationStandardDeviation_total_amount_of_customer_orders(self):
        from requests.customer_order_request import CustomerOrderRequest
        return self.squareRootOfPopulationStandardDeviation_total_amount_of_customer_orders_as(
            "squareRootOfPopulationStandardDeviation_total_amount_of_customer_orders", CustomerOrderRequest())

    def squareRootOfPopulationStandardDeviation_total_amount_of_customer_orders_as(self, alias: str, child_request):
        query = deepcopy(child_request.query)
        query.aggregates = []
        query.squareRootOfPopulationStandardDeviation("total_amount", alias)
        self.query.relation_aggregates.append(
            RelationAggregate("customer_order_list", alias, query, True,
                QueryOperation("aggregate", "squareRootOfPopulationStandardDeviation_total_amount_of_customer_orders_as", alias, "customer_order_list"))
        )
        return self
    def sampleVariance_total_amount_of_customer_orders(self):
        from requests.customer_order_request import CustomerOrderRequest
        return self.sampleVariance_total_amount_of_customer_orders_as(
            "sampleVariance_total_amount_of_customer_orders", CustomerOrderRequest())

    def sampleVariance_total_amount_of_customer_orders_as(self, alias: str, child_request):
        query = deepcopy(child_request.query)
        query.aggregates = []
        query.sampleVariance("total_amount", alias)
        self.query.relation_aggregates.append(
            RelationAggregate("customer_order_list", alias, query, True,
                QueryOperation("aggregate", "sampleVariance_total_amount_of_customer_orders_as", alias, "customer_order_list"))
        )
        return self
    def samplePopulationVariance_total_amount_of_customer_orders(self):
        from requests.customer_order_request import CustomerOrderRequest
        return self.samplePopulationVariance_total_amount_of_customer_orders_as(
            "samplePopulationVariance_total_amount_of_customer_orders", CustomerOrderRequest())

    def samplePopulationVariance_total_amount_of_customer_orders_as(self, alias: str, child_request):
        query = deepcopy(child_request.query)
        query.aggregates = []
        query.samplePopulationVariance("total_amount", alias)
        self.query.relation_aggregates.append(
            RelationAggregate("customer_order_list", alias, query, True,
                QueryOperation("aggregate", "samplePopulationVariance_total_amount_of_customer_orders_as", alias, "customer_order_list"))
        )
        return self
    def facet_by_platform_as(self, name: str, request: QuerySelection,
                                      include_all_facets: bool = True):
        self.query.facet_by(name, _TeaqlFields.PLATFORM_PROPERTY_COLUMN, request.query, include_all_facets,
            QueryOperation("facet", "facet_by_platform_as", name, _TeaqlFields.PLATFORM_PROPERTY_COLUMN))
        return self


class ExecutableOrderStatusRequest:
    def __init__(self, request):
        self._request = request

    def comment(self, c: str):
        self._request.comment(c)
        return self

    async def new_entity(self, context) -> OrderStatus:
        request = self._request
        QueryIntent(request._comment, request._purpose)
        identity = await context.next_id("OrderStatus")
        entity = context.initialize_entity("OrderStatus", OrderStatus._teaql_from_reserved_id(identity))
        if not isinstance(entity, OrderStatus):
            raise TypeError("entity initializer returned an incompatible OrderStatus")
        return entity

    async def execute_for_result(self, context):
        self = self._request
        req = QueryRequest(self.query, _comment=self._comment, _purpose=self._purpose)
        req = context.prepare_query_request(req)
        service = context.require_resource("dataService")
        return await service.query(context, req)

    async def execute_for_rows(self, context):
        return (await self.execute_for_result(context)).rows

    async def execute_for_list(self, context) -> SmartList[OrderStatus]:
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
            lambda row: OrderStatus._teaql_from_record(_entity_root=EntityRoot(), **row),
            count_operation=operation, count_alias=request._page_count_alias)

    async def execute_for_one(self, context):
        request = deepcopy(self._request)
        request.limit(1)
        entities = await ExecutableOrderStatusRequest(request).execute_for_list(context)
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
            lambda row: OrderStatus._teaql_from_record(_entity_root=EntityRoot(), **row), chunk_size)
