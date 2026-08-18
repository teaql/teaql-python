from teaql.core.query import SelectQuery
from teaql.data_service import QueryRequest
from teaql.core.expr import eq, contain
from models.product import Product

class ProductRequest:
    def __init__(self):
        self.query = SelectQuery("Product")
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
        return ExecutableProductRequest(self)

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

    def with_sku_containing(self, val: str):
        self.query.and_filter(contain("sku", val))
        return self

    def with_sku_is(self, val: str):
        self.query.and_filter(eq("sku", val))
        return self

    def with_image_url_containing(self, val: str):
        self.query.and_filter(contain("image_url", val))
        return self

    def with_image_url_is(self, val: str):
        self.query.and_filter(eq("image_url", val))
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

    def order_by_name_ascending(self):
        self.query.order_by("name", "asc")
        return self

    def order_by_name_descending(self):
        self.query.order_by("name", "desc")
        return self

    def order_by_sku_ascending(self):
        self.query.order_by("sku", "asc")
        return self

    def order_by_sku_descending(self):
        self.query.order_by("sku", "desc")
        return self

    def order_by_image_url_ascending(self):
        self.query.order_by("image_url", "asc")
        return self

    def order_by_image_url_descending(self):
        self.query.order_by("image_url", "desc")
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
    def group_by_sku(self):
        self.query.group_by("sku")
        return self

    def group_by_sku_as(self, ret_name: str):
        self.query.group_by("sku") 
        return self
    def group_by_image_url(self):
        self.query.group_by("image_url")
        return self

    def group_by_image_url_as(self, ret_name: str):
        self.query.group_by("image_url") 
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

class ExecutableProductRequest:
    def __init__(self, request):
        self._request = request

    def new_entity(self, context) -> Product:
        return Product()

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
        return [Product(**row) for row in res["data"]]

    async def execute_entity_for_one(self, context):
        self._request.limit(1)
        entities = await self.execute_entities_for_list(context)
        return entities[0] if entities else None