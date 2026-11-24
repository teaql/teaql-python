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
from models.order_attachment import _TeaqlFields, OrderAttachment
from typing import Protocol

class QuerySelection(Protocol):
    query: SelectQuery

class OrderAttachmentRequest:
    def __init__(self, minimal=False):
        self.query = SelectQuery("OrderAttachment")
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
        return ExecutableOrderAttachmentRequest(self)

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
        self.query.project(_TeaqlFields.ID_PROPERTY_COLUMN, _TeaqlFields.CUSTOMER_ORDER_PROPERTY_COLUMN, _TeaqlFields.FILE_NAME_PROPERTY_COLUMN, _TeaqlFields.CONTENT_TYPE_PROPERTY_COLUMN, _TeaqlFields.CONTENT_LENGTH_PROPERTY_COLUMN, _TeaqlFields.CONTENT_SHA256_PROPERTY_COLUMN, _TeaqlFields.OBJECT_KEY_PROPERTY_COLUMN, _TeaqlFields.VERSION_PROPERTY_COLUMN)
        return self

    def select_id(self):
        self.query.project(_TeaqlFields.ID_PROPERTY_COLUMN)
        return self


    def select_file_name(self):
        self.query.project(_TeaqlFields.FILE_NAME_PROPERTY_COLUMN)
        return self

    def select_content_type(self):
        self.query.project(_TeaqlFields.CONTENT_TYPE_PROPERTY_COLUMN)
        return self

    def select_content_length(self):
        self.query.project(_TeaqlFields.CONTENT_LENGTH_PROPERTY_COLUMN)
        return self

    def select_content_sha256(self):
        self.query.project(_TeaqlFields.CONTENT_SHA256_PROPERTY_COLUMN)
        return self

    def select_object_key(self):
        self.query.project(_TeaqlFields.OBJECT_KEY_PROPERTY_COLUMN)
        return self

    def select_version(self):
        self.query.project(_TeaqlFields.VERSION_PROPERTY_COLUMN)
        return self

    def select_customer_order_with(self, child_request):
        self.query.project(_TeaqlFields.CUSTOMER_ORDER_PROPERTY_COLUMN)
        self.query.relation_query(_TeaqlFields.CUSTOMER_ORDER_PROPERTY_COLUMN, child_request.query,
            QueryOperation("relation-select", "select_customer_order_with", relation=_TeaqlFields.CUSTOMER_ORDER_PROPERTY_COLUMN))
        return self
    def with_customer_order_matching(self, child_request):
        child_request.query.projection = ["id"]
        self.query.and_filter(in_subquery(column(_TeaqlFields.CUSTOMER_ORDER_PROPERTY_COLUMN), "CustomerOrder", child_request.query))
        return self

    def without_customer_order_matching(self, child_request):
        child_request.query.projection = ["id"]
        self.query.and_filter(not_in_subquery(column(_TeaqlFields.CUSTOMER_ORDER_PROPERTY_COLUMN), "CustomerOrder", child_request.query))
        return self

    def have_customer_order(self):
        self.query.and_filter(is_not_null(column(_TeaqlFields.CUSTOMER_ORDER_PROPERTY_COLUMN)))
        return self

    def have_no_customer_order(self):
        self.query.and_filter(is_null(column(_TeaqlFields.CUSTOMER_ORDER_PROPERTY_COLUMN)))
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

    def filter_by_customer_order(self, val):
        self.query.and_filter(eq(_TeaqlFields.CUSTOMER_ORDER_PROPERTY_COLUMN, val))
        return self

    def with_file_name_containing(self, val: str):
        self.query.and_filter(contain(_TeaqlFields.FILE_NAME_PROPERTY_COLUMN, val))
        return self

    def with_file_name_not_containing(self, val: str):
        self.query.and_filter(not_contain(_TeaqlFields.FILE_NAME_PROPERTY_COLUMN, val))
        return self

    def with_file_name_starting_with(self, val: str):
        self.query.and_filter(begin_with(_TeaqlFields.FILE_NAME_PROPERTY_COLUMN, val))
        return self

    def with_file_name_not_starting_with(self, val: str):
        self.query.and_filter(not_begin_with(_TeaqlFields.FILE_NAME_PROPERTY_COLUMN, val))
        return self

    def with_file_name_ending_with(self, val: str):
        self.query.and_filter(end_with(_TeaqlFields.FILE_NAME_PROPERTY_COLUMN, val))
        return self

    def with_file_name_not_ending_with(self, val: str):
        self.query.and_filter(not_end_with(_TeaqlFields.FILE_NAME_PROPERTY_COLUMN, val))
        return self

    def with_file_name_sounding_like(self, val: str):
        self.query.and_filter(sound_like(_TeaqlFields.FILE_NAME_PROPERTY_COLUMN, val))
        return self

    def with_file_name_is(self, val: str):
        self.query.and_filter(eq(_TeaqlFields.FILE_NAME_PROPERTY_COLUMN, val))
        return self
    def with_file_name_is_not(self, val):
        self.query.and_filter(ne(_TeaqlFields.FILE_NAME_PROPERTY_COLUMN, val))
        return self

    def with_file_name_in(self, *vals):
        self.query.and_filter(in_list(_TeaqlFields.FILE_NAME_PROPERTY_COLUMN, list(vals)))
        return self

    def with_file_name_not_in(self, *vals):
        self.query.and_filter(not_in_list(_TeaqlFields.FILE_NAME_PROPERTY_COLUMN, list(vals)))
        return self

    def with_file_name_greater_than(self, val):
        self.query.and_filter(gt(_TeaqlFields.FILE_NAME_PROPERTY_COLUMN, val))
        return self

    def with_file_name_greater_than_or_equal_to(self, val):
        self.query.and_filter(gte(_TeaqlFields.FILE_NAME_PROPERTY_COLUMN, val))
        return self

    def with_file_name_less_than(self, val):
        self.query.and_filter(lt(_TeaqlFields.FILE_NAME_PROPERTY_COLUMN, val))
        return self

    def with_file_name_less_than_or_equal_to(self, val):
        self.query.and_filter(lte(_TeaqlFields.FILE_NAME_PROPERTY_COLUMN, val))
        return self

    def with_file_name_between(self, lower, upper):
        self.query.and_filter(between(column(_TeaqlFields.FILE_NAME_PROPERTY_COLUMN), value(lower), value(upper)))
        return self

    def with_file_name_is_known(self):
        self.query.and_filter(is_not_null(column(_TeaqlFields.FILE_NAME_PROPERTY_COLUMN)))
        return self

    def with_file_name_is_unknown(self):
        self.query.and_filter(is_null(column(_TeaqlFields.FILE_NAME_PROPERTY_COLUMN)))
        return self

    def with_content_type_containing(self, val: str):
        self.query.and_filter(contain(_TeaqlFields.CONTENT_TYPE_PROPERTY_COLUMN, val))
        return self

    def with_content_type_not_containing(self, val: str):
        self.query.and_filter(not_contain(_TeaqlFields.CONTENT_TYPE_PROPERTY_COLUMN, val))
        return self

    def with_content_type_starting_with(self, val: str):
        self.query.and_filter(begin_with(_TeaqlFields.CONTENT_TYPE_PROPERTY_COLUMN, val))
        return self

    def with_content_type_not_starting_with(self, val: str):
        self.query.and_filter(not_begin_with(_TeaqlFields.CONTENT_TYPE_PROPERTY_COLUMN, val))
        return self

    def with_content_type_ending_with(self, val: str):
        self.query.and_filter(end_with(_TeaqlFields.CONTENT_TYPE_PROPERTY_COLUMN, val))
        return self

    def with_content_type_not_ending_with(self, val: str):
        self.query.and_filter(not_end_with(_TeaqlFields.CONTENT_TYPE_PROPERTY_COLUMN, val))
        return self

    def with_content_type_sounding_like(self, val: str):
        self.query.and_filter(sound_like(_TeaqlFields.CONTENT_TYPE_PROPERTY_COLUMN, val))
        return self

    def with_content_type_is(self, val: str):
        self.query.and_filter(eq(_TeaqlFields.CONTENT_TYPE_PROPERTY_COLUMN, val))
        return self
    def with_content_type_is_not(self, val):
        self.query.and_filter(ne(_TeaqlFields.CONTENT_TYPE_PROPERTY_COLUMN, val))
        return self

    def with_content_type_in(self, *vals):
        self.query.and_filter(in_list(_TeaqlFields.CONTENT_TYPE_PROPERTY_COLUMN, list(vals)))
        return self

    def with_content_type_not_in(self, *vals):
        self.query.and_filter(not_in_list(_TeaqlFields.CONTENT_TYPE_PROPERTY_COLUMN, list(vals)))
        return self

    def with_content_type_greater_than(self, val):
        self.query.and_filter(gt(_TeaqlFields.CONTENT_TYPE_PROPERTY_COLUMN, val))
        return self

    def with_content_type_greater_than_or_equal_to(self, val):
        self.query.and_filter(gte(_TeaqlFields.CONTENT_TYPE_PROPERTY_COLUMN, val))
        return self

    def with_content_type_less_than(self, val):
        self.query.and_filter(lt(_TeaqlFields.CONTENT_TYPE_PROPERTY_COLUMN, val))
        return self

    def with_content_type_less_than_or_equal_to(self, val):
        self.query.and_filter(lte(_TeaqlFields.CONTENT_TYPE_PROPERTY_COLUMN, val))
        return self

    def with_content_type_between(self, lower, upper):
        self.query.and_filter(between(column(_TeaqlFields.CONTENT_TYPE_PROPERTY_COLUMN), value(lower), value(upper)))
        return self

    def with_content_type_is_known(self):
        self.query.and_filter(is_not_null(column(_TeaqlFields.CONTENT_TYPE_PROPERTY_COLUMN)))
        return self

    def with_content_type_is_unknown(self):
        self.query.and_filter(is_null(column(_TeaqlFields.CONTENT_TYPE_PROPERTY_COLUMN)))
        return self

    def with_content_length_is(self, val):
        self.query.and_filter(eq(_TeaqlFields.CONTENT_LENGTH_PROPERTY_COLUMN, val))
        return self

    def with_content_length_is_not(self, val):
        self.query.and_filter(ne(_TeaqlFields.CONTENT_LENGTH_PROPERTY_COLUMN, val))
        return self

    def with_content_length_in(self, *vals):
        self.query.and_filter(in_list(_TeaqlFields.CONTENT_LENGTH_PROPERTY_COLUMN, list(vals)))
        return self

    def with_content_length_not_in(self, *vals):
        self.query.and_filter(not_in_list(_TeaqlFields.CONTENT_LENGTH_PROPERTY_COLUMN, list(vals)))
        return self

    def with_content_length_greater_than(self, val):
        self.query.and_filter(gt(_TeaqlFields.CONTENT_LENGTH_PROPERTY_COLUMN, val))
        return self

    def with_content_length_greater_than_or_equal_to(self, val):
        self.query.and_filter(gte(_TeaqlFields.CONTENT_LENGTH_PROPERTY_COLUMN, val))
        return self

    def with_content_length_less_than(self, val):
        self.query.and_filter(lt(_TeaqlFields.CONTENT_LENGTH_PROPERTY_COLUMN, val))
        return self

    def with_content_length_less_than_or_equal_to(self, val):
        self.query.and_filter(lte(_TeaqlFields.CONTENT_LENGTH_PROPERTY_COLUMN, val))
        return self

    def with_content_length_between(self, lower, upper):
        self.query.and_filter(between(column(_TeaqlFields.CONTENT_LENGTH_PROPERTY_COLUMN), value(lower), value(upper)))
        return self

    def with_content_length_is_known(self):
        self.query.and_filter(is_not_null(column(_TeaqlFields.CONTENT_LENGTH_PROPERTY_COLUMN)))
        return self

    def with_content_length_is_unknown(self):
        self.query.and_filter(is_null(column(_TeaqlFields.CONTENT_LENGTH_PROPERTY_COLUMN)))
        return self

    def with_content_sha256_containing(self, val: str):
        self.query.and_filter(contain(_TeaqlFields.CONTENT_SHA256_PROPERTY_COLUMN, val))
        return self

    def with_content_sha256_not_containing(self, val: str):
        self.query.and_filter(not_contain(_TeaqlFields.CONTENT_SHA256_PROPERTY_COLUMN, val))
        return self

    def with_content_sha256_starting_with(self, val: str):
        self.query.and_filter(begin_with(_TeaqlFields.CONTENT_SHA256_PROPERTY_COLUMN, val))
        return self

    def with_content_sha256_not_starting_with(self, val: str):
        self.query.and_filter(not_begin_with(_TeaqlFields.CONTENT_SHA256_PROPERTY_COLUMN, val))
        return self

    def with_content_sha256_ending_with(self, val: str):
        self.query.and_filter(end_with(_TeaqlFields.CONTENT_SHA256_PROPERTY_COLUMN, val))
        return self

    def with_content_sha256_not_ending_with(self, val: str):
        self.query.and_filter(not_end_with(_TeaqlFields.CONTENT_SHA256_PROPERTY_COLUMN, val))
        return self

    def with_content_sha256_sounding_like(self, val: str):
        self.query.and_filter(sound_like(_TeaqlFields.CONTENT_SHA256_PROPERTY_COLUMN, val))
        return self

    def with_content_sha256_is(self, val: str):
        self.query.and_filter(eq(_TeaqlFields.CONTENT_SHA256_PROPERTY_COLUMN, val))
        return self
    def with_content_sha256_is_not(self, val):
        self.query.and_filter(ne(_TeaqlFields.CONTENT_SHA256_PROPERTY_COLUMN, val))
        return self

    def with_content_sha256_in(self, *vals):
        self.query.and_filter(in_list(_TeaqlFields.CONTENT_SHA256_PROPERTY_COLUMN, list(vals)))
        return self

    def with_content_sha256_not_in(self, *vals):
        self.query.and_filter(not_in_list(_TeaqlFields.CONTENT_SHA256_PROPERTY_COLUMN, list(vals)))
        return self

    def with_content_sha256_greater_than(self, val):
        self.query.and_filter(gt(_TeaqlFields.CONTENT_SHA256_PROPERTY_COLUMN, val))
        return self

    def with_content_sha256_greater_than_or_equal_to(self, val):
        self.query.and_filter(gte(_TeaqlFields.CONTENT_SHA256_PROPERTY_COLUMN, val))
        return self

    def with_content_sha256_less_than(self, val):
        self.query.and_filter(lt(_TeaqlFields.CONTENT_SHA256_PROPERTY_COLUMN, val))
        return self

    def with_content_sha256_less_than_or_equal_to(self, val):
        self.query.and_filter(lte(_TeaqlFields.CONTENT_SHA256_PROPERTY_COLUMN, val))
        return self

    def with_content_sha256_between(self, lower, upper):
        self.query.and_filter(between(column(_TeaqlFields.CONTENT_SHA256_PROPERTY_COLUMN), value(lower), value(upper)))
        return self

    def with_content_sha256_is_known(self):
        self.query.and_filter(is_not_null(column(_TeaqlFields.CONTENT_SHA256_PROPERTY_COLUMN)))
        return self

    def with_content_sha256_is_unknown(self):
        self.query.and_filter(is_null(column(_TeaqlFields.CONTENT_SHA256_PROPERTY_COLUMN)))
        return self

    def with_object_key_containing(self, val: str):
        self.query.and_filter(contain(_TeaqlFields.OBJECT_KEY_PROPERTY_COLUMN, val))
        return self

    def with_object_key_not_containing(self, val: str):
        self.query.and_filter(not_contain(_TeaqlFields.OBJECT_KEY_PROPERTY_COLUMN, val))
        return self

    def with_object_key_starting_with(self, val: str):
        self.query.and_filter(begin_with(_TeaqlFields.OBJECT_KEY_PROPERTY_COLUMN, val))
        return self

    def with_object_key_not_starting_with(self, val: str):
        self.query.and_filter(not_begin_with(_TeaqlFields.OBJECT_KEY_PROPERTY_COLUMN, val))
        return self

    def with_object_key_ending_with(self, val: str):
        self.query.and_filter(end_with(_TeaqlFields.OBJECT_KEY_PROPERTY_COLUMN, val))
        return self

    def with_object_key_not_ending_with(self, val: str):
        self.query.and_filter(not_end_with(_TeaqlFields.OBJECT_KEY_PROPERTY_COLUMN, val))
        return self

    def with_object_key_sounding_like(self, val: str):
        self.query.and_filter(sound_like(_TeaqlFields.OBJECT_KEY_PROPERTY_COLUMN, val))
        return self

    def with_object_key_is(self, val: str):
        self.query.and_filter(eq(_TeaqlFields.OBJECT_KEY_PROPERTY_COLUMN, val))
        return self
    def with_object_key_is_not(self, val):
        self.query.and_filter(ne(_TeaqlFields.OBJECT_KEY_PROPERTY_COLUMN, val))
        return self

    def with_object_key_in(self, *vals):
        self.query.and_filter(in_list(_TeaqlFields.OBJECT_KEY_PROPERTY_COLUMN, list(vals)))
        return self

    def with_object_key_not_in(self, *vals):
        self.query.and_filter(not_in_list(_TeaqlFields.OBJECT_KEY_PROPERTY_COLUMN, list(vals)))
        return self

    def with_object_key_greater_than(self, val):
        self.query.and_filter(gt(_TeaqlFields.OBJECT_KEY_PROPERTY_COLUMN, val))
        return self

    def with_object_key_greater_than_or_equal_to(self, val):
        self.query.and_filter(gte(_TeaqlFields.OBJECT_KEY_PROPERTY_COLUMN, val))
        return self

    def with_object_key_less_than(self, val):
        self.query.and_filter(lt(_TeaqlFields.OBJECT_KEY_PROPERTY_COLUMN, val))
        return self

    def with_object_key_less_than_or_equal_to(self, val):
        self.query.and_filter(lte(_TeaqlFields.OBJECT_KEY_PROPERTY_COLUMN, val))
        return self

    def with_object_key_between(self, lower, upper):
        self.query.and_filter(between(column(_TeaqlFields.OBJECT_KEY_PROPERTY_COLUMN), value(lower), value(upper)))
        return self

    def with_object_key_is_known(self):
        self.query.and_filter(is_not_null(column(_TeaqlFields.OBJECT_KEY_PROPERTY_COLUMN)))
        return self

    def with_object_key_is_unknown(self):
        self.query.and_filter(is_null(column(_TeaqlFields.OBJECT_KEY_PROPERTY_COLUMN)))
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


    def order_by_file_name_ascending(self):
        self.query.order_by(_TeaqlFields.FILE_NAME_PROPERTY_COLUMN, "asc")
        return self

    def order_by_file_name_descending(self):
        self.query.order_by(_TeaqlFields.FILE_NAME_PROPERTY_COLUMN, "desc")
        return self

    def order_by_content_type_ascending(self):
        self.query.order_by(_TeaqlFields.CONTENT_TYPE_PROPERTY_COLUMN, "asc")
        return self

    def order_by_content_type_descending(self):
        self.query.order_by(_TeaqlFields.CONTENT_TYPE_PROPERTY_COLUMN, "desc")
        return self

    def order_by_content_length_ascending(self):
        self.query.order_by(_TeaqlFields.CONTENT_LENGTH_PROPERTY_COLUMN, "asc")
        return self

    def order_by_content_length_descending(self):
        self.query.order_by(_TeaqlFields.CONTENT_LENGTH_PROPERTY_COLUMN, "desc")
        return self

    def order_by_content_sha256_ascending(self):
        self.query.order_by(_TeaqlFields.CONTENT_SHA256_PROPERTY_COLUMN, "asc")
        return self

    def order_by_content_sha256_descending(self):
        self.query.order_by(_TeaqlFields.CONTENT_SHA256_PROPERTY_COLUMN, "desc")
        return self

    def order_by_object_key_ascending(self):
        self.query.order_by(_TeaqlFields.OBJECT_KEY_PROPERTY_COLUMN, "asc")
        return self

    def order_by_object_key_descending(self):
        self.query.order_by(_TeaqlFields.OBJECT_KEY_PROPERTY_COLUMN, "desc")
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

    def min_content_length(self):
        return self.min_content_length_as("minOfContentLength")

    def min_content_length_as(self, ret_name: str):
        self.query.min(_TeaqlFields.CONTENT_LENGTH_PROPERTY_COLUMN, ret_name)
        return self
    def max_content_length(self):
        return self.max_content_length_as("maxOfContentLength")

    def max_content_length_as(self, ret_name: str):
        self.query.max(_TeaqlFields.CONTENT_LENGTH_PROPERTY_COLUMN, ret_name)
        return self
    def sum_content_length(self):
        return self.sum_content_length_as("sumOfContentLength")

    def sum_content_length_as(self, ret_name: str):
        self.query.sum(_TeaqlFields.CONTENT_LENGTH_PROPERTY_COLUMN, ret_name)
        return self
    def avg_content_length(self):
        return self.avg_content_length_as("avgOfContentLength")

    def avg_content_length_as(self, ret_name: str):
        self.query.avg(_TeaqlFields.CONTENT_LENGTH_PROPERTY_COLUMN, ret_name)
        return self
    def standardDeviation_content_length(self):
        return self.standardDeviation_content_length_as("standardDeviationOfContentLength")

    def standardDeviation_content_length_as(self, ret_name: str):
        self.query.standardDeviation(_TeaqlFields.CONTENT_LENGTH_PROPERTY_COLUMN, ret_name)
        return self
    def squareRootOfPopulationStandardDeviation_content_length(self):
        return self.squareRootOfPopulationStandardDeviation_content_length_as("squareRootOfPopulationStandardDeviationOfContentLength")

    def squareRootOfPopulationStandardDeviation_content_length_as(self, ret_name: str):
        self.query.squareRootOfPopulationStandardDeviation(_TeaqlFields.CONTENT_LENGTH_PROPERTY_COLUMN, ret_name)
        return self
    def sampleVariance_content_length(self):
        return self.sampleVariance_content_length_as("sampleVarianceOfContentLength")

    def sampleVariance_content_length_as(self, ret_name: str):
        self.query.sampleVariance(_TeaqlFields.CONTENT_LENGTH_PROPERTY_COLUMN, ret_name)
        return self
    def samplePopulationVariance_content_length(self):
        return self.samplePopulationVariance_content_length_as("samplePopulationVarianceOfContentLength")

    def samplePopulationVariance_content_length_as(self, ret_name: str):
        self.query.samplePopulationVariance(_TeaqlFields.CONTENT_LENGTH_PROPERTY_COLUMN, ret_name)
        return self
    def group_by_id(self):
        self.query.group_by(_TeaqlFields.ID_PROPERTY_COLUMN)
        return self

    def group_by_id_as(self, ret_name: str):
        self.query.group_by(_TeaqlFields.ID_PROPERTY_COLUMN)
        self.query.project_expr(ret_name, column(_TeaqlFields.ID_PROPERTY_COLUMN))
        return self
    def group_by_customer_order(self):
        self.query.group_by(_TeaqlFields.CUSTOMER_ORDER_PROPERTY_COLUMN)
        return self

    def group_by_customer_order_as(self, ret_name: str):
        self.query.group_by(_TeaqlFields.CUSTOMER_ORDER_PROPERTY_COLUMN)
        self.query.project_expr(ret_name, column(_TeaqlFields.CUSTOMER_ORDER_PROPERTY_COLUMN))
        return self
    def group_by_file_name(self):
        self.query.group_by(_TeaqlFields.FILE_NAME_PROPERTY_COLUMN)
        return self

    def group_by_file_name_as(self, ret_name: str):
        self.query.group_by(_TeaqlFields.FILE_NAME_PROPERTY_COLUMN)
        self.query.project_expr(ret_name, column(_TeaqlFields.FILE_NAME_PROPERTY_COLUMN))
        return self
    def group_by_content_type(self):
        self.query.group_by(_TeaqlFields.CONTENT_TYPE_PROPERTY_COLUMN)
        return self

    def group_by_content_type_as(self, ret_name: str):
        self.query.group_by(_TeaqlFields.CONTENT_TYPE_PROPERTY_COLUMN)
        self.query.project_expr(ret_name, column(_TeaqlFields.CONTENT_TYPE_PROPERTY_COLUMN))
        return self
    def group_by_content_length(self):
        self.query.group_by(_TeaqlFields.CONTENT_LENGTH_PROPERTY_COLUMN)
        return self

    def group_by_content_length_as(self, ret_name: str):
        self.query.group_by(_TeaqlFields.CONTENT_LENGTH_PROPERTY_COLUMN)
        self.query.project_expr(ret_name, column(_TeaqlFields.CONTENT_LENGTH_PROPERTY_COLUMN))
        return self
    def group_by_content_sha256(self):
        self.query.group_by(_TeaqlFields.CONTENT_SHA256_PROPERTY_COLUMN)
        return self

    def group_by_content_sha256_as(self, ret_name: str):
        self.query.group_by(_TeaqlFields.CONTENT_SHA256_PROPERTY_COLUMN)
        self.query.project_expr(ret_name, column(_TeaqlFields.CONTENT_SHA256_PROPERTY_COLUMN))
        return self
    def group_by_object_key(self):
        self.query.group_by(_TeaqlFields.OBJECT_KEY_PROPERTY_COLUMN)
        return self

    def group_by_object_key_as(self, ret_name: str):
        self.query.group_by(_TeaqlFields.OBJECT_KEY_PROPERTY_COLUMN)
        self.query.project_expr(ret_name, column(_TeaqlFields.OBJECT_KEY_PROPERTY_COLUMN))
        return self
    def group_by_version(self):
        self.query.group_by(_TeaqlFields.VERSION_PROPERTY_COLUMN)
        return self

    def group_by_version_as(self, ret_name: str):
        self.query.group_by(_TeaqlFields.VERSION_PROPERTY_COLUMN)
        self.query.project_expr(ret_name, column(_TeaqlFields.VERSION_PROPERTY_COLUMN))
        return self
    def facet_by_customer_order_as(self, name: str, request: QuerySelection,
                                      include_all_facets: bool = True):
        self.query.facet_by(name, _TeaqlFields.CUSTOMER_ORDER_PROPERTY_COLUMN, request.query, include_all_facets,
            QueryOperation("facet", "facet_by_customer_order_as", name, _TeaqlFields.CUSTOMER_ORDER_PROPERTY_COLUMN))
        return self


