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
from models.freight_quote import _TeaqlFields, FreightQuote
from typing import Protocol

class QuerySelection(Protocol):
    query: SelectQuery

class FreightQuoteRequest:
    def __init__(self, minimal=False):
        self.query = SelectQuery("FreightQuote")
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
        return ExecutableFreightQuoteRequest(self)

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
        self.query.project(_TeaqlFields.ID_PROPERTY_COLUMN, _TeaqlFields.PLATFORM_PROPERTY_COLUMN, _TeaqlFields.REFERENCE_PROPERTY_COLUMN, _TeaqlFields.AMOUNT_PROPERTY_COLUMN, _TeaqlFields.SHIPMENT_NUMBER_PROPERTY_COLUMN, _TeaqlFields.PACKAGE_COUNT_PROPERTY_COLUMN, _TeaqlFields.DELIVERY_DATE_PROPERTY_COLUMN, _TeaqlFields.PICKUP_TIME_PROPERTY_COLUMN, _TeaqlFields.QUOTED_AT_PROPERTY_COLUMN, _TeaqlFields.INSTRUCTIONS_PROPERTY_COLUMN, _TeaqlFields.VERSION_PROPERTY_COLUMN)
        return self

    def select_id(self):
        self.query.project(_TeaqlFields.ID_PROPERTY_COLUMN)
        return self


    def select_reference(self):
        self.query.project(_TeaqlFields.REFERENCE_PROPERTY_COLUMN)
        return self

    def select_amount(self):
        self.query.project(_TeaqlFields.AMOUNT_PROPERTY_COLUMN)
        return self

    def select_shipment_number(self):
        self.query.project(_TeaqlFields.SHIPMENT_NUMBER_PROPERTY_COLUMN)
        return self

    def select_package_count(self):
        self.query.project(_TeaqlFields.PACKAGE_COUNT_PROPERTY_COLUMN)
        return self

    def select_delivery_date(self):
        self.query.project(_TeaqlFields.DELIVERY_DATE_PROPERTY_COLUMN)
        return self

    def select_pickup_time(self):
        self.query.project(_TeaqlFields.PICKUP_TIME_PROPERTY_COLUMN)
        return self

    def select_quoted_at(self):
        self.query.project(_TeaqlFields.QUOTED_AT_PROPERTY_COLUMN)
        return self

    def select_instructions(self):
        self.query.project(_TeaqlFields.INSTRUCTIONS_PROPERTY_COLUMN)
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

    def filter_by_platform(self, val):
        self.query.and_filter(eq(_TeaqlFields.PLATFORM_PROPERTY_COLUMN, val))
        return self

    def with_reference_containing(self, val: str):
        self.query.and_filter(contain(_TeaqlFields.REFERENCE_PROPERTY_COLUMN, val))
        return self

    def with_reference_not_containing(self, val: str):
        self.query.and_filter(not_contain(_TeaqlFields.REFERENCE_PROPERTY_COLUMN, val))
        return self

    def with_reference_starting_with(self, val: str):
        self.query.and_filter(begin_with(_TeaqlFields.REFERENCE_PROPERTY_COLUMN, val))
        return self

    def with_reference_not_starting_with(self, val: str):
        self.query.and_filter(not_begin_with(_TeaqlFields.REFERENCE_PROPERTY_COLUMN, val))
        return self

    def with_reference_ending_with(self, val: str):
        self.query.and_filter(end_with(_TeaqlFields.REFERENCE_PROPERTY_COLUMN, val))
        return self

    def with_reference_not_ending_with(self, val: str):
        self.query.and_filter(not_end_with(_TeaqlFields.REFERENCE_PROPERTY_COLUMN, val))
        return self

    def with_reference_sounding_like(self, val: str):
        self.query.and_filter(sound_like(_TeaqlFields.REFERENCE_PROPERTY_COLUMN, val))
        return self

    def with_reference_is(self, val: str):
        self.query.and_filter(eq(_TeaqlFields.REFERENCE_PROPERTY_COLUMN, val))
        return self
    def with_reference_is_not(self, val):
        self.query.and_filter(ne(_TeaqlFields.REFERENCE_PROPERTY_COLUMN, val))
        return self

    def with_reference_in(self, *vals):
        self.query.and_filter(in_list(_TeaqlFields.REFERENCE_PROPERTY_COLUMN, list(vals)))
        return self

    def with_reference_not_in(self, *vals):
        self.query.and_filter(not_in_list(_TeaqlFields.REFERENCE_PROPERTY_COLUMN, list(vals)))
        return self

    def with_reference_greater_than(self, val):
        self.query.and_filter(gt(_TeaqlFields.REFERENCE_PROPERTY_COLUMN, val))
        return self

    def with_reference_greater_than_or_equal_to(self, val):
        self.query.and_filter(gte(_TeaqlFields.REFERENCE_PROPERTY_COLUMN, val))
        return self

    def with_reference_less_than(self, val):
        self.query.and_filter(lt(_TeaqlFields.REFERENCE_PROPERTY_COLUMN, val))
        return self

    def with_reference_less_than_or_equal_to(self, val):
        self.query.and_filter(lte(_TeaqlFields.REFERENCE_PROPERTY_COLUMN, val))
        return self

    def with_reference_between(self, lower, upper):
        self.query.and_filter(between(column(_TeaqlFields.REFERENCE_PROPERTY_COLUMN), value(lower), value(upper)))
        return self

    def with_reference_is_known(self):
        self.query.and_filter(is_not_null(column(_TeaqlFields.REFERENCE_PROPERTY_COLUMN)))
        return self

    def with_reference_is_unknown(self):
        self.query.and_filter(is_null(column(_TeaqlFields.REFERENCE_PROPERTY_COLUMN)))
        return self

    def with_amount_is(self, val):
        self.query.and_filter(eq(_TeaqlFields.AMOUNT_PROPERTY_COLUMN, val))
        return self

    def with_amount_is_not(self, val):
        self.query.and_filter(ne(_TeaqlFields.AMOUNT_PROPERTY_COLUMN, val))
        return self

    def with_amount_in(self, *vals):
        self.query.and_filter(in_list(_TeaqlFields.AMOUNT_PROPERTY_COLUMN, list(vals)))
        return self

    def with_amount_not_in(self, *vals):
        self.query.and_filter(not_in_list(_TeaqlFields.AMOUNT_PROPERTY_COLUMN, list(vals)))
        return self

    def with_amount_greater_than(self, val):
        self.query.and_filter(gt(_TeaqlFields.AMOUNT_PROPERTY_COLUMN, val))
        return self

    def with_amount_greater_than_or_equal_to(self, val):
        self.query.and_filter(gte(_TeaqlFields.AMOUNT_PROPERTY_COLUMN, val))
        return self

    def with_amount_less_than(self, val):
        self.query.and_filter(lt(_TeaqlFields.AMOUNT_PROPERTY_COLUMN, val))
        return self

    def with_amount_less_than_or_equal_to(self, val):
        self.query.and_filter(lte(_TeaqlFields.AMOUNT_PROPERTY_COLUMN, val))
        return self

    def with_amount_between(self, lower, upper):
        self.query.and_filter(between(column(_TeaqlFields.AMOUNT_PROPERTY_COLUMN), value(lower), value(upper)))
        return self

    def with_amount_is_known(self):
        self.query.and_filter(is_not_null(column(_TeaqlFields.AMOUNT_PROPERTY_COLUMN)))
        return self

    def with_amount_is_unknown(self):
        self.query.and_filter(is_null(column(_TeaqlFields.AMOUNT_PROPERTY_COLUMN)))
        return self

    def with_shipment_number_is(self, val):
        self.query.and_filter(eq(_TeaqlFields.SHIPMENT_NUMBER_PROPERTY_COLUMN, val))
        return self

    def with_shipment_number_is_not(self, val):
        self.query.and_filter(ne(_TeaqlFields.SHIPMENT_NUMBER_PROPERTY_COLUMN, val))
        return self

    def with_shipment_number_in(self, *vals):
        self.query.and_filter(in_list(_TeaqlFields.SHIPMENT_NUMBER_PROPERTY_COLUMN, list(vals)))
        return self

    def with_shipment_number_not_in(self, *vals):
        self.query.and_filter(not_in_list(_TeaqlFields.SHIPMENT_NUMBER_PROPERTY_COLUMN, list(vals)))
        return self

    def with_shipment_number_greater_than(self, val):
        self.query.and_filter(gt(_TeaqlFields.SHIPMENT_NUMBER_PROPERTY_COLUMN, val))
        return self

    def with_shipment_number_greater_than_or_equal_to(self, val):
        self.query.and_filter(gte(_TeaqlFields.SHIPMENT_NUMBER_PROPERTY_COLUMN, val))
        return self

    def with_shipment_number_less_than(self, val):
        self.query.and_filter(lt(_TeaqlFields.SHIPMENT_NUMBER_PROPERTY_COLUMN, val))
        return self

    def with_shipment_number_less_than_or_equal_to(self, val):
        self.query.and_filter(lte(_TeaqlFields.SHIPMENT_NUMBER_PROPERTY_COLUMN, val))
        return self

    def with_shipment_number_between(self, lower, upper):
        self.query.and_filter(between(column(_TeaqlFields.SHIPMENT_NUMBER_PROPERTY_COLUMN), value(lower), value(upper)))
        return self

    def with_shipment_number_is_known(self):
        self.query.and_filter(is_not_null(column(_TeaqlFields.SHIPMENT_NUMBER_PROPERTY_COLUMN)))
        return self

    def with_shipment_number_is_unknown(self):
        self.query.and_filter(is_null(column(_TeaqlFields.SHIPMENT_NUMBER_PROPERTY_COLUMN)))
        return self

    def with_package_count_is(self, val):
        self.query.and_filter(eq(_TeaqlFields.PACKAGE_COUNT_PROPERTY_COLUMN, val))
        return self

    def with_package_count_is_not(self, val):
        self.query.and_filter(ne(_TeaqlFields.PACKAGE_COUNT_PROPERTY_COLUMN, val))
        return self

    def with_package_count_in(self, *vals):
        self.query.and_filter(in_list(_TeaqlFields.PACKAGE_COUNT_PROPERTY_COLUMN, list(vals)))
        return self

    def with_package_count_not_in(self, *vals):
        self.query.and_filter(not_in_list(_TeaqlFields.PACKAGE_COUNT_PROPERTY_COLUMN, list(vals)))
        return self

    def with_package_count_greater_than(self, val):
        self.query.and_filter(gt(_TeaqlFields.PACKAGE_COUNT_PROPERTY_COLUMN, val))
        return self

    def with_package_count_greater_than_or_equal_to(self, val):
        self.query.and_filter(gte(_TeaqlFields.PACKAGE_COUNT_PROPERTY_COLUMN, val))
        return self

    def with_package_count_less_than(self, val):
        self.query.and_filter(lt(_TeaqlFields.PACKAGE_COUNT_PROPERTY_COLUMN, val))
        return self

    def with_package_count_less_than_or_equal_to(self, val):
        self.query.and_filter(lte(_TeaqlFields.PACKAGE_COUNT_PROPERTY_COLUMN, val))
        return self

    def with_package_count_between(self, lower, upper):
        self.query.and_filter(between(column(_TeaqlFields.PACKAGE_COUNT_PROPERTY_COLUMN), value(lower), value(upper)))
        return self

    def with_package_count_is_known(self):
        self.query.and_filter(is_not_null(column(_TeaqlFields.PACKAGE_COUNT_PROPERTY_COLUMN)))
        return self

    def with_package_count_is_unknown(self):
        self.query.and_filter(is_null(column(_TeaqlFields.PACKAGE_COUNT_PROPERTY_COLUMN)))
        return self

    def with_delivery_date_is(self, val):
        self.query.and_filter(eq(_TeaqlFields.DELIVERY_DATE_PROPERTY_COLUMN, val))
        return self

    def with_delivery_date_is_not(self, val):
        self.query.and_filter(ne(_TeaqlFields.DELIVERY_DATE_PROPERTY_COLUMN, val))
        return self

    def with_delivery_date_in(self, *vals):
        self.query.and_filter(in_list(_TeaqlFields.DELIVERY_DATE_PROPERTY_COLUMN, list(vals)))
        return self

    def with_delivery_date_not_in(self, *vals):
        self.query.and_filter(not_in_list(_TeaqlFields.DELIVERY_DATE_PROPERTY_COLUMN, list(vals)))
        return self

    def with_delivery_date_greater_than(self, val):
        self.query.and_filter(gt(_TeaqlFields.DELIVERY_DATE_PROPERTY_COLUMN, val))
        return self

    def with_delivery_date_greater_than_or_equal_to(self, val):
        self.query.and_filter(gte(_TeaqlFields.DELIVERY_DATE_PROPERTY_COLUMN, val))
        return self

    def with_delivery_date_less_than(self, val):
        self.query.and_filter(lt(_TeaqlFields.DELIVERY_DATE_PROPERTY_COLUMN, val))
        return self

    def with_delivery_date_less_than_or_equal_to(self, val):
        self.query.and_filter(lte(_TeaqlFields.DELIVERY_DATE_PROPERTY_COLUMN, val))
        return self

    def with_delivery_date_between(self, lower, upper):
        self.query.and_filter(between(column(_TeaqlFields.DELIVERY_DATE_PROPERTY_COLUMN), value(lower), value(upper)))
        return self

    def with_delivery_date_is_known(self):
        self.query.and_filter(is_not_null(column(_TeaqlFields.DELIVERY_DATE_PROPERTY_COLUMN)))
        return self

    def with_delivery_date_is_unknown(self):
        self.query.and_filter(is_null(column(_TeaqlFields.DELIVERY_DATE_PROPERTY_COLUMN)))
        return self

    def with_pickup_time_is(self, val):
        self.query.and_filter(eq(_TeaqlFields.PICKUP_TIME_PROPERTY_COLUMN, val))
        return self

    def with_pickup_time_is_not(self, val):
        self.query.and_filter(ne(_TeaqlFields.PICKUP_TIME_PROPERTY_COLUMN, val))
        return self

    def with_pickup_time_in(self, *vals):
        self.query.and_filter(in_list(_TeaqlFields.PICKUP_TIME_PROPERTY_COLUMN, list(vals)))
        return self

    def with_pickup_time_not_in(self, *vals):
        self.query.and_filter(not_in_list(_TeaqlFields.PICKUP_TIME_PROPERTY_COLUMN, list(vals)))
        return self

    def with_pickup_time_greater_than(self, val):
        self.query.and_filter(gt(_TeaqlFields.PICKUP_TIME_PROPERTY_COLUMN, val))
        return self

    def with_pickup_time_greater_than_or_equal_to(self, val):
        self.query.and_filter(gte(_TeaqlFields.PICKUP_TIME_PROPERTY_COLUMN, val))
        return self

    def with_pickup_time_less_than(self, val):
        self.query.and_filter(lt(_TeaqlFields.PICKUP_TIME_PROPERTY_COLUMN, val))
        return self

    def with_pickup_time_less_than_or_equal_to(self, val):
        self.query.and_filter(lte(_TeaqlFields.PICKUP_TIME_PROPERTY_COLUMN, val))
        return self

    def with_pickup_time_between(self, lower, upper):
        self.query.and_filter(between(column(_TeaqlFields.PICKUP_TIME_PROPERTY_COLUMN), value(lower), value(upper)))
        return self

    def with_pickup_time_is_known(self):
        self.query.and_filter(is_not_null(column(_TeaqlFields.PICKUP_TIME_PROPERTY_COLUMN)))
        return self

    def with_pickup_time_is_unknown(self):
        self.query.and_filter(is_null(column(_TeaqlFields.PICKUP_TIME_PROPERTY_COLUMN)))
        return self

    def with_quoted_at_is(self, val):
        self.query.and_filter(eq(_TeaqlFields.QUOTED_AT_PROPERTY_COLUMN, val))
        return self

    def with_quoted_at_is_not(self, val):
        self.query.and_filter(ne(_TeaqlFields.QUOTED_AT_PROPERTY_COLUMN, val))
        return self

    def with_quoted_at_in(self, *vals):
        self.query.and_filter(in_list(_TeaqlFields.QUOTED_AT_PROPERTY_COLUMN, list(vals)))
        return self

    def with_quoted_at_not_in(self, *vals):
        self.query.and_filter(not_in_list(_TeaqlFields.QUOTED_AT_PROPERTY_COLUMN, list(vals)))
        return self

    def with_quoted_at_greater_than(self, val):
        self.query.and_filter(gt(_TeaqlFields.QUOTED_AT_PROPERTY_COLUMN, val))
        return self

    def with_quoted_at_greater_than_or_equal_to(self, val):
        self.query.and_filter(gte(_TeaqlFields.QUOTED_AT_PROPERTY_COLUMN, val))
        return self

    def with_quoted_at_less_than(self, val):
        self.query.and_filter(lt(_TeaqlFields.QUOTED_AT_PROPERTY_COLUMN, val))
        return self

    def with_quoted_at_less_than_or_equal_to(self, val):
        self.query.and_filter(lte(_TeaqlFields.QUOTED_AT_PROPERTY_COLUMN, val))
        return self

    def with_quoted_at_between(self, lower, upper):
        self.query.and_filter(between(column(_TeaqlFields.QUOTED_AT_PROPERTY_COLUMN), value(lower), value(upper)))
        return self

    def with_quoted_at_is_known(self):
        self.query.and_filter(is_not_null(column(_TeaqlFields.QUOTED_AT_PROPERTY_COLUMN)))
        return self

    def with_quoted_at_is_unknown(self):
        self.query.and_filter(is_null(column(_TeaqlFields.QUOTED_AT_PROPERTY_COLUMN)))
        return self

    def with_instructions_containing(self, val: str):
        self.query.and_filter(contain(_TeaqlFields.INSTRUCTIONS_PROPERTY_COLUMN, val))
        return self

    def with_instructions_not_containing(self, val: str):
        self.query.and_filter(not_contain(_TeaqlFields.INSTRUCTIONS_PROPERTY_COLUMN, val))
        return self

    def with_instructions_starting_with(self, val: str):
        self.query.and_filter(begin_with(_TeaqlFields.INSTRUCTIONS_PROPERTY_COLUMN, val))
        return self

    def with_instructions_not_starting_with(self, val: str):
        self.query.and_filter(not_begin_with(_TeaqlFields.INSTRUCTIONS_PROPERTY_COLUMN, val))
        return self

    def with_instructions_ending_with(self, val: str):
        self.query.and_filter(end_with(_TeaqlFields.INSTRUCTIONS_PROPERTY_COLUMN, val))
        return self

    def with_instructions_not_ending_with(self, val: str):
        self.query.and_filter(not_end_with(_TeaqlFields.INSTRUCTIONS_PROPERTY_COLUMN, val))
        return self

    def with_instructions_sounding_like(self, val: str):
        self.query.and_filter(sound_like(_TeaqlFields.INSTRUCTIONS_PROPERTY_COLUMN, val))
        return self

    def with_instructions_is(self, val: str):
        self.query.and_filter(eq(_TeaqlFields.INSTRUCTIONS_PROPERTY_COLUMN, val))
        return self
    def with_instructions_is_not(self, val):
        self.query.and_filter(ne(_TeaqlFields.INSTRUCTIONS_PROPERTY_COLUMN, val))
        return self

    def with_instructions_in(self, *vals):
        self.query.and_filter(in_list(_TeaqlFields.INSTRUCTIONS_PROPERTY_COLUMN, list(vals)))
        return self

    def with_instructions_not_in(self, *vals):
        self.query.and_filter(not_in_list(_TeaqlFields.INSTRUCTIONS_PROPERTY_COLUMN, list(vals)))
        return self

    def with_instructions_greater_than(self, val):
        self.query.and_filter(gt(_TeaqlFields.INSTRUCTIONS_PROPERTY_COLUMN, val))
        return self

    def with_instructions_greater_than_or_equal_to(self, val):
        self.query.and_filter(gte(_TeaqlFields.INSTRUCTIONS_PROPERTY_COLUMN, val))
        return self

    def with_instructions_less_than(self, val):
        self.query.and_filter(lt(_TeaqlFields.INSTRUCTIONS_PROPERTY_COLUMN, val))
        return self

    def with_instructions_less_than_or_equal_to(self, val):
        self.query.and_filter(lte(_TeaqlFields.INSTRUCTIONS_PROPERTY_COLUMN, val))
        return self

    def with_instructions_between(self, lower, upper):
        self.query.and_filter(between(column(_TeaqlFields.INSTRUCTIONS_PROPERTY_COLUMN), value(lower), value(upper)))
        return self

    def with_instructions_is_known(self):
        self.query.and_filter(is_not_null(column(_TeaqlFields.INSTRUCTIONS_PROPERTY_COLUMN)))
        return self

    def with_instructions_is_unknown(self):
        self.query.and_filter(is_null(column(_TeaqlFields.INSTRUCTIONS_PROPERTY_COLUMN)))
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


    def order_by_reference_ascending(self):
        self.query.order_by(_TeaqlFields.REFERENCE_PROPERTY_COLUMN, "asc")
        return self

    def order_by_reference_descending(self):
        self.query.order_by(_TeaqlFields.REFERENCE_PROPERTY_COLUMN, "desc")
        return self

    def order_by_amount_ascending(self):
        self.query.order_by(_TeaqlFields.AMOUNT_PROPERTY_COLUMN, "asc")
        return self

    def order_by_amount_descending(self):
        self.query.order_by(_TeaqlFields.AMOUNT_PROPERTY_COLUMN, "desc")
        return self

    def order_by_shipment_number_ascending(self):
        self.query.order_by(_TeaqlFields.SHIPMENT_NUMBER_PROPERTY_COLUMN, "asc")
        return self

    def order_by_shipment_number_descending(self):
        self.query.order_by(_TeaqlFields.SHIPMENT_NUMBER_PROPERTY_COLUMN, "desc")
        return self

    def order_by_package_count_ascending(self):
        self.query.order_by(_TeaqlFields.PACKAGE_COUNT_PROPERTY_COLUMN, "asc")
        return self

    def order_by_package_count_descending(self):
        self.query.order_by(_TeaqlFields.PACKAGE_COUNT_PROPERTY_COLUMN, "desc")
        return self

    def order_by_delivery_date_ascending(self):
        self.query.order_by(_TeaqlFields.DELIVERY_DATE_PROPERTY_COLUMN, "asc")
        return self

    def order_by_delivery_date_descending(self):
        self.query.order_by(_TeaqlFields.DELIVERY_DATE_PROPERTY_COLUMN, "desc")
        return self

    def order_by_pickup_time_ascending(self):
        self.query.order_by(_TeaqlFields.PICKUP_TIME_PROPERTY_COLUMN, "asc")
        return self

    def order_by_pickup_time_descending(self):
        self.query.order_by(_TeaqlFields.PICKUP_TIME_PROPERTY_COLUMN, "desc")
        return self

    def order_by_quoted_at_ascending(self):
        self.query.order_by(_TeaqlFields.QUOTED_AT_PROPERTY_COLUMN, "asc")
        return self

    def order_by_quoted_at_descending(self):
        self.query.order_by(_TeaqlFields.QUOTED_AT_PROPERTY_COLUMN, "desc")
        return self

    def order_by_instructions_ascending(self):
        self.query.order_by(_TeaqlFields.INSTRUCTIONS_PROPERTY_COLUMN, "asc")
        return self

    def order_by_instructions_descending(self):
        self.query.order_by(_TeaqlFields.INSTRUCTIONS_PROPERTY_COLUMN, "desc")
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

    def min_amount(self):
        return self.min_amount_as("minOfAmount")

    def min_amount_as(self, ret_name: str):
        self.query.min(_TeaqlFields.AMOUNT_PROPERTY_COLUMN, ret_name)
        return self
    def max_amount(self):
        return self.max_amount_as("maxOfAmount")

    def max_amount_as(self, ret_name: str):
        self.query.max(_TeaqlFields.AMOUNT_PROPERTY_COLUMN, ret_name)
        return self
    def sum_amount(self):
        return self.sum_amount_as("sumOfAmount")

    def sum_amount_as(self, ret_name: str):
        self.query.sum(_TeaqlFields.AMOUNT_PROPERTY_COLUMN, ret_name)
        return self
    def avg_amount(self):
        return self.avg_amount_as("avgOfAmount")

    def avg_amount_as(self, ret_name: str):
        self.query.avg(_TeaqlFields.AMOUNT_PROPERTY_COLUMN, ret_name)
        return self
    def standardDeviation_amount(self):
        return self.standardDeviation_amount_as("standardDeviationOfAmount")

    def standardDeviation_amount_as(self, ret_name: str):
        self.query.standardDeviation(_TeaqlFields.AMOUNT_PROPERTY_COLUMN, ret_name)
        return self
    def squareRootOfPopulationStandardDeviation_amount(self):
        return self.squareRootOfPopulationStandardDeviation_amount_as("squareRootOfPopulationStandardDeviationOfAmount")

    def squareRootOfPopulationStandardDeviation_amount_as(self, ret_name: str):
        self.query.squareRootOfPopulationStandardDeviation(_TeaqlFields.AMOUNT_PROPERTY_COLUMN, ret_name)
        return self
    def sampleVariance_amount(self):
        return self.sampleVariance_amount_as("sampleVarianceOfAmount")

    def sampleVariance_amount_as(self, ret_name: str):
        self.query.sampleVariance(_TeaqlFields.AMOUNT_PROPERTY_COLUMN, ret_name)
        return self
    def samplePopulationVariance_amount(self):
        return self.samplePopulationVariance_amount_as("samplePopulationVarianceOfAmount")

    def samplePopulationVariance_amount_as(self, ret_name: str):
        self.query.samplePopulationVariance(_TeaqlFields.AMOUNT_PROPERTY_COLUMN, ret_name)
        return self
    def min_shipment_number(self):
        return self.min_shipment_number_as("minOfShipmentNumber")

    def min_shipment_number_as(self, ret_name: str):
        self.query.min(_TeaqlFields.SHIPMENT_NUMBER_PROPERTY_COLUMN, ret_name)
        return self
    def max_shipment_number(self):
        return self.max_shipment_number_as("maxOfShipmentNumber")

    def max_shipment_number_as(self, ret_name: str):
        self.query.max(_TeaqlFields.SHIPMENT_NUMBER_PROPERTY_COLUMN, ret_name)
        return self
    def sum_shipment_number(self):
        return self.sum_shipment_number_as("sumOfShipmentNumber")

    def sum_shipment_number_as(self, ret_name: str):
        self.query.sum(_TeaqlFields.SHIPMENT_NUMBER_PROPERTY_COLUMN, ret_name)
        return self
    def avg_shipment_number(self):
        return self.avg_shipment_number_as("avgOfShipmentNumber")

    def avg_shipment_number_as(self, ret_name: str):
        self.query.avg(_TeaqlFields.SHIPMENT_NUMBER_PROPERTY_COLUMN, ret_name)
        return self
    def standardDeviation_shipment_number(self):
        return self.standardDeviation_shipment_number_as("standardDeviationOfShipmentNumber")

    def standardDeviation_shipment_number_as(self, ret_name: str):
        self.query.standardDeviation(_TeaqlFields.SHIPMENT_NUMBER_PROPERTY_COLUMN, ret_name)
        return self
    def squareRootOfPopulationStandardDeviation_shipment_number(self):
        return self.squareRootOfPopulationStandardDeviation_shipment_number_as("squareRootOfPopulationStandardDeviationOfShipmentNumber")

    def squareRootOfPopulationStandardDeviation_shipment_number_as(self, ret_name: str):
        self.query.squareRootOfPopulationStandardDeviation(_TeaqlFields.SHIPMENT_NUMBER_PROPERTY_COLUMN, ret_name)
        return self
    def sampleVariance_shipment_number(self):
        return self.sampleVariance_shipment_number_as("sampleVarianceOfShipmentNumber")

    def sampleVariance_shipment_number_as(self, ret_name: str):
        self.query.sampleVariance(_TeaqlFields.SHIPMENT_NUMBER_PROPERTY_COLUMN, ret_name)
        return self
    def samplePopulationVariance_shipment_number(self):
        return self.samplePopulationVariance_shipment_number_as("samplePopulationVarianceOfShipmentNumber")

    def samplePopulationVariance_shipment_number_as(self, ret_name: str):
        self.query.samplePopulationVariance(_TeaqlFields.SHIPMENT_NUMBER_PROPERTY_COLUMN, ret_name)
        return self
    def min_package_count(self):
        return self.min_package_count_as("minOfPackageCount")

    def min_package_count_as(self, ret_name: str):
        self.query.min(_TeaqlFields.PACKAGE_COUNT_PROPERTY_COLUMN, ret_name)
        return self
    def max_package_count(self):
        return self.max_package_count_as("maxOfPackageCount")

    def max_package_count_as(self, ret_name: str):
        self.query.max(_TeaqlFields.PACKAGE_COUNT_PROPERTY_COLUMN, ret_name)
        return self
    def sum_package_count(self):
        return self.sum_package_count_as("sumOfPackageCount")

    def sum_package_count_as(self, ret_name: str):
        self.query.sum(_TeaqlFields.PACKAGE_COUNT_PROPERTY_COLUMN, ret_name)
        return self
    def avg_package_count(self):
        return self.avg_package_count_as("avgOfPackageCount")

    def avg_package_count_as(self, ret_name: str):
        self.query.avg(_TeaqlFields.PACKAGE_COUNT_PROPERTY_COLUMN, ret_name)
        return self
    def standardDeviation_package_count(self):
        return self.standardDeviation_package_count_as("standardDeviationOfPackageCount")

    def standardDeviation_package_count_as(self, ret_name: str):
        self.query.standardDeviation(_TeaqlFields.PACKAGE_COUNT_PROPERTY_COLUMN, ret_name)
        return self
    def squareRootOfPopulationStandardDeviation_package_count(self):
        return self.squareRootOfPopulationStandardDeviation_package_count_as("squareRootOfPopulationStandardDeviationOfPackageCount")

    def squareRootOfPopulationStandardDeviation_package_count_as(self, ret_name: str):
        self.query.squareRootOfPopulationStandardDeviation(_TeaqlFields.PACKAGE_COUNT_PROPERTY_COLUMN, ret_name)
        return self
    def sampleVariance_package_count(self):
        return self.sampleVariance_package_count_as("sampleVarianceOfPackageCount")

    def sampleVariance_package_count_as(self, ret_name: str):
        self.query.sampleVariance(_TeaqlFields.PACKAGE_COUNT_PROPERTY_COLUMN, ret_name)
        return self
    def samplePopulationVariance_package_count(self):
        return self.samplePopulationVariance_package_count_as("samplePopulationVarianceOfPackageCount")

    def samplePopulationVariance_package_count_as(self, ret_name: str):
        self.query.samplePopulationVariance(_TeaqlFields.PACKAGE_COUNT_PROPERTY_COLUMN, ret_name)
        return self
    def group_by_id(self):
        self.query.group_by(_TeaqlFields.ID_PROPERTY_COLUMN)
        return self

    def group_by_id_as(self, ret_name: str):
        self.query.group_by(_TeaqlFields.ID_PROPERTY_COLUMN)
        self.query.project_expr(ret_name, column(_TeaqlFields.ID_PROPERTY_COLUMN))
        return self
    def group_by_platform(self):
        self.query.group_by(_TeaqlFields.PLATFORM_PROPERTY_COLUMN)
        return self

    def group_by_platform_as(self, ret_name: str):
        self.query.group_by(_TeaqlFields.PLATFORM_PROPERTY_COLUMN)
        self.query.project_expr(ret_name, column(_TeaqlFields.PLATFORM_PROPERTY_COLUMN))
        return self
    def group_by_reference(self):
        self.query.group_by(_TeaqlFields.REFERENCE_PROPERTY_COLUMN)
        return self

    def group_by_reference_as(self, ret_name: str):
        self.query.group_by(_TeaqlFields.REFERENCE_PROPERTY_COLUMN)
        self.query.project_expr(ret_name, column(_TeaqlFields.REFERENCE_PROPERTY_COLUMN))
        return self
    def group_by_amount(self):
        self.query.group_by(_TeaqlFields.AMOUNT_PROPERTY_COLUMN)
        return self

    def group_by_amount_as(self, ret_name: str):
        self.query.group_by(_TeaqlFields.AMOUNT_PROPERTY_COLUMN)
        self.query.project_expr(ret_name, column(_TeaqlFields.AMOUNT_PROPERTY_COLUMN))
        return self
    def group_by_shipment_number(self):
        self.query.group_by(_TeaqlFields.SHIPMENT_NUMBER_PROPERTY_COLUMN)
        return self

    def group_by_shipment_number_as(self, ret_name: str):
        self.query.group_by(_TeaqlFields.SHIPMENT_NUMBER_PROPERTY_COLUMN)
        self.query.project_expr(ret_name, column(_TeaqlFields.SHIPMENT_NUMBER_PROPERTY_COLUMN))
        return self
    def group_by_package_count(self):
        self.query.group_by(_TeaqlFields.PACKAGE_COUNT_PROPERTY_COLUMN)
        return self

    def group_by_package_count_as(self, ret_name: str):
        self.query.group_by(_TeaqlFields.PACKAGE_COUNT_PROPERTY_COLUMN)
        self.query.project_expr(ret_name, column(_TeaqlFields.PACKAGE_COUNT_PROPERTY_COLUMN))
        return self
    def group_by_delivery_date(self):
        self.query.group_by(_TeaqlFields.DELIVERY_DATE_PROPERTY_COLUMN)
        return self

    def group_by_delivery_date_as(self, ret_name: str):
        self.query.group_by(_TeaqlFields.DELIVERY_DATE_PROPERTY_COLUMN)
        self.query.project_expr(ret_name, column(_TeaqlFields.DELIVERY_DATE_PROPERTY_COLUMN))
        return self
    def group_by_pickup_time(self):
        self.query.group_by(_TeaqlFields.PICKUP_TIME_PROPERTY_COLUMN)
        return self

    def group_by_pickup_time_as(self, ret_name: str):
        self.query.group_by(_TeaqlFields.PICKUP_TIME_PROPERTY_COLUMN)
        self.query.project_expr(ret_name, column(_TeaqlFields.PICKUP_TIME_PROPERTY_COLUMN))
        return self
    def group_by_quoted_at(self):
        self.query.group_by(_TeaqlFields.QUOTED_AT_PROPERTY_COLUMN)
        return self

    def group_by_quoted_at_as(self, ret_name: str):
        self.query.group_by(_TeaqlFields.QUOTED_AT_PROPERTY_COLUMN)
        self.query.project_expr(ret_name, column(_TeaqlFields.QUOTED_AT_PROPERTY_COLUMN))
        return self
    def group_by_instructions(self):
        self.query.group_by(_TeaqlFields.INSTRUCTIONS_PROPERTY_COLUMN)
        return self

    def group_by_instructions_as(self, ret_name: str):
        self.query.group_by(_TeaqlFields.INSTRUCTIONS_PROPERTY_COLUMN)
        self.query.project_expr(ret_name, column(_TeaqlFields.INSTRUCTIONS_PROPERTY_COLUMN))
        return self
    def group_by_version(self):
        self.query.group_by(_TeaqlFields.VERSION_PROPERTY_COLUMN)
        return self

    def group_by_version_as(self, ret_name: str):
        self.query.group_by(_TeaqlFields.VERSION_PROPERTY_COLUMN)
        self.query.project_expr(ret_name, column(_TeaqlFields.VERSION_PROPERTY_COLUMN))
        return self
    def facet_by_platform_as(self, name: str, request: QuerySelection,
                                      include_all_facets: bool = True):
        self.query.facet_by(name, _TeaqlFields.PLATFORM_PROPERTY_COLUMN, request.query, include_all_facets,
            QueryOperation("facet", "facet_by_platform_as", name, _TeaqlFields.PLATFORM_PROPERTY_COLUMN))
        return self


