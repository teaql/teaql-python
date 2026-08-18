from teaql.core.query import SelectQuery
from teaql.data_service import QueryRequest
from teaql.core.expr import eq, contain
from models.order_search_preset import OrderSearchPreset

class OrderSearchPresetRequest:
    def __init__(self):
        self.query = SelectQuery("OrderSearchPreset")
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
        return ExecutableOrderSearchPresetRequest(self)

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

    def with_filter_json_containing(self, val: str):
        self.query.and_filter(contain("filter_json", val))
        return self

    def with_filter_json_is(self, val: str):
        self.query.and_filter(eq("filter_json", val))
        return self

    def with_request_id_containing(self, val: str):
        self.query.and_filter(contain("request_id", val))
        return self

    def with_request_id_is(self, val: str):
        self.query.and_filter(eq("request_id", val))
        return self

    def with_owner_user_id_containing(self, val: str):
        self.query.and_filter(contain("owner_user_id", val))
        return self

    def with_owner_user_id_is(self, val: str):
        self.query.and_filter(eq("owner_user_id", val))
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

    def order_by_filter_json_ascending(self):
        self.query.order_by("filter_json", "asc")
        return self

    def order_by_filter_json_descending(self):
        self.query.order_by("filter_json", "desc")
        return self

    def order_by_request_id_ascending(self):
        self.query.order_by("request_id", "asc")
        return self

    def order_by_request_id_descending(self):
        self.query.order_by("request_id", "desc")
        return self

    def order_by_owner_user_id_ascending(self):
        self.query.order_by("owner_user_id", "asc")
        return self

    def order_by_owner_user_id_descending(self):
        self.query.order_by("owner_user_id", "desc")
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
    def group_by_filter_json(self):
        self.query.group_by("filter_json")
        return self

    def group_by_filter_json_as(self, ret_name: str):
        self.query.group_by("filter_json") 
        return self
    def group_by_request_id(self):
        self.query.group_by("request_id")
        return self

    def group_by_request_id_as(self, ret_name: str):
        self.query.group_by("request_id") 
        return self
    def group_by_owner_user_id(self):
        self.query.group_by("owner_user_id")
        return self

    def group_by_owner_user_id_as(self, ret_name: str):
        self.query.group_by("owner_user_id") 
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

class ExecutableOrderSearchPresetRequest:
    def __init__(self, request):
        self._request = request

    def new_entity(self, context) -> OrderSearchPreset:
        return OrderSearchPreset()

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
        return [OrderSearchPreset(**row) for row in res["data"]]

    async def execute_entity_for_one(self, context):
        self._request.limit(1)
        entities = await self.execute_entities_for_list(context)
        return entities[0] if entities else None