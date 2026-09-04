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
from models.order_line import OrderLine
from typing import Protocol

class QuerySelection(Protocol):
    query: SelectQuery

class OrderLineRequest:
    def __init__(self, minimal=False):
        self.query = SelectQuery("OrderLine")
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
        return ExecutableOrderLineRequest(self)

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
        self.query.project("id", "customer_order", "product", "product_name", "sku", "quantity", "commerce_platform", "create_time", "version")
        return self

    def select_id(self):
        self.query.project("id")
        return self



    def select_product_name(self):
        self.query.project("product_name")
        return self

    def select_sku(self):
        self.query.project("sku")
        return self

    def select_quantity(self):
        self.query.project("quantity")
        return self


    def select_create_time(self):
        self.query.project("create_time")
        return self

    def select_version(self):
        self.query.project("version")
        return self

    def select_customer_order_with(self, child_request):
        self.query.project("customer_order")
        self.query.relation_query("customer_order", child_request.query)
        return self
    def select_product_with(self, child_request):
        self.query.project("product")
        self.query.relation_query("product", child_request.query)
        return self
    def select_commerce_platform_with(self, child_request):
        self.query.project("commerce_platform")
        self.query.relation_query("commerce_platform", child_request.query)
        return self
    def with_customer_order_matching(self, child_request):
        child_request.query._projection = ["id"]
        self.query.and_filter(in_subquery(column("customer_order"), "CustomerOrder", child_request.query))
        return self

    def without_customer_order_matching(self, child_request):
        child_request.query._projection = ["id"]
        self.query.and_filter(not_in_subquery(column("customer_order"), "CustomerOrder", child_request.query))
        return self

    def have_customer_order(self):
        self.query.and_filter(is_not_null(column("customer_order")))
        return self

    def have_no_customer_order(self):
        self.query.and_filter(is_null(column("customer_order")))
        return self
    def with_product_matching(self, child_request):
        child_request.query._projection = ["id"]
        self.query.and_filter(in_subquery(column("product"), "Product", child_request.query))
        return self

    def without_product_matching(self, child_request):
        child_request.query._projection = ["id"]
        self.query.and_filter(not_in_subquery(column("product"), "Product", child_request.query))
        return self

    def have_product(self):
        self.query.and_filter(is_not_null(column("product")))
        return self

    def have_no_product(self):
        self.query.and_filter(is_null(column("product")))
        return self
    def with_commerce_platform_matching(self, child_request):
        child_request.query._projection = ["id"]
        self.query.and_filter(in_subquery(column("commerce_platform"), "CommercePlatform", child_request.query))
        return self

    def without_commerce_platform_matching(self, child_request):
        child_request.query._projection = ["id"]
        self.query.and_filter(not_in_subquery(column("commerce_platform"), "CommercePlatform", child_request.query))
        return self

    def have_commerce_platform(self):
        self.query.and_filter(is_not_null(column("commerce_platform")))
        return self

    def have_no_commerce_platform(self):
        self.query.and_filter(is_null(column("commerce_platform")))
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

    def filter_by_customer_order(self, val):
        self.query.and_filter(eq("customer_order", val))
        return self

    def filter_by_product(self, val):
        self.query.and_filter(eq("product", val))
        return self

    def with_product_name_containing(self, val: str):
        self.query.and_filter(contain("product_name", val))
        return self

    def with_product_name_not_containing(self, val: str):
        self.query.and_filter(not_contain("product_name", val))
        return self

    def with_product_name_starting_with(self, val: str):
        self.query.and_filter(begin_with("product_name", val))
        return self

    def with_product_name_not_starting_with(self, val: str):
        self.query.and_filter(not_begin_with("product_name", val))
        return self

    def with_product_name_ending_with(self, val: str):
        self.query.and_filter(end_with("product_name", val))
        return self

    def with_product_name_not_ending_with(self, val: str):
        self.query.and_filter(not_end_with("product_name", val))
        return self

    def with_product_name_sounding_like(self, val: str):
        self.query.and_filter(sound_like("product_name", val))
        return self

    def with_product_name_is(self, val: str):
        self.query.and_filter(eq("product_name", val))
        return self
    def with_product_name_is_not(self, val):
        self.query.and_filter(ne("product_name", val))
        return self

    def with_product_name_in(self, *vals):
        self.query.and_filter(in_list("product_name", list(vals)))
        return self

    def with_product_name_not_in(self, *vals):
        self.query.and_filter(not_in_list("product_name", list(vals)))
        return self

    def with_product_name_greater_than(self, val):
        self.query.and_filter(gt("product_name", val))
        return self

    def with_product_name_greater_than_or_equal_to(self, val):
        self.query.and_filter(gte("product_name", val))
        return self

    def with_product_name_less_than(self, val):
        self.query.and_filter(lt("product_name", val))
        return self

    def with_product_name_less_than_or_equal_to(self, val):
        self.query.and_filter(lte("product_name", val))
        return self

    def with_product_name_between(self, lower, upper):
        self.query.and_filter(between(column("product_name"), value(lower), value(upper)))
        return self

    def with_product_name_is_known(self):
        self.query.and_filter(is_not_null(column("product_name")))
        return self

    def with_product_name_is_unknown(self):
        self.query.and_filter(is_null(column("product_name")))
        return self

    def with_sku_containing(self, val: str):
        self.query.and_filter(contain("sku", val))
        return self

    def with_sku_not_containing(self, val: str):
        self.query.and_filter(not_contain("sku", val))
        return self

    def with_sku_starting_with(self, val: str):
        self.query.and_filter(begin_with("sku", val))
        return self

    def with_sku_not_starting_with(self, val: str):
        self.query.and_filter(not_begin_with("sku", val))
        return self

    def with_sku_ending_with(self, val: str):
        self.query.and_filter(end_with("sku", val))
        return self

    def with_sku_not_ending_with(self, val: str):
        self.query.and_filter(not_end_with("sku", val))
        return self

    def with_sku_sounding_like(self, val: str):
        self.query.and_filter(sound_like("sku", val))
        return self

    def with_sku_is(self, val: str):
        self.query.and_filter(eq("sku", val))
        return self
    def with_sku_is_not(self, val):
        self.query.and_filter(ne("sku", val))
        return self

    def with_sku_in(self, *vals):
        self.query.and_filter(in_list("sku", list(vals)))
        return self

    def with_sku_not_in(self, *vals):
        self.query.and_filter(not_in_list("sku", list(vals)))
        return self

    def with_sku_greater_than(self, val):
        self.query.and_filter(gt("sku", val))
        return self

    def with_sku_greater_than_or_equal_to(self, val):
        self.query.and_filter(gte("sku", val))
        return self

    def with_sku_less_than(self, val):
        self.query.and_filter(lt("sku", val))
        return self

    def with_sku_less_than_or_equal_to(self, val):
        self.query.and_filter(lte("sku", val))
        return self

    def with_sku_between(self, lower, upper):
        self.query.and_filter(between(column("sku"), value(lower), value(upper)))
        return self

    def with_sku_is_known(self):
        self.query.and_filter(is_not_null(column("sku")))
        return self

    def with_sku_is_unknown(self):
        self.query.and_filter(is_null(column("sku")))
        return self

    def with_quantity_is(self, val):
        self.query.and_filter(eq("quantity", val))
        return self

    def with_quantity_is_not(self, val):
        self.query.and_filter(ne("quantity", val))
        return self

    def with_quantity_in(self, *vals):
        self.query.and_filter(in_list("quantity", list(vals)))
        return self

    def with_quantity_not_in(self, *vals):
        self.query.and_filter(not_in_list("quantity", list(vals)))
        return self

    def with_quantity_greater_than(self, val):
        self.query.and_filter(gt("quantity", val))
        return self

    def with_quantity_greater_than_or_equal_to(self, val):
        self.query.and_filter(gte("quantity", val))
        return self

    def with_quantity_less_than(self, val):
        self.query.and_filter(lt("quantity", val))
        return self

    def with_quantity_less_than_or_equal_to(self, val):
        self.query.and_filter(lte("quantity", val))
        return self

    def with_quantity_between(self, lower, upper):
        self.query.and_filter(between(column("quantity"), value(lower), value(upper)))
        return self

    def with_quantity_is_known(self):
        self.query.and_filter(is_not_null(column("quantity")))
        return self

    def with_quantity_is_unknown(self):
        self.query.and_filter(is_null(column("quantity")))
        return self

    def filter_by_commerce_platform(self, val):
        self.query.and_filter(eq("commerce_platform", val))
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



    def order_by_product_name_ascending(self):
        self.query.order_by("product_name", "asc")
        return self

    def order_by_product_name_descending(self):
        self.query.order_by("product_name", "desc")
        return self

    def order_by_sku_ascending(self):
        self.query.order_by("sku", "asc")
        return self

    def order_by_sku_descending(self):
        self.query.order_by("sku", "desc")
        return self

    def order_by_quantity_ascending(self):
        self.query.order_by("quantity", "asc")
        return self

    def order_by_quantity_descending(self):
        self.query.order_by("quantity", "desc")
        return self


    def order_by_create_time_ascending(self):
        self.query.order_by("create_time", "asc")
        return self

    def order_by_create_time_descending(self):
        self.query.order_by("create_time", "desc")
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

    def min_quantity(self):
        return self.min_quantity_as("minOfQuantity")

    def min_quantity_as(self, ret_name: str):
        self.query.aggregate("min", "quantity", ret_name)
        return self
    def max_quantity(self):
        return self.max_quantity_as("maxOfQuantity")

    def max_quantity_as(self, ret_name: str):
        self.query.aggregate("max", "quantity", ret_name)
        return self
    def sum_quantity(self):
        return self.sum_quantity_as("sumOfQuantity")

    def sum_quantity_as(self, ret_name: str):
        self.query.aggregate("sum", "quantity", ret_name)
        return self
    def avg_quantity(self):
        return self.avg_quantity_as("avgOfQuantity")

    def avg_quantity_as(self, ret_name: str):
        self.query.aggregate("avg", "quantity", ret_name)
        return self
    def standardDeviation_quantity(self):
        return self.standardDeviation_quantity_as("standardDeviationOfQuantity")

    def standardDeviation_quantity_as(self, ret_name: str):
        self.query.aggregate("stddev", "quantity", ret_name)
        return self
    def squareRootOfPopulationStandardDeviation_quantity(self):
        return self.squareRootOfPopulationStandardDeviation_quantity_as("squareRootOfPopulationStandardDeviationOfQuantity")

    def squareRootOfPopulationStandardDeviation_quantity_as(self, ret_name: str):
        self.query.aggregate("stddev_pop", "quantity", ret_name)
        return self
    def sampleVariance_quantity(self):
        return self.sampleVariance_quantity_as("sampleVarianceOfQuantity")

    def sampleVariance_quantity_as(self, ret_name: str):
        self.query.aggregate("var_samp", "quantity", ret_name)
        return self
    def samplePopulationVariance_quantity(self):
        return self.samplePopulationVariance_quantity_as("samplePopulationVarianceOfQuantity")

    def samplePopulationVariance_quantity_as(self, ret_name: str):
        self.query.aggregate("var_pop", "quantity", ret_name)
        return self
    def group_by_id(self):
        self.query.group_by("id")
        return self

    def group_by_id_as(self, ret_name: str):
        self.query.group_by("id") 
        return self
    def group_by_customer_order(self):
        self.query.group_by("customer_order")
        return self

    def group_by_customer_order_as(self, ret_name: str):
        self.query.group_by("customer_order") 
        return self
    def group_by_product(self):
        self.query.group_by("product")
        return self

    def group_by_product_as(self, ret_name: str):
        self.query.group_by("product") 
        return self
    def group_by_product_name(self):
        self.query.group_by("product_name")
        return self

    def group_by_product_name_as(self, ret_name: str):
        self.query.group_by("product_name") 
        return self
    def group_by_sku(self):
        self.query.group_by("sku")
        return self

    def group_by_sku_as(self, ret_name: str):
        self.query.group_by("sku") 
        return self
    def group_by_quantity(self):
        self.query.group_by("quantity")
        return self

    def group_by_quantity_as(self, ret_name: str):
        self.query.group_by("quantity") 
        return self
    def group_by_commerce_platform(self):
        self.query.group_by("commerce_platform")
        return self

    def group_by_commerce_platform_as(self, ret_name: str):
        self.query.group_by("commerce_platform") 
        return self
    def group_by_create_time(self):
        self.query.group_by("create_time")
        return self

    def group_by_create_time_as(self, ret_name: str):
        self.query.group_by("create_time") 
        return self
    def group_by_version(self):
        self.query.group_by("version")
        return self

    def group_by_version_as(self, ret_name: str):
        self.query.group_by("version") 
        return self
    def facet_by_customer_order_as(self, name: str, request: QuerySelection,
                                      include_all_facets: bool = True):
        self.query.facet_by(name, "customer_order", request.query, include_all_facets)
        return self

    def facet_by_product_as(self, name: str, request: QuerySelection,
                                      include_all_facets: bool = True):
        self.query.facet_by(name, "product", request.query, include_all_facets)
        return self

    def facet_by_commerce_platform_as(self, name: str, request: QuerySelection,
                                      include_all_facets: bool = True):
        self.query.facet_by(name, "commerce_platform", request.query, include_all_facets)
        return self


class ExecutableOrderLineRequest:
    def __init__(self, request):
        self._request = request

    def comment(self, c: str):
        self._request.comment(c)
        return self

    def new_entity(self, context) -> OrderLine:
        request = self._request
        if not request._comment or not request._comment.strip() or not request._purpose or not request._purpose.strip():
            raise ValueError("Security audit failure: non-empty comment() and purpose() are required before new_entity()")
        entity = context.initialize_entity("OrderLine", OrderLine())
        if not isinstance(entity, OrderLine):
            raise TypeError("entity initializer returned an incompatible OrderLine")
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

    async def execute_for_list(self, context) -> SmartList[OrderLine]:
        result = await self.execute_for_result(context)
        query_root = EntityRoot()
        return SmartList(
            (OrderLine(_entity_root=query_root, **row) for row in result.rows),
            facets=result.facets)

    async def execute_for_page(self, context, offset: int, limit: int) -> TeaQLPage[OrderLine]:
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
        data = SmartList(OrderLine(_entity_root=query_root, **row) for row in row_result.rows)
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
                yield OrderLine(_entity_root=query_root, **row)
