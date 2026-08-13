from teaql.core.query import SelectQuery
from teaql.data_service import QueryRequest
from teaql.core.expr import eq, contain
from models.customer_order import CustomerOrder

class CustomerOrderRequest:
    def __init__(self):
        self.query = SelectQuery("CustomerOrder")
        self._purpose = None
        self._comment = None

    def comment(self, c: str):
        self.query.comment(c)
        self._comment = c
        return self

    def purpose(self, p: str):
        if not self._comment or not self._comment.strip():
            raise ValueError("purpose() requires a non-empty comment() set earlier on the request")
        self.query.purpose(p)
        self._purpose = p
        return ExecutableCustomerOrderRequest(self)

    def limit(self, n: int):
        self.query.limit(n)
        return self

    def offset(self, n: int):
        self.query.offset(n)
        return self

    def with_id_is(self, val):
        self.query.and_filter(eq("id", val))
        return self

    def with_order_number_containing(self, val: str):
        self.query.and_filter(contain("order_number", val))
        return self

    def with_order_number_is(self, val: str):
        self.query.and_filter(eq("order_number", val))
        return self

    def with_order_date_is(self, val):
        self.query.and_filter(eq("order_date", val))
        return self

    def with_total_amount_is(self, val):
        self.query.and_filter(eq("total_amount", val))
        return self

    def filter_by_status(self, val):
        self.query.and_filter(eq("status", val))
        return self

    def filter_by_customer(self, val):
        self.query.and_filter(eq("customer", val))
        return self

    def filter_by_commerce_platform(self, val):
        self.query.and_filter(eq("commerce_platform", val))
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

    def order_by_order_number_ascending(self):
        self.query.order_by("order_number", "asc")
        return self

    def order_by_order_number_descending(self):
        self.query.order_by("order_number", "desc")
        return self

    def order_by_order_date_ascending(self):
        self.query.order_by("order_date", "asc")
        return self

    def order_by_order_date_descending(self):
        self.query.order_by("order_date", "desc")
        return self

    def order_by_total_amount_ascending(self):
        self.query.order_by("total_amount", "asc")
        return self

    def order_by_total_amount_descending(self):
        self.query.order_by("total_amount", "desc")
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

    def min_total_amount(self):
        return self.min_total_amount_as("minOfTotalAmount")

    def min_total_amount_as(self, ret_name: str):
        self.query.aggregate("min", "total_amount", ret_name)
        return self
    def max_total_amount(self):
        return self.max_total_amount_as("maxOfTotalAmount")

    def max_total_amount_as(self, ret_name: str):
        self.query.aggregate("max", "total_amount", ret_name)
        return self
    def sum_total_amount(self):
        return self.sum_total_amount_as("sumOfTotalAmount")

    def sum_total_amount_as(self, ret_name: str):
        self.query.aggregate("sum", "total_amount", ret_name)
        return self
    def avg_total_amount(self):
        return self.avg_total_amount_as("avgOfTotalAmount")

    def avg_total_amount_as(self, ret_name: str):
        self.query.aggregate("avg", "total_amount", ret_name)
        return self
    def standardDeviation_total_amount(self):
        return self.standardDeviation_total_amount_as("standardDeviationOfTotalAmount")

    def standardDeviation_total_amount_as(self, ret_name: str):
        self.query.aggregate("stddev", "total_amount", ret_name)
        return self
    def squareRootOfPopulationStandardDeviation_total_amount(self):
        return self.squareRootOfPopulationStandardDeviation_total_amount_as("squareRootOfPopulationStandardDeviationOfTotalAmount")

    def squareRootOfPopulationStandardDeviation_total_amount_as(self, ret_name: str):
        self.query.aggregate("stddev_pop", "total_amount", ret_name)
        return self
    def sampleVariance_total_amount(self):
        return self.sampleVariance_total_amount_as("sampleVarianceOfTotalAmount")

    def sampleVariance_total_amount_as(self, ret_name: str):
        self.query.aggregate("var_samp", "total_amount", ret_name)
        return self
    def samplePopulationVariance_total_amount(self):
        return self.samplePopulationVariance_total_amount_as("samplePopulationVarianceOfTotalAmount")

    def samplePopulationVariance_total_amount_as(self, ret_name: str):
        self.query.aggregate("var_pop", "total_amount", ret_name)
        return self
    def group_by_id(self):
        self.query.group_by("id")
        return self

    def group_by_id_as(self, ret_name: str):
        self.query.group_by("id") 
        return self
    def group_by_order_number(self):
        self.query.group_by("order_number")
        return self

    def group_by_order_number_as(self, ret_name: str):
        self.query.group_by("order_number") 
        return self
    def group_by_order_date(self):
        self.query.group_by("order_date")
        return self

    def group_by_order_date_as(self, ret_name: str):
        self.query.group_by("order_date") 
        return self
    def group_by_total_amount(self):
        self.query.group_by("total_amount")
        return self

    def group_by_total_amount_as(self, ret_name: str):
        self.query.group_by("total_amount") 
        return self
    def group_by_status(self):
        self.query.group_by("status")
        return self

    def group_by_status_as(self, ret_name: str):
        self.query.group_by("status") 
        return self
    def group_by_customer(self):
        self.query.group_by("customer")
        return self

    def group_by_customer_as(self, ret_name: str):
        self.query.group_by("customer") 
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
    def select_order_line_list(self):
        from requests.order_line_request import OrderLineRequest
        return self.select_order_line_list_with(OrderLineRequest())

    def select_order_line_list_with(self, child_request):
        self.query.relation_query("order_line_list", child_request.query)
        return self

class ExecutableCustomerOrderRequest:
    def __init__(self, request):
        self._request = request

    def new_entity(self, ctx) -> CustomerOrder:
        return CustomerOrder()

    async def execute_for_list(self, ctx):
        self = self._request
        if not self._purpose or not self._comment:
            raise Exception("Security audit failure: comment() and purpose() must be called before execute_for_list()")
        service = ctx.require_resource("dataService")
        req = QueryRequest(self.query)
        res = await service.query(ctx, req)

        result = {"data": res.rows}
        return result

    async def execute_for_one(self, ctx):
        self._request.limit(1)
        res = await self.execute_for_list(ctx)
        if res["data"]:
            return res["data"][0]
        return None

    async def execute_entities_for_list(self, ctx):
        res = await self.execute_for_list(ctx)
        return [CustomerOrder(**row) for row in res["data"]]

    async def execute_entity_for_one(self, ctx):
        self._request.limit(1)
        entities = await self.execute_entities_for_list(ctx)
        return entities[0] if entities else None