from teaql.core.query import SelectQuery
from teaql.data_service import QueryRequest
from teaql.core.expr import eq, contain
from models.order_line import OrderLine

class OrderLineRequest:
    def __init__(self):
        self.query = SelectQuery("OrderLine")
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
        return ExecutableOrderLineRequest(self)

    def limit(self, n: int):
        self.query.limit(n)
        return self

    def offset(self, n: int):
        self.query.offset(n)
        return self

    def with_id_is(self, val):
        self.query.and_filter(eq("id", val))
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

    def with_product_name_is(self, val: str):
        self.query.and_filter(eq("product_name", val))
        return self

    def with_sku_containing(self, val: str):
        self.query.and_filter(contain("sku", val))
        return self

    def with_sku_is(self, val: str):
        self.query.and_filter(eq("sku", val))
        return self

    def with_quantity_is(self, val):
        self.query.and_filter(eq("quantity", val))
        return self

    def filter_by_commerce_platform(self, val):
        self.query.and_filter(eq("commerce_platform", val))
        return self

    def with_create_time_is(self, val):
        self.query.and_filter(eq("create_time", val))
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

class ExecutableOrderLineRequest:
    def __init__(self, request):
        self._request = request

    def new_entity(self, context) -> OrderLine:
        return OrderLine()

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
        return [OrderLine(**row) for row in res["data"]]

    async def execute_entity_for_one(self, context):
        self._request.limit(1)
        entities = await self.execute_entities_for_list(context)
        return entities[0] if entities else None