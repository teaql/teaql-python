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
from models.school import _TeaqlFields, School
from typing import Protocol

class QuerySelection(Protocol):
    query: SelectQuery

class SchoolRequest:
    def __init__(self, minimal=False):
        self.query = SelectQuery("School")
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
        return ExecutableSchoolRequest(self)

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
        self.query.project(_TeaqlFields.ID_PROPERTY_COLUMN, _TeaqlFields.PLATFORM_PROPERTY_COLUMN, _TeaqlFields.SCHOOL_TYPE_PROPERTY_COLUMN, _TeaqlFields.NAME_PROPERTY_COLUMN, _TeaqlFields.ADDRESS_PROPERTY_COLUMN, _TeaqlFields.ESTABLISHED_DATE_PROPERTY_COLUMN, _TeaqlFields.STUDENT_CAPACITY_PROPERTY_COLUMN, _TeaqlFields.ACTIVE_PROPERTY_COLUMN, _TeaqlFields.CREATE_TIME_PROPERTY_COLUMN, _TeaqlFields.UPDATE_TIME_PROPERTY_COLUMN, _TeaqlFields.VERSION_PROPERTY_COLUMN)
        return self

    def select_id(self):
        self.query.project(_TeaqlFields.ID_PROPERTY_COLUMN)
        return self



    def select_name(self):
        self.query.project(_TeaqlFields.NAME_PROPERTY_COLUMN)
        return self

    def select_address(self):
        self.query.project(_TeaqlFields.ADDRESS_PROPERTY_COLUMN)
        return self

    def select_established_date(self):
        self.query.project(_TeaqlFields.ESTABLISHED_DATE_PROPERTY_COLUMN)
        return self

    def select_student_capacity(self):
        self.query.project(_TeaqlFields.STUDENT_CAPACITY_PROPERTY_COLUMN)
        return self

    def select_active(self):
        self.query.project(_TeaqlFields.ACTIVE_PROPERTY_COLUMN)
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

    def select_platform_with(self, child_request):
        self.query.project(_TeaqlFields.PLATFORM_PROPERTY_COLUMN)
        self.query.relation_query(_TeaqlFields.PLATFORM_PROPERTY_COLUMN, child_request.query,
            QueryOperation("relation-select", "select_platform_with", relation=_TeaqlFields.PLATFORM_PROPERTY_COLUMN))
        return self
    def select_school_type_with(self, child_request):
        self.query.project(_TeaqlFields.SCHOOL_TYPE_PROPERTY_COLUMN)
        self.query.relation_query(_TeaqlFields.SCHOOL_TYPE_PROPERTY_COLUMN, child_request.query,
            QueryOperation("relation-select", "select_school_type_with", relation=_TeaqlFields.SCHOOL_TYPE_PROPERTY_COLUMN))
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
    def with_school_type_matching(self, child_request):
        child_request.query.projection = ["id"]
        self.query.and_filter(in_subquery(column(_TeaqlFields.SCHOOL_TYPE_PROPERTY_COLUMN), "SchoolType", child_request.query))
        return self

    def without_school_type_matching(self, child_request):
        child_request.query.projection = ["id"]
        self.query.and_filter(not_in_subquery(column(_TeaqlFields.SCHOOL_TYPE_PROPERTY_COLUMN), "SchoolType", child_request.query))
        return self

    def have_school_type(self):
        self.query.and_filter(is_not_null(column(_TeaqlFields.SCHOOL_TYPE_PROPERTY_COLUMN)))
        return self

    def have_no_school_type(self):
        self.query.and_filter(is_null(column(_TeaqlFields.SCHOOL_TYPE_PROPERTY_COLUMN)))
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

    def filter_by_school_type(self, val):
        self.query.and_filter(eq(_TeaqlFields.SCHOOL_TYPE_PROPERTY_COLUMN, val))
        return self
    def with_school_type_is_primary(self):
        self.query.and_filter(eq(_TeaqlFields.SCHOOL_TYPE_PROPERTY_COLUMN, 1001))
        return self
    def with_school_type_is_secondary(self):
        self.query.and_filter(eq(_TeaqlFields.SCHOOL_TYPE_PROPERTY_COLUMN, 1002))
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

    def with_address_containing(self, val: str):
        self.query.and_filter(contain(_TeaqlFields.ADDRESS_PROPERTY_COLUMN, val))
        return self

    def with_address_not_containing(self, val: str):
        self.query.and_filter(not_contain(_TeaqlFields.ADDRESS_PROPERTY_COLUMN, val))
        return self

    def with_address_starting_with(self, val: str):
        self.query.and_filter(begin_with(_TeaqlFields.ADDRESS_PROPERTY_COLUMN, val))
        return self

    def with_address_not_starting_with(self, val: str):
        self.query.and_filter(not_begin_with(_TeaqlFields.ADDRESS_PROPERTY_COLUMN, val))
        return self

    def with_address_ending_with(self, val: str):
        self.query.and_filter(end_with(_TeaqlFields.ADDRESS_PROPERTY_COLUMN, val))
        return self

    def with_address_not_ending_with(self, val: str):
        self.query.and_filter(not_end_with(_TeaqlFields.ADDRESS_PROPERTY_COLUMN, val))
        return self

    def with_address_sounding_like(self, val: str):
        self.query.and_filter(sound_like(_TeaqlFields.ADDRESS_PROPERTY_COLUMN, val))
        return self

    def with_address_is(self, val: str):
        self.query.and_filter(eq(_TeaqlFields.ADDRESS_PROPERTY_COLUMN, val))
        return self
    def with_address_is_not(self, val):
        self.query.and_filter(ne(_TeaqlFields.ADDRESS_PROPERTY_COLUMN, val))
        return self

    def with_address_in(self, *vals):
        self.query.and_filter(in_list(_TeaqlFields.ADDRESS_PROPERTY_COLUMN, list(vals)))
        return self

    def with_address_not_in(self, *vals):
        self.query.and_filter(not_in_list(_TeaqlFields.ADDRESS_PROPERTY_COLUMN, list(vals)))
        return self

    def with_address_greater_than(self, val):
        self.query.and_filter(gt(_TeaqlFields.ADDRESS_PROPERTY_COLUMN, val))
        return self

    def with_address_greater_than_or_equal_to(self, val):
        self.query.and_filter(gte(_TeaqlFields.ADDRESS_PROPERTY_COLUMN, val))
        return self

    def with_address_less_than(self, val):
        self.query.and_filter(lt(_TeaqlFields.ADDRESS_PROPERTY_COLUMN, val))
        return self

    def with_address_less_than_or_equal_to(self, val):
        self.query.and_filter(lte(_TeaqlFields.ADDRESS_PROPERTY_COLUMN, val))
        return self

    def with_address_between(self, lower, upper):
        self.query.and_filter(between(column(_TeaqlFields.ADDRESS_PROPERTY_COLUMN), value(lower), value(upper)))
        return self

    def with_address_is_known(self):
        self.query.and_filter(is_not_null(column(_TeaqlFields.ADDRESS_PROPERTY_COLUMN)))
        return self

    def with_address_is_unknown(self):
        self.query.and_filter(is_null(column(_TeaqlFields.ADDRESS_PROPERTY_COLUMN)))
        return self

    def with_established_date_is(self, val):
        self.query.and_filter(eq(_TeaqlFields.ESTABLISHED_DATE_PROPERTY_COLUMN, val))
        return self

    def with_established_date_is_not(self, val):
        self.query.and_filter(ne(_TeaqlFields.ESTABLISHED_DATE_PROPERTY_COLUMN, val))
        return self

    def with_established_date_in(self, *vals):
        self.query.and_filter(in_list(_TeaqlFields.ESTABLISHED_DATE_PROPERTY_COLUMN, list(vals)))
        return self

    def with_established_date_not_in(self, *vals):
        self.query.and_filter(not_in_list(_TeaqlFields.ESTABLISHED_DATE_PROPERTY_COLUMN, list(vals)))
        return self

    def with_established_date_greater_than(self, val):
        self.query.and_filter(gt(_TeaqlFields.ESTABLISHED_DATE_PROPERTY_COLUMN, val))
        return self

    def with_established_date_greater_than_or_equal_to(self, val):
        self.query.and_filter(gte(_TeaqlFields.ESTABLISHED_DATE_PROPERTY_COLUMN, val))
        return self

    def with_established_date_less_than(self, val):
        self.query.and_filter(lt(_TeaqlFields.ESTABLISHED_DATE_PROPERTY_COLUMN, val))
        return self

    def with_established_date_less_than_or_equal_to(self, val):
        self.query.and_filter(lte(_TeaqlFields.ESTABLISHED_DATE_PROPERTY_COLUMN, val))
        return self

    def with_established_date_between(self, lower, upper):
        self.query.and_filter(between(column(_TeaqlFields.ESTABLISHED_DATE_PROPERTY_COLUMN), value(lower), value(upper)))
        return self

    def with_established_date_is_known(self):
        self.query.and_filter(is_not_null(column(_TeaqlFields.ESTABLISHED_DATE_PROPERTY_COLUMN)))
        return self

    def with_established_date_is_unknown(self):
        self.query.and_filter(is_null(column(_TeaqlFields.ESTABLISHED_DATE_PROPERTY_COLUMN)))
        return self

    def with_student_capacity_is(self, val):
        self.query.and_filter(eq(_TeaqlFields.STUDENT_CAPACITY_PROPERTY_COLUMN, val))
        return self

    def with_student_capacity_is_not(self, val):
        self.query.and_filter(ne(_TeaqlFields.STUDENT_CAPACITY_PROPERTY_COLUMN, val))
        return self

    def with_student_capacity_in(self, *vals):
        self.query.and_filter(in_list(_TeaqlFields.STUDENT_CAPACITY_PROPERTY_COLUMN, list(vals)))
        return self

    def with_student_capacity_not_in(self, *vals):
        self.query.and_filter(not_in_list(_TeaqlFields.STUDENT_CAPACITY_PROPERTY_COLUMN, list(vals)))
        return self

    def with_student_capacity_greater_than(self, val):
        self.query.and_filter(gt(_TeaqlFields.STUDENT_CAPACITY_PROPERTY_COLUMN, val))
        return self

    def with_student_capacity_greater_than_or_equal_to(self, val):
        self.query.and_filter(gte(_TeaqlFields.STUDENT_CAPACITY_PROPERTY_COLUMN, val))
        return self

    def with_student_capacity_less_than(self, val):
        self.query.and_filter(lt(_TeaqlFields.STUDENT_CAPACITY_PROPERTY_COLUMN, val))
        return self

    def with_student_capacity_less_than_or_equal_to(self, val):
        self.query.and_filter(lte(_TeaqlFields.STUDENT_CAPACITY_PROPERTY_COLUMN, val))
        return self

    def with_student_capacity_between(self, lower, upper):
        self.query.and_filter(between(column(_TeaqlFields.STUDENT_CAPACITY_PROPERTY_COLUMN), value(lower), value(upper)))
        return self

    def with_student_capacity_is_known(self):
        self.query.and_filter(is_not_null(column(_TeaqlFields.STUDENT_CAPACITY_PROPERTY_COLUMN)))
        return self

    def with_student_capacity_is_unknown(self):
        self.query.and_filter(is_null(column(_TeaqlFields.STUDENT_CAPACITY_PROPERTY_COLUMN)))
        return self

    def which_are_active(self):
        self.query.and_filter(eq(_TeaqlFields.ACTIVE_PROPERTY_COLUMN, True))
        return self

    def which_are_not_active(self):
        self.query.and_filter(eq(_TeaqlFields.ACTIVE_PROPERTY_COLUMN, False))
        return self
    def with_active_is_not(self, val):
        self.query.and_filter(ne(_TeaqlFields.ACTIVE_PROPERTY_COLUMN, val))
        return self

    def with_active_in(self, *vals):
        self.query.and_filter(in_list(_TeaqlFields.ACTIVE_PROPERTY_COLUMN, list(vals)))
        return self

    def with_active_not_in(self, *vals):
        self.query.and_filter(not_in_list(_TeaqlFields.ACTIVE_PROPERTY_COLUMN, list(vals)))
        return self

    def with_active_greater_than(self, val):
        self.query.and_filter(gt(_TeaqlFields.ACTIVE_PROPERTY_COLUMN, val))
        return self

    def with_active_greater_than_or_equal_to(self, val):
        self.query.and_filter(gte(_TeaqlFields.ACTIVE_PROPERTY_COLUMN, val))
        return self

    def with_active_less_than(self, val):
        self.query.and_filter(lt(_TeaqlFields.ACTIVE_PROPERTY_COLUMN, val))
        return self

    def with_active_less_than_or_equal_to(self, val):
        self.query.and_filter(lte(_TeaqlFields.ACTIVE_PROPERTY_COLUMN, val))
        return self

    def with_active_between(self, lower, upper):
        self.query.and_filter(between(column(_TeaqlFields.ACTIVE_PROPERTY_COLUMN), value(lower), value(upper)))
        return self

    def with_active_is_known(self):
        self.query.and_filter(is_not_null(column(_TeaqlFields.ACTIVE_PROPERTY_COLUMN)))
        return self

    def with_active_is_unknown(self):
        self.query.and_filter(is_null(column(_TeaqlFields.ACTIVE_PROPERTY_COLUMN)))
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



    def order_by_name_ascending(self):
        self.query.order_by(_TeaqlFields.NAME_PROPERTY_COLUMN, "asc")
        return self

    def order_by_name_descending(self):
        self.query.order_by(_TeaqlFields.NAME_PROPERTY_COLUMN, "desc")
        return self

    def order_by_address_ascending(self):
        self.query.order_by(_TeaqlFields.ADDRESS_PROPERTY_COLUMN, "asc")
        return self

    def order_by_address_descending(self):
        self.query.order_by(_TeaqlFields.ADDRESS_PROPERTY_COLUMN, "desc")
        return self

    def order_by_established_date_ascending(self):
        self.query.order_by(_TeaqlFields.ESTABLISHED_DATE_PROPERTY_COLUMN, "asc")
        return self

    def order_by_established_date_descending(self):
        self.query.order_by(_TeaqlFields.ESTABLISHED_DATE_PROPERTY_COLUMN, "desc")
        return self

    def order_by_student_capacity_ascending(self):
        self.query.order_by(_TeaqlFields.STUDENT_CAPACITY_PROPERTY_COLUMN, "asc")
        return self

    def order_by_student_capacity_descending(self):
        self.query.order_by(_TeaqlFields.STUDENT_CAPACITY_PROPERTY_COLUMN, "desc")
        return self

    def order_by_active_ascending(self):
        self.query.order_by(_TeaqlFields.ACTIVE_PROPERTY_COLUMN, "asc")
        return self

    def order_by_active_descending(self):
        self.query.order_by(_TeaqlFields.ACTIVE_PROPERTY_COLUMN, "desc")
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

    def min_student_capacity(self):
        return self.min_student_capacity_as("minOfStudentCapacity")

    def min_student_capacity_as(self, ret_name: str):
        self.query.min(_TeaqlFields.STUDENT_CAPACITY_PROPERTY_COLUMN, ret_name)
        return self
    def max_student_capacity(self):
        return self.max_student_capacity_as("maxOfStudentCapacity")

    def max_student_capacity_as(self, ret_name: str):
        self.query.max(_TeaqlFields.STUDENT_CAPACITY_PROPERTY_COLUMN, ret_name)
        return self
    def sum_student_capacity(self):
        return self.sum_student_capacity_as("sumOfStudentCapacity")

    def sum_student_capacity_as(self, ret_name: str):
        self.query.sum(_TeaqlFields.STUDENT_CAPACITY_PROPERTY_COLUMN, ret_name)
        return self
    def avg_student_capacity(self):
        return self.avg_student_capacity_as("avgOfStudentCapacity")

    def avg_student_capacity_as(self, ret_name: str):
        self.query.avg(_TeaqlFields.STUDENT_CAPACITY_PROPERTY_COLUMN, ret_name)
        return self
    def standardDeviation_student_capacity(self):
        return self.standardDeviation_student_capacity_as("standardDeviationOfStudentCapacity")

    def standardDeviation_student_capacity_as(self, ret_name: str):
        self.query.standardDeviation(_TeaqlFields.STUDENT_CAPACITY_PROPERTY_COLUMN, ret_name)
        return self
    def squareRootOfPopulationStandardDeviation_student_capacity(self):
        return self.squareRootOfPopulationStandardDeviation_student_capacity_as("squareRootOfPopulationStandardDeviationOfStudentCapacity")

    def squareRootOfPopulationStandardDeviation_student_capacity_as(self, ret_name: str):
        self.query.squareRootOfPopulationStandardDeviation(_TeaqlFields.STUDENT_CAPACITY_PROPERTY_COLUMN, ret_name)
        return self
    def sampleVariance_student_capacity(self):
        return self.sampleVariance_student_capacity_as("sampleVarianceOfStudentCapacity")

    def sampleVariance_student_capacity_as(self, ret_name: str):
        self.query.sampleVariance(_TeaqlFields.STUDENT_CAPACITY_PROPERTY_COLUMN, ret_name)
        return self
    def samplePopulationVariance_student_capacity(self):
        return self.samplePopulationVariance_student_capacity_as("samplePopulationVarianceOfStudentCapacity")

    def samplePopulationVariance_student_capacity_as(self, ret_name: str):
        self.query.samplePopulationVariance(_TeaqlFields.STUDENT_CAPACITY_PROPERTY_COLUMN, ret_name)
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
    def group_by_school_type(self):
        self.query.group_by(_TeaqlFields.SCHOOL_TYPE_PROPERTY_COLUMN)
        return self

    def group_by_school_type_as(self, ret_name: str):
        self.query.group_by(_TeaqlFields.SCHOOL_TYPE_PROPERTY_COLUMN)
        self.query.project_expr(ret_name, column(_TeaqlFields.SCHOOL_TYPE_PROPERTY_COLUMN))
        return self
    def group_by_name(self):
        self.query.group_by(_TeaqlFields.NAME_PROPERTY_COLUMN)
        return self

    def group_by_name_as(self, ret_name: str):
        self.query.group_by(_TeaqlFields.NAME_PROPERTY_COLUMN)
        self.query.project_expr(ret_name, column(_TeaqlFields.NAME_PROPERTY_COLUMN))
        return self
    def group_by_address(self):
        self.query.group_by(_TeaqlFields.ADDRESS_PROPERTY_COLUMN)
        return self

    def group_by_address_as(self, ret_name: str):
        self.query.group_by(_TeaqlFields.ADDRESS_PROPERTY_COLUMN)
        self.query.project_expr(ret_name, column(_TeaqlFields.ADDRESS_PROPERTY_COLUMN))
        return self
    def group_by_established_date(self):
        self.query.group_by(_TeaqlFields.ESTABLISHED_DATE_PROPERTY_COLUMN)
        return self

    def group_by_established_date_as(self, ret_name: str):
        self.query.group_by(_TeaqlFields.ESTABLISHED_DATE_PROPERTY_COLUMN)
        self.query.project_expr(ret_name, column(_TeaqlFields.ESTABLISHED_DATE_PROPERTY_COLUMN))
        return self
    def group_by_student_capacity(self):
        self.query.group_by(_TeaqlFields.STUDENT_CAPACITY_PROPERTY_COLUMN)
        return self

    def group_by_student_capacity_as(self, ret_name: str):
        self.query.group_by(_TeaqlFields.STUDENT_CAPACITY_PROPERTY_COLUMN)
        self.query.project_expr(ret_name, column(_TeaqlFields.STUDENT_CAPACITY_PROPERTY_COLUMN))
        return self
    def group_by_active(self):
        self.query.group_by(_TeaqlFields.ACTIVE_PROPERTY_COLUMN)
        return self

    def group_by_active_as(self, ret_name: str):
        self.query.group_by(_TeaqlFields.ACTIVE_PROPERTY_COLUMN)
        self.query.project_expr(ret_name, column(_TeaqlFields.ACTIVE_PROPERTY_COLUMN))
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
    def facet_by_platform_as(self, name: str, request: QuerySelection,
                                      include_all_facets: bool = True):
        self.query.facet_by(name, _TeaqlFields.PLATFORM_PROPERTY_COLUMN, request.query, include_all_facets,
            QueryOperation("facet", "facet_by_platform_as", name, _TeaqlFields.PLATFORM_PROPERTY_COLUMN))
        return self

    def facet_by_school_type_as(self, name: str, request: QuerySelection,
                                      include_all_facets: bool = True):
        self.query.facet_by(name, _TeaqlFields.SCHOOL_TYPE_PROPERTY_COLUMN, request.query, include_all_facets,
            QueryOperation("facet", "facet_by_school_type_as", name, _TeaqlFields.SCHOOL_TYPE_PROPERTY_COLUMN))
        return self