class ExecutableOrderAttachmentRequest:
    def __init__(self, request):
        self._request = request

    def comment(self, c: str):
        self._request.comment(c)
        return self

    async def new_entity(self, context) -> OrderAttachment:
        request = self._request
        QueryIntent(request._comment, request._purpose)
        identity = await context.next_id("OrderAttachment")
        entity = context.initialize_entity("OrderAttachment", OrderAttachment._teaql_from_reserved_id(identity))
        if not isinstance(entity, OrderAttachment):
            raise TypeError("entity initializer returned an incompatible OrderAttachment")
        return entity

    async def execute_for_result(self, context):
        self = self._request
        req = QueryRequest(self.query, _comment=self._comment, _purpose=self._purpose)
        req = context.prepare_query_request(req)
        service = context.require_resource("dataService")
        return await service.query(context, req)

    async def execute_for_rows(self, context):
        return (await self.execute_for_result(context)).rows

    async def execute_for_list(self, context) -> SmartList[OrderAttachment]:
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
            lambda row: OrderAttachment._teaql_from_record(_entity_root=EntityRoot(), **row),
            count_operation=operation, count_alias=request._page_count_alias)

    async def execute_for_one(self, context):
        request = deepcopy(self._request)
        request.limit(1)
        entities = await ExecutableOrderAttachmentRequest(request).execute_for_list(context)
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
            lambda row: OrderAttachment._teaql_from_record(_entity_root=EntityRoot(), **row), chunk_size)
