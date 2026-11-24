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
from models.customer import _TeaqlFields, Customer
from typing import Protocol

class QuerySelection(Protocol):
    query: SelectQuery

class CustomerRequest:
    def __init__(self, minimal=False):
        self.query = SelectQuery("Customer")
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
        return ExecutableCustomerRequest(self)

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
        self.query.project(_TeaqlFields.ID_PROPERTY_COLUMN, _TeaqlFields.PLATFORM_PROPERTY_COLUMN, _TeaqlFields.EMAIL_PROPERTY_COLUMN, _TeaqlFields.VERSION_PROPERTY_COLUMN)
        return self

    def select_id(self):
        self.query.project(_TeaqlFields.ID_PROPERTY_COLUMN)
        return self


    def select_email(self):
        self.query.project(_TeaqlFields.EMAIL_PROPERTY_COLUMN)
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

    def with_email_containing(self, val: str):
        self.query.and_filter(contain(_TeaqlFields.EMAIL_PROPERTY_COLUMN, val))
        return self

    def with_email_not_containing(self, val: str):
        self.query.and_filter(not_contain(_TeaqlFields.EMAIL_PROPERTY_COLUMN, val))
        return self

    def with_email_starting_with(self, val: str):
        self.query.and_filter(begin_with(_TeaqlFields.EMAIL_PROPERTY_COLUMN, val))
        return self

    def with_email_not_starting_with(self, val: str):
        self.query.and_filter(not_begin_with(_TeaqlFields.EMAIL_PROPERTY_COLUMN, val))
        return self

    def with_email_ending_with(self, val: str):
        self.query.and_filter(end_with(_TeaqlFields.EMAIL_PROPERTY_COLUMN, val))
        return self

    def with_email_not_ending_with(self, val: str):
        self.query.and_filter(not_end_with(_TeaqlFields.EMAIL_PROPERTY_COLUMN, val))
        return self

    def with_email_sounding_like(self, val: str):
        self.query.and_filter(sound_like(_TeaqlFields.EMAIL_PROPERTY_COLUMN, val))
        return self

    def with_email_is(self, val: str):
        self.query.and_filter(eq(_TeaqlFields.EMAIL_PROPERTY_COLUMN, val))
        return self
    def with_email_is_not(self, val):
        self.query.and_filter(ne(_TeaqlFields.EMAIL_PROPERTY_COLUMN, val))
        return self

    def with_email_in(self, *vals):
        self.query.and_filter(in_list(_TeaqlFields.EMAIL_PROPERTY_COLUMN, list(vals)))
        return self

    def with_email_not_in(self, *vals):
        self.query.and_filter(not_in_list(_TeaqlFields.EMAIL_PROPERTY_COLUMN, list(vals)))
        return self

    def with_email_greater_than(self, val):
        self.query.and_filter(gt(_TeaqlFields.EMAIL_PROPERTY_COLUMN, val))
        return self

    def with_email_greater_than_or_equal_to(self, val):
        self.query.and_filter(gte(_TeaqlFields.EMAIL_PROPERTY_COLUMN, val))
        return self

    def with_email_less_than(self, val):
        self.query.and_filter(lt(_TeaqlFields.EMAIL_PROPERTY_COLUMN, val))
        return self

    def with_email_less_than_or_equal_to(self, val):
        self.query.and_filter(lte(_TeaqlFields.EMAIL_PROPERTY_COLUMN, val))
        return self

    def with_email_between(self, lower, upper):
        self.query.and_filter(between(column(_TeaqlFields.EMAIL_PROPERTY_COLUMN), value(lower), value(upper)))
        return self

    def with_email_is_known(self):
        self.query.and_filter(is_not_null(column(_TeaqlFields.EMAIL_PROPERTY_COLUMN)))
        return self

    def with_email_is_unknown(self):
        self.query.and_filter(is_null(column(_TeaqlFields.EMAIL_PROPERTY_COLUMN)))
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


    def order_by_email_ascending(self):
        self.query.order_by(_TeaqlFields.EMAIL_PROPERTY_COLUMN, "asc")
        return self

    def order_by_email_descending(self):
        self.query.order_by(_TeaqlFields.EMAIL_PROPERTY_COLUMN, "desc")
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
    def group_by_email(self):
        self.query.group_by(_TeaqlFields.EMAIL_PROPERTY_COLUMN)
        return self

    def group_by_email_as(self, ret_name: str):
        self.query.group_by(_TeaqlFields.EMAIL_PROPERTY_COLUMN)
        self.query.project_expr(ret_name, column(_TeaqlFields.EMAIL_PROPERTY_COLUMN))
        return self
    def group_by_version(self):
        self.query.group_by(_TeaqlFields.VERSION_PROPERTY_COLUMN)
        return self

    def group_by_version_as(self, ret_name: str):
        self.query.group_by(_TeaqlFields.VERSION_PROPERTY_COLUMN)
        self.query.project_expr(ret_name, column(_TeaqlFields.VERSION_PROPERTY_COLUMN))
        return self
    def select_customer_contact_list(self):
        from requests.customer_contact_request import CustomerContactRequest
        return self.select_customer_contact_list_with(CustomerContactRequest())

    def select_customer_contact_list_with(self, child_request):
        self.query.relation_query("customer_contact_list", child_request.query,
            QueryOperation("relation-select", "select_customer_contact_list_with", relation="customer_contact_list"))
        return self
    def have_customer_contacts(self):
        from requests.customer_contact_request import CustomerContactRequest
        return self.with_customer_contact_list_matching(CustomerContactRequest())

    def have_no_customer_contacts(self):
        from requests.customer_contact_request import CustomerContactRequest
        return self.without_customer_contact_list_matching(CustomerContactRequest())

    def with_customer_contact_list_matching(self, child_request):
        child_request.query.projection = ["customer"]
        self.query.and_filter(in_subquery(column("id"), "CustomerContact", child_request.query))
        return self

    def without_customer_contact_list_matching(self, child_request):
        child_request.query.projection = ["customer"]
        self.query.and_filter(not_in_subquery(column("id"), "CustomerContact", child_request.query))
        return self
    def count_customer_contacts(self):
        return self.count_customer_contacts_as("count_customer_contacts")

    def count_customer_contacts_as(self, alias: str):
        from requests.customer_contact_request import CustomerContactRequest
        self.count_customer_contacts_with(alias, CustomerContactRequest())
        self.query.relation_aggregates[-1].operation = QueryOperation(
            "relation-count", "count_customer_contacts_as", alias, "customer_contact_list")
        return self

    def count_customer_contacts_with(self, alias: str, child_request):
        query = deepcopy(child_request.query)
        query.aggregates = []
        query.count_field("id", alias)
        self.query.relation_aggregates.append(
            RelationAggregate("customer_contact_list", alias, query, True,
                QueryOperation("relation-count", "count_customer_contacts_with", alias, "customer_contact_list"))
        )
        return self


    def facet_by_platform_as(self, name: str, request: QuerySelection,
                                      include_all_facets: bool = True):
        self.query.facet_by(name, _TeaqlFields.PLATFORM_PROPERTY_COLUMN, request.query, include_all_facets,
            QueryOperation("facet", "facet_by_platform_as", name, _TeaqlFields.PLATFORM_PROPERTY_COLUMN))
        return self