class ExecutableSchoolRequest:
    def __init__(self, request):
        self._request = request

    def comment(self, c: str):
        self._request.comment(c)
        return self

    async def new_entity(self, context) -> School:
        request = self._request
        QueryIntent(request._comment, request._purpose)
        identity = await context.next_id("School")
        entity = context.initialize_entity("School", School._teaql_from_reserved_id(identity))
        if not isinstance(entity, School):
            raise TypeError("entity initializer returned an incompatible School")
        return entity

    async def execute_for_result(self, context):
        self = self._request
        req = QueryRequest(self.query, _comment=self._comment, _purpose=self._purpose)
        req = context.prepare_query_request(req)
        service = context.require_resource("dataService")
        return await service.query(context, req)

    async def execute_for_rows(self, context):
        return (await self.execute_for_result(context)).rows

    async def execute_for_list(self, context) -> SmartList[School]:
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
            lambda row: School._teaql_from_record(_entity_root=EntityRoot(), **row),
            count_operation=operation, count_alias=request._page_count_alias)

    async def execute_for_one(self, context):
        request = deepcopy(self._request)
        request.limit(1)
        entities = await ExecutableSchoolRequest(request).execute_for_list(context)
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
            lambda row: School._teaql_from_record(_entity_root=EntityRoot(), **row), chunk_size)
