from teaql.core.query import SelectQuery
from teaql.core.list import SmartList, TeaQLPage
from teaql.data_service import QueryRequest
from teaql.core.expr import eq, contain, gte, lte
from models.school import School

class SchoolRequest:
    def __init__(self, minimal=False):
        self.query = SelectQuery("School")
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
        return ExecutableSchoolRequest(self)

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
        self.query.project("id", "platform", "school_type", "name", "address", "established_date", "student_capacity", "active", "create_time", "update_time", "version")
        return self

    def select_id(self):
        self.query.project("id")
        return self



    def select_name(self):
        self.query.project("name")
        return self

    def select_address(self):
        self.query.project("address")
        return self

    def select_established_date(self):
        self.query.project("established_date")
        return self

    def select_student_capacity(self):
        self.query.project("student_capacity")
        return self

    def select_active(self):
        self.query.project("active")
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

    def select_platform_with(self, child_request):
        self.query.project("platform")
        self.query.relation_query("platform", child_request.query)
        return self
    def select_school_type_with(self, child_request):
        self.query.project("school_type")
        self.query.relation_query("school_type", child_request.query)
        return self

    def with_id_is(self, val):
        self.query.and_filter(eq("id", val))
        return self

    def filter_by_platform(self, val):
        self.query.and_filter(eq("platform", val))
        return self

    def filter_by_school_type(self, val):
        self.query.and_filter(eq("school_type", val))
        return self
    def with_school_type_is_primary(self):
        self.query.and_filter(eq("school_type", 1001))
        return self

    def with_name_containing(self, val: str):
        self.query.and_filter(contain("name", val))
        return self

    def with_name_is(self, val: str):
        self.query.and_filter(eq("name", val))
        return self

    def with_address_containing(self, val: str):
        self.query.and_filter(contain("address", val))
        return self

    def with_address_is(self, val: str):
        self.query.and_filter(eq("address", val))
        return self

    def with_established_date_is(self, val):
        self.query.and_filter(eq("established_date", val))
        return self

    def with_student_capacity_is(self, val):
        self.query.and_filter(eq("student_capacity", val))
        return self

    def which_are_active(self):
        self.query.and_filter(eq("active", True))
        return self

    def which_are_not_active(self):
        self.query.and_filter(eq("active", False))
        return self

    def with_create_time_is(self, val):
        self.query.and_filter(eq("create_time", val))
        return self

    def with_update_time_is(self, val):
        self.query.and_filter(eq("update_time", val))
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

    def order_by_address_ascending(self):
        self.query.order_by("address", "asc")
        return self

    def order_by_address_descending(self):
        self.query.order_by("address", "desc")
        return self

    def order_by_established_date_ascending(self):
        self.query.order_by("established_date", "asc")
        return self

    def order_by_established_date_descending(self):
        self.query.order_by("established_date", "desc")
        return self

    def order_by_student_capacity_ascending(self):
        self.query.order_by("student_capacity", "asc")
        return self

    def order_by_student_capacity_descending(self):
        self.query.order_by("student_capacity", "desc")
        return self

    def order_by_active_ascending(self):
        self.query.order_by("active", "asc")
        return self

    def order_by_active_descending(self):
        self.query.order_by("active", "desc")
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

    def min_student_capacity(self):
        return self.min_student_capacity_as("minOfStudentCapacity")

    def min_student_capacity_as(self, ret_name: str):
        self.query.aggregate("min", "student_capacity", ret_name)
        return self
    def max_student_capacity(self):
        return self.max_student_capacity_as("maxOfStudentCapacity")

    def max_student_capacity_as(self, ret_name: str):
        self.query.aggregate("max", "student_capacity", ret_name)
        return self
    def sum_student_capacity(self):
        return self.sum_student_capacity_as("sumOfStudentCapacity")

    def sum_student_capacity_as(self, ret_name: str):
        self.query.aggregate("sum", "student_capacity", ret_name)
        return self
    def avg_student_capacity(self):
        return self.avg_student_capacity_as("avgOfStudentCapacity")

    def avg_student_capacity_as(self, ret_name: str):
        self.query.aggregate("avg", "student_capacity", ret_name)
        return self
    def standardDeviation_student_capacity(self):
        return self.standardDeviation_student_capacity_as("standardDeviationOfStudentCapacity")

    def standardDeviation_student_capacity_as(self, ret_name: str):
        self.query.aggregate("stddev", "student_capacity", ret_name)
        return self
    def squareRootOfPopulationStandardDeviation_student_capacity(self):
        return self.squareRootOfPopulationStandardDeviation_student_capacity_as("squareRootOfPopulationStandardDeviationOfStudentCapacity")

    def squareRootOfPopulationStandardDeviation_student_capacity_as(self, ret_name: str):
        self.query.aggregate("stddev_pop", "student_capacity", ret_name)
        return self
    def sampleVariance_student_capacity(self):
        return self.sampleVariance_student_capacity_as("sampleVarianceOfStudentCapacity")

    def sampleVariance_student_capacity_as(self, ret_name: str):
        self.query.aggregate("var_samp", "student_capacity", ret_name)
        return self
    def samplePopulationVariance_student_capacity(self):
        return self.samplePopulationVariance_student_capacity_as("samplePopulationVarianceOfStudentCapacity")

    def samplePopulationVariance_student_capacity_as(self, ret_name: str):
        self.query.aggregate("var_pop", "student_capacity", ret_name)
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
    def group_by_school_type(self):
        self.query.group_by("school_type")
        return self

    def group_by_school_type_as(self, ret_name: str):
        self.query.group_by("school_type") 
        return self
    def group_by_name(self):
        self.query.group_by("name")
        return self

    def group_by_name_as(self, ret_name: str):
        self.query.group_by("name") 
        return self
    def group_by_address(self):
        self.query.group_by("address")
        return self

    def group_by_address_as(self, ret_name: str):
        self.query.group_by("address") 
        return self
    def group_by_established_date(self):
        self.query.group_by("established_date")
        return self

    def group_by_established_date_as(self, ret_name: str):
        self.query.group_by("established_date") 
        return self
    def group_by_student_capacity(self):
        self.query.group_by("student_capacity")
        return self

    def group_by_student_capacity_as(self, ret_name: str):
        self.query.group_by("student_capacity") 
        return self
    def group_by_active(self):
        self.query.group_by("active")
        return self

    def group_by_active_as(self, ret_name: str):
        self.query.group_by("active") 
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

