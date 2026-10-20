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
from models.scalar_type_probe import ScalarTypeProbe
from typing import Protocol

class QuerySelection(Protocol):
    query: SelectQuery

class ScalarTypeProbeRequest:
    def __init__(self, minimal=False):
        self.query = SelectQuery("ScalarTypeProbe")
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
        return ExecutableScalarTypeProbeRequest(self)

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
        self.query.project("id", "type_platform", "required_string", "optional_string", "large_text", "required_boolean", "optional_boolean", "required_integer", "optional_integer", "required_long", "optional_long", "required_decimal", "optional_decimal", "required_float", "optional_float", "required_double", "optional_double", "required_date", "optional_date", "required_time", "optional_time", "required_datetime", "optional_datetime", "create_time", "update_time", "version")
        return self

    def select_id(self):
        self.query.project("id")
        return self


    def select_required_string(self):
        self.query.project("required_string")
        return self

    def select_optional_string(self):
        self.query.project("optional_string")
        return self

    def select_large_text(self):
        self.query.project("large_text")
        return self

    def select_required_boolean(self):
        self.query.project("required_boolean")
        return self

    def select_optional_boolean(self):
        self.query.project("optional_boolean")
        return self

    def select_required_integer(self):
        self.query.project("required_integer")
        return self

    def select_optional_integer(self):
        self.query.project("optional_integer")
        return self

    def select_required_long(self):
        self.query.project("required_long")
        return self

    def select_optional_long(self):
        self.query.project("optional_long")
        return self

    def select_required_decimal(self):
        self.query.project("required_decimal")
        return self

    def select_optional_decimal(self):
        self.query.project("optional_decimal")
        return self

    def select_required_float(self):
        self.query.project("required_float")
        return self

    def select_optional_float(self):
        self.query.project("optional_float")
        return self

    def select_required_double(self):
        self.query.project("required_double")
        return self

    def select_optional_double(self):
        self.query.project("optional_double")
        return self

    def select_required_date(self):
        self.query.project("required_date")
        return self

    def select_optional_date(self):
        self.query.project("optional_date")
        return self

    def select_required_time(self):
        self.query.project("required_time")
        return self

    def select_optional_time(self):
        self.query.project("optional_time")
        return self

    def select_required_datetime(self):
        self.query.project("required_datetime")
        return self

    def select_optional_datetime(self):
        self.query.project("optional_datetime")
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

    def select_type_platform_with(self, child_request):
        self.query.project("type_platform")
        self.query.relation_query("type_platform", child_request.query,
            QueryOperation("relation-select", "select_type_platform_with", relation="type_platform"))
        return self
    def with_type_platform_matching(self, child_request):
        child_request.query.projection = ["id"]
        self.query.and_filter(in_subquery(column("type_platform"), "TypePlatform", child_request.query))
        return self

    def without_type_platform_matching(self, child_request):
        child_request.query.projection = ["id"]
        self.query.and_filter(not_in_subquery(column("type_platform"), "TypePlatform", child_request.query))
        return self

    def have_type_platform(self):
        self.query.and_filter(is_not_null(column("type_platform")))
        return self

    def have_no_type_platform(self):
        self.query.and_filter(is_null(column("type_platform")))
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

    def filter_by_type_platform(self, val):
        self.query.and_filter(eq("type_platform", val))
        return self

    def with_required_string_containing(self, val: str):
        self.query.and_filter(contain("required_string", val))
        return self

    def with_required_string_not_containing(self, val: str):
        self.query.and_filter(not_contain("required_string", val))
        return self

    def with_required_string_starting_with(self, val: str):
        self.query.and_filter(begin_with("required_string", val))
        return self

    def with_required_string_not_starting_with(self, val: str):
        self.query.and_filter(not_begin_with("required_string", val))
        return self

    def with_required_string_ending_with(self, val: str):
        self.query.and_filter(end_with("required_string", val))
        return self

    def with_required_string_not_ending_with(self, val: str):
        self.query.and_filter(not_end_with("required_string", val))
        return self

    def with_required_string_sounding_like(self, val: str):
        self.query.and_filter(sound_like("required_string", val))
        return self

    def with_required_string_is(self, val: str):
        self.query.and_filter(eq("required_string", val))
        return self
    def with_required_string_is_not(self, val):
        self.query.and_filter(ne("required_string", val))
        return self

    def with_required_string_in(self, *vals):
        self.query.and_filter(in_list("required_string", list(vals)))
        return self

    def with_required_string_not_in(self, *vals):
        self.query.and_filter(not_in_list("required_string", list(vals)))
        return self

    def with_required_string_greater_than(self, val):
        self.query.and_filter(gt("required_string", val))
        return self

    def with_required_string_greater_than_or_equal_to(self, val):
        self.query.and_filter(gte("required_string", val))
        return self

    def with_required_string_less_than(self, val):
        self.query.and_filter(lt("required_string", val))
        return self

    def with_required_string_less_than_or_equal_to(self, val):
        self.query.and_filter(lte("required_string", val))
        return self

    def with_required_string_between(self, lower, upper):
        self.query.and_filter(between(column("required_string"), value(lower), value(upper)))
        return self

    def with_required_string_is_known(self):
        self.query.and_filter(is_not_null(column("required_string")))
        return self

    def with_required_string_is_unknown(self):
        self.query.and_filter(is_null(column("required_string")))
        return self

    def with_optional_string_containing(self, val: str):
        self.query.and_filter(contain("optional_string", val))
        return self

    def with_optional_string_not_containing(self, val: str):
        self.query.and_filter(not_contain("optional_string", val))
        return self

    def with_optional_string_starting_with(self, val: str):
        self.query.and_filter(begin_with("optional_string", val))
        return self

    def with_optional_string_not_starting_with(self, val: str):
        self.query.and_filter(not_begin_with("optional_string", val))
        return self

    def with_optional_string_ending_with(self, val: str):
        self.query.and_filter(end_with("optional_string", val))
        return self

    def with_optional_string_not_ending_with(self, val: str):
        self.query.and_filter(not_end_with("optional_string", val))
        return self

    def with_optional_string_sounding_like(self, val: str):
        self.query.and_filter(sound_like("optional_string", val))
        return self

    def with_optional_string_is(self, val: str):
        self.query.and_filter(eq("optional_string", val))
        return self
    def with_optional_string_is_not(self, val):
        self.query.and_filter(ne("optional_string", val))
        return self

    def with_optional_string_in(self, *vals):
        self.query.and_filter(in_list("optional_string", list(vals)))
        return self

    def with_optional_string_not_in(self, *vals):
        self.query.and_filter(not_in_list("optional_string", list(vals)))
        return self

    def with_optional_string_greater_than(self, val):
        self.query.and_filter(gt("optional_string", val))
        return self

    def with_optional_string_greater_than_or_equal_to(self, val):
        self.query.and_filter(gte("optional_string", val))
        return self

    def with_optional_string_less_than(self, val):
        self.query.and_filter(lt("optional_string", val))
        return self

    def with_optional_string_less_than_or_equal_to(self, val):
        self.query.and_filter(lte("optional_string", val))
        return self

    def with_optional_string_between(self, lower, upper):
        self.query.and_filter(between(column("optional_string"), value(lower), value(upper)))
        return self

    def with_optional_string_is_known(self):
        self.query.and_filter(is_not_null(column("optional_string")))
        return self

    def with_optional_string_is_unknown(self):
        self.query.and_filter(is_null(column("optional_string")))
        return self

    def with_large_text_containing(self, val: str):
        self.query.and_filter(contain("large_text", val))
        return self

    def with_large_text_not_containing(self, val: str):
        self.query.and_filter(not_contain("large_text", val))
        return self

    def with_large_text_starting_with(self, val: str):
        self.query.and_filter(begin_with("large_text", val))
        return self

    def with_large_text_not_starting_with(self, val: str):
        self.query.and_filter(not_begin_with("large_text", val))
        return self

    def with_large_text_ending_with(self, val: str):
        self.query.and_filter(end_with("large_text", val))
        return self

    def with_large_text_not_ending_with(self, val: str):
        self.query.and_filter(not_end_with("large_text", val))
        return self

    def with_large_text_sounding_like(self, val: str):
        self.query.and_filter(sound_like("large_text", val))
        return self

    def with_large_text_is(self, val: str):
        self.query.and_filter(eq("large_text", val))
        return self
    def with_large_text_is_not(self, val):
        self.query.and_filter(ne("large_text", val))
        return self

    def with_large_text_in(self, *vals):
        self.query.and_filter(in_list("large_text", list(vals)))
        return self

    def with_large_text_not_in(self, *vals):
        self.query.and_filter(not_in_list("large_text", list(vals)))
        return self

    def with_large_text_greater_than(self, val):
        self.query.and_filter(gt("large_text", val))
        return self

    def with_large_text_greater_than_or_equal_to(self, val):
        self.query.and_filter(gte("large_text", val))
        return self

    def with_large_text_less_than(self, val):
        self.query.and_filter(lt("large_text", val))
        return self

    def with_large_text_less_than_or_equal_to(self, val):
        self.query.and_filter(lte("large_text", val))
        return self

    def with_large_text_between(self, lower, upper):
        self.query.and_filter(between(column("large_text"), value(lower), value(upper)))
        return self

    def with_large_text_is_known(self):
        self.query.and_filter(is_not_null(column("large_text")))
        return self

    def with_large_text_is_unknown(self):
        self.query.and_filter(is_null(column("large_text")))
        return self

    def which_are_required_boolean(self):
        self.query.and_filter(eq("required_boolean", True))
        return self

    def which_are_not_required_boolean(self):
        self.query.and_filter(eq("required_boolean", False))
        return self
    def with_required_boolean_is_not(self, val):
        self.query.and_filter(ne("required_boolean", val))
        return self

    def with_required_boolean_in(self, *vals):
        self.query.and_filter(in_list("required_boolean", list(vals)))
        return self

    def with_required_boolean_not_in(self, *vals):
        self.query.and_filter(not_in_list("required_boolean", list(vals)))
        return self

    def with_required_boolean_greater_than(self, val):
        self.query.and_filter(gt("required_boolean", val))
        return self

    def with_required_boolean_greater_than_or_equal_to(self, val):
        self.query.and_filter(gte("required_boolean", val))
        return self

    def with_required_boolean_less_than(self, val):
        self.query.and_filter(lt("required_boolean", val))
        return self

    def with_required_boolean_less_than_or_equal_to(self, val):
        self.query.and_filter(lte("required_boolean", val))
        return self

    def with_required_boolean_between(self, lower, upper):
        self.query.and_filter(between(column("required_boolean"), value(lower), value(upper)))
        return self

    def with_required_boolean_is_known(self):
        self.query.and_filter(is_not_null(column("required_boolean")))
        return self

    def with_required_boolean_is_unknown(self):
        self.query.and_filter(is_null(column("required_boolean")))
        return self

    def which_are_optional_boolean(self):
        self.query.and_filter(eq("optional_boolean", True))
        return self

    def which_are_not_optional_boolean(self):
        self.query.and_filter(eq("optional_boolean", False))
        return self
    def with_optional_boolean_is_not(self, val):
        self.query.and_filter(ne("optional_boolean", val))
        return self

    def with_optional_boolean_in(self, *vals):
        self.query.and_filter(in_list("optional_boolean", list(vals)))
        return self

    def with_optional_boolean_not_in(self, *vals):
        self.query.and_filter(not_in_list("optional_boolean", list(vals)))
        return self

    def with_optional_boolean_greater_than(self, val):
        self.query.and_filter(gt("optional_boolean", val))
        return self

    def with_optional_boolean_greater_than_or_equal_to(self, val):
        self.query.and_filter(gte("optional_boolean", val))
        return self

    def with_optional_boolean_less_than(self, val):
        self.query.and_filter(lt("optional_boolean", val))
        return self

    def with_optional_boolean_less_than_or_equal_to(self, val):
        self.query.and_filter(lte("optional_boolean", val))
        return self

    def with_optional_boolean_between(self, lower, upper):
        self.query.and_filter(between(column("optional_boolean"), value(lower), value(upper)))
        return self

    def with_optional_boolean_is_known(self):
        self.query.and_filter(is_not_null(column("optional_boolean")))
        return self

    def with_optional_boolean_is_unknown(self):
        self.query.and_filter(is_null(column("optional_boolean")))
        return self

    def with_required_integer_is(self, val):
        self.query.and_filter(eq("required_integer", val))
        return self

    def with_required_integer_is_not(self, val):
        self.query.and_filter(ne("required_integer", val))
        return self

    def with_required_integer_in(self, *vals):
        self.query.and_filter(in_list("required_integer", list(vals)))
        return self

    def with_required_integer_not_in(self, *vals):
        self.query.and_filter(not_in_list("required_integer", list(vals)))
        return self

    def with_required_integer_greater_than(self, val):
        self.query.and_filter(gt("required_integer", val))
        return self

    def with_required_integer_greater_than_or_equal_to(self, val):
        self.query.and_filter(gte("required_integer", val))
        return self

    def with_required_integer_less_than(self, val):
        self.query.and_filter(lt("required_integer", val))
        return self

    def with_required_integer_less_than_or_equal_to(self, val):
        self.query.and_filter(lte("required_integer", val))
        return self

    def with_required_integer_between(self, lower, upper):
        self.query.and_filter(between(column("required_integer"), value(lower), value(upper)))
        return self

    def with_required_integer_is_known(self):
        self.query.and_filter(is_not_null(column("required_integer")))
        return self

    def with_required_integer_is_unknown(self):
        self.query.and_filter(is_null(column("required_integer")))
        return self

    def with_optional_integer_is(self, val):
        self.query.and_filter(eq("optional_integer", val))
        return self

    def with_optional_integer_is_not(self, val):
        self.query.and_filter(ne("optional_integer", val))
        return self

    def with_optional_integer_in(self, *vals):
        self.query.and_filter(in_list("optional_integer", list(vals)))
        return self

    def with_optional_integer_not_in(self, *vals):
        self.query.and_filter(not_in_list("optional_integer", list(vals)))
        return self

    def with_optional_integer_greater_than(self, val):
        self.query.and_filter(gt("optional_integer", val))
        return self

    def with_optional_integer_greater_than_or_equal_to(self, val):
        self.query.and_filter(gte("optional_integer", val))
        return self

    def with_optional_integer_less_than(self, val):
        self.query.and_filter(lt("optional_integer", val))
        return self

    def with_optional_integer_less_than_or_equal_to(self, val):
        self.query.and_filter(lte("optional_integer", val))
        return self

    def with_optional_integer_between(self, lower, upper):
        self.query.and_filter(between(column("optional_integer"), value(lower), value(upper)))
        return self

    def with_optional_integer_is_known(self):
        self.query.and_filter(is_not_null(column("optional_integer")))
        return self

    def with_optional_integer_is_unknown(self):
        self.query.and_filter(is_null(column("optional_integer")))
        return self

    def with_required_long_is(self, val):
        self.query.and_filter(eq("required_long", val))
        return self

    def with_required_long_is_not(self, val):
        self.query.and_filter(ne("required_long", val))
        return self

    def with_required_long_in(self, *vals):
        self.query.and_filter(in_list("required_long", list(vals)))
        return self

    def with_required_long_not_in(self, *vals):
        self.query.and_filter(not_in_list("required_long", list(vals)))
        return self

    def with_required_long_greater_than(self, val):
        self.query.and_filter(gt("required_long", val))
        return self

    def with_required_long_greater_than_or_equal_to(self, val):
        self.query.and_filter(gte("required_long", val))
        return self

    def with_required_long_less_than(self, val):
        self.query.and_filter(lt("required_long", val))
        return self

    def with_required_long_less_than_or_equal_to(self, val):
        self.query.and_filter(lte("required_long", val))
        return self

    def with_required_long_between(self, lower, upper):
        self.query.and_filter(between(column("required_long"), value(lower), value(upper)))
        return self

    def with_required_long_is_known(self):
        self.query.and_filter(is_not_null(column("required_long")))
        return self

    def with_required_long_is_unknown(self):
        self.query.and_filter(is_null(column("required_long")))
        return self

    def with_optional_long_is(self, val):
        self.query.and_filter(eq("optional_long", val))
        return self

    def with_optional_long_is_not(self, val):
        self.query.and_filter(ne("optional_long", val))
        return self

    def with_optional_long_in(self, *vals):
        self.query.and_filter(in_list("optional_long", list(vals)))
        return self

    def with_optional_long_not_in(self, *vals):
        self.query.and_filter(not_in_list("optional_long", list(vals)))
        return self

    def with_optional_long_greater_than(self, val):
        self.query.and_filter(gt("optional_long", val))
        return self

    def with_optional_long_greater_than_or_equal_to(self, val):
        self.query.and_filter(gte("optional_long", val))
        return self

    def with_optional_long_less_than(self, val):
        self.query.and_filter(lt("optional_long", val))
        return self

    def with_optional_long_less_than_or_equal_to(self, val):
        self.query.and_filter(lte("optional_long", val))
        return self

    def with_optional_long_between(self, lower, upper):
        self.query.and_filter(between(column("optional_long"), value(lower), value(upper)))
        return self

    def with_optional_long_is_known(self):
        self.query.and_filter(is_not_null(column("optional_long")))
        return self

    def with_optional_long_is_unknown(self):
        self.query.and_filter(is_null(column("optional_long")))
        return self

    def with_required_decimal_is(self, val):
        self.query.and_filter(eq("required_decimal", val))
        return self

    def with_required_decimal_is_not(self, val):
        self.query.and_filter(ne("required_decimal", val))
        return self

    def with_required_decimal_in(self, *vals):
        self.query.and_filter(in_list("required_decimal", list(vals)))
        return self

    def with_required_decimal_not_in(self, *vals):
        self.query.and_filter(not_in_list("required_decimal", list(vals)))
        return self

    def with_required_decimal_greater_than(self, val):
        self.query.and_filter(gt("required_decimal", val))
        return self

    def with_required_decimal_greater_than_or_equal_to(self, val):
        self.query.and_filter(gte("required_decimal", val))
        return self

    def with_required_decimal_less_than(self, val):
        self.query.and_filter(lt("required_decimal", val))
        return self

    def with_required_decimal_less_than_or_equal_to(self, val):
        self.query.and_filter(lte("required_decimal", val))
        return self

    def with_required_decimal_between(self, lower, upper):
        self.query.and_filter(between(column("required_decimal"), value(lower), value(upper)))
        return self

    def with_required_decimal_is_known(self):
        self.query.and_filter(is_not_null(column("required_decimal")))
        return self

    def with_required_decimal_is_unknown(self):
        self.query.and_filter(is_null(column("required_decimal")))
        return self

    def with_optional_decimal_is(self, val):
        self.query.and_filter(eq("optional_decimal", val))
        return self

    def with_optional_decimal_is_not(self, val):
        self.query.and_filter(ne("optional_decimal", val))
        return self

    def with_optional_decimal_in(self, *vals):
        self.query.and_filter(in_list("optional_decimal", list(vals)))
        return self

    def with_optional_decimal_not_in(self, *vals):
        self.query.and_filter(not_in_list("optional_decimal", list(vals)))
        return self

    def with_optional_decimal_greater_than(self, val):
        self.query.and_filter(gt("optional_decimal", val))
        return self

    def with_optional_decimal_greater_than_or_equal_to(self, val):
        self.query.and_filter(gte("optional_decimal", val))
        return self

    def with_optional_decimal_less_than(self, val):
        self.query.and_filter(lt("optional_decimal", val))
        return self

    def with_optional_decimal_less_than_or_equal_to(self, val):
        self.query.and_filter(lte("optional_decimal", val))
        return self

    def with_optional_decimal_between(self, lower, upper):
        self.query.and_filter(between(column("optional_decimal"), value(lower), value(upper)))
        return self

    def with_optional_decimal_is_known(self):
        self.query.and_filter(is_not_null(column("optional_decimal")))
        return self

    def with_optional_decimal_is_unknown(self):
        self.query.and_filter(is_null(column("optional_decimal")))
        return self

    def with_required_float_is(self, val):
        self.query.and_filter(eq("required_float", val))
        return self

    def with_required_float_is_not(self, val):
        self.query.and_filter(ne("required_float", val))
        return self

    def with_required_float_in(self, *vals):
        self.query.and_filter(in_list("required_float", list(vals)))
        return self

    def with_required_float_not_in(self, *vals):
        self.query.and_filter(not_in_list("required_float", list(vals)))
        return self

    def with_required_float_greater_than(self, val):
        self.query.and_filter(gt("required_float", val))
        return self

    def with_required_float_greater_than_or_equal_to(self, val):
        self.query.and_filter(gte("required_float", val))
        return self

    def with_required_float_less_than(self, val):
        self.query.and_filter(lt("required_float", val))
        return self

    def with_required_float_less_than_or_equal_to(self, val):
        self.query.and_filter(lte("required_float", val))
        return self

    def with_required_float_between(self, lower, upper):
        self.query.and_filter(between(column("required_float"), value(lower), value(upper)))
        return self

    def with_required_float_is_known(self):
        self.query.and_filter(is_not_null(column("required_float")))
        return self

    def with_required_float_is_unknown(self):
        self.query.and_filter(is_null(column("required_float")))
        return self

    def with_optional_float_is(self, val):
        self.query.and_filter(eq("optional_float", val))
        return self

    def with_optional_float_is_not(self, val):
        self.query.and_filter(ne("optional_float", val))
        return self

    def with_optional_float_in(self, *vals):
        self.query.and_filter(in_list("optional_float", list(vals)))
        return self

    def with_optional_float_not_in(self, *vals):
        self.query.and_filter(not_in_list("optional_float", list(vals)))
        return self

    def with_optional_float_greater_than(self, val):
        self.query.and_filter(gt("optional_float", val))
        return self

    def with_optional_float_greater_than_or_equal_to(self, val):
        self.query.and_filter(gte("optional_float", val))
        return self

    def with_optional_float_less_than(self, val):
        self.query.and_filter(lt("optional_float", val))
        return self

    def with_optional_float_less_than_or_equal_to(self, val):
        self.query.and_filter(lte("optional_float", val))
        return self

    def with_optional_float_between(self, lower, upper):
        self.query.and_filter(between(column("optional_float"), value(lower), value(upper)))
        return self

    def with_optional_float_is_known(self):
        self.query.and_filter(is_not_null(column("optional_float")))
        return self

    def with_optional_float_is_unknown(self):
        self.query.and_filter(is_null(column("optional_float")))
        return self

    def with_required_double_is(self, val):
        self.query.and_filter(eq("required_double", val))
        return self

    def with_required_double_is_not(self, val):
        self.query.and_filter(ne("required_double", val))
        return self

    def with_required_double_in(self, *vals):
        self.query.and_filter(in_list("required_double", list(vals)))
        return self

    def with_required_double_not_in(self, *vals):
        self.query.and_filter(not_in_list("required_double", list(vals)))
        return self

    def with_required_double_greater_than(self, val):
        self.query.and_filter(gt("required_double", val))
        return self

    def with_required_double_greater_than_or_equal_to(self, val):
        self.query.and_filter(gte("required_double", val))
        return self

    def with_required_double_less_than(self, val):
        self.query.and_filter(lt("required_double", val))
        return self

    def with_required_double_less_than_or_equal_to(self, val):
        self.query.and_filter(lte("required_double", val))
        return self

    def with_required_double_between(self, lower, upper):
        self.query.and_filter(between(column("required_double"), value(lower), value(upper)))
        return self

    def with_required_double_is_known(self):
        self.query.and_filter(is_not_null(column("required_double")))
        return self

    def with_required_double_is_unknown(self):
        self.query.and_filter(is_null(column("required_double")))
        return self

    def with_optional_double_is(self, val):
        self.query.and_filter(eq("optional_double", val))
        return self

    def with_optional_double_is_not(self, val):
        self.query.and_filter(ne("optional_double", val))
        return self

    def with_optional_double_in(self, *vals):
        self.query.and_filter(in_list("optional_double", list(vals)))
        return self

    def with_optional_double_not_in(self, *vals):
        self.query.and_filter(not_in_list("optional_double", list(vals)))
        return self

    def with_optional_double_greater_than(self, val):
        self.query.and_filter(gt("optional_double", val))
        return self

    def with_optional_double_greater_than_or_equal_to(self, val):
        self.query.and_filter(gte("optional_double", val))
        return self

    def with_optional_double_less_than(self, val):
        self.query.and_filter(lt("optional_double", val))
        return self

    def with_optional_double_less_than_or_equal_to(self, val):
        self.query.and_filter(lte("optional_double", val))
        return self

    def with_optional_double_between(self, lower, upper):
        self.query.and_filter(between(column("optional_double"), value(lower), value(upper)))
        return self

    def with_optional_double_is_known(self):
        self.query.and_filter(is_not_null(column("optional_double")))
        return self

    def with_optional_double_is_unknown(self):
        self.query.and_filter(is_null(column("optional_double")))
        return self

    def with_required_date_is(self, val):
        self.query.and_filter(eq("required_date", val))
        return self

    def with_required_date_is_not(self, val):
        self.query.and_filter(ne("required_date", val))
        return self

    def with_required_date_in(self, *vals):
        self.query.and_filter(in_list("required_date", list(vals)))
        return self

    def with_required_date_not_in(self, *vals):
        self.query.and_filter(not_in_list("required_date", list(vals)))
        return self

    def with_required_date_greater_than(self, val):
        self.query.and_filter(gt("required_date", val))
        return self

    def with_required_date_greater_than_or_equal_to(self, val):
        self.query.and_filter(gte("required_date", val))
        return self

    def with_required_date_less_than(self, val):
        self.query.and_filter(lt("required_date", val))
        return self

    def with_required_date_less_than_or_equal_to(self, val):
        self.query.and_filter(lte("required_date", val))
        return self

    def with_required_date_between(self, lower, upper):
        self.query.and_filter(between(column("required_date"), value(lower), value(upper)))
        return self

    def with_required_date_is_known(self):
        self.query.and_filter(is_not_null(column("required_date")))
        return self

    def with_required_date_is_unknown(self):
        self.query.and_filter(is_null(column("required_date")))
        return self

    def with_optional_date_is(self, val):
        self.query.and_filter(eq("optional_date", val))
        return self

    def with_optional_date_is_not(self, val):
        self.query.and_filter(ne("optional_date", val))
        return self

    def with_optional_date_in(self, *vals):
        self.query.and_filter(in_list("optional_date", list(vals)))
        return self

    def with_optional_date_not_in(self, *vals):
        self.query.and_filter(not_in_list("optional_date", list(vals)))
        return self

    def with_optional_date_greater_than(self, val):
        self.query.and_filter(gt("optional_date", val))
        return self

    def with_optional_date_greater_than_or_equal_to(self, val):
        self.query.and_filter(gte("optional_date", val))
        return self

    def with_optional_date_less_than(self, val):
        self.query.and_filter(lt("optional_date", val))
        return self

    def with_optional_date_less_than_or_equal_to(self, val):
        self.query.and_filter(lte("optional_date", val))
        return self

    def with_optional_date_between(self, lower, upper):
        self.query.and_filter(between(column("optional_date"), value(lower), value(upper)))
        return self

    def with_optional_date_is_known(self):
        self.query.and_filter(is_not_null(column("optional_date")))
        return self

    def with_optional_date_is_unknown(self):
        self.query.and_filter(is_null(column("optional_date")))
        return self

    def with_required_time_is(self, val):
        self.query.and_filter(eq("required_time", val))
        return self

    def with_required_time_is_not(self, val):
        self.query.and_filter(ne("required_time", val))
        return self

    def with_required_time_in(self, *vals):
        self.query.and_filter(in_list("required_time", list(vals)))
        return self

    def with_required_time_not_in(self, *vals):
        self.query.and_filter(not_in_list("required_time", list(vals)))
        return self

    def with_required_time_greater_than(self, val):
        self.query.and_filter(gt("required_time", val))
        return self

    def with_required_time_greater_than_or_equal_to(self, val):
        self.query.and_filter(gte("required_time", val))
        return self

    def with_required_time_less_than(self, val):
        self.query.and_filter(lt("required_time", val))
        return self

    def with_required_time_less_than_or_equal_to(self, val):
        self.query.and_filter(lte("required_time", val))
        return self

    def with_required_time_between(self, lower, upper):
        self.query.and_filter(between(column("required_time"), value(lower), value(upper)))
        return self

    def with_required_time_is_known(self):
        self.query.and_filter(is_not_null(column("required_time")))
        return self

    def with_required_time_is_unknown(self):
        self.query.and_filter(is_null(column("required_time")))
        return self

    def with_optional_time_is(self, val):
        self.query.and_filter(eq("optional_time", val))
        return self

    def with_optional_time_is_not(self, val):
        self.query.and_filter(ne("optional_time", val))
        return self

    def with_optional_time_in(self, *vals):
        self.query.and_filter(in_list("optional_time", list(vals)))
        return self

    def with_optional_time_not_in(self, *vals):
        self.query.and_filter(not_in_list("optional_time", list(vals)))
        return self

    def with_optional_time_greater_than(self, val):
        self.query.and_filter(gt("optional_time", val))
        return self

    def with_optional_time_greater_than_or_equal_to(self, val):
        self.query.and_filter(gte("optional_time", val))
        return self

    def with_optional_time_less_than(self, val):
        self.query.and_filter(lt("optional_time", val))
        return self

    def with_optional_time_less_than_or_equal_to(self, val):
        self.query.and_filter(lte("optional_time", val))
        return self

    def with_optional_time_between(self, lower, upper):
        self.query.and_filter(between(column("optional_time"), value(lower), value(upper)))
        return self

    def with_optional_time_is_known(self):
        self.query.and_filter(is_not_null(column("optional_time")))
        return self

    def with_optional_time_is_unknown(self):
        self.query.and_filter(is_null(column("optional_time")))
        return self

    def with_required_datetime_is(self, val):
        self.query.and_filter(eq("required_datetime", val))
        return self

    def with_required_datetime_is_not(self, val):
        self.query.and_filter(ne("required_datetime", val))
        return self

    def with_required_datetime_in(self, *vals):
        self.query.and_filter(in_list("required_datetime", list(vals)))
        return self

    def with_required_datetime_not_in(self, *vals):
        self.query.and_filter(not_in_list("required_datetime", list(vals)))
        return self

    def with_required_datetime_greater_than(self, val):
        self.query.and_filter(gt("required_datetime", val))
        return self

    def with_required_datetime_greater_than_or_equal_to(self, val):
        self.query.and_filter(gte("required_datetime", val))
        return self

    def with_required_datetime_less_than(self, val):
        self.query.and_filter(lt("required_datetime", val))
        return self

    def with_required_datetime_less_than_or_equal_to(self, val):
        self.query.and_filter(lte("required_datetime", val))
        return self

    def with_required_datetime_between(self, lower, upper):
        self.query.and_filter(between(column("required_datetime"), value(lower), value(upper)))
        return self

    def with_required_datetime_is_known(self):
        self.query.and_filter(is_not_null(column("required_datetime")))
        return self

    def with_required_datetime_is_unknown(self):
        self.query.and_filter(is_null(column("required_datetime")))
        return self

    def with_optional_datetime_is(self, val):
        self.query.and_filter(eq("optional_datetime", val))
        return self

    def with_optional_datetime_is_not(self, val):
        self.query.and_filter(ne("optional_datetime", val))
        return self

    def with_optional_datetime_in(self, *vals):
        self.query.and_filter(in_list("optional_datetime", list(vals)))
        return self

    def with_optional_datetime_not_in(self, *vals):
        self.query.and_filter(not_in_list("optional_datetime", list(vals)))
        return self

    def with_optional_datetime_greater_than(self, val):
        self.query.and_filter(gt("optional_datetime", val))
        return self

    def with_optional_datetime_greater_than_or_equal_to(self, val):
        self.query.and_filter(gte("optional_datetime", val))
        return self

    def with_optional_datetime_less_than(self, val):
        self.query.and_filter(lt("optional_datetime", val))
        return self

    def with_optional_datetime_less_than_or_equal_to(self, val):
        self.query.and_filter(lte("optional_datetime", val))
        return self

    def with_optional_datetime_between(self, lower, upper):
        self.query.and_filter(between(column("optional_datetime"), value(lower), value(upper)))
        return self

    def with_optional_datetime_is_known(self):
        self.query.and_filter(is_not_null(column("optional_datetime")))
        return self

    def with_optional_datetime_is_unknown(self):
        self.query.and_filter(is_null(column("optional_datetime")))
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


    def order_by_required_string_ascending(self):
        self.query.order_by("required_string", "asc")
        return self

    def order_by_required_string_descending(self):
        self.query.order_by("required_string", "desc")
        return self

    def order_by_optional_string_ascending(self):
        self.query.order_by("optional_string", "asc")
        return self

    def order_by_optional_string_descending(self):
        self.query.order_by("optional_string", "desc")
        return self

    def order_by_large_text_ascending(self):
        self.query.order_by("large_text", "asc")
        return self

    def order_by_large_text_descending(self):
        self.query.order_by("large_text", "desc")
        return self

    def order_by_required_boolean_ascending(self):
        self.query.order_by("required_boolean", "asc")
        return self

    def order_by_required_boolean_descending(self):
        self.query.order_by("required_boolean", "desc")
        return self

    def order_by_optional_boolean_ascending(self):
        self.query.order_by("optional_boolean", "asc")
        return self

    def order_by_optional_boolean_descending(self):
        self.query.order_by("optional_boolean", "desc")
        return self

    def order_by_required_integer_ascending(self):
        self.query.order_by("required_integer", "asc")
        return self

    def order_by_required_integer_descending(self):
        self.query.order_by("required_integer", "desc")
        return self

    def order_by_optional_integer_ascending(self):
        self.query.order_by("optional_integer", "asc")
        return self

    def order_by_optional_integer_descending(self):
        self.query.order_by("optional_integer", "desc")
        return self

    def order_by_required_long_ascending(self):
        self.query.order_by("required_long", "asc")
        return self

    def order_by_required_long_descending(self):
        self.query.order_by("required_long", "desc")
        return self

    def order_by_optional_long_ascending(self):
        self.query.order_by("optional_long", "asc")
        return self

    def order_by_optional_long_descending(self):
        self.query.order_by("optional_long", "desc")
        return self

    def order_by_required_decimal_ascending(self):
        self.query.order_by("required_decimal", "asc")
        return self

    def order_by_required_decimal_descending(self):
        self.query.order_by("required_decimal", "desc")
        return self

    def order_by_optional_decimal_ascending(self):
        self.query.order_by("optional_decimal", "asc")
        return self

    def order_by_optional_decimal_descending(self):
        self.query.order_by("optional_decimal", "desc")
        return self

    def order_by_required_float_ascending(self):
        self.query.order_by("required_float", "asc")
        return self

    def order_by_required_float_descending(self):
        self.query.order_by("required_float", "desc")
        return self

    def order_by_optional_float_ascending(self):
        self.query.order_by("optional_float", "asc")
        return self

    def order_by_optional_float_descending(self):
        self.query.order_by("optional_float", "desc")
        return self

    def order_by_required_double_ascending(self):
        self.query.order_by("required_double", "asc")
        return self

    def order_by_required_double_descending(self):
        self.query.order_by("required_double", "desc")
        return self

    def order_by_optional_double_ascending(self):
        self.query.order_by("optional_double", "asc")
        return self

    def order_by_optional_double_descending(self):
        self.query.order_by("optional_double", "desc")
        return self

    def order_by_required_date_ascending(self):
        self.query.order_by("required_date", "asc")
        return self

    def order_by_required_date_descending(self):
        self.query.order_by("required_date", "desc")
        return self

    def order_by_optional_date_ascending(self):
        self.query.order_by("optional_date", "asc")
        return self

    def order_by_optional_date_descending(self):
        self.query.order_by("optional_date", "desc")
        return self

    def order_by_required_time_ascending(self):
        self.query.order_by("required_time", "asc")
        return self

    def order_by_required_time_descending(self):
        self.query.order_by("required_time", "desc")
        return self

    def order_by_optional_time_ascending(self):
        self.query.order_by("optional_time", "asc")
        return self

    def order_by_optional_time_descending(self):
        self.query.order_by("optional_time", "desc")
        return self

    def order_by_required_datetime_ascending(self):
        self.query.order_by("required_datetime", "asc")
        return self

    def order_by_required_datetime_descending(self):
        self.query.order_by("required_datetime", "desc")
        return self

    def order_by_optional_datetime_ascending(self):
        self.query.order_by("optional_datetime", "asc")
        return self

    def order_by_optional_datetime_descending(self):
        self.query.order_by("optional_datetime", "desc")
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
        self._page_count_alias = "count"
        self._page_count_method = "count"
        return self

    def count_as(self, ret_name: str):
        self.query.count_field("id", ret_name)
        self._page_count_alias = ret_name
        self._page_count_method = "count_as"
        return self

    def min_required_integer(self):
        return self.min_required_integer_as("minOfRequiredInteger")

    def min_required_integer_as(self, ret_name: str):
        self.query.min("required_integer", ret_name)
        return self
    def max_required_integer(self):
        return self.max_required_integer_as("maxOfRequiredInteger")

    def max_required_integer_as(self, ret_name: str):
        self.query.max("required_integer", ret_name)
        return self
    def sum_required_integer(self):
        return self.sum_required_integer_as("sumOfRequiredInteger")

    def sum_required_integer_as(self, ret_name: str):
        self.query.sum("required_integer", ret_name)
        return self
    def avg_required_integer(self):
        return self.avg_required_integer_as("avgOfRequiredInteger")

    def avg_required_integer_as(self, ret_name: str):
        self.query.avg("required_integer", ret_name)
        return self
    def standardDeviation_required_integer(self):
        return self.standardDeviation_required_integer_as("standardDeviationOfRequiredInteger")

    def standardDeviation_required_integer_as(self, ret_name: str):
        self.query.standardDeviation("required_integer", ret_name)
        return self
    def squareRootOfPopulationStandardDeviation_required_integer(self):
        return self.squareRootOfPopulationStandardDeviation_required_integer_as("squareRootOfPopulationStandardDeviationOfRequiredInteger")

    def squareRootOfPopulationStandardDeviation_required_integer_as(self, ret_name: str):
        self.query.squareRootOfPopulationStandardDeviation("required_integer", ret_name)
        return self
    def sampleVariance_required_integer(self):
        return self.sampleVariance_required_integer_as("sampleVarianceOfRequiredInteger")

    def sampleVariance_required_integer_as(self, ret_name: str):
        self.query.sampleVariance("required_integer", ret_name)
        return self
    def samplePopulationVariance_required_integer(self):
        return self.samplePopulationVariance_required_integer_as("samplePopulationVarianceOfRequiredInteger")

    def samplePopulationVariance_required_integer_as(self, ret_name: str):
        self.query.samplePopulationVariance("required_integer", ret_name)
        return self
    def min_optional_integer(self):
        return self.min_optional_integer_as("minOfOptionalInteger")

    def min_optional_integer_as(self, ret_name: str):
        self.query.min("optional_integer", ret_name)
        return self
    def max_optional_integer(self):
        return self.max_optional_integer_as("maxOfOptionalInteger")

    def max_optional_integer_as(self, ret_name: str):
        self.query.max("optional_integer", ret_name)
        return self
    def sum_optional_integer(self):
        return self.sum_optional_integer_as("sumOfOptionalInteger")

    def sum_optional_integer_as(self, ret_name: str):
        self.query.sum("optional_integer", ret_name)
        return self
    def avg_optional_integer(self):
        return self.avg_optional_integer_as("avgOfOptionalInteger")

    def avg_optional_integer_as(self, ret_name: str):
        self.query.avg("optional_integer", ret_name)
        return self
    def standardDeviation_optional_integer(self):
        return self.standardDeviation_optional_integer_as("standardDeviationOfOptionalInteger")

    def standardDeviation_optional_integer_as(self, ret_name: str):
        self.query.standardDeviation("optional_integer", ret_name)
        return self
    def squareRootOfPopulationStandardDeviation_optional_integer(self):
        return self.squareRootOfPopulationStandardDeviation_optional_integer_as("squareRootOfPopulationStandardDeviationOfOptionalInteger")

    def squareRootOfPopulationStandardDeviation_optional_integer_as(self, ret_name: str):
        self.query.squareRootOfPopulationStandardDeviation("optional_integer", ret_name)
        return self
    def sampleVariance_optional_integer(self):
        return self.sampleVariance_optional_integer_as("sampleVarianceOfOptionalInteger")

    def sampleVariance_optional_integer_as(self, ret_name: str):
        self.query.sampleVariance("optional_integer", ret_name)
        return self
    def samplePopulationVariance_optional_integer(self):
        return self.samplePopulationVariance_optional_integer_as("samplePopulationVarianceOfOptionalInteger")

    def samplePopulationVariance_optional_integer_as(self, ret_name: str):
        self.query.samplePopulationVariance("optional_integer", ret_name)
        return self
    def min_required_long(self):
        return self.min_required_long_as("minOfRequiredLong")

    def min_required_long_as(self, ret_name: str):
        self.query.min("required_long", ret_name)
        return self
    def max_required_long(self):
        return self.max_required_long_as("maxOfRequiredLong")

    def max_required_long_as(self, ret_name: str):
        self.query.max("required_long", ret_name)
        return self
    def sum_required_long(self):
        return self.sum_required_long_as("sumOfRequiredLong")

    def sum_required_long_as(self, ret_name: str):
        self.query.sum("required_long", ret_name)
        return self
    def avg_required_long(self):
        return self.avg_required_long_as("avgOfRequiredLong")

    def avg_required_long_as(self, ret_name: str):
        self.query.avg("required_long", ret_name)
        return self
    def standardDeviation_required_long(self):
        return self.standardDeviation_required_long_as("standardDeviationOfRequiredLong")

    def standardDeviation_required_long_as(self, ret_name: str):
        self.query.standardDeviation("required_long", ret_name)
        return self
    def squareRootOfPopulationStandardDeviation_required_long(self):
        return self.squareRootOfPopulationStandardDeviation_required_long_as("squareRootOfPopulationStandardDeviationOfRequiredLong")

    def squareRootOfPopulationStandardDeviation_required_long_as(self, ret_name: str):
        self.query.squareRootOfPopulationStandardDeviation("required_long", ret_name)
        return self
    def sampleVariance_required_long(self):
        return self.sampleVariance_required_long_as("sampleVarianceOfRequiredLong")

    def sampleVariance_required_long_as(self, ret_name: str):
        self.query.sampleVariance("required_long", ret_name)
        return self
    def samplePopulationVariance_required_long(self):
        return self.samplePopulationVariance_required_long_as("samplePopulationVarianceOfRequiredLong")

    def samplePopulationVariance_required_long_as(self, ret_name: str):
        self.query.samplePopulationVariance("required_long", ret_name)
        return self
    def min_optional_long(self):
        return self.min_optional_long_as("minOfOptionalLong")

    def min_optional_long_as(self, ret_name: str):
        self.query.min("optional_long", ret_name)
        return self
    def max_optional_long(self):
        return self.max_optional_long_as("maxOfOptionalLong")

    def max_optional_long_as(self, ret_name: str):
        self.query.max("optional_long", ret_name)
        return self
    def sum_optional_long(self):
        return self.sum_optional_long_as("sumOfOptionalLong")

    def sum_optional_long_as(self, ret_name: str):
        self.query.sum("optional_long", ret_name)
        return self
    def avg_optional_long(self):
        return self.avg_optional_long_as("avgOfOptionalLong")

    def avg_optional_long_as(self, ret_name: str):
        self.query.avg("optional_long", ret_name)
        return self
    def standardDeviation_optional_long(self):
        return self.standardDeviation_optional_long_as("standardDeviationOfOptionalLong")

    def standardDeviation_optional_long_as(self, ret_name: str):
        self.query.standardDeviation("optional_long", ret_name)
        return self
    def squareRootOfPopulationStandardDeviation_optional_long(self):
        return self.squareRootOfPopulationStandardDeviation_optional_long_as("squareRootOfPopulationStandardDeviationOfOptionalLong")

    def squareRootOfPopulationStandardDeviation_optional_long_as(self, ret_name: str):
        self.query.squareRootOfPopulationStandardDeviation("optional_long", ret_name)
        return self
    def sampleVariance_optional_long(self):
        return self.sampleVariance_optional_long_as("sampleVarianceOfOptionalLong")

    def sampleVariance_optional_long_as(self, ret_name: str):
        self.query.sampleVariance("optional_long", ret_name)
        return self
    def samplePopulationVariance_optional_long(self):
        return self.samplePopulationVariance_optional_long_as("samplePopulationVarianceOfOptionalLong")

    def samplePopulationVariance_optional_long_as(self, ret_name: str):
        self.query.samplePopulationVariance("optional_long", ret_name)
        return self
    def min_required_decimal(self):
        return self.min_required_decimal_as("minOfRequiredDecimal")

    def min_required_decimal_as(self, ret_name: str):
        self.query.min("required_decimal", ret_name)
        return self
    def max_required_decimal(self):
        return self.max_required_decimal_as("maxOfRequiredDecimal")

    def max_required_decimal_as(self, ret_name: str):
        self.query.max("required_decimal", ret_name)
        return self
    def sum_required_decimal(self):
        return self.sum_required_decimal_as("sumOfRequiredDecimal")

    def sum_required_decimal_as(self, ret_name: str):
        self.query.sum("required_decimal", ret_name)
        return self
    def avg_required_decimal(self):
        return self.avg_required_decimal_as("avgOfRequiredDecimal")

    def avg_required_decimal_as(self, ret_name: str):
        self.query.avg("required_decimal", ret_name)
        return self
    def standardDeviation_required_decimal(self):
        return self.standardDeviation_required_decimal_as("standardDeviationOfRequiredDecimal")

    def standardDeviation_required_decimal_as(self, ret_name: str):
        self.query.standardDeviation("required_decimal", ret_name)
        return self
    def squareRootOfPopulationStandardDeviation_required_decimal(self):
        return self.squareRootOfPopulationStandardDeviation_required_decimal_as("squareRootOfPopulationStandardDeviationOfRequiredDecimal")

    def squareRootOfPopulationStandardDeviation_required_decimal_as(self, ret_name: str):
        self.query.squareRootOfPopulationStandardDeviation("required_decimal", ret_name)
        return self
    def sampleVariance_required_decimal(self):
        return self.sampleVariance_required_decimal_as("sampleVarianceOfRequiredDecimal")

    def sampleVariance_required_decimal_as(self, ret_name: str):
        self.query.sampleVariance("required_decimal", ret_name)
        return self
    def samplePopulationVariance_required_decimal(self):
        return self.samplePopulationVariance_required_decimal_as("samplePopulationVarianceOfRequiredDecimal")

    def samplePopulationVariance_required_decimal_as(self, ret_name: str):
        self.query.samplePopulationVariance("required_decimal", ret_name)
        return self
    def min_optional_decimal(self):
        return self.min_optional_decimal_as("minOfOptionalDecimal")

    def min_optional_decimal_as(self, ret_name: str):
        self.query.min("optional_decimal", ret_name)
        return self
    def max_optional_decimal(self):
        return self.max_optional_decimal_as("maxOfOptionalDecimal")

    def max_optional_decimal_as(self, ret_name: str):
        self.query.max("optional_decimal", ret_name)
        return self
    def sum_optional_decimal(self):
        return self.sum_optional_decimal_as("sumOfOptionalDecimal")

    def sum_optional_decimal_as(self, ret_name: str):
        self.query.sum("optional_decimal", ret_name)
        return self
    def avg_optional_decimal(self):
        return self.avg_optional_decimal_as("avgOfOptionalDecimal")

    def avg_optional_decimal_as(self, ret_name: str):
        self.query.avg("optional_decimal", ret_name)
        return self
    def standardDeviation_optional_decimal(self):
        return self.standardDeviation_optional_decimal_as("standardDeviationOfOptionalDecimal")

    def standardDeviation_optional_decimal_as(self, ret_name: str):
        self.query.standardDeviation("optional_decimal", ret_name)
        return self
    def squareRootOfPopulationStandardDeviation_optional_decimal(self):
        return self.squareRootOfPopulationStandardDeviation_optional_decimal_as("squareRootOfPopulationStandardDeviationOfOptionalDecimal")

    def squareRootOfPopulationStandardDeviation_optional_decimal_as(self, ret_name: str):
        self.query.squareRootOfPopulationStandardDeviation("optional_decimal", ret_name)
        return self
    def sampleVariance_optional_decimal(self):
        return self.sampleVariance_optional_decimal_as("sampleVarianceOfOptionalDecimal")

    def sampleVariance_optional_decimal_as(self, ret_name: str):
        self.query.sampleVariance("optional_decimal", ret_name)
        return self
    def samplePopulationVariance_optional_decimal(self):
        return self.samplePopulationVariance_optional_decimal_as("samplePopulationVarianceOfOptionalDecimal")

    def samplePopulationVariance_optional_decimal_as(self, ret_name: str):
        self.query.samplePopulationVariance("optional_decimal", ret_name)
        return self
    def min_required_float(self):
        return self.min_required_float_as("minOfRequiredFloat")

    def min_required_float_as(self, ret_name: str):
        self.query.min("required_float", ret_name)
        return self
    def max_required_float(self):
        return self.max_required_float_as("maxOfRequiredFloat")

    def max_required_float_as(self, ret_name: str):
        self.query.max("required_float", ret_name)
        return self
    def sum_required_float(self):
        return self.sum_required_float_as("sumOfRequiredFloat")

    def sum_required_float_as(self, ret_name: str):
        self.query.sum("required_float", ret_name)
        return self
    def avg_required_float(self):
        return self.avg_required_float_as("avgOfRequiredFloat")

    def avg_required_float_as(self, ret_name: str):
        self.query.avg("required_float", ret_name)
        return self
    def standardDeviation_required_float(self):
        return self.standardDeviation_required_float_as("standardDeviationOfRequiredFloat")

    def standardDeviation_required_float_as(self, ret_name: str):
        self.query.standardDeviation("required_float", ret_name)
        return self
    def squareRootOfPopulationStandardDeviation_required_float(self):
        return self.squareRootOfPopulationStandardDeviation_required_float_as("squareRootOfPopulationStandardDeviationOfRequiredFloat")

    def squareRootOfPopulationStandardDeviation_required_float_as(self, ret_name: str):
        self.query.squareRootOfPopulationStandardDeviation("required_float", ret_name)
        return self
    def sampleVariance_required_float(self):
        return self.sampleVariance_required_float_as("sampleVarianceOfRequiredFloat")

    def sampleVariance_required_float_as(self, ret_name: str):
        self.query.sampleVariance("required_float", ret_name)
        return self
    def samplePopulationVariance_required_float(self):
        return self.samplePopulationVariance_required_float_as("samplePopulationVarianceOfRequiredFloat")

    def samplePopulationVariance_required_float_as(self, ret_name: str):
        self.query.samplePopulationVariance("required_float", ret_name)
        return self
    def min_optional_float(self):
        return self.min_optional_float_as("minOfOptionalFloat")

    def min_optional_float_as(self, ret_name: str):
        self.query.min("optional_float", ret_name)
        return self
    def max_optional_float(self):
        return self.max_optional_float_as("maxOfOptionalFloat")

    def max_optional_float_as(self, ret_name: str):
        self.query.max("optional_float", ret_name)
        return self
    def sum_optional_float(self):
        return self.sum_optional_float_as("sumOfOptionalFloat")

    def sum_optional_float_as(self, ret_name: str):
        self.query.sum("optional_float", ret_name)
        return self
    def avg_optional_float(self):
        return self.avg_optional_float_as("avgOfOptionalFloat")

    def avg_optional_float_as(self, ret_name: str):
        self.query.avg("optional_float", ret_name)
        return self
    def standardDeviation_optional_float(self):
        return self.standardDeviation_optional_float_as("standardDeviationOfOptionalFloat")

    def standardDeviation_optional_float_as(self, ret_name: str):
        self.query.standardDeviation("optional_float", ret_name)
        return self
    def squareRootOfPopulationStandardDeviation_optional_float(self):
        return self.squareRootOfPopulationStandardDeviation_optional_float_as("squareRootOfPopulationStandardDeviationOfOptionalFloat")

    def squareRootOfPopulationStandardDeviation_optional_float_as(self, ret_name: str):
        self.query.squareRootOfPopulationStandardDeviation("optional_float", ret_name)
        return self
    def sampleVariance_optional_float(self):
        return self.sampleVariance_optional_float_as("sampleVarianceOfOptionalFloat")

    def sampleVariance_optional_float_as(self, ret_name: str):
        self.query.sampleVariance("optional_float", ret_name)
        return self
    def samplePopulationVariance_optional_float(self):
        return self.samplePopulationVariance_optional_float_as("samplePopulationVarianceOfOptionalFloat")

    def samplePopulationVariance_optional_float_as(self, ret_name: str):
        self.query.samplePopulationVariance("optional_float", ret_name)
        return self
    def min_required_double(self):
        return self.min_required_double_as("minOfRequiredDouble")

    def min_required_double_as(self, ret_name: str):
        self.query.min("required_double", ret_name)
        return self
    def max_required_double(self):
        return self.max_required_double_as("maxOfRequiredDouble")

    def max_required_double_as(self, ret_name: str):
        self.query.max("required_double", ret_name)
        return self
    def sum_required_double(self):
        return self.sum_required_double_as("sumOfRequiredDouble")

    def sum_required_double_as(self, ret_name: str):
        self.query.sum("required_double", ret_name)
        return self
    def avg_required_double(self):
        return self.avg_required_double_as("avgOfRequiredDouble")

    def avg_required_double_as(self, ret_name: str):
        self.query.avg("required_double", ret_name)
        return self
    def standardDeviation_required_double(self):
        return self.standardDeviation_required_double_as("standardDeviationOfRequiredDouble")

    def standardDeviation_required_double_as(self, ret_name: str):
        self.query.standardDeviation("required_double", ret_name)
        return self
    def squareRootOfPopulationStandardDeviation_required_double(self):
        return self.squareRootOfPopulationStandardDeviation_required_double_as("squareRootOfPopulationStandardDeviationOfRequiredDouble")

    def squareRootOfPopulationStandardDeviation_required_double_as(self, ret_name: str):
        self.query.squareRootOfPopulationStandardDeviation("required_double", ret_name)
        return self
    def sampleVariance_required_double(self):
        return self.sampleVariance_required_double_as("sampleVarianceOfRequiredDouble")

    def sampleVariance_required_double_as(self, ret_name: str):
        self.query.sampleVariance("required_double", ret_name)
        return self
    def samplePopulationVariance_required_double(self):
        return self.samplePopulationVariance_required_double_as("samplePopulationVarianceOfRequiredDouble")

    def samplePopulationVariance_required_double_as(self, ret_name: str):
        self.query.samplePopulationVariance("required_double", ret_name)
        return self
    def min_optional_double(self):
        return self.min_optional_double_as("minOfOptionalDouble")

    def min_optional_double_as(self, ret_name: str):
        self.query.min("optional_double", ret_name)
        return self
    def max_optional_double(self):
        return self.max_optional_double_as("maxOfOptionalDouble")

    def max_optional_double_as(self, ret_name: str):
        self.query.max("optional_double", ret_name)
        return self
    def sum_optional_double(self):
        return self.sum_optional_double_as("sumOfOptionalDouble")

    def sum_optional_double_as(self, ret_name: str):
        self.query.sum("optional_double", ret_name)
        return self
    def avg_optional_double(self):
        return self.avg_optional_double_as("avgOfOptionalDouble")

    def avg_optional_double_as(self, ret_name: str):
        self.query.avg("optional_double", ret_name)
        return self
    def standardDeviation_optional_double(self):
        return self.standardDeviation_optional_double_as("standardDeviationOfOptionalDouble")

    def standardDeviation_optional_double_as(self, ret_name: str):
        self.query.standardDeviation("optional_double", ret_name)
        return self
    def squareRootOfPopulationStandardDeviation_optional_double(self):
        return self.squareRootOfPopulationStandardDeviation_optional_double_as("squareRootOfPopulationStandardDeviationOfOptionalDouble")

    def squareRootOfPopulationStandardDeviation_optional_double_as(self, ret_name: str):
        self.query.squareRootOfPopulationStandardDeviation("optional_double", ret_name)
        return self
    def sampleVariance_optional_double(self):
        return self.sampleVariance_optional_double_as("sampleVarianceOfOptionalDouble")

    def sampleVariance_optional_double_as(self, ret_name: str):
        self.query.sampleVariance("optional_double", ret_name)
        return self
    def samplePopulationVariance_optional_double(self):
        return self.samplePopulationVariance_optional_double_as("samplePopulationVarianceOfOptionalDouble")

    def samplePopulationVariance_optional_double_as(self, ret_name: str):
        self.query.samplePopulationVariance("optional_double", ret_name)
        return self
    def group_by_id(self):
        self.query.group_by("id")
        return self

    def group_by_id_as(self, ret_name: str):
        self.query.group_by("id")
        return self
    def group_by_type_platform(self):
        self.query.group_by("type_platform")
        return self

    def group_by_type_platform_as(self, ret_name: str):
        self.query.group_by("type_platform")
        return self
    def group_by_required_string(self):
        self.query.group_by("required_string")
        return self

    def group_by_required_string_as(self, ret_name: str):
        self.query.group_by("required_string")
        return self
    def group_by_optional_string(self):
        self.query.group_by("optional_string")
        return self

    def group_by_optional_string_as(self, ret_name: str):
        self.query.group_by("optional_string")
        return self
    def group_by_large_text(self):
        self.query.group_by("large_text")
        return self

    def group_by_large_text_as(self, ret_name: str):
        self.query.group_by("large_text")
        return self
    def group_by_required_boolean(self):
        self.query.group_by("required_boolean")
        return self

    def group_by_required_boolean_as(self, ret_name: str):
        self.query.group_by("required_boolean")
        return self
    def group_by_optional_boolean(self):
        self.query.group_by("optional_boolean")
        return self

    def group_by_optional_boolean_as(self, ret_name: str):
        self.query.group_by("optional_boolean")
        return self
    def group_by_required_integer(self):
        self.query.group_by("required_integer")
        return self

    def group_by_required_integer_as(self, ret_name: str):
        self.query.group_by("required_integer")
        return self
    def group_by_optional_integer(self):
        self.query.group_by("optional_integer")
        return self

    def group_by_optional_integer_as(self, ret_name: str):
        self.query.group_by("optional_integer")
        return self
    def group_by_required_long(self):
        self.query.group_by("required_long")
        return self

    def group_by_required_long_as(self, ret_name: str):
        self.query.group_by("required_long")
        return self
    def group_by_optional_long(self):
        self.query.group_by("optional_long")
        return self

    def group_by_optional_long_as(self, ret_name: str):
        self.query.group_by("optional_long")
        return self
    def group_by_required_decimal(self):
        self.query.group_by("required_decimal")
        return self

    def group_by_required_decimal_as(self, ret_name: str):
        self.query.group_by("required_decimal")
        return self
    def group_by_optional_decimal(self):
        self.query.group_by("optional_decimal")
        return self

    def group_by_optional_decimal_as(self, ret_name: str):
        self.query.group_by("optional_decimal")
        return self
    def group_by_required_float(self):
        self.query.group_by("required_float")
        return self

    def group_by_required_float_as(self, ret_name: str):
        self.query.group_by("required_float")
        return self
    def group_by_optional_float(self):
        self.query.group_by("optional_float")
        return self

    def group_by_optional_float_as(self, ret_name: str):
        self.query.group_by("optional_float")
        return self
    def group_by_required_double(self):
        self.query.group_by("required_double")
        return self

    def group_by_required_double_as(self, ret_name: str):
        self.query.group_by("required_double")
        return self
    def group_by_optional_double(self):
        self.query.group_by("optional_double")
        return self

    def group_by_optional_double_as(self, ret_name: str):
        self.query.group_by("optional_double")
        return self
    def group_by_required_date(self):
        self.query.group_by("required_date")
        return self

    def group_by_required_date_as(self, ret_name: str):
        self.query.group_by("required_date")
        return self
    def group_by_optional_date(self):
        self.query.group_by("optional_date")
        return self

    def group_by_optional_date_as(self, ret_name: str):
        self.query.group_by("optional_date")
        return self
    def group_by_required_time(self):
        self.query.group_by("required_time")
        return self

    def group_by_required_time_as(self, ret_name: str):
        self.query.group_by("required_time")
        return self
    def group_by_optional_time(self):
        self.query.group_by("optional_time")
        return self

    def group_by_optional_time_as(self, ret_name: str):
        self.query.group_by("optional_time")
        return self
    def group_by_required_datetime(self):
        self.query.group_by("required_datetime")
        return self

    def group_by_required_datetime_as(self, ret_name: str):
        self.query.group_by("required_datetime")
        return self
    def group_by_optional_datetime(self):
        self.query.group_by("optional_datetime")
        return self

    def group_by_optional_datetime_as(self, ret_name: str):
        self.query.group_by("optional_datetime")
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
    def facet_by_type_platform_as(self, name: str, request: QuerySelection,
                                      include_all_facets: bool = True):
        self.query.facet_by(name, "type_platform", request.query, include_all_facets,
            QueryOperation("facet", "facet_by_type_platform_as", name, "type_platform"))
        return self


class ExecutableScalarTypeProbeRequest:
    def __init__(self, request):
        self._request = request

    def comment(self, c: str):
        self._request.comment(c)
        return self

    def new_entity(self, context) -> ScalarTypeProbe:
        request = self._request
        if not request._comment or not request._comment.strip() or not request._purpose or not request._purpose.strip():
            raise ValueError("Security audit failure: non-empty comment() and purpose() are required before new_entity()")
        entity = context.initialize_entity("ScalarTypeProbe", ScalarTypeProbe())
        if not isinstance(entity, ScalarTypeProbe):
            raise TypeError("entity initializer returned an incompatible ScalarTypeProbe")
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

    async def execute_for_list(self, context) -> SmartList[ScalarTypeProbe]:
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
            lambda row: ScalarTypeProbe(_entity_root=EntityRoot(), **row),
            count_operation=operation, count_alias=request._page_count_alias)

    async def execute_for_one(self, context):
        request = deepcopy(self._request)
        request.limit(1)
        entities = await ExecutableScalarTypeProbeRequest(request).execute_for_list(context)
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
            lambda row: ScalarTypeProbe(_entity_root=EntityRoot(), **row), chunk_size)
