from teaql.core.query import SelectQuery
from teaql.data_service import QueryRequest
from teaql.core.expr import eq, contain
from models.order_status import OrderStatus

class OrderStatusRequest:
    def __init__(self):
        self.query = SelectQuery("OrderStatus")
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
        return ExecutableOrderStatusRequest(self)

    def limit(self, n: int):
        self.query.limit(n)
        return self

    def offset(self, n: int):
        self.query.offset(n)
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

    def with_color_containing(self, val: str):
        self.query.and_filter(contain("color", val))
        return self

    def with_color_is(self, val: str):
        self.query.and_filter(eq("color", val))
        return self

    def with_display_order_is(self, val):
        self.query.and_filter(eq("display_order", val))
        return self

    def filter_by_commerce_platform(self, val):
        self.query.and_filter(eq("commerce_platform", val))
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

    def order_by_color_ascending(self):
        self.query.order_by("color", "asc")
        return self

    def order_by_color_descending(self):
        self.query.order_by("color", "desc")
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
    def group_by_color(self):
        self.query.group_by("color")
        return self

    def group_by_color_as(self, ret_name: str):
        self.query.group_by("color") 
        return self
    def group_by_display_order(self):
        self.query.group_by("display_order")
        return self

    def group_by_display_order_as(self, ret_name: str):
        self.query.group_by("display_order") 
        return self
    def group_by_commerce_platform(self):
        self.query.group_by("commerce_platform")
        return self

    def group_by_commerce_platform_as(self, ret_name: str):
        self.query.group_by("commerce_platform") 
        return self
    def group_by_version(self):
        self.query.group_by("version")
        return self

    def group_by_version_as(self, ret_name: str):
        self.query.group_by("version") 
        return self
    def select_customer_order_list(self):
        from requests.customer_order_request import CustomerOrderRequest
        return self.select_customer_order_list_with(CustomerOrderRequest())

    def select_customer_order_list_with(self, child_request):
        self.query.relation_query("customer_order_list", child_request.query)
        return self

class ExecutableOrderStatusRequest:
    def __init__(self, request):
        self._request = request

    def new_entity(self, context) -> OrderStatus:
        return OrderStatus()

    async def execute_for_list(self, context):
        self = self._request
        if not self._purpose or not self._comment:
            raise Exception("Security audit failure: comment() and purpose() must be called before execute_for_list()")
        service = context.require_resource("dataService")
        req = QueryRequest(self.query)
        res = await service.query(context, req)

        result = {"data": res.rows}
        return result

    async def execute_for_one(self, context):
        self._request.limit(1)
        res = await self.execute_for_list(context)
        if res["data"]:
            return res["data"][0]
        return None

    async def execute_entities_for_list(self, context):
        res = await self.execute_for_list(context)
        return [OrderStatus(**row) for row in res["data"]]

    async def execute_entity_for_one(self, context):
        self._request.limit(1)
        entities = await self.execute_entities_for_list(context)
        return entities[0] if entities else None