class ExecutableSchoolRequest:
    def __init__(self, request):
        self._request = request

    def comment(self, c: str):
        self._request.comment(c)
        return self

    def new_entity(self, context) -> School:
        request = self._request
        if not request._comment or not request._comment.strip() or not request._purpose or not request._purpose.strip():
            raise ValueError("Security audit failure: non-empty comment() and purpose() are required before new_entity()")
        entity = context.initialize_entity("School", School(_entity_root=context.entity_root()))
        if not isinstance(entity, School):
            raise TypeError("entity initializer returned an incompatible School")
        return entity

    async def execute_for_rows(self, context):
        self = self._request
        if not self._purpose or not self._purpose.strip() or not self._comment or not self._comment.strip():
            raise Exception("Security audit failure: comment() and purpose() must be called before execute_for_rows()")
        service = context.require_resource("dataService")
        req = QueryRequest(context.prepare_query(self.query))
        res = await service.query(context, req)
        return res.rows

    async def execute_for_list(self, context) -> SmartList[School]:
        rows = await self.execute_for_rows(context)
        return SmartList(School(_entity_root=context.entity_root(), **row) for row in rows)

    async def execute_for_page(self, context, offset: int, limit: int) -> TeaQLPage[School]:
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
        data = SmartList(School(_entity_root=context.entity_root(), **row) for row in row_result.rows)
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
                yield School(_entity_root=context.entity_root(), **row)