class ExecutableCustomerRequest:
    def __init__(self, request):
        self._request = request

    def comment(self, c: str):
        self._request.comment(c)
        return self

    async def new_entity(self, context) -> Customer:
        request = self._request
        QueryIntent(request._comment, request._purpose)
        identity = await context.next_id("Customer")
        entity = context.initialize_entity("Customer", Customer._teaql_from_reserved_id(identity))
        if not isinstance(entity, Customer):
            raise TypeError("entity initializer returned an incompatible Customer")
        return entity

    async def execute_for_result(self, context):
        self = self._request
        req = QueryRequest(self.query, _comment=self._comment, _purpose=self._purpose)
        req = context.prepare_query_request(req)
        service = context.require_resource("dataService")
        return await service.query(context, req)

    async def execute_for_rows(self, context):
        return (await self.execute_for_result(context)).rows

    async def execute_for_list(self, context) -> SmartList[Customer]:
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
            lambda row: Customer._teaql_from_record(_entity_root=EntityRoot(), **row),
            count_operation=operation, count_alias=request._page_count_alias)

    async def execute_for_one(self, context):
        request = deepcopy(self._request)
        request.limit(1)
        entities = await ExecutableCustomerRequest(request).execute_for_list(context)
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
            lambda row: Customer._teaql_from_record(_entity_root=EntityRoot(), **row), chunk_size)
