from teaql.core.query import SelectQuery
from teaql.core.list import SmartList, TeaQLPage
from teaql.data_service import QueryRequest
from teaql.core.expr import eq, contain, gte, lte
from models.school_type import SchoolType

class SchoolTypeRequest:
    def __init__(self, minimal=False):
        self.query = SelectQuery("SchoolType")
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
        return ExecutableSchoolTypeRequest(self)

    def optimize_for_continuous_page_fetch(self):
        self.query.optimize_for_continuous_page_fetch()
        return self

    def optimize_for_continuous_page_fetch_with(self, namespace: str, ttl_seconds: int):
        self.query.optimize_for_continuous_page_fetch_with(namespace, ttl_seconds)
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
        self.query.project("platform", "id", "name", "code", "display_order", "version")
        return self

    def select_id(self):
        self.query.project("id")
        return self

    def select_name(self):
        self.query.project("name")
        return self

    def select_code(self):
        self.query.project("code")
        return self

    def select_display_order(self):
        self.query.project("display_order")
        return self

    def select_version(self):
        self.query.project("version")
        return self

    def select_platform_with(self, child_request):
        self.query.project("platform")
        self.query.relation_query("platform", child_request.query)
        return self

    def filter_by_platform(self, val):
        self.query.and_filter(eq("platform", val))
        return self

    def with_id_is(self, val):
        self.query.and_filter(eq("id", val))
        return self

    def with_name_containing(self, val: str):
        self.query.and_filter(contain("name", val))
        return self

    def with_name_is(self, val: str):
        self.query.and_filter(eq("name", val))
        return self

    def with_code_containing(self, val: str):
        self.query.and_filter(contain("code", val))
        return self

    def with_code_is(self, val: str):
        self.query.and_filter(eq("code", val))
        return self

    def with_display_order_is(self, val):
        self.query.and_filter(eq("display_order", val))
        return self

    def with_version_is(self, val):
        self.query.and_filter(eq("version", val))
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

    def order_by_code_ascending(self):
        self.query.order_by("code", "asc")
        return self

    def order_by_code_descending(self):
        self.query.order_by("code", "desc")
        return self

    def order_by_display_order_ascending(self):
        self.query.order_by("display_order", "asc")
        return self

    def order_by_display_order_descending(self):
        self.query.order_by("display_order", "desc")
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

    def min_display_order(self):
        return self.min_display_order_as("minOfDisplayOrder")

    def min_display_order_as(self, ret_name: str):
        self.query.aggregate("min", "display_order", ret_name)
        return self
    def max_display_order(self):
        return self.max_display_order_as("maxOfDisplayOrder")

    def max_display_order_as(self, ret_name: str):
        self.query.aggregate("max", "display_order", ret_name)
        return self
    def sum_display_order(self):
        return self.sum_display_order_as("sumOfDisplayOrder")

    def sum_display_order_as(self, ret_name: str):
        self.query.aggregate("sum", "display_order", ret_name)
        return self
    def avg_display_order(self):
        return self.avg_display_order_as("avgOfDisplayOrder")

    def avg_display_order_as(self, ret_name: str):
        self.query.aggregate("avg", "display_order", ret_name)
        return self
    def standardDeviation_display_order(self):
        return self.standardDeviation_display_order_as("standardDeviationOfDisplayOrder")

    def standardDeviation_display_order_as(self, ret_name: str):
        self.query.aggregate("stddev", "display_order", ret_name)
        return self
    def squareRootOfPopulationStandardDeviation_display_order(self):
        return self.squareRootOfPopulationStandardDeviation_display_order_as("squareRootOfPopulationStandardDeviationOfDisplayOrder")

    def squareRootOfPopulationStandardDeviation_display_order_as(self, ret_name: str):
        self.query.aggregate("stddev_pop", "display_order", ret_name)
        return self
    def sampleVariance_display_order(self):
        return self.sampleVariance_display_order_as("sampleVarianceOfDisplayOrder")

    def sampleVariance_display_order_as(self, ret_name: str):
        self.query.aggregate("var_samp", "display_order", ret_name)
        return self
    def samplePopulationVariance_display_order(self):
        return self.samplePopulationVariance_display_order_as("samplePopulationVarianceOfDisplayOrder")

    def samplePopulationVariance_display_order_as(self, ret_name: str):
        self.query.aggregate("var_pop", "display_order", ret_name)
        return self
    def group_by_platform(self):
        self.query.group_by("platform")
        return self

    def group_by_platform_as(self, ret_name: str):
        self.query.group_by("platform") 
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
    def group_by_code(self):
        self.query.group_by("code")
        return self

    def group_by_code_as(self, ret_name: str):
        self.query.group_by("code") 
        return self
    def group_by_display_order(self):
        self.query.group_by("display_order")
        return self

    def group_by_display_order_as(self, ret_name: str):
        self.query.group_by("display_order") 
        return self
    def group_by_version(self):
        self.query.group_by("version")
        return self

    def group_by_version_as(self, ret_name: str):
        self.query.group_by("version") 
        return self
    def select_school_list(self):
        from requests.school_request import SchoolRequest
        return self.select_school_list_with(SchoolRequest())

    def select_school_list_with(self, child_request):
        self.query.relation_query("school_list", child_request.query)
        return self

class ExecutableSchoolTypeRequest:
    def __init__(self, request):
        self._request = request

    def comment(self, c: str):
        self._request.comment(c)
        return self

    def new_entity(self, context) -> SchoolType:
        request = self._request
        if not request._comment or not request._comment.strip() or not request._purpose or not request._purpose.strip():
            raise ValueError("Security audit failure: non-empty comment() and purpose() are required before new_entity()")
        entity = context.initialize_entity("SchoolType", SchoolType(_entity_root=context.entity_root()))
        if not isinstance(entity, SchoolType):
            raise TypeError("entity initializer returned an incompatible SchoolType")
        return entity

    async def execute_for_rows(self, context):
        self = self._request
        if not self._purpose or not self._purpose.strip() or not self._comment or not self._comment.strip():
            raise Exception("Security audit failure: comment() and purpose() must be called before execute_for_rows()")
        service = context.require_resource("dataService")
        req = QueryRequest(context.prepare_query(self.query))
        res = await service.query(context, req)
        return res.rows

    async def execute_for_list(self, context) -> SmartList[SchoolType]:
        rows = await self.execute_for_rows(context)
        return SmartList(SchoolType(_entity_root=context.entity_root(), **row) for row in rows)

    async def execute_for_page(self, context, offset: int, limit: int) -> TeaQLPage[SchoolType]:
        request = self._request
        if not request._purpose or not request._purpose.strip() or not request._comment or not request._comment.strip():
            raise ValueError("Security audit failure: comment() and purpose() must be called before execute_for_page()")
        request.query.offset(offset).limit(limit)
        authorized = context.prepare_query(request.query)
        service = context.require_resource("dataService")
        alias = "__teaql_total"
        count_result = await service.query(context, QueryRequest(authorized.for_exact_count(alias)))
        if not count_result.rows or not isinstance(count_result.rows[0].get(alias), (int, float)):
            raise RuntimeError("dataService did not return an exact page count")
        row_result = await service.query(context, QueryRequest(authorized))
        data = SmartList(SchoolType(_entity_root=context.entity_root(), **row) for row in row_result.rows)
        return TeaQLPage(data=data, total_count=int(count_result.rows[0][alias]), offset=offset, limit=limit)

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
        async for chunk in service.query_stream(context, QueryRequest(request.query), chunk_size):
            for row in chunk.rows:
                yield SchoolType(_entity_root=context.entity_root(), **row)
