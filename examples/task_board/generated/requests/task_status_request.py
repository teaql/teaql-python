from teaql.core.query import SelectQuery
from teaql.data_service import QueryRequest
from teaql.core.expr import eq, contain

class TaskStatusRequest:
    def __init__(self):
        self.query = SelectQuery("TaskStatus")

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

    def with_progress_is(self, val):
        self.query.and_filter(eq("progress", val))
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

    def min_display_order(self):
        return self.min_display_order_as("minOfDisplayOrder")

    def min_display_order_as(self, ret_name: str):
        self.query.("display_order", ret_name)
        return self
    def max_display_order(self):
        return self.max_display_order_as("maxOfDisplayOrder")

    def max_display_order_as(self, ret_name: str):
        self.query.("display_order", ret_name)
        return self
    def sum_display_order(self):
        return self.sum_display_order_as("sumOfDisplayOrder")

    def sum_display_order_as(self, ret_name: str):
        self.query.("display_order", ret_name)
        return self
    def avg_display_order(self):
        return self.avg_display_order_as("avgOfDisplayOrder")

    def avg_display_order_as(self, ret_name: str):
        self.query.("display_order", ret_name)
        return self
    def standardDeviation_display_order(self):
        return self.standardDeviation_display_order_as("standardDeviationOfDisplayOrder")

    def standardDeviation_display_order_as(self, ret_name: str):
        self.query.("display_order", ret_name)
        return self
    def squareRootOfPopulationStandardDeviation_display_order(self):
        return self.squareRootOfPopulationStandardDeviation_display_order_as("squareRootOfPopulationStandardDeviationOfDisplayOrder")

    def squareRootOfPopulationStandardDeviation_display_order_as(self, ret_name: str):
        self.query.("display_order", ret_name)
        return self
    def sampleVariance_display_order(self):
        return self.sampleVariance_display_order_as("sampleVarianceOfDisplayOrder")

    def sampleVariance_display_order_as(self, ret_name: str):
        self.query.("display_order", ret_name)
        return self
    def samplePopulationVariance_display_order(self):
        return self.samplePopulationVariance_display_order_as("samplePopulationVarianceOfDisplayOrder")

    def samplePopulationVariance_display_order_as(self, ret_name: str):
        self.query.("display_order", ret_name)
        return self
    def min_progress(self):
        return self.min_progress_as("minOfProgress")

    def min_progress_as(self, ret_name: str):
        self.query.("progress", ret_name)
        return self
    def max_progress(self):
        return self.max_progress_as("maxOfProgress")

    def max_progress_as(self, ret_name: str):
        self.query.("progress", ret_name)
        return self
    def sum_progress(self):
        return self.sum_progress_as("sumOfProgress")

    def sum_progress_as(self, ret_name: str):
        self.query.("progress", ret_name)
        return self
    def avg_progress(self):
        return self.avg_progress_as("avgOfProgress")

    def avg_progress_as(self, ret_name: str):
        self.query.("progress", ret_name)
        return self
    def standardDeviation_progress(self):
        return self.standardDeviation_progress_as("standardDeviationOfProgress")

    def standardDeviation_progress_as(self, ret_name: str):
        self.query.("progress", ret_name)
        return self
    def squareRootOfPopulationStandardDeviation_progress(self):
        return self.squareRootOfPopulationStandardDeviation_progress_as("squareRootOfPopulationStandardDeviationOfProgress")

    def squareRootOfPopulationStandardDeviation_progress_as(self, ret_name: str):
        self.query.("progress", ret_name)
        return self
    def sampleVariance_progress(self):
        return self.sampleVariance_progress_as("sampleVarianceOfProgress")

    def sampleVariance_progress_as(self, ret_name: str):
        self.query.("progress", ret_name)
        return self
    def samplePopulationVariance_progress(self):
        return self.samplePopulationVariance_progress_as("samplePopulationVarianceOfProgress")

    def samplePopulationVariance_progress_as(self, ret_name: str):
        self.query.("progress", ret_name)
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

    def group_by_progress(self):
        self.query.group_by("progress")
        return self

    def group_by_progress_as(self, ret_name: str):
        self.query.group_by("progress") 
        return self


    def group_by_version(self):
        self.query.group_by("version")
        return self

    def group_by_version_as(self, ret_name: str):
        self.query.group_by("version") 
        return self


    async def execute_for_list(self, context, service):
        req = QueryRequest(self.query)
        res = await service.query(context, req)

        result = {"data": res.rows}
        return result