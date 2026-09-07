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
from models.platform import Platform
from typing import Protocol
from copy import deepcopy

class QuerySelection(Protocol):
    query: SelectQuery

class PlatformRequest:
    def __init__(self, minimal=False):
        self.query = SelectQuery("Platform")
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
        return ExecutablePlatformRequest(self)

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
        self.query.project("id", "name", "base_url", "create_time", "update_time", "version")
        return self

    def select_id(self):
        self.query.project("id")
        return self

    def select_name(self):
        self.query.project("name")
        return self

    def select_base_url(self):
        self.query.project("base_url")
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

    def with_base_url_containing(self, val: str):
        self.query.and_filter(contain("base_url", val))
        return self

    def with_base_url_not_containing(self, val: str):
        self.query.and_filter(not_contain("base_url", val))
        return self

    def with_base_url_starting_with(self, val: str):
        self.query.and_filter(begin_with("base_url", val))
        return self

    def with_base_url_not_starting_with(self, val: str):
        self.query.and_filter(not_begin_with("base_url", val))
        return self

    def with_base_url_ending_with(self, val: str):
        self.query.and_filter(end_with("base_url", val))
        return self

    def with_base_url_not_ending_with(self, val: str):
        self.query.and_filter(not_end_with("base_url", val))
        return self

    def with_base_url_sounding_like(self, val: str):
        self.query.and_filter(sound_like("base_url", val))
        return self

    def with_base_url_is(self, val: str):
        self.query.and_filter(eq("base_url", val))
        return self
    def with_base_url_is_not(self, val):
        self.query.and_filter(ne("base_url", val))
        return self

    def with_base_url_in(self, *vals):
        self.query.and_filter(in_list("base_url", list(vals)))
        return self

    def with_base_url_not_in(self, *vals):
        self.query.and_filter(not_in_list("base_url", list(vals)))
        return self

    def with_base_url_greater_than(self, val):
        self.query.and_filter(gt("base_url", val))
        return self

    def with_base_url_greater_than_or_equal_to(self, val):
        self.query.and_filter(gte("base_url", val))
        return self

    def with_base_url_less_than(self, val):
        self.query.and_filter(lt("base_url", val))
        return self

    def with_base_url_less_than_or_equal_to(self, val):
        self.query.and_filter(lte("base_url", val))
        return self

    def with_base_url_between(self, lower, upper):
        self.query.and_filter(between(column("base_url"), value(lower), value(upper)))
        return self

    def with_base_url_is_known(self):
        self.query.and_filter(is_not_null(column("base_url")))
        return self

    def with_base_url_is_unknown(self):
        self.query.and_filter(is_null(column("base_url")))
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

    def order_by_base_url_ascending(self):
        self.query.order_by("base_url", "asc")
        return self

    def order_by_base_url_descending(self):
        self.query.order_by("base_url", "desc")
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
    def group_by_base_url(self):
        self.query.group_by("base_url")
        return self

    def group_by_base_url_as(self, ret_name: str):
        self.query.group_by("base_url") 
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
    def select_school_type_list(self):
        from requests.school_type_request import SchoolTypeRequest
        return self.select_school_type_list_with(SchoolTypeRequest())

    def select_school_type_list_with(self, child_request):
        self.query.relation_query("school_type_list", child_request.query)
        return self
    def select_school_list(self):
        from requests.school_request import SchoolRequest
        return self.select_school_list_with(SchoolRequest())

    def select_school_list_with(self, child_request):
        self.query.relation_query("school_list", child_request.query)
        return self
    def have_school_types(self):
        from requests.school_type_request import SchoolTypeRequest
        return self.with_school_type_list_matching(SchoolTypeRequest())

    def have_no_school_types(self):
        from requests.school_type_request import SchoolTypeRequest
        return self.without_school_type_list_matching(SchoolTypeRequest())

    def with_school_type_list_matching(self, child_request):
        child_query = deepcopy(child_request.query)
        child_query.projection = ["platform"]
        self.query.and_filter(in_subquery(column("id"), "SchoolType", child_query))
        return self

    def without_school_type_list_matching(self, child_request):
        child_query = deepcopy(child_request.query)
        child_query.projection = ["platform"]
        self.query.and_filter(not_in_subquery(column("id"), "SchoolType", child_query))
        return self
    def have_schools(self):
        from requests.school_request import SchoolRequest
        return self.with_school_list_matching(SchoolRequest())

    def have_no_schools(self):
        from requests.school_request import SchoolRequest
        return self.without_school_list_matching(SchoolRequest())

    def with_school_list_matching(self, child_request):
        child_query = deepcopy(child_request.query)
        child_query.projection = ["platform"]
        self.query.and_filter(in_subquery(column("id"), "School", child_query))
        return self

    def without_school_list_matching(self, child_request):
        child_query = deepcopy(child_request.query)
        child_query.projection = ["platform"]
        self.query.and_filter(not_in_subquery(column("id"), "School", child_query))
        return self
    def count_school_types(self):
        return self.count_school_types_as("count_school_types")

    def count_school_types_as(self, alias: str):
        from requests.school_type_request import SchoolTypeRequest
        return self.count_school_types_with(alias, SchoolTypeRequest())

    def count_school_types_with(self, alias: str, child_request):
        child_request.query.count_field("id", alias)
        self.query.relation_aggregate("school_type_list", alias, child_request.query, True)
        return self

    def min_display_order_of_school_types(self):
        from requests.school_type_request import SchoolTypeRequest
        return self.min_display_order_of_school_types_as(
            "min_display_order_of_school_types", SchoolTypeRequest())

    def min_display_order_of_school_types_as(self, alias: str, child_request):
        child_request.query.aggregate("min", "display_order", "min_display_order")
        self.query.relation_aggregate("school_type_list", alias, child_request.query, True)
        return self
    def max_display_order_of_school_types(self):
        from requests.school_type_request import SchoolTypeRequest
        return self.max_display_order_of_school_types_as(
            "max_display_order_of_school_types", SchoolTypeRequest())

    def max_display_order_of_school_types_as(self, alias: str, child_request):
        child_request.query.aggregate("max", "display_order", "max_display_order")
        self.query.relation_aggregate("school_type_list", alias, child_request.query, True)
        return self
    def sum_display_order_of_school_types(self):
        from requests.school_type_request import SchoolTypeRequest
        return self.sum_display_order_of_school_types_as(
            "sum_display_order_of_school_types", SchoolTypeRequest())

    def sum_display_order_of_school_types_as(self, alias: str, child_request):
        child_request.query.aggregate("sum", "display_order", "sum_display_order")
        self.query.relation_aggregate("school_type_list", alias, child_request.query, True)
        return self
    def avg_display_order_of_school_types(self):
        from requests.school_type_request import SchoolTypeRequest
        return self.avg_display_order_of_school_types_as(
            "avg_display_order_of_school_types", SchoolTypeRequest())

    def avg_display_order_of_school_types_as(self, alias: str, child_request):
        child_request.query.aggregate("avg", "display_order", "avg_display_order")
        self.query.relation_aggregate("school_type_list", alias, child_request.query, True)
        return self
    def standardDeviation_display_order_of_school_types(self):
        from requests.school_type_request import SchoolTypeRequest
        return self.standardDeviation_display_order_of_school_types_as(
            "standardDeviation_display_order_of_school_types", SchoolTypeRequest())

    def standardDeviation_display_order_of_school_types_as(self, alias: str, child_request):
        child_request.query.aggregate("stddev", "display_order", "standardDeviation_display_order")
        self.query.relation_aggregate("school_type_list", alias, child_request.query, True)
        return self
    def squareRootOfPopulationStandardDeviation_display_order_of_school_types(self):
        from requests.school_type_request import SchoolTypeRequest
        return self.squareRootOfPopulationStandardDeviation_display_order_of_school_types_as(
            "squareRootOfPopulationStandardDeviation_display_order_of_school_types", SchoolTypeRequest())

    def squareRootOfPopulationStandardDeviation_display_order_of_school_types_as(self, alias: str, child_request):
        child_request.query.aggregate("stddev_pop", "display_order", "squareRootOfPopulationStandardDeviation_display_order")
        self.query.relation_aggregate("school_type_list", alias, child_request.query, True)
        return self
    def sampleVariance_display_order_of_school_types(self):
        from requests.school_type_request import SchoolTypeRequest
        return self.sampleVariance_display_order_of_school_types_as(
            "sampleVariance_display_order_of_school_types", SchoolTypeRequest())

    def sampleVariance_display_order_of_school_types_as(self, alias: str, child_request):
        child_request.query.aggregate("var_samp", "display_order", "sampleVariance_display_order")
        self.query.relation_aggregate("school_type_list", alias, child_request.query, True)
        return self
    def samplePopulationVariance_display_order_of_school_types(self):
        from requests.school_type_request import SchoolTypeRequest
        return self.samplePopulationVariance_display_order_of_school_types_as(
            "samplePopulationVariance_display_order_of_school_types", SchoolTypeRequest())

    def samplePopulationVariance_display_order_of_school_types_as(self, alias: str, child_request):
        child_request.query.aggregate("var_pop", "display_order", "samplePopulationVariance_display_order")
        self.query.relation_aggregate("school_type_list", alias, child_request.query, True)
        return self
    def count_schools(self):
        return self.count_schools_as("count_schools")

    def count_schools_as(self, alias: str):
        from requests.school_request import SchoolRequest
        return self.count_schools_with(alias, SchoolRequest())

    def count_schools_with(self, alias: str, child_request):
        child_request.query.count_field("id", alias)
        self.query.relation_aggregate("school_list", alias, child_request.query, True)
        return self

    def min_student_capacity_of_schools(self):
        from requests.school_request import SchoolRequest
        return self.min_student_capacity_of_schools_as(
            "min_student_capacity_of_schools", SchoolRequest())

    def min_student_capacity_of_schools_as(self, alias: str, child_request):
        child_request.query.aggregate("min", "student_capacity", "min_student_capacity")
        self.query.relation_aggregate("school_list", alias, child_request.query, True)
        return self
    def max_student_capacity_of_schools(self):
        from requests.school_request import SchoolRequest
        return self.max_student_capacity_of_schools_as(
            "max_student_capacity_of_schools", SchoolRequest())

    def max_student_capacity_of_schools_as(self, alias: str, child_request):
        child_request.query.aggregate("max", "student_capacity", "max_student_capacity")
        self.query.relation_aggregate("school_list", alias, child_request.query, True)
        return self
    def sum_student_capacity_of_schools(self):
        from requests.school_request import SchoolRequest
        return self.sum_student_capacity_of_schools_as(
            "sum_student_capacity_of_schools", SchoolRequest())

    def sum_student_capacity_of_schools_as(self, alias: str, child_request):
        child_request.query.aggregate("sum", "student_capacity", "sum_student_capacity")
        self.query.relation_aggregate("school_list", alias, child_request.query, True)
        return self
    def avg_student_capacity_of_schools(self):
        from requests.school_request import SchoolRequest
        return self.avg_student_capacity_of_schools_as(
            "avg_student_capacity_of_schools", SchoolRequest())

    def avg_student_capacity_of_schools_as(self, alias: str, child_request):
        child_request.query.aggregate("avg", "student_capacity", "avg_student_capacity")
        self.query.relation_aggregate("school_list", alias, child_request.query, True)
        return self
    def standardDeviation_student_capacity_of_schools(self):
        from requests.school_request import SchoolRequest
        return self.standardDeviation_student_capacity_of_schools_as(
            "standardDeviation_student_capacity_of_schools", SchoolRequest())

    def standardDeviation_student_capacity_of_schools_as(self, alias: str, child_request):
        child_request.query.aggregate("stddev", "student_capacity", "standardDeviation_student_capacity")
        self.query.relation_aggregate("school_list", alias, child_request.query, True)
        return self
    def squareRootOfPopulationStandardDeviation_student_capacity_of_schools(self):
        from requests.school_request import SchoolRequest
        return self.squareRootOfPopulationStandardDeviation_student_capacity_of_schools_as(
            "squareRootOfPopulationStandardDeviation_student_capacity_of_schools", SchoolRequest())

    def squareRootOfPopulationStandardDeviation_student_capacity_of_schools_as(self, alias: str, child_request):
        child_request.query.aggregate("stddev_pop", "student_capacity", "squareRootOfPopulationStandardDeviation_student_capacity")
        self.query.relation_aggregate("school_list", alias, child_request.query, True)
        return self
    def sampleVariance_student_capacity_of_schools(self):
        from requests.school_request import SchoolRequest
        return self.sampleVariance_student_capacity_of_schools_as(
            "sampleVariance_student_capacity_of_schools", SchoolRequest())

    def sampleVariance_student_capacity_of_schools_as(self, alias: str, child_request):
        child_request.query.aggregate("var_samp", "student_capacity", "sampleVariance_student_capacity")
        self.query.relation_aggregate("school_list", alias, child_request.query, True)
        return self
    def samplePopulationVariance_student_capacity_of_schools(self):
        from requests.school_request import SchoolRequest
        return self.samplePopulationVariance_student_capacity_of_schools_as(
            "samplePopulationVariance_student_capacity_of_schools", SchoolRequest())

    def samplePopulationVariance_student_capacity_of_schools_as(self, alias: str, child_request):
        child_request.query.aggregate("var_pop", "student_capacity", "samplePopulationVariance_student_capacity")
        self.query.relation_aggregate("school_list", alias, child_request.query, True)
        return self

class ExecutablePlatformRequest:
    def __init__(self, request):
        self._request = request

    def comment(self, c: str):
        self._request.comment(c)
        return self

    def new_entity(self, context) -> Platform:
        request = self._request
        if not request._comment or not request._comment.strip() or not request._purpose or not request._purpose.strip():
            raise ValueError("Security audit failure: non-empty comment() and purpose() are required before new_entity()")
        entity = context.initialize_entity("Platform", Platform())
        if not isinstance(entity, Platform):
            raise TypeError("entity initializer returned an incompatible Platform")
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

    async def execute_for_list(self, context) -> SmartList[Platform]:
        result = await self.execute_for_result(context)
        query_root = EntityRoot()
        return SmartList(
            (Platform(_entity_root=query_root, **row) for row in result.rows),
            facets=result.facets)

    async def execute_for_page(self, context, offset: int, limit: int) -> TeaQLPage[Platform]:
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
        data = SmartList(Platform(_entity_root=query_root, **row) for row in row_result.rows)
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
                yield Platform(_entity_root=query_root, **row)