class ExecutableFreightQuoteRequest:
    def __init__(self, request):
        self._request = request

    def comment(self, c: str):
        self._request.comment(c)
        return self

    async def new_entity(self, context) -> FreightQuote:
        request = self._request
        QueryIntent(request._comment, request._purpose)
        identity = await context.next_id("FreightQuote")
        entity = context.initialize_entity("FreightQuote", FreightQuote._teaql_from_reserved_id(identity))
        if not isinstance(entity, FreightQuote):
            raise TypeError("entity initializer returned an incompatible FreightQuote")
        return entity

    async def execute_for_result(self, context):
        self = self._request
        req = QueryRequest(self.query, _comment=self._comment, _purpose=self._purpose)
        req = context.prepare_query_request(req)
        service = context.require_resource("dataService")
        return await service.query(context, req)

    async def execute_for_rows(self, context):
        return (await self.execute_for_result(context)).rows

    async def execute_for_list(self, context) -> SmartList[FreightQuote]:
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
            lambda row: FreightQuote._teaql_from_record(_entity_root=EntityRoot(), **row),
            count_operation=operation, count_alias=request._page_count_alias)

    async def execute_for_one(self, context):
        request = deepcopy(self._request)
        request.limit(1)
        entities = await ExecutableFreightQuoteRequest(request).execute_for_list(context)
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
            lambda row: FreightQuote._teaql_from_record(_entity_root=EntityRoot(), **row), chunk_size)
