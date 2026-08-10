from teaql.core.query import SelectQuery
from teaql.data_service import QueryRequest
from teaql.core.expr import eq, contain

class PlatformRequest:
    def __init__(self):
        self.query = SelectQuery("Platform")

    def comment(self, c: str):
        self.query.comment(c)
        return self

    def purpose(self, p: str):
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

    def with_founded_is(self, val):
        self.query.and_filter(eq("founded", val))
        return self

    def with_user_email_containing(self, val: str):
        self.query.and_filter(contain("user_email", val))
        return self

    def with_user_email_is(self, val: str):
        self.query.and_filter(eq("user_email", val))
        return self

    def with_version_is(self, val):
        self.query.and_filter(eq("version", val))
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

    def group_by_founded(self):
        self.query.group_by("founded")
        return self

    def group_by_founded_as(self, ret_name: str):
        self.query.group_by("founded") 
        return self

    def group_by_user_email(self):
        self.query.group_by("user_email")
        return self

    def group_by_user_email_as(self, ret_name: str):
        self.query.group_by("user_email") 
        return self

    def group_by_version(self):
        self.query.group_by("version")
        return self

    def group_by_version_as(self, ret_name: str):
        self.query.group_by("version") 
        return self


    async def execute_for_list(self, ctx, service):
        req = QueryRequest(self.query)
        res = await service.query(ctx, req)

        result = {"data": res.rows}
        return result