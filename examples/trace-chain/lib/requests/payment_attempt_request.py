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
from models.payment_attempt import PaymentAttempt
from typing import Protocol

class QuerySelection(Protocol):
    query: SelectQuery

class PaymentAttemptRequest:
    def __init__(self, minimal=False):
        self.query = SelectQuery("PaymentAttempt")
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
        return ExecutablePaymentAttemptRequest(self)

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
        self.query.project("id", "payment", "reference_code", "version")
        return self

    def select_id(self):
        self.query.project("id")
        return self


    def select_reference_code(self):
        self.query.project("reference_code")
        return self

    def select_version(self):
        self.query.project("version")
        return self

    def select_payment_with(self, child_request):
        self.query.project("payment")
        self.query.relation_query("payment", child_request.query)
        return self
    def with_payment_matching(self, child_request):
        child_request.query.projection = ["id"]
        self.query.and_filter(in_subquery(column("payment"), "Payment", child_request.query))
        return self

    def without_payment_matching(self, child_request):
        child_request.query.projection = ["id"]
        self.query.and_filter(not_in_subquery(column("payment"), "Payment", child_request.query))
        return self

    def have_payment(self):
        self.query.and_filter(is_not_null(column("payment")))
        return self

    def have_no_payment(self):
        self.query.and_filter(is_null(column("payment")))
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

    def filter_by_payment(self, val):
        self.query.and_filter(eq("payment", val))
        return self

    def with_reference_code_containing(self, val: str):
        self.query.and_filter(contain("reference_code", val))
        return self

    def with_reference_code_not_containing(self, val: str):
        self.query.and_filter(not_contain("reference_code", val))
        return self

    def with_reference_code_starting_with(self, val: str):
        self.query.and_filter(begin_with("reference_code", val))
        return self

    def with_reference_code_not_starting_with(self, val: str):
        self.query.and_filter(not_begin_with("reference_code", val))
        return self

    def with_reference_code_ending_with(self, val: str):
        self.query.and_filter(end_with("reference_code", val))
        return self

    def with_reference_code_not_ending_with(self, val: str):
        self.query.and_filter(not_end_with("reference_code", val))
        return self

    def with_reference_code_sounding_like(self, val: str):
        self.query.and_filter(sound_like("reference_code", val))
        return self

    def with_reference_code_is(self, val: str):
        self.query.and_filter(eq("reference_code", val))
        return self
    def with_reference_code_is_not(self, val):
        self.query.and_filter(ne("reference_code", val))
        return self

    def with_reference_code_in(self, *vals):
        self.query.and_filter(in_list("reference_code", list(vals)))
        return self

    def with_reference_code_not_in(self, *vals):
        self.query.and_filter(not_in_list("reference_code", list(vals)))
        return self

    def with_reference_code_greater_than(self, val):
        self.query.and_filter(gt("reference_code", val))
        return self

    def with_reference_code_greater_than_or_equal_to(self, val):
        self.query.and_filter(gte("reference_code", val))
        return self

    def with_reference_code_less_than(self, val):
        self.query.and_filter(lt("reference_code", val))
        return self

    def with_reference_code_less_than_or_equal_to(self, val):
        self.query.and_filter(lte("reference_code", val))
        return self

    def with_reference_code_between(self, lower, upper):
        self.query.and_filter(between(column("reference_code"), value(lower), value(upper)))
        return self

    def with_reference_code_is_known(self):
        self.query.and_filter(is_not_null(column("reference_code")))
        return self

    def with_reference_code_is_unknown(self):
        self.query.and_filter(is_null(column("reference_code")))
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


    def order_by_reference_code_ascending(self):
        self.query.order_by("reference_code", "asc")
        return self

    def order_by_reference_code_descending(self):
        self.query.order_by("reference_code", "desc")
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
    def group_by_payment(self):
        self.query.group_by("payment")
        return self

    def group_by_payment_as(self, ret_name: str):
        self.query.group_by("payment")
        return self
    def group_by_reference_code(self):
        self.query.group_by("reference_code")
        return self

    def group_by_reference_code_as(self, ret_name: str):
        self.query.group_by("reference_code")
        return self
    def group_by_version(self):
        self.query.group_by("version")
        return self

    def group_by_version_as(self, ret_name: str):
        self.query.group_by("version")
        return self
    def facet_by_payment_as(self, name: str, request: QuerySelection,
                                      include_all_facets: bool = True):
        self.query.facet_by(name, "payment", request.query, include_all_facets)
        return self


