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
        self.query.project("id", "platform", "order_number", "description", "version")
        return self

    def select_id(self):
        self.query.project("id")
        return self


    def select_order_number(self):
        self.query.project("order_number")
        return self

    def select_description(self):
        self.query.project("description")
        return self

    def select_version(self):
        self.query.project("version")
        return self

    def select_platform_with(self, child_request):
        self.query.project("platform")
        self.query.relation_query("platform", child_request.query)
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

    def with_description_containing(self, val: str):
        self.query.and_filter(contain("description", val))
        return self

    def with_description_not_containing(self, val: str):
        self.query.and_filter(not_contain("description", val))
        return self

    def with_description_starting_with(self, val: str):
        self.query.and_filter(begin_with("description", val))
        return self

    def with_description_not_starting_with(self, val: str):
        self.query.and_filter(not_begin_with("description", val))
        return self

    def with_description_ending_with(self, val: str):
        self.query.and_filter(end_with("description", val))
        return self

    def with_description_not_ending_with(self, val: str):
        self.query.and_filter(not_end_with("description", val))
        return self

    def with_description_sounding_like(self, val: str):
        self.query.and_filter(sound_like("description", val))
        return self

    def with_description_is(self, val: str):
        self.query.and_filter(eq("description", val))
        return self
    def with_description_is_not(self, val):
        self.query.and_filter(ne("description", val))
        return self

    def with_description_in(self, *vals):
        self.query.and_filter(in_list("description", list(vals)))
        return self

    def with_description_not_in(self, *vals):
        self.query.and_filter(not_in_list("description", list(vals)))
        return self

    def with_description_greater_than(self, val):
        self.query.and_filter(gt("description", val))
        return self

    def with_description_greater_than_or_equal_to(self, val):
        self.query.and_filter(gte("description", val))
        return self

    def with_description_less_than(self, val):
        self.query.and_filter(lt("description", val))
        return self

    def with_description_less_than_or_equal_to(self, val):
        self.query.and_filter(lte("description", val))
        return self

    def with_description_between(self, lower, upper):
        self.query.and_filter(between(column("description"), value(lower), value(upper)))
        return self

    def with_description_is_known(self):
        self.query.and_filter(is_not_null(column("description")))
        return self

    def with_description_is_unknown(self):
        self.query.and_filter(is_null(column("description")))
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

    def order_by_description_ascending(self):
        self.query.order_by("description", "asc")
        return self

    def order_by_description_descending(self):
        self.query.order_by("description", "desc")
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
    def group_by_platform(self):
        self.query.group_by("platform")
        return self

    def group_by_platform_as(self, ret_name: str):
        self.query.group_by("platform")
        return self
    def group_by_order_number(self):
        self.query.group_by("order_number")
        return self

    def group_by_order_number_as(self, ret_name: str):
        self.query.group_by("order_number")
        return self
    def group_by_description(self):
        self.query.group_by("description")
        return self

    def group_by_description_as(self, ret_name: str):
        self.query.group_by("description")
        return self
    def group_by_version(self):
        self.query.group_by("version")
        return self

    def group_by_version_as(self, ret_name: str):
        self.query.group_by("version")
        return self
    def select_order_item_list(self):
        from requests.order_item_request import OrderItemRequest
        return self.select_order_item_list_with(OrderItemRequest())

    def select_order_item_list_with(self, child_request):
        self.query.relation_query("order_item_list", child_request.query)
        return self
    def select_payment_list(self):
        from requests.payment_request import PaymentRequest
        return self.select_payment_list_with(PaymentRequest())

    def select_payment_list_with(self, child_request):
        self.query.relation_query("payment_list", child_request.query)
        return self
    def select_shipment_list(self):
        from requests.shipment_request import ShipmentRequest
        return self.select_shipment_list_with(ShipmentRequest())

    def select_shipment_list_with(self, child_request):
        self.query.relation_query("shipment_list", child_request.query)
        return self
    def have_order_items(self):
        from requests.order_item_request import OrderItemRequest
        return self.with_order_item_list_matching(OrderItemRequest())

    def have_no_order_items(self):
        from requests.order_item_request import OrderItemRequest
        return self.without_order_item_list_matching(OrderItemRequest())

    def with_order_item_list_matching(self, child_request):
        child_request.query.projection = ["customer_order"]
        self.query.and_filter(in_subquery(column("id"), "OrderItem", child_request.query))
        return self

    def without_order_item_list_matching(self, child_request):
        child_request.query.projection = ["customer_order"]
        self.query.and_filter(not_in_subquery(column("id"), "OrderItem", child_request.query))
        return self
    def have_payments(self):
        from requests.payment_request import PaymentRequest
        return self.with_payment_list_matching(PaymentRequest())

    def have_no_payments(self):
        from requests.payment_request import PaymentRequest
        return self.without_payment_list_matching(PaymentRequest())

    def with_payment_list_matching(self, child_request):
        child_request.query.projection = ["customer_order"]
        self.query.and_filter(in_subquery(column("id"), "Payment", child_request.query))
        return self

    def without_payment_list_matching(self, child_request):
        child_request.query.projection = ["customer_order"]
        self.query.and_filter(not_in_subquery(column("id"), "Payment", child_request.query))
        return self
    def have_shipments(self):
        from requests.shipment_request import ShipmentRequest
        return self.with_shipment_list_matching(ShipmentRequest())

    def have_no_shipments(self):
        from requests.shipment_request import ShipmentRequest
        return self.without_shipment_list_matching(ShipmentRequest())

    def with_shipment_list_matching(self, child_request):
        child_request.query.projection = ["customer_order"]
        self.query.and_filter(in_subquery(column("id"), "Shipment", child_request.query))
        return self

    def without_shipment_list_matching(self, child_request):
        child_request.query.projection = ["customer_order"]
        self.query.and_filter(not_in_subquery(column("id"), "Shipment", child_request.query))
        return self
    def count_order_items(self):
        return self.count_order_items_as("count_order_items")

    def count_order_items_as(self, alias: str):
        from requests.order_item_request import OrderItemRequest
        return self.count_order_items_with(alias, OrderItemRequest())

    def count_order_items_with(self, alias: str, child_request):
        child_request.query.count_field("id", alias)
        self.query.relation_aggregates.append(
            RelationAggregate("order_item_list", alias, child_request.query, True)
        )
        return self


    def count_payments(self):
        return self.count_payments_as("count_payments")

    def count_payments_as(self, alias: str):
        from requests.payment_request import PaymentRequest
        return self.count_payments_with(alias, PaymentRequest())

    def count_payments_with(self, alias: str, child_request):
        child_request.query.count_field("id", alias)
        self.query.relation_aggregates.append(
            RelationAggregate("payment_list", alias, child_request.query, True)
        )
        return self


    def count_shipments(self):
        return self.count_shipments_as("count_shipments")

    def count_shipments_as(self, alias: str):
        from requests.shipment_request import ShipmentRequest
        return self.count_shipments_with(alias, ShipmentRequest())

    def count_shipments_with(self, alias: str, child_request):
        child_request.query.count_field("id", alias)
        self.query.relation_aggregates.append(
            RelationAggregate("shipment_list", alias, child_request.query, True)
        )
        return self


    def facet_by_platform_as(self, name: str, request: QuerySelection,
                                      include_all_facets: bool = True):
        self.query.facet_by(name, "platform", request.query, include_all_facets)
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
        authorized = context.prepare_query_request(QueryRequest(query, _comment=intent.comment, _purpose=intent.purpose)).query
        service = context.require_resource("dataService")
        alias = "__teaql_total"
        if authorized.id_set_pagination is not None:
            row_result = await service.query(context, QueryRequest(authorized, _comment=request._comment, _purpose=request._purpose))
            retained_count, accuracy = context.id_set_count()
            if accuracy == "EXACT":
                total_count = retained_count
            else:
                count_result = await service.query(context, QueryRequest(authorized.for_exact_count(alias), _comment=request._comment, _purpose=request._purpose))
                if not count_result.rows or not isinstance(count_result.rows[0].get(alias), (int, float)):
                    raise RuntimeError("dataService did not return an exact page count")
                total_count = int(count_result.rows[0][alias])
        else:
            count_result = await service.query(context, QueryRequest(authorized.for_exact_count(alias), _comment=request._comment, _purpose=request._purpose))
            if not count_result.rows or not isinstance(count_result.rows[0].get(alias), (int, float)):
                raise RuntimeError("dataService did not return an exact page count")
            total_count = int(count_result.rows[0][alias])
            row_result = await service.query(context, QueryRequest(authorized, _comment=request._comment, _purpose=request._purpose))
        data = SmartList(CustomerOrder(**row) for row in row_result.rows)
        return TeaQLPage(data=data, total_count=total_count, offset=offset, limit=limit)

    async def execute_for_one(self, context):
        request = deepcopy(self._request)
        request.limit(1)
        entities = await ExecutableCustomerOrderRequest(request).execute_for_list(context)
        return entities[0] if entities else None

    async def execute_for_stream(self, context, chunk_size: int = 1000):
        """Yield entity chunks lazily from the provider cursor."""
        request = self._request
        req = QueryRequest(request.query, _comment=request._comment, _purpose=request._purpose)
        req = context.prepare_query_request(req)
        service = context.require_resource("dataService")
        if not hasattr(service, "query_stream"):
            raise RuntimeError("dataService does not implement query_stream")
        async for chunk in service.query_stream(context, req, chunk_size):
            for row in chunk.rows:
                yield CustomerOrder(**row)
