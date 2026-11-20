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
from models.freight_quote import FreightQuote
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
        self.query.project("id", "platform", "reference", "amount", "shipment_number", "package_count", "delivery_date", "pickup_time", "quoted_at", "instructions", "version")
        return self

    def select_id(self):
        self.query.project("id")
        return self


    def select_reference(self):
        self.query.project("reference")
        return self

    def select_amount(self):
        self.query.project("amount")
        return self

    def select_shipment_number(self):
        self.query.project("shipment_number")
        return self

    def select_package_count(self):
        self.query.project("package_count")
        return self

    def select_delivery_date(self):
        self.query.project("delivery_date")
        return self

    def select_pickup_time(self):
        self.query.project("pickup_time")
        return self

    def select_quoted_at(self):
        self.query.project("quoted_at")
        return self

    def select_instructions(self):
        self.query.project("instructions")
        return self

    def select_version(self):
        self.query.project("version")
        return self

    def select_platform_with(self, child_request):
        self.query.project("platform")
        self.query.relation_query("platform", child_request.query,
            QueryOperation("relation-select", "select_platform_with", relation="platform"))
        return self
    def with_platform_matching(self, child_request):
        child_request.query.projection = ["id"]
        self.query.and_filter(in_subquery(column("platform"), "Platform", child_request.query))
        return self

    def without_platform_matching(self, child_request):
        child_request.query.projection = ["id"]
        self.query.and_filter(not_in_subquery(column("platform"), "Platform", child_request.query))
        return self

    def have_platform(self):
        self.query.and_filter(is_not_null(column("platform")))
        return self

    def have_no_platform(self):
        self.query.and_filter(is_null(column("platform")))
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

    def filter_by_platform(self, val):
        self.query.and_filter(eq("platform", val))
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

    def with_amount_is(self, val):
        self.query.and_filter(eq("amount", val))
        return self

    def with_amount_is_not(self, val):
        self.query.and_filter(ne("amount", val))
        return self

    def with_amount_in(self, *vals):
        self.query.and_filter(in_list("amount", list(vals)))
        return self

    def with_amount_not_in(self, *vals):
        self.query.and_filter(not_in_list("amount", list(vals)))
        return self

    def with_amount_greater_than(self, val):
        self.query.and_filter(gt("amount", val))
        return self

    def with_amount_greater_than_or_equal_to(self, val):
        self.query.and_filter(gte("amount", val))
        return self

    def with_amount_less_than(self, val):
        self.query.and_filter(lt("amount", val))
        return self

    def with_amount_less_than_or_equal_to(self, val):
        self.query.and_filter(lte("amount", val))
        return self

    def with_amount_between(self, lower, upper):
        self.query.and_filter(between(column("amount"), value(lower), value(upper)))
        return self

    def with_amount_is_known(self):
        self.query.and_filter(is_not_null(column("amount")))
        return self

    def with_amount_is_unknown(self):
        self.query.and_filter(is_null(column("amount")))
        return self

    def with_shipment_number_is(self, val):
        self.query.and_filter(eq("shipment_number", val))
        return self

    def with_shipment_number_is_not(self, val):
        self.query.and_filter(ne("shipment_number", val))
        return self

    def with_shipment_number_in(self, *vals):
        self.query.and_filter(in_list("shipment_number", list(vals)))
        return self

    def with_shipment_number_not_in(self, *vals):
        self.query.and_filter(not_in_list("shipment_number", list(vals)))
        return self

    def with_shipment_number_greater_than(self, val):
        self.query.and_filter(gt("shipment_number", val))
        return self

    def with_shipment_number_greater_than_or_equal_to(self, val):
        self.query.and_filter(gte("shipment_number", val))
        return self

    def with_shipment_number_less_than(self, val):
        self.query.and_filter(lt("shipment_number", val))
        return self

    def with_shipment_number_less_than_or_equal_to(self, val):
        self.query.and_filter(lte("shipment_number", val))
        return self

    def with_shipment_number_between(self, lower, upper):
        self.query.and_filter(between(column("shipment_number"), value(lower), value(upper)))
        return self

    def with_shipment_number_is_known(self):
        self.query.and_filter(is_not_null(column("shipment_number")))
        return self

    def with_shipment_number_is_unknown(self):
        self.query.and_filter(is_null(column("shipment_number")))
        return self

    def with_package_count_is(self, val):
        self.query.and_filter(eq("package_count", val))
        return self

    def with_package_count_is_not(self, val):
        self.query.and_filter(ne("package_count", val))
        return self

    def with_package_count_in(self, *vals):
        self.query.and_filter(in_list("package_count", list(vals)))
        return self

    def with_package_count_not_in(self, *vals):
        self.query.and_filter(not_in_list("package_count", list(vals)))
        return self

    def with_package_count_greater_than(self, val):
        self.query.and_filter(gt("package_count", val))
        return self

    def with_package_count_greater_than_or_equal_to(self, val):
        self.query.and_filter(gte("package_count", val))
        return self

    def with_package_count_less_than(self, val):
        self.query.and_filter(lt("package_count", val))
        return self

    def with_package_count_less_than_or_equal_to(self, val):
        self.query.and_filter(lte("package_count", val))
        return self

    def with_package_count_between(self, lower, upper):
        self.query.and_filter(between(column("package_count"), value(lower), value(upper)))
        return self

    def with_package_count_is_known(self):
        self.query.and_filter(is_not_null(column("package_count")))
        return self

    def with_package_count_is_unknown(self):
        self.query.and_filter(is_null(column("package_count")))
        return self

    def with_delivery_date_is(self, val):
        self.query.and_filter(eq("delivery_date", val))
        return self

    def with_delivery_date_is_not(self, val):
        self.query.and_filter(ne("delivery_date", val))
        return self

    def with_delivery_date_in(self, *vals):
        self.query.and_filter(in_list("delivery_date", list(vals)))
        return self

    def with_delivery_date_not_in(self, *vals):
        self.query.and_filter(not_in_list("delivery_date", list(vals)))
        return self

    def with_delivery_date_greater_than(self, val):
        self.query.and_filter(gt("delivery_date", val))
        return self

    def with_delivery_date_greater_than_or_equal_to(self, val):
        self.query.and_filter(gte("delivery_date", val))
        return self

    def with_delivery_date_less_than(self, val):
        self.query.and_filter(lt("delivery_date", val))
        return self

    def with_delivery_date_less_than_or_equal_to(self, val):
        self.query.and_filter(lte("delivery_date", val))
        return self

    def with_delivery_date_between(self, lower, upper):
        self.query.and_filter(between(column("delivery_date"), value(lower), value(upper)))
        return self

    def with_delivery_date_is_known(self):
        self.query.and_filter(is_not_null(column("delivery_date")))
        return self

    def with_delivery_date_is_unknown(self):
        self.query.and_filter(is_null(column("delivery_date")))
        return self

    def with_pickup_time_is(self, val):
        self.query.and_filter(eq("pickup_time", val))
        return self

    def with_pickup_time_is_not(self, val):
        self.query.and_filter(ne("pickup_time", val))
        return self

    def with_pickup_time_in(self, *vals):
        self.query.and_filter(in_list("pickup_time", list(vals)))
        return self

    def with_pickup_time_not_in(self, *vals):
        self.query.and_filter(not_in_list("pickup_time", list(vals)))
        return self

    def with_pickup_time_greater_than(self, val):
        self.query.and_filter(gt("pickup_time", val))
        return self

    def with_pickup_time_greater_than_or_equal_to(self, val):
        self.query.and_filter(gte("pickup_time", val))
        return self

    def with_pickup_time_less_than(self, val):
        self.query.and_filter(lt("pickup_time", val))
        return self

    def with_pickup_time_less_than_or_equal_to(self, val):
        self.query.and_filter(lte("pickup_time", val))
        return self

    def with_pickup_time_between(self, lower, upper):
        self.query.and_filter(between(column("pickup_time"), value(lower), value(upper)))
        return self

    def with_pickup_time_is_known(self):
        self.query.and_filter(is_not_null(column("pickup_time")))
        return self

    def with_pickup_time_is_unknown(self):
        self.query.and_filter(is_null(column("pickup_time")))
        return self

    def with_quoted_at_is(self, val):
        self.query.and_filter(eq("quoted_at", val))
        return self

    def with_quoted_at_is_not(self, val):
        self.query.and_filter(ne("quoted_at", val))
        return self

    def with_quoted_at_in(self, *vals):
        self.query.and_filter(in_list("quoted_at", list(vals)))
        return self

    def with_quoted_at_not_in(self, *vals):
        self.query.and_filter(not_in_list("quoted_at", list(vals)))
        return self

    def with_quoted_at_greater_than(self, val):
        self.query.and_filter(gt("quoted_at", val))
        return self

    def with_quoted_at_greater_than_or_equal_to(self, val):
        self.query.and_filter(gte("quoted_at", val))
        return self

    def with_quoted_at_less_than(self, val):
        self.query.and_filter(lt("quoted_at", val))
        return self

    def with_quoted_at_less_than_or_equal_to(self, val):
        self.query.and_filter(lte("quoted_at", val))
        return self

    def with_quoted_at_between(self, lower, upper):
        self.query.and_filter(between(column("quoted_at"), value(lower), value(upper)))
        return self

    def with_quoted_at_is_known(self):
        self.query.and_filter(is_not_null(column("quoted_at")))
        return self

    def with_quoted_at_is_unknown(self):
        self.query.and_filter(is_null(column("quoted_at")))
        return self

    def with_instructions_containing(self, val: str):
        self.query.and_filter(contain("instructions", val))
        return self

    def with_instructions_not_containing(self, val: str):
        self.query.and_filter(not_contain("instructions", val))
        return self

    def with_instructions_starting_with(self, val: str):
        self.query.and_filter(begin_with("instructions", val))
        return self

    def with_instructions_not_starting_with(self, val: str):
        self.query.and_filter(not_begin_with("instructions", val))
        return self

    def with_instructions_ending_with(self, val: str):
        self.query.and_filter(end_with("instructions", val))
        return self

    def with_instructions_not_ending_with(self, val: str):
        self.query.and_filter(not_end_with("instructions", val))
        return self

    def with_instructions_sounding_like(self, val: str):
        self.query.and_filter(sound_like("instructions", val))
        return self

    def with_instructions_is(self, val: str):
        self.query.and_filter(eq("instructions", val))
        return self
    def with_instructions_is_not(self, val):
        self.query.and_filter(ne("instructions", val))
        return self

    def with_instructions_in(self, *vals):
        self.query.and_filter(in_list("instructions", list(vals)))
        return self

    def with_instructions_not_in(self, *vals):
        self.query.and_filter(not_in_list("instructions", list(vals)))
        return self

    def with_instructions_greater_than(self, val):
        self.query.and_filter(gt("instructions", val))
        return self

    def with_instructions_greater_than_or_equal_to(self, val):
        self.query.and_filter(gte("instructions", val))
        return self

    def with_instructions_less_than(self, val):
        self.query.and_filter(lt("instructions", val))
        return self

    def with_instructions_less_than_or_equal_to(self, val):
        self.query.and_filter(lte("instructions", val))
        return self

    def with_instructions_between(self, lower, upper):
        self.query.and_filter(between(column("instructions"), value(lower), value(upper)))
        return self

    def with_instructions_is_known(self):
        self.query.and_filter(is_not_null(column("instructions")))
        return self

    def with_instructions_is_unknown(self):
        self.query.and_filter(is_null(column("instructions")))
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

    def order_by_amount_ascending(self):
        self.query.order_by("amount", "asc")
        return self

    def order_by_amount_descending(self):
        self.query.order_by("amount", "desc")
        return self

    def order_by_shipment_number_ascending(self):
        self.query.order_by("shipment_number", "asc")
        return self

    def order_by_shipment_number_descending(self):
        self.query.order_by("shipment_number", "desc")
        return self

    def order_by_package_count_ascending(self):
        self.query.order_by("package_count", "asc")
        return self

    def order_by_package_count_descending(self):
        self.query.order_by("package_count", "desc")
        return self

    def order_by_delivery_date_ascending(self):
        self.query.order_by("delivery_date", "asc")
        return self

    def order_by_delivery_date_descending(self):
        self.query.order_by("delivery_date", "desc")
        return self

    def order_by_pickup_time_ascending(self):
        self.query.order_by("pickup_time", "asc")
        return self

    def order_by_pickup_time_descending(self):
        self.query.order_by("pickup_time", "desc")
        return self

    def order_by_quoted_at_ascending(self):
        self.query.order_by("quoted_at", "asc")
        return self

    def order_by_quoted_at_descending(self):
        self.query.order_by("quoted_at", "desc")
        return self

    def order_by_instructions_ascending(self):
        self.query.order_by("instructions", "asc")
        return self

    def order_by_instructions_descending(self):
        self.query.order_by("instructions", "desc")
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

    def min_amount(self):
        return self.min_amount_as("minOfAmount")

    def min_amount_as(self, ret_name: str):
        self.query.min("amount", ret_name)
        return self
    def max_amount(self):
        return self.max_amount_as("maxOfAmount")

    def max_amount_as(self, ret_name: str):
        self.query.max("amount", ret_name)
        return self
    def sum_amount(self):
        return self.sum_amount_as("sumOfAmount")

    def sum_amount_as(self, ret_name: str):
        self.query.sum("amount", ret_name)
        return self
    def avg_amount(self):
        return self.avg_amount_as("avgOfAmount")

    def avg_amount_as(self, ret_name: str):
        self.query.avg("amount", ret_name)
        return self
    def standardDeviation_amount(self):
        return self.standardDeviation_amount_as("standardDeviationOfAmount")

    def standardDeviation_amount_as(self, ret_name: str):
        self.query.standardDeviation("amount", ret_name)
        return self
    def squareRootOfPopulationStandardDeviation_amount(self):
        return self.squareRootOfPopulationStandardDeviation_amount_as("squareRootOfPopulationStandardDeviationOfAmount")

    def squareRootOfPopulationStandardDeviation_amount_as(self, ret_name: str):
        self.query.squareRootOfPopulationStandardDeviation("amount", ret_name)
        return self
    def sampleVariance_amount(self):
        return self.sampleVariance_amount_as("sampleVarianceOfAmount")

    def sampleVariance_amount_as(self, ret_name: str):
        self.query.sampleVariance("amount", ret_name)
        return self
    def samplePopulationVariance_amount(self):
        return self.samplePopulationVariance_amount_as("samplePopulationVarianceOfAmount")

    def samplePopulationVariance_amount_as(self, ret_name: str):
        self.query.samplePopulationVariance("amount", ret_name)
        return self
    def min_shipment_number(self):
        return self.min_shipment_number_as("minOfShipmentNumber")

    def min_shipment_number_as(self, ret_name: str):
        self.query.min("shipment_number", ret_name)
        return self
    def max_shipment_number(self):
        return self.max_shipment_number_as("maxOfShipmentNumber")

    def max_shipment_number_as(self, ret_name: str):
        self.query.max("shipment_number", ret_name)
        return self
    def sum_shipment_number(self):
        return self.sum_shipment_number_as("sumOfShipmentNumber")

    def sum_shipment_number_as(self, ret_name: str):
        self.query.sum("shipment_number", ret_name)
        return self
    def avg_shipment_number(self):
        return self.avg_shipment_number_as("avgOfShipmentNumber")

    def avg_shipment_number_as(self, ret_name: str):
        self.query.avg("shipment_number", ret_name)
        return self
    def standardDeviation_shipment_number(self):
        return self.standardDeviation_shipment_number_as("standardDeviationOfShipmentNumber")

    def standardDeviation_shipment_number_as(self, ret_name: str):
        self.query.standardDeviation("shipment_number", ret_name)
        return self
    def squareRootOfPopulationStandardDeviation_shipment_number(self):
        return self.squareRootOfPopulationStandardDeviation_shipment_number_as("squareRootOfPopulationStandardDeviationOfShipmentNumber")

    def squareRootOfPopulationStandardDeviation_shipment_number_as(self, ret_name: str):
        self.query.squareRootOfPopulationStandardDeviation("shipment_number", ret_name)
        return self
    def sampleVariance_shipment_number(self):
        return self.sampleVariance_shipment_number_as("sampleVarianceOfShipmentNumber")

    def sampleVariance_shipment_number_as(self, ret_name: str):
        self.query.sampleVariance("shipment_number", ret_name)
        return self
    def samplePopulationVariance_shipment_number(self):
        return self.samplePopulationVariance_shipment_number_as("samplePopulationVarianceOfShipmentNumber")

    def samplePopulationVariance_shipment_number_as(self, ret_name: str):
        self.query.samplePopulationVariance("shipment_number", ret_name)
        return self
    def min_package_count(self):
        return self.min_package_count_as("minOfPackageCount")

    def min_package_count_as(self, ret_name: str):
        self.query.min("package_count", ret_name)
        return self
    def max_package_count(self):
        return self.max_package_count_as("maxOfPackageCount")

    def max_package_count_as(self, ret_name: str):
        self.query.max("package_count", ret_name)
        return self
    def sum_package_count(self):
        return self.sum_package_count_as("sumOfPackageCount")

    def sum_package_count_as(self, ret_name: str):
        self.query.sum("package_count", ret_name)
        return self
    def avg_package_count(self):
        return self.avg_package_count_as("avgOfPackageCount")

    def avg_package_count_as(self, ret_name: str):
        self.query.avg("package_count", ret_name)
        return self
    def standardDeviation_package_count(self):
        return self.standardDeviation_package_count_as("standardDeviationOfPackageCount")

    def standardDeviation_package_count_as(self, ret_name: str):
        self.query.standardDeviation("package_count", ret_name)
        return self
    def squareRootOfPopulationStandardDeviation_package_count(self):
        return self.squareRootOfPopulationStandardDeviation_package_count_as("squareRootOfPopulationStandardDeviationOfPackageCount")

    def squareRootOfPopulationStandardDeviation_package_count_as(self, ret_name: str):
        self.query.squareRootOfPopulationStandardDeviation("package_count", ret_name)
        return self
    def sampleVariance_package_count(self):
        return self.sampleVariance_package_count_as("sampleVarianceOfPackageCount")

    def sampleVariance_package_count_as(self, ret_name: str):
        self.query.sampleVariance("package_count", ret_name)
        return self
    def samplePopulationVariance_package_count(self):
        return self.samplePopulationVariance_package_count_as("samplePopulationVarianceOfPackageCount")

    def samplePopulationVariance_package_count_as(self, ret_name: str):
        self.query.samplePopulationVariance("package_count", ret_name)
        return self
    def group_by_id(self):
        self.query.group_by("id")
        return self

    def group_by_id_as(self, ret_name: str):
        self.query.group_by("id")
        self.query.project_expr(ret_name, column("id"))
        return self
    def group_by_platform(self):
        self.query.group_by("platform")
        return self

    def group_by_platform_as(self, ret_name: str):
        self.query.group_by("platform")
        self.query.project_expr(ret_name, column("platform"))
        return self
    def group_by_reference(self):
        self.query.group_by("reference")
        return self

    def group_by_reference_as(self, ret_name: str):
        self.query.group_by("reference")
        self.query.project_expr(ret_name, column("reference"))
        return self
    def group_by_amount(self):
        self.query.group_by("amount")
        return self

    def group_by_amount_as(self, ret_name: str):
        self.query.group_by("amount")
        self.query.project_expr(ret_name, column("amount"))
        return self
    def group_by_shipment_number(self):
        self.query.group_by("shipment_number")
        return self

    def group_by_shipment_number_as(self, ret_name: str):
        self.query.group_by("shipment_number")
        self.query.project_expr(ret_name, column("shipment_number"))
        return self
    def group_by_package_count(self):
        self.query.group_by("package_count")
        return self

    def group_by_package_count_as(self, ret_name: str):
        self.query.group_by("package_count")
        self.query.project_expr(ret_name, column("package_count"))
        return self
    def group_by_delivery_date(self):
        self.query.group_by("delivery_date")
        return self

    def group_by_delivery_date_as(self, ret_name: str):
        self.query.group_by("delivery_date")
        self.query.project_expr(ret_name, column("delivery_date"))
        return self
    def group_by_pickup_time(self):
        self.query.group_by("pickup_time")
        return self

    def group_by_pickup_time_as(self, ret_name: str):
        self.query.group_by("pickup_time")
        self.query.project_expr(ret_name, column("pickup_time"))
        return self
    def group_by_quoted_at(self):
        self.query.group_by("quoted_at")
        return self

    def group_by_quoted_at_as(self, ret_name: str):
        self.query.group_by("quoted_at")
        self.query.project_expr(ret_name, column("quoted_at"))
        return self
    def group_by_instructions(self):
        self.query.group_by("instructions")
        return self

    def group_by_instructions_as(self, ret_name: str):
        self.query.group_by("instructions")
        self.query.project_expr(ret_name, column("instructions"))
        return self
    def group_by_version(self):
        self.query.group_by("version")
        return self

    def group_by_version_as(self, ret_name: str):
        self.query.group_by("version")
        self.query.project_expr(ret_name, column("version"))
        return self
    def facet_by_platform_as(self, name: str, request: QuerySelection,
                                      include_all_facets: bool = True):
        self.query.facet_by(name, "platform", request.query, include_all_facets,
            QueryOperation("facet", "facet_by_platform_as", name, "platform"))
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