class ExecutablePaymentAttemptRequest:
    def __init__(self, request):
        self._request = request

    def comment(self, c: str):
        self._request.comment(c)
        return self

    def new_entity(self, context) -> PaymentAttempt:
        request = self._request
        QueryIntent(request._comment, request._purpose)
        entity = context.initialize_entity("PaymentAttempt", PaymentAttempt())
        if not isinstance(entity, PaymentAttempt):
            raise TypeError("entity initializer returned an incompatible PaymentAttempt")
        return entity

    async def execute_for_result(self, context):
        self = self._request
        req = QueryRequest(self.query, _comment=self._comment, _purpose=self._purpose)
        req = context.prepare_query_request(req)
        service = context.require_resource("dataService")
        return await service.query(context, req)

    async def execute_for_rows(self, context):
        return (await self.execute_for_result(context)).rows

    async def execute_for_list(self, context) -> SmartList[PaymentAttempt]:
        result = await self.execute_for_result(context)
        return SmartList(
            (PaymentAttempt(**row) for row in result.rows),
            facets=result.facets)

    async def execute_for_page(self, context, offset: int, limit: int) -> TeaQLPage[PaymentAttempt]:
        request = self._request
        intent = QueryIntent(request._comment, request._purpose)
        query = deepcopy(request.query)
        query.offset(offset).limit(limit)
        authorized = context.prepare_query_request(QueryRequest(query, _comment=intent.comment, _purpose=intent.purpose))
        service = context.require_resource("dataService")
        alias = "__teaql_total"
        if authorized.query.id_set_pagination is not None:
            row_result = await service.query(context, authorized)
            retained_count, accuracy = context.id_set_count()
            if accuracy == "EXACT":
                total_count = retained_count
            else:
                count_result = await service.query(context, authorized.with_query(authorized.query.for_exact_count(alias)))
                if not count_result.rows or not isinstance(count_result.rows[0].get(alias), (int, float)):
                    raise RuntimeError("dataService did not return an exact page count")
                total_count = int(count_result.rows[0][alias])
        else:
            count_result = await service.query(context, authorized.with_query(authorized.query.for_exact_count(alias)))
            if not count_result.rows or not isinstance(count_result.rows[0].get(alias), (int, float)):
                raise RuntimeError("dataService did not return an exact page count")
            total_count = int(count_result.rows[0][alias])
            row_result = await service.query(context, authorized)
        data = SmartList(PaymentAttempt(**row) for row in row_result.rows)
        return TeaQLPage(data=data, total_count=total_count, offset=offset, limit=limit)

    async def execute_for_one(self, context):
        request = deepcopy(self._request)
        request.limit(1)
        entities = await ExecutablePaymentAttemptRequest(request).execute_for_list(context)
        return entities[0] if entities else None

    def execute_for_stream(self, context, chunk_size: int = 1000):
        """Yield entity chunks lazily from the provider cursor."""
        request = self._request
        req = QueryRequest(request.query, _comment=request._comment, _purpose=request._purpose)
        req = context.prepare_query_request(req)
        service = context.require_resource("dataService")
        if not hasattr(service, "query_stream"):
            raise RuntimeError("dataService does not implement query_stream")
        stream = service.query_stream(context, req, chunk_size)
        async def entities():
            try:
                async for chunk in stream:
                    for row in chunk.rows:
                        yield PaymentAttempt(**row)
            finally:
                close = getattr(stream, "aclose", None)
                if close is not None:
                    await close()
        return entities()
