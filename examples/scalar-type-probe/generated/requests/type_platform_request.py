from teaql.core.query import AggregateFunction, RelationAggregate, SelectQuery
from teaql.core.request_tree import QueryOperation
from teaql.core.dynamic_search import merge_generated_scalar_search
from generated_search_models import GENERATED_SEARCH_MODELS
from teaql.core.list import SmartList
from teaql.core.request_intent import QueryIntent
from teaql.runtime import EntityRoot
from teaql.data_service import QueryRequest
from copy import deepcopy
from teaql.core.expr import (
    begin_with, between, column, contain, end_with, eq, gt, gte,
    in_list, in_subquery, is_not_null, is_null, lt, lte, ne, not_begin_with,
    not_contain, not_end_with, not_in_list, not_in_subquery, value,
    sound_like,
)
from models.type_platform import TypePlatform
from typing import Protocol

class QuerySelection(Protocol):
    query: SelectQuery

class TypePlatformRequest:
    def __init__(self, minimal=False):
        self.query = SelectQuery("TypePlatform")
        self._purpose = None
        self._comment = None
        self._page_count_alias = None
        self._page_count_method = None
        self._dynamic_search_warnings = []
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

    def filter_by_json(self, source, warn=None):
        kwargs = {} if warn is None else {"warn": warn}
        query, warnings = merge_generated_scalar_search(self.query, source, GENERATED_SEARCH_MODELS, **kwargs)
        self.query = query
        self._dynamic_search_warnings.extend(warnings)
        return self

    @property
    def dynamic_search_warnings(self):
        return tuple(dict(warning) for warning in self._dynamic_search_warnings)

    def purpose(self, p: str):
        self.query.purpose(p)
        self._purpose = p
        return ExecutableTypePlatformRequest(self)

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
        self.query.with_deleted_rows()
        return self

    def deleted_rows_only(self):
        self.query.deleted_rows_only()
        return self

    def select_self_fields(self):
        self.query.project("id", "name", "version")
        return self

    def select_id(self):
        self.query.project("id")
        return self

    def select_name(self):
        self.query.project("name")
        return self

    def select_version(self):
        self.query.project("version")
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

    def with_name_containing(self, val: str):
        self.query.and_filter(contain("name", val))
        return self

    def with_name_not_containing(self, val: str):
        self.query.and_filter(not_contain("name", val))
        return self

    def with_name_starting_with(self, val: str):
        self.query.and_filter(begin_with("name", val))
        return self

    def with_name_not_starting_with(self, val: str):
        self.query.and_filter(not_begin_with("name", val))
        return self

    def with_name_ending_with(self, val: str):
        self.query.and_filter(end_with("name", val))
        return self

    def with_name_not_ending_with(self, val: str):
        self.query.and_filter(not_end_with("name", val))
        return self

    def with_name_sounding_like(self, val: str):
        self.query.and_filter(sound_like("name", val))
        return self

    def with_name_is(self, val: str):
        self.query.and_filter(eq("name", val))
        return self
    def with_name_is_not(self, val):
        self.query.and_filter(ne("name", val))
        return self

    def with_name_in(self, *vals):
        self.query.and_filter(in_list("name", list(vals)))
        return self

    def with_name_not_in(self, *vals):
        self.query.and_filter(not_in_list("name", list(vals)))
        return self

    def with_name_greater_than(self, val):
        self.query.and_filter(gt("name", val))
        return self

    def with_name_greater_than_or_equal_to(self, val):
        self.query.and_filter(gte("name", val))
        return self

    def with_name_less_than(self, val):
        self.query.and_filter(lt("name", val))
        return self

    def with_name_less_than_or_equal_to(self, val):
        self.query.and_filter(lte("name", val))
        return self

    def with_name_between(self, lower, upper):
        self.query.and_filter(between(column("name"), value(lower), value(upper)))
        return self

    def with_name_is_known(self):
        self.query.and_filter(is_not_null(column("name")))
        return self

    def with_name_is_unknown(self):
        self.query.and_filter(is_null(column("name")))
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

    def order_by_name_ascending(self):
        self.query.order_by("name", "asc")
        return self

    def order_by_name_descending(self):
        self.query.order_by("name", "desc")
        return self

    def order_by_version_ascending(self):
        self.query.order_by("version", "asc")
        return self

    def order_by_version_descending(self):
        self.query.order_by("version", "desc")
        return self


    def count(self):
        self.query.count_field("id", "count")
        self._page_count_alias = "count"
        self._page_count_method = "count"
        return self

    def count_as(self, ret_name: str):
        self.query.count_field("id", ret_name)
        self._page_count_alias = ret_name
        self._page_count_method = "count_as"
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
    def group_by_version(self):
        self.query.group_by("version")
        return self

    def group_by_version_as(self, ret_name: str):
        self.query.group_by("version")
        return self
    def select_scalar_type_probe_list(self):
        from requests.scalar_type_probe_request import ScalarTypeProbeRequest
        return self.select_scalar_type_probe_list_with(ScalarTypeProbeRequest())

    def select_scalar_type_probe_list_with(self, child_request):
        self.query.relation_query("scalar_type_probe_list", child_request.query,
            QueryOperation("relation-select", "select_scalar_type_probe_list_with", relation="scalar_type_probe_list"))
        return self
    def have_scalar_type_probes(self):
        from requests.scalar_type_probe_request import ScalarTypeProbeRequest
        return self.with_scalar_type_probe_list_matching(ScalarTypeProbeRequest())

    def have_no_scalar_type_probes(self):
        from requests.scalar_type_probe_request import ScalarTypeProbeRequest
        return self.without_scalar_type_probe_list_matching(ScalarTypeProbeRequest())

    def with_scalar_type_probe_list_matching(self, child_request):
        child_request.query.projection = ["type_platform"]
        self.query.and_filter(in_subquery(column("id"), "ScalarTypeProbe", child_request.query))
        return self

    def without_scalar_type_probe_list_matching(self, child_request):
        child_request.query.projection = ["type_platform"]
        self.query.and_filter(not_in_subquery(column("id"), "ScalarTypeProbe", child_request.query))
        return self
    def count_scalar_type_probes(self):
        return self.count_scalar_type_probes_as("count_scalar_type_probes")

    def count_scalar_type_probes_as(self, alias: str):
        from requests.scalar_type_probe_request import ScalarTypeProbeRequest
        self.count_scalar_type_probes_with(alias, ScalarTypeProbeRequest())
        self.query.relation_aggregates[-1].operation = QueryOperation(
            "relation-count", "count_scalar_type_probes_as", alias, "scalar_type_probe_list")
        return self

    def count_scalar_type_probes_with(self, alias: str, child_request):
        query = deepcopy(child_request.query)
        query.aggregates = []
        query.count_field("id", alias)
        self.query.relation_aggregates.append(
            RelationAggregate("scalar_type_probe_list", alias, query, True,
                QueryOperation("relation-count", "count_scalar_type_probes_with", alias, "scalar_type_probe_list"))
        )
        return self

    def min_required_integer_of_scalar_type_probes(self):
        from requests.scalar_type_probe_request import ScalarTypeProbeRequest
        return self.min_required_integer_of_scalar_type_probes_as(
            "min_required_integer_of_scalar_type_probes", ScalarTypeProbeRequest())

    def min_required_integer_of_scalar_type_probes_as(self, alias: str, child_request):
        query = deepcopy(child_request.query)
        query.aggregates = []
        query.min("required_integer", alias)
        self.query.relation_aggregates.append(
            RelationAggregate("scalar_type_probe_list", alias, query, True,
                QueryOperation("aggregate", "min_required_integer_of_scalar_type_probes_as", alias, "scalar_type_probe_list"))
        )
        return self
    def max_required_integer_of_scalar_type_probes(self):
        from requests.scalar_type_probe_request import ScalarTypeProbeRequest
        return self.max_required_integer_of_scalar_type_probes_as(
            "max_required_integer_of_scalar_type_probes", ScalarTypeProbeRequest())

    def max_required_integer_of_scalar_type_probes_as(self, alias: str, child_request):
        query = deepcopy(child_request.query)
        query.aggregates = []
        query.max("required_integer", alias)
        self.query.relation_aggregates.append(
            RelationAggregate("scalar_type_probe_list", alias, query, True,
                QueryOperation("aggregate", "max_required_integer_of_scalar_type_probes_as", alias, "scalar_type_probe_list"))
        )
        return self
    def sum_required_integer_of_scalar_type_probes(self):
        from requests.scalar_type_probe_request import ScalarTypeProbeRequest
        return self.sum_required_integer_of_scalar_type_probes_as(
            "sum_required_integer_of_scalar_type_probes", ScalarTypeProbeRequest())

    def sum_required_integer_of_scalar_type_probes_as(self, alias: str, child_request):
        query = deepcopy(child_request.query)
        query.aggregates = []
        query.sum("required_integer", alias)
        self.query.relation_aggregates.append(
            RelationAggregate("scalar_type_probe_list", alias, query, True,
                QueryOperation("aggregate", "sum_required_integer_of_scalar_type_probes_as", alias, "scalar_type_probe_list"))
        )
        return self
    def avg_required_integer_of_scalar_type_probes(self):
        from requests.scalar_type_probe_request import ScalarTypeProbeRequest
        return self.avg_required_integer_of_scalar_type_probes_as(
            "avg_required_integer_of_scalar_type_probes", ScalarTypeProbeRequest())

    def avg_required_integer_of_scalar_type_probes_as(self, alias: str, child_request):
        query = deepcopy(child_request.query)
        query.aggregates = []
        query.avg("required_integer", alias)
        self.query.relation_aggregates.append(
            RelationAggregate("scalar_type_probe_list", alias, query, True,
                QueryOperation("aggregate", "avg_required_integer_of_scalar_type_probes_as", alias, "scalar_type_probe_list"))
        )
        return self
    def standardDeviation_required_integer_of_scalar_type_probes(self):
        from requests.scalar_type_probe_request import ScalarTypeProbeRequest
        return self.standardDeviation_required_integer_of_scalar_type_probes_as(
            "standardDeviation_required_integer_of_scalar_type_probes", ScalarTypeProbeRequest())

    def standardDeviation_required_integer_of_scalar_type_probes_as(self, alias: str, child_request):
        query = deepcopy(child_request.query)
        query.aggregates = []
        query.standardDeviation("required_integer", alias)
        self.query.relation_aggregates.append(
            RelationAggregate("scalar_type_probe_list", alias, query, True,
                QueryOperation("aggregate", "standardDeviation_required_integer_of_scalar_type_probes_as", alias, "scalar_type_probe_list"))
        )
        return self
    def squareRootOfPopulationStandardDeviation_required_integer_of_scalar_type_probes(self):
        from requests.scalar_type_probe_request import ScalarTypeProbeRequest
        return self.squareRootOfPopulationStandardDeviation_required_integer_of_scalar_type_probes_as(
            "squareRootOfPopulationStandardDeviation_required_integer_of_scalar_type_probes", ScalarTypeProbeRequest())

    def squareRootOfPopulationStandardDeviation_required_integer_of_scalar_type_probes_as(self, alias: str, child_request):
        query = deepcopy(child_request.query)
        query.aggregates = []
        query.squareRootOfPopulationStandardDeviation("required_integer", alias)
        self.query.relation_aggregates.append(
            RelationAggregate("scalar_type_probe_list", alias, query, True,
                QueryOperation("aggregate", "squareRootOfPopulationStandardDeviation_required_integer_of_scalar_type_probes_as", alias, "scalar_type_probe_list"))
        )
        return self
    def sampleVariance_required_integer_of_scalar_type_probes(self):
        from requests.scalar_type_probe_request import ScalarTypeProbeRequest
        return self.sampleVariance_required_integer_of_scalar_type_probes_as(
            "sampleVariance_required_integer_of_scalar_type_probes", ScalarTypeProbeRequest())

    def sampleVariance_required_integer_of_scalar_type_probes_as(self, alias: str, child_request):
        query = deepcopy(child_request.query)
        query.aggregates = []
        query.sampleVariance("required_integer", alias)
        self.query.relation_aggregates.append(
            RelationAggregate("scalar_type_probe_list", alias, query, True,
                QueryOperation("aggregate", "sampleVariance_required_integer_of_scalar_type_probes_as", alias, "scalar_type_probe_list"))
        )
        return self
    def samplePopulationVariance_required_integer_of_scalar_type_probes(self):
        from requests.scalar_type_probe_request import ScalarTypeProbeRequest
        return self.samplePopulationVariance_required_integer_of_scalar_type_probes_as(
            "samplePopulationVariance_required_integer_of_scalar_type_probes", ScalarTypeProbeRequest())

    def samplePopulationVariance_required_integer_of_scalar_type_probes_as(self, alias: str, child_request):
        query = deepcopy(child_request.query)
        query.aggregates = []
        query.samplePopulationVariance("required_integer", alias)
        self.query.relation_aggregates.append(
            RelationAggregate("scalar_type_probe_list", alias, query, True,
                QueryOperation("aggregate", "samplePopulationVariance_required_integer_of_scalar_type_probes_as", alias, "scalar_type_probe_list"))
        )
        return self
    def min_optional_integer_of_scalar_type_probes(self):
        from requests.scalar_type_probe_request import ScalarTypeProbeRequest
        return self.min_optional_integer_of_scalar_type_probes_as(
            "min_optional_integer_of_scalar_type_probes", ScalarTypeProbeRequest())

    def min_optional_integer_of_scalar_type_probes_as(self, alias: str, child_request):
        query = deepcopy(child_request.query)
        query.aggregates = []
        query.min("optional_integer", alias)
        self.query.relation_aggregates.append(
            RelationAggregate("scalar_type_probe_list", alias, query, True,
                QueryOperation("aggregate", "min_optional_integer_of_scalar_type_probes_as", alias, "scalar_type_probe_list"))
        )
        return self
    def max_optional_integer_of_scalar_type_probes(self):
        from requests.scalar_type_probe_request import ScalarTypeProbeRequest
        return self.max_optional_integer_of_scalar_type_probes_as(
            "max_optional_integer_of_scalar_type_probes", ScalarTypeProbeRequest())

    def max_optional_integer_of_scalar_type_probes_as(self, alias: str, child_request):
        query = deepcopy(child_request.query)
        query.aggregates = []
        query.max("optional_integer", alias)
        self.query.relation_aggregates.append(
            RelationAggregate("scalar_type_probe_list", alias, query, True,
                QueryOperation("aggregate", "max_optional_integer_of_scalar_type_probes_as", alias, "scalar_type_probe_list"))
        )
        return self
    def sum_optional_integer_of_scalar_type_probes(self):
        from requests.scalar_type_probe_request import ScalarTypeProbeRequest
        return self.sum_optional_integer_of_scalar_type_probes_as(
            "sum_optional_integer_of_scalar_type_probes", ScalarTypeProbeRequest())

    def sum_optional_integer_of_scalar_type_probes_as(self, alias: str, child_request):
        query = deepcopy(child_request.query)
        query.aggregates = []
        query.sum("optional_integer", alias)
        self.query.relation_aggregates.append(
            RelationAggregate("scalar_type_probe_list", alias, query, True,
                QueryOperation("aggregate", "sum_optional_integer_of_scalar_type_probes_as", alias, "scalar_type_probe_list"))
        )
        return self
    def avg_optional_integer_of_scalar_type_probes(self):
        from requests.scalar_type_probe_request import ScalarTypeProbeRequest
        return self.avg_optional_integer_of_scalar_type_probes_as(
            "avg_optional_integer_of_scalar_type_probes", ScalarTypeProbeRequest())

    def avg_optional_integer_of_scalar_type_probes_as(self, alias: str, child_request):
        query = deepcopy(child_request.query)
        query.aggregates = []
        query.avg("optional_integer", alias)
        self.query.relation_aggregates.append(
            RelationAggregate("scalar_type_probe_list", alias, query, True,
                QueryOperation("aggregate", "avg_optional_integer_of_scalar_type_probes_as", alias, "scalar_type_probe_list"))
        )
        return self
    def standardDeviation_optional_integer_of_scalar_type_probes(self):
        from requests.scalar_type_probe_request import ScalarTypeProbeRequest
        return self.standardDeviation_optional_integer_of_scalar_type_probes_as(
            "standardDeviation_optional_integer_of_scalar_type_probes", ScalarTypeProbeRequest())

    def standardDeviation_optional_integer_of_scalar_type_probes_as(self, alias: str, child_request):
        query = deepcopy(child_request.query)
        query.aggregates = []
        query.standardDeviation("optional_integer", alias)
        self.query.relation_aggregates.append(
            RelationAggregate("scalar_type_probe_list", alias, query, True,
                QueryOperation("aggregate", "standardDeviation_optional_integer_of_scalar_type_probes_as", alias, "scalar_type_probe_list"))
        )
        return self
    def squareRootOfPopulationStandardDeviation_optional_integer_of_scalar_type_probes(self):
        from requests.scalar_type_probe_request import ScalarTypeProbeRequest
        return self.squareRootOfPopulationStandardDeviation_optional_integer_of_scalar_type_probes_as(
            "squareRootOfPopulationStandardDeviation_optional_integer_of_scalar_type_probes", ScalarTypeProbeRequest())

    def squareRootOfPopulationStandardDeviation_optional_integer_of_scalar_type_probes_as(self, alias: str, child_request):
        query = deepcopy(child_request.query)
        query.aggregates = []
        query.squareRootOfPopulationStandardDeviation("optional_integer", alias)
        self.query.relation_aggregates.append(
            RelationAggregate("scalar_type_probe_list", alias, query, True,
                QueryOperation("aggregate", "squareRootOfPopulationStandardDeviation_optional_integer_of_scalar_type_probes_as", alias, "scalar_type_probe_list"))
        )
        return self
    def sampleVariance_optional_integer_of_scalar_type_probes(self):
        from requests.scalar_type_probe_request import ScalarTypeProbeRequest
        return self.sampleVariance_optional_integer_of_scalar_type_probes_as(
            "sampleVariance_optional_integer_of_scalar_type_probes", ScalarTypeProbeRequest())

    def sampleVariance_optional_integer_of_scalar_type_probes_as(self, alias: str, child_request):
        query = deepcopy(child_request.query)
        query.aggregates = []
        query.sampleVariance("optional_integer", alias)
        self.query.relation_aggregates.append(
            RelationAggregate("scalar_type_probe_list", alias, query, True,
                QueryOperation("aggregate", "sampleVariance_optional_integer_of_scalar_type_probes_as", alias, "scalar_type_probe_list"))
        )
        return self
    def samplePopulationVariance_optional_integer_of_scalar_type_probes(self):
        from requests.scalar_type_probe_request import ScalarTypeProbeRequest
        return self.samplePopulationVariance_optional_integer_of_scalar_type_probes_as(
            "samplePopulationVariance_optional_integer_of_scalar_type_probes", ScalarTypeProbeRequest())

    def samplePopulationVariance_optional_integer_of_scalar_type_probes_as(self, alias: str, child_request):
        query = deepcopy(child_request.query)
        query.aggregates = []
        query.samplePopulationVariance("optional_integer", alias)
        self.query.relation_aggregates.append(
            RelationAggregate("scalar_type_probe_list", alias, query, True,
                QueryOperation("aggregate", "samplePopulationVariance_optional_integer_of_scalar_type_probes_as", alias, "scalar_type_probe_list"))
        )
        return self
    def min_required_long_of_scalar_type_probes(self):
        from requests.scalar_type_probe_request import ScalarTypeProbeRequest
        return self.min_required_long_of_scalar_type_probes_as(
            "min_required_long_of_scalar_type_probes", ScalarTypeProbeRequest())

    def min_required_long_of_scalar_type_probes_as(self, alias: str, child_request):
        query = deepcopy(child_request.query)
        query.aggregates = []
        query.min("required_long", alias)
        self.query.relation_aggregates.append(
            RelationAggregate("scalar_type_probe_list", alias, query, True,
                QueryOperation("aggregate", "min_required_long_of_scalar_type_probes_as", alias, "scalar_type_probe_list"))
        )
        return self
    def max_required_long_of_scalar_type_probes(self):
        from requests.scalar_type_probe_request import ScalarTypeProbeRequest
        return self.max_required_long_of_scalar_type_probes_as(
            "max_required_long_of_scalar_type_probes", ScalarTypeProbeRequest())

    def max_required_long_of_scalar_type_probes_as(self, alias: str, child_request):
        query = deepcopy(child_request.query)
        query.aggregates = []
        query.max("required_long", alias)
        self.query.relation_aggregates.append(
            RelationAggregate("scalar_type_probe_list", alias, query, True,
                QueryOperation("aggregate", "max_required_long_of_scalar_type_probes_as", alias, "scalar_type_probe_list"))
        )
        return self
    def sum_required_long_of_scalar_type_probes(self):
        from requests.scalar_type_probe_request import ScalarTypeProbeRequest
        return self.sum_required_long_of_scalar_type_probes_as(
            "sum_required_long_of_scalar_type_probes", ScalarTypeProbeRequest())

    def sum_required_long_of_scalar_type_probes_as(self, alias: str, child_request):
        query = deepcopy(child_request.query)
        query.aggregates = []
        query.sum("required_long", alias)
        self.query.relation_aggregates.append(
            RelationAggregate("scalar_type_probe_list", alias, query, True,
                QueryOperation("aggregate", "sum_required_long_of_scalar_type_probes_as", alias, "scalar_type_probe_list"))
        )
        return self
    def avg_required_long_of_scalar_type_probes(self):
        from requests.scalar_type_probe_request import ScalarTypeProbeRequest
        return self.avg_required_long_of_scalar_type_probes_as(
            "avg_required_long_of_scalar_type_probes", ScalarTypeProbeRequest())

    def avg_required_long_of_scalar_type_probes_as(self, alias: str, child_request):
        query = deepcopy(child_request.query)
        query.aggregates = []
        query.avg("required_long", alias)
        self.query.relation_aggregates.append(
            RelationAggregate("scalar_type_probe_list", alias, query, True,
                QueryOperation("aggregate", "avg_required_long_of_scalar_type_probes_as", alias, "scalar_type_probe_list"))
        )
        return self
    def standardDeviation_required_long_of_scalar_type_probes(self):
        from requests.scalar_type_probe_request import ScalarTypeProbeRequest
        return self.standardDeviation_required_long_of_scalar_type_probes_as(
            "standardDeviation_required_long_of_scalar_type_probes", ScalarTypeProbeRequest())

    def standardDeviation_required_long_of_scalar_type_probes_as(self, alias: str, child_request):
        query = deepcopy(child_request.query)
        query.aggregates = []
        query.standardDeviation("required_long", alias)
        self.query.relation_aggregates.append(
            RelationAggregate("scalar_type_probe_list", alias, query, True,
                QueryOperation("aggregate", "standardDeviation_required_long_of_scalar_type_probes_as", alias, "scalar_type_probe_list"))
        )
        return self
    def squareRootOfPopulationStandardDeviation_required_long_of_scalar_type_probes(self):
        from requests.scalar_type_probe_request import ScalarTypeProbeRequest
        return self.squareRootOfPopulationStandardDeviation_required_long_of_scalar_type_probes_as(
            "squareRootOfPopulationStandardDeviation_required_long_of_scalar_type_probes", ScalarTypeProbeRequest())

    def squareRootOfPopulationStandardDeviation_required_long_of_scalar_type_probes_as(self, alias: str, child_request):
        query = deepcopy(child_request.query)
        query.aggregates = []
        query.squareRootOfPopulationStandardDeviation("required_long", alias)
        self.query.relation_aggregates.append(
            RelationAggregate("scalar_type_probe_list", alias, query, True,
                QueryOperation("aggregate", "squareRootOfPopulationStandardDeviation_required_long_of_scalar_type_probes_as", alias, "scalar_type_probe_list"))
        )
        return self
    def sampleVariance_required_long_of_scalar_type_probes(self):
        from requests.scalar_type_probe_request import ScalarTypeProbeRequest
        return self.sampleVariance_required_long_of_scalar_type_probes_as(
            "sampleVariance_required_long_of_scalar_type_probes", ScalarTypeProbeRequest())

    def sampleVariance_required_long_of_scalar_type_probes_as(self, alias: str, child_request):
        query = deepcopy(child_request.query)
        query.aggregates = []
        query.sampleVariance("required_long", alias)
        self.query.relation_aggregates.append(
            RelationAggregate("scalar_type_probe_list", alias, query, True,
                QueryOperation("aggregate", "sampleVariance_required_long_of_scalar_type_probes_as", alias, "scalar_type_probe_list"))
        )
        return self
    def samplePopulationVariance_required_long_of_scalar_type_probes(self):
        from requests.scalar_type_probe_request import ScalarTypeProbeRequest
        return self.samplePopulationVariance_required_long_of_scalar_type_probes_as(
            "samplePopulationVariance_required_long_of_scalar_type_probes", ScalarTypeProbeRequest())

    def samplePopulationVariance_required_long_of_scalar_type_probes_as(self, alias: str, child_request):
        query = deepcopy(child_request.query)
        query.aggregates = []
        query.samplePopulationVariance("required_long", alias)
        self.query.relation_aggregates.append(
            RelationAggregate("scalar_type_probe_list", alias, query, True,
                QueryOperation("aggregate", "samplePopulationVariance_required_long_of_scalar_type_probes_as", alias, "scalar_type_probe_list"))
        )
        return self
    def min_optional_long_of_scalar_type_probes(self):
        from requests.scalar_type_probe_request import ScalarTypeProbeRequest
        return self.min_optional_long_of_scalar_type_probes_as(
            "min_optional_long_of_scalar_type_probes", ScalarTypeProbeRequest())

    def min_optional_long_of_scalar_type_probes_as(self, alias: str, child_request):
        query = deepcopy(child_request.query)
        query.aggregates = []
        query.min("optional_long", alias)
        self.query.relation_aggregates.append(
            RelationAggregate("scalar_type_probe_list", alias, query, True,
                QueryOperation("aggregate", "min_optional_long_of_scalar_type_probes_as", alias, "scalar_type_probe_list"))
        )
        return self
    def max_optional_long_of_scalar_type_probes(self):
        from requests.scalar_type_probe_request import ScalarTypeProbeRequest
        return self.max_optional_long_of_scalar_type_probes_as(
            "max_optional_long_of_scalar_type_probes", ScalarTypeProbeRequest())

    def max_optional_long_of_scalar_type_probes_as(self, alias: str, child_request):
        query = deepcopy(child_request.query)
        query.aggregates = []
        query.max("optional_long", alias)
        self.query.relation_aggregates.append(
            RelationAggregate("scalar_type_probe_list", alias, query, True,
                QueryOperation("aggregate", "max_optional_long_of_scalar_type_probes_as", alias, "scalar_type_probe_list"))
        )
        return self
    def sum_optional_long_of_scalar_type_probes(self):
        from requests.scalar_type_probe_request import ScalarTypeProbeRequest
        return self.sum_optional_long_of_scalar_type_probes_as(
            "sum_optional_long_of_scalar_type_probes", ScalarTypeProbeRequest())

    def sum_optional_long_of_scalar_type_probes_as(self, alias: str, child_request):
        query = deepcopy(child_request.query)
        query.aggregates = []
        query.sum("optional_long", alias)
        self.query.relation_aggregates.append(
            RelationAggregate("scalar_type_probe_list", alias, query, True,
                QueryOperation("aggregate", "sum_optional_long_of_scalar_type_probes_as", alias, "scalar_type_probe_list"))
        )
        return self
    def avg_optional_long_of_scalar_type_probes(self):
        from requests.scalar_type_probe_request import ScalarTypeProbeRequest
        return self.avg_optional_long_of_scalar_type_probes_as(
            "avg_optional_long_of_scalar_type_probes", ScalarTypeProbeRequest())

    def avg_optional_long_of_scalar_type_probes_as(self, alias: str, child_request):
        query = deepcopy(child_request.query)
        query.aggregates = []
        query.avg("optional_long", alias)
        self.query.relation_aggregates.append(
            RelationAggregate("scalar_type_probe_list", alias, query, True,
                QueryOperation("aggregate", "avg_optional_long_of_scalar_type_probes_as", alias, "scalar_type_probe_list"))
        )
        return self
    def standardDeviation_optional_long_of_scalar_type_probes(self):
        from requests.scalar_type_probe_request import ScalarTypeProbeRequest
        return self.standardDeviation_optional_long_of_scalar_type_probes_as(
            "standardDeviation_optional_long_of_scalar_type_probes", ScalarTypeProbeRequest())

    def standardDeviation_optional_long_of_scalar_type_probes_as(self, alias: str, child_request):
        query = deepcopy(child_request.query)
        query.aggregates = []
        query.standardDeviation("optional_long", alias)
        self.query.relation_aggregates.append(
            RelationAggregate("scalar_type_probe_list", alias, query, True,
                QueryOperation("aggregate", "standardDeviation_optional_long_of_scalar_type_probes_as", alias, "scalar_type_probe_list"))
        )
        return self
    def squareRootOfPopulationStandardDeviation_optional_long_of_scalar_type_probes(self):
        from requests.scalar_type_probe_request import ScalarTypeProbeRequest
        return self.squareRootOfPopulationStandardDeviation_optional_long_of_scalar_type_probes_as(
            "squareRootOfPopulationStandardDeviation_optional_long_of_scalar_type_probes", ScalarTypeProbeRequest())

    def squareRootOfPopulationStandardDeviation_optional_long_of_scalar_type_probes_as(self, alias: str, child_request):
        query = deepcopy(child_request.query)
        query.aggregates = []
        query.squareRootOfPopulationStandardDeviation("optional_long", alias)
        self.query.relation_aggregates.append(
            RelationAggregate("scalar_type_probe_list", alias, query, True,
                QueryOperation("aggregate", "squareRootOfPopulationStandardDeviation_optional_long_of_scalar_type_probes_as", alias, "scalar_type_probe_list"))
        )
        return self
    def sampleVariance_optional_long_of_scalar_type_probes(self):
        from requests.scalar_type_probe_request import ScalarTypeProbeRequest
        return self.sampleVariance_optional_long_of_scalar_type_probes_as(
            "sampleVariance_optional_long_of_scalar_type_probes", ScalarTypeProbeRequest())

    def sampleVariance_optional_long_of_scalar_type_probes_as(self, alias: str, child_request):
        query = deepcopy(child_request.query)
        query.aggregates = []
        query.sampleVariance("optional_long", alias)
        self.query.relation_aggregates.append(
            RelationAggregate("scalar_type_probe_list", alias, query, True,
                QueryOperation("aggregate", "sampleVariance_optional_long_of_scalar_type_probes_as", alias, "scalar_type_probe_list"))
        )
        return self
    def samplePopulationVariance_optional_long_of_scalar_type_probes(self):
        from requests.scalar_type_probe_request import ScalarTypeProbeRequest
        return self.samplePopulationVariance_optional_long_of_scalar_type_probes_as(
            "samplePopulationVariance_optional_long_of_scalar_type_probes", ScalarTypeProbeRequest())

    def samplePopulationVariance_optional_long_of_scalar_type_probes_as(self, alias: str, child_request):
        query = deepcopy(child_request.query)
        query.aggregates = []
        query.samplePopulationVariance("optional_long", alias)
        self.query.relation_aggregates.append(
            RelationAggregate("scalar_type_probe_list", alias, query, True,
                QueryOperation("aggregate", "samplePopulationVariance_optional_long_of_scalar_type_probes_as", alias, "scalar_type_probe_list"))
        )
        return self
    def min_required_decimal_of_scalar_type_probes(self):
        from requests.scalar_type_probe_request import ScalarTypeProbeRequest
        return self.min_required_decimal_of_scalar_type_probes_as(
            "min_required_decimal_of_scalar_type_probes", ScalarTypeProbeRequest())

    def min_required_decimal_of_scalar_type_probes_as(self, alias: str, child_request):
        query = deepcopy(child_request.query)
        query.aggregates = []
        query.min("required_decimal", alias)
        self.query.relation_aggregates.append(
            RelationAggregate("scalar_type_probe_list", alias, query, True,
                QueryOperation("aggregate", "min_required_decimal_of_scalar_type_probes_as", alias, "scalar_type_probe_list"))
        )
        return self
    def max_required_decimal_of_scalar_type_probes(self):
        from requests.scalar_type_probe_request import ScalarTypeProbeRequest
        return self.max_required_decimal_of_scalar_type_probes_as(
            "max_required_decimal_of_scalar_type_probes", ScalarTypeProbeRequest())

    def max_required_decimal_of_scalar_type_probes_as(self, alias: str, child_request):
        query = deepcopy(child_request.query)
        query.aggregates = []
        query.max("required_decimal", alias)
        self.query.relation_aggregates.append(
            RelationAggregate("scalar_type_probe_list", alias, query, True,
                QueryOperation("aggregate", "max_required_decimal_of_scalar_type_probes_as", alias, "scalar_type_probe_list"))
        )
        return self
    def sum_required_decimal_of_scalar_type_probes(self):
        from requests.scalar_type_probe_request import ScalarTypeProbeRequest
        return self.sum_required_decimal_of_scalar_type_probes_as(
            "sum_required_decimal_of_scalar_type_probes", ScalarTypeProbeRequest())

    def sum_required_decimal_of_scalar_type_probes_as(self, alias: str, child_request):
        query = deepcopy(child_request.query)
        query.aggregates = []
        query.sum("required_decimal", alias)
        self.query.relation_aggregates.append(
            RelationAggregate("scalar_type_probe_list", alias, query, True,
                QueryOperation("aggregate", "sum_required_decimal_of_scalar_type_probes_as", alias, "scalar_type_probe_list"))
        )
        return self
    def avg_required_decimal_of_scalar_type_probes(self):
        from requests.scalar_type_probe_request import ScalarTypeProbeRequest
        return self.avg_required_decimal_of_scalar_type_probes_as(
            "avg_required_decimal_of_scalar_type_probes", ScalarTypeProbeRequest())

    def avg_required_decimal_of_scalar_type_probes_as(self, alias: str, child_request):
        query = deepcopy(child_request.query)
        query.aggregates = []
        query.avg("required_decimal", alias)
        self.query.relation_aggregates.append(
            RelationAggregate("scalar_type_probe_list", alias, query, True,
                QueryOperation("aggregate", "avg_required_decimal_of_scalar_type_probes_as", alias, "scalar_type_probe_list"))
        )
        return self
    def standardDeviation_required_decimal_of_scalar_type_probes(self):
        from requests.scalar_type_probe_request import ScalarTypeProbeRequest
        return self.standardDeviation_required_decimal_of_scalar_type_probes_as(
            "standardDeviation_required_decimal_of_scalar_type_probes", ScalarTypeProbeRequest())

    def standardDeviation_required_decimal_of_scalar_type_probes_as(self, alias: str, child_request):
        query = deepcopy(child_request.query)
        query.aggregates = []
        query.standardDeviation("required_decimal", alias)
        self.query.relation_aggregates.append(
            RelationAggregate("scalar_type_probe_list", alias, query, True,
                QueryOperation("aggregate", "standardDeviation_required_decimal_of_scalar_type_probes_as", alias, "scalar_type_probe_list"))
        )
        return self
    def squareRootOfPopulationStandardDeviation_required_decimal_of_scalar_type_probes(self):
        from requests.scalar_type_probe_request import ScalarTypeProbeRequest
        return self.squareRootOfPopulationStandardDeviation_required_decimal_of_scalar_type_probes_as(
            "squareRootOfPopulationStandardDeviation_required_decimal_of_scalar_type_probes", ScalarTypeProbeRequest())

    def squareRootOfPopulationStandardDeviation_required_decimal_of_scalar_type_probes_as(self, alias: str, child_request):
        query = deepcopy(child_request.query)
        query.aggregates = []
        query.squareRootOfPopulationStandardDeviation("required_decimal", alias)
        self.query.relation_aggregates.append(
            RelationAggregate("scalar_type_probe_list", alias, query, True,
                QueryOperation("aggregate", "squareRootOfPopulationStandardDeviation_required_decimal_of_scalar_type_probes_as", alias, "scalar_type_probe_list"))
        )
        return self
    def sampleVariance_required_decimal_of_scalar_type_probes(self):
        from requests.scalar_type_probe_request import ScalarTypeProbeRequest
        return self.sampleVariance_required_decimal_of_scalar_type_probes_as(
            "sampleVariance_required_decimal_of_scalar_type_probes", ScalarTypeProbeRequest())

    def sampleVariance_required_decimal_of_scalar_type_probes_as(self, alias: str, child_request):
        query = deepcopy(child_request.query)
        query.aggregates = []
        query.sampleVariance("required_decimal", alias)
        self.query.relation_aggregates.append(
            RelationAggregate("scalar_type_probe_list", alias, query, True,
                QueryOperation("aggregate", "sampleVariance_required_decimal_of_scalar_type_probes_as", alias, "scalar_type_probe_list"))
        )
        return self
    def samplePopulationVariance_required_decimal_of_scalar_type_probes(self):
        from requests.scalar_type_probe_request import ScalarTypeProbeRequest
        return self.samplePopulationVariance_required_decimal_of_scalar_type_probes_as(
            "samplePopulationVariance_required_decimal_of_scalar_type_probes", ScalarTypeProbeRequest())

    def samplePopulationVariance_required_decimal_of_scalar_type_probes_as(self, alias: str, child_request):
        query = deepcopy(child_request.query)
        query.aggregates = []
        query.samplePopulationVariance("required_decimal", alias)
        self.query.relation_aggregates.append(
            RelationAggregate("scalar_type_probe_list", alias, query, True,
                QueryOperation("aggregate", "samplePopulationVariance_required_decimal_of_scalar_type_probes_as", alias, "scalar_type_probe_list"))
        )
        return self
    def min_optional_decimal_of_scalar_type_probes(self):
        from requests.scalar_type_probe_request import ScalarTypeProbeRequest
        return self.min_optional_decimal_of_scalar_type_probes_as(
            "min_optional_decimal_of_scalar_type_probes", ScalarTypeProbeRequest())

    def min_optional_decimal_of_scalar_type_probes_as(self, alias: str, child_request):
        query = deepcopy(child_request.query)
        query.aggregates = []
        query.min("optional_decimal", alias)
        self.query.relation_aggregates.append(
            RelationAggregate("scalar_type_probe_list", alias, query, True,
                QueryOperation("aggregate", "min_optional_decimal_of_scalar_type_probes_as", alias, "scalar_type_probe_list"))
        )
        return self
    def max_optional_decimal_of_scalar_type_probes(self):
        from requests.scalar_type_probe_request import ScalarTypeProbeRequest
        return self.max_optional_decimal_of_scalar_type_probes_as(
            "max_optional_decimal_of_scalar_type_probes", ScalarTypeProbeRequest())

    def max_optional_decimal_of_scalar_type_probes_as(self, alias: str, child_request):
        query = deepcopy(child_request.query)
        query.aggregates = []
        query.max("optional_decimal", alias)
        self.query.relation_aggregates.append(
            RelationAggregate("scalar_type_probe_list", alias, query, True,
                QueryOperation("aggregate", "max_optional_decimal_of_scalar_type_probes_as", alias, "scalar_type_probe_list"))
        )
        return self
    def sum_optional_decimal_of_scalar_type_probes(self):
        from requests.scalar_type_probe_request import ScalarTypeProbeRequest
        return self.sum_optional_decimal_of_scalar_type_probes_as(
            "sum_optional_decimal_of_scalar_type_probes", ScalarTypeProbeRequest())

    def sum_optional_decimal_of_scalar_type_probes_as(self, alias: str, child_request):
        query = deepcopy(child_request.query)
        query.aggregates = []
        query.sum("optional_decimal", alias)
        self.query.relation_aggregates.append(
            RelationAggregate("scalar_type_probe_list", alias, query, True,
                QueryOperation("aggregate", "sum_optional_decimal_of_scalar_type_probes_as", alias, "scalar_type_probe_list"))
        )
        return self
    def avg_optional_decimal_of_scalar_type_probes(self):
        from requests.scalar_type_probe_request import ScalarTypeProbeRequest
        return self.avg_optional_decimal_of_scalar_type_probes_as(
            "avg_optional_decimal_of_scalar_type_probes", ScalarTypeProbeRequest())

    def avg_optional_decimal_of_scalar_type_probes_as(self, alias: str, child_request):
        query = deepcopy(child_request.query)
        query.aggregates = []
        query.avg("optional_decimal", alias)
        self.query.relation_aggregates.append(
            RelationAggregate("scalar_type_probe_list", alias, query, True,
                QueryOperation("aggregate", "avg_optional_decimal_of_scalar_type_probes_as", alias, "scalar_type_probe_list"))
        )
        return self
    def standardDeviation_optional_decimal_of_scalar_type_probes(self):
        from requests.scalar_type_probe_request import ScalarTypeProbeRequest
        return self.standardDeviation_optional_decimal_of_scalar_type_probes_as(
            "standardDeviation_optional_decimal_of_scalar_type_probes", ScalarTypeProbeRequest())

    def standardDeviation_optional_decimal_of_scalar_type_probes_as(self, alias: str, child_request):
        query = deepcopy(child_request.query)
        query.aggregates = []
        query.standardDeviation("optional_decimal", alias)
        self.query.relation_aggregates.append(
            RelationAggregate("scalar_type_probe_list", alias, query, True,
                QueryOperation("aggregate", "standardDeviation_optional_decimal_of_scalar_type_probes_as", alias, "scalar_type_probe_list"))
        )
        return self
    def squareRootOfPopulationStandardDeviation_optional_decimal_of_scalar_type_probes(self):
        from requests.scalar_type_probe_request import ScalarTypeProbeRequest
        return self.squareRootOfPopulationStandardDeviation_optional_decimal_of_scalar_type_probes_as(
            "squareRootOfPopulationStandardDeviation_optional_decimal_of_scalar_type_probes", ScalarTypeProbeRequest())

    def squareRootOfPopulationStandardDeviation_optional_decimal_of_scalar_type_probes_as(self, alias: str, child_request):
        query = deepcopy(child_request.query)
        query.aggregates = []
        query.squareRootOfPopulationStandardDeviation("optional_decimal", alias)
        self.query.relation_aggregates.append(
            RelationAggregate("scalar_type_probe_list", alias, query, True,
                QueryOperation("aggregate", "squareRootOfPopulationStandardDeviation_optional_decimal_of_scalar_type_probes_as", alias, "scalar_type_probe_list"))
        )
        return self
    def sampleVariance_optional_decimal_of_scalar_type_probes(self):
        from requests.scalar_type_probe_request import ScalarTypeProbeRequest
        return self.sampleVariance_optional_decimal_of_scalar_type_probes_as(
            "sampleVariance_optional_decimal_of_scalar_type_probes", ScalarTypeProbeRequest())

    def sampleVariance_optional_decimal_of_scalar_type_probes_as(self, alias: str, child_request):
        query = deepcopy(child_request.query)
        query.aggregates = []
        query.sampleVariance("optional_decimal", alias)
        self.query.relation_aggregates.append(
            RelationAggregate("scalar_type_probe_list", alias, query, True,
                QueryOperation("aggregate", "sampleVariance_optional_decimal_of_scalar_type_probes_as", alias, "scalar_type_probe_list"))
        )
        return self
    def samplePopulationVariance_optional_decimal_of_scalar_type_probes(self):
        from requests.scalar_type_probe_request import ScalarTypeProbeRequest
        return self.samplePopulationVariance_optional_decimal_of_scalar_type_probes_as(
            "samplePopulationVariance_optional_decimal_of_scalar_type_probes", ScalarTypeProbeRequest())

    def samplePopulationVariance_optional_decimal_of_scalar_type_probes_as(self, alias: str, child_request):
        query = deepcopy(child_request.query)
        query.aggregates = []
        query.samplePopulationVariance("optional_decimal", alias)
        self.query.relation_aggregates.append(
            RelationAggregate("scalar_type_probe_list", alias, query, True,
                QueryOperation("aggregate", "samplePopulationVariance_optional_decimal_of_scalar_type_probes_as", alias, "scalar_type_probe_list"))
        )
        return self
    def min_required_float_of_scalar_type_probes(self):
        from requests.scalar_type_probe_request import ScalarTypeProbeRequest
        return self.min_required_float_of_scalar_type_probes_as(
            "min_required_float_of_scalar_type_probes", ScalarTypeProbeRequest())

    def min_required_float_of_scalar_type_probes_as(self, alias: str, child_request):
        query = deepcopy(child_request.query)
        query.aggregates = []
        query.min("required_float", alias)
        self.query.relation_aggregates.append(
            RelationAggregate("scalar_type_probe_list", alias, query, True,
                QueryOperation("aggregate", "min_required_float_of_scalar_type_probes_as", alias, "scalar_type_probe_list"))
        )
        return self
    def max_required_float_of_scalar_type_probes(self):
        from requests.scalar_type_probe_request import ScalarTypeProbeRequest
        return self.max_required_float_of_scalar_type_probes_as(
            "max_required_float_of_scalar_type_probes", ScalarTypeProbeRequest())

    def max_required_float_of_scalar_type_probes_as(self, alias: str, child_request):
        query = deepcopy(child_request.query)
        query.aggregates = []
        query.max("required_float", alias)
        self.query.relation_aggregates.append(
            RelationAggregate("scalar_type_probe_list", alias, query, True,
                QueryOperation("aggregate", "max_required_float_of_scalar_type_probes_as", alias, "scalar_type_probe_list"))
        )
        return self
    def sum_required_float_of_scalar_type_probes(self):
        from requests.scalar_type_probe_request import ScalarTypeProbeRequest
        return self.sum_required_float_of_scalar_type_probes_as(
            "sum_required_float_of_scalar_type_probes", ScalarTypeProbeRequest())

    def sum_required_float_of_scalar_type_probes_as(self, alias: str, child_request):
        query = deepcopy(child_request.query)
        query.aggregates = []
        query.sum("required_float", alias)
        self.query.relation_aggregates.append(
            RelationAggregate("scalar_type_probe_list", alias, query, True,
                QueryOperation("aggregate", "sum_required_float_of_scalar_type_probes_as", alias, "scalar_type_probe_list"))
        )
        return self
    def avg_required_float_of_scalar_type_probes(self):
        from requests.scalar_type_probe_request import ScalarTypeProbeRequest
        return self.avg_required_float_of_scalar_type_probes_as(
            "avg_required_float_of_scalar_type_probes", ScalarTypeProbeRequest())

    def avg_required_float_of_scalar_type_probes_as(self, alias: str, child_request):
        query = deepcopy(child_request.query)
        query.aggregates = []
        query.avg("required_float", alias)
        self.query.relation_aggregates.append(
            RelationAggregate("scalar_type_probe_list", alias, query, True,
                QueryOperation("aggregate", "avg_required_float_of_scalar_type_probes_as", alias, "scalar_type_probe_list"))
        )
        return self
    def standardDeviation_required_float_of_scalar_type_probes(self):
        from requests.scalar_type_probe_request import ScalarTypeProbeRequest
        return self.standardDeviation_required_float_of_scalar_type_probes_as(
            "standardDeviation_required_float_of_scalar_type_probes", ScalarTypeProbeRequest())

    def standardDeviation_required_float_of_scalar_type_probes_as(self, alias: str, child_request):
        query = deepcopy(child_request.query)
        query.aggregates = []
        query.standardDeviation("required_float", alias)
        self.query.relation_aggregates.append(
            RelationAggregate("scalar_type_probe_list", alias, query, True,
                QueryOperation("aggregate", "standardDeviation_required_float_of_scalar_type_probes_as", alias, "scalar_type_probe_list"))
        )
        return self
    def squareRootOfPopulationStandardDeviation_required_float_of_scalar_type_probes(self):
        from requests.scalar_type_probe_request import ScalarTypeProbeRequest
        return self.squareRootOfPopulationStandardDeviation_required_float_of_scalar_type_probes_as(
            "squareRootOfPopulationStandardDeviation_required_float_of_scalar_type_probes", ScalarTypeProbeRequest())

    def squareRootOfPopulationStandardDeviation_required_float_of_scalar_type_probes_as(self, alias: str, child_request):
        query = deepcopy(child_request.query)
        query.aggregates = []
        query.squareRootOfPopulationStandardDeviation("required_float", alias)
        self.query.relation_aggregates.append(
            RelationAggregate("scalar_type_probe_list", alias, query, True,
                QueryOperation("aggregate", "squareRootOfPopulationStandardDeviation_required_float_of_scalar_type_probes_as", alias, "scalar_type_probe_list"))
        )
        return self
    def sampleVariance_required_float_of_scalar_type_probes(self):
        from requests.scalar_type_probe_request import ScalarTypeProbeRequest
        return self.sampleVariance_required_float_of_scalar_type_probes_as(
            "sampleVariance_required_float_of_scalar_type_probes", ScalarTypeProbeRequest())

    def sampleVariance_required_float_of_scalar_type_probes_as(self, alias: str, child_request):
        query = deepcopy(child_request.query)
        query.aggregates = []
        query.sampleVariance("required_float", alias)
        self.query.relation_aggregates.append(
            RelationAggregate("scalar_type_probe_list", alias, query, True,
                QueryOperation("aggregate", "sampleVariance_required_float_of_scalar_type_probes_as", alias, "scalar_type_probe_list"))
        )
        return self
    def samplePopulationVariance_required_float_of_scalar_type_probes(self):
        from requests.scalar_type_probe_request import ScalarTypeProbeRequest
        return self.samplePopulationVariance_required_float_of_scalar_type_probes_as(
            "samplePopulationVariance_required_float_of_scalar_type_probes", ScalarTypeProbeRequest())

    def samplePopulationVariance_required_float_of_scalar_type_probes_as(self, alias: str, child_request):
        query = deepcopy(child_request.query)
        query.aggregates = []
        query.samplePopulationVariance("required_float", alias)
        self.query.relation_aggregates.append(
            RelationAggregate("scalar_type_probe_list", alias, query, True,
                QueryOperation("aggregate", "samplePopulationVariance_required_float_of_scalar_type_probes_as", alias, "scalar_type_probe_list"))
        )
        return self
    def min_optional_float_of_scalar_type_probes(self):
        from requests.scalar_type_probe_request import ScalarTypeProbeRequest
        return self.min_optional_float_of_scalar_type_probes_as(
            "min_optional_float_of_scalar_type_probes", ScalarTypeProbeRequest())

    def min_optional_float_of_scalar_type_probes_as(self, alias: str, child_request):
        query = deepcopy(child_request.query)
        query.aggregates = []
        query.min("optional_float", alias)
        self.query.relation_aggregates.append(
            RelationAggregate("scalar_type_probe_list", alias, query, True,
                QueryOperation("aggregate", "min_optional_float_of_scalar_type_probes_as", alias, "scalar_type_probe_list"))
        )
        return self
    def max_optional_float_of_scalar_type_probes(self):
        from requests.scalar_type_probe_request import ScalarTypeProbeRequest
        return self.max_optional_float_of_scalar_type_probes_as(
            "max_optional_float_of_scalar_type_probes", ScalarTypeProbeRequest())

    def max_optional_float_of_scalar_type_probes_as(self, alias: str, child_request):
        query = deepcopy(child_request.query)
        query.aggregates = []
        query.max("optional_float", alias)
        self.query.relation_aggregates.append(
            RelationAggregate("scalar_type_probe_list", alias, query, True,
                QueryOperation("aggregate", "max_optional_float_of_scalar_type_probes_as", alias, "scalar_type_probe_list"))
        )
        return self
    def sum_optional_float_of_scalar_type_probes(self):
        from requests.scalar_type_probe_request import ScalarTypeProbeRequest
        return self.sum_optional_float_of_scalar_type_probes_as(
            "sum_optional_float_of_scalar_type_probes", ScalarTypeProbeRequest())

    def sum_optional_float_of_scalar_type_probes_as(self, alias: str, child_request):
        query = deepcopy(child_request.query)
        query.aggregates = []
        query.sum("optional_float", alias)
        self.query.relation_aggregates.append(
            RelationAggregate("scalar_type_probe_list", alias, query, True,
                QueryOperation("aggregate", "sum_optional_float_of_scalar_type_probes_as", alias, "scalar_type_probe_list"))
        )
        return self
    def avg_optional_float_of_scalar_type_probes(self):
        from requests.scalar_type_probe_request import ScalarTypeProbeRequest
        return self.avg_optional_float_of_scalar_type_probes_as(
            "avg_optional_float_of_scalar_type_probes", ScalarTypeProbeRequest())

    def avg_optional_float_of_scalar_type_probes_as(self, alias: str, child_request):
        query = deepcopy(child_request.query)
        query.aggregates = []
        query.avg("optional_float", alias)
        self.query.relation_aggregates.append(
            RelationAggregate("scalar_type_probe_list", alias, query, True,
                QueryOperation("aggregate", "avg_optional_float_of_scalar_type_probes_as", alias, "scalar_type_probe_list"))
        )
        return self
    def standardDeviation_optional_float_of_scalar_type_probes(self):
        from requests.scalar_type_probe_request import ScalarTypeProbeRequest
        return self.standardDeviation_optional_float_of_scalar_type_probes_as(
            "standardDeviation_optional_float_of_scalar_type_probes", ScalarTypeProbeRequest())

    def standardDeviation_optional_float_of_scalar_type_probes_as(self, alias: str, child_request):
        query = deepcopy(child_request.query)
        query.aggregates = []
        query.standardDeviation("optional_float", alias)
        self.query.relation_aggregates.append(
            RelationAggregate("scalar_type_probe_list", alias, query, True,
                QueryOperation("aggregate", "standardDeviation_optional_float_of_scalar_type_probes_as", alias, "scalar_type_probe_list"))
        )
        return self
    def squareRootOfPopulationStandardDeviation_optional_float_of_scalar_type_probes(self):
        from requests.scalar_type_probe_request import ScalarTypeProbeRequest
        return self.squareRootOfPopulationStandardDeviation_optional_float_of_scalar_type_probes_as(
            "squareRootOfPopulationStandardDeviation_optional_float_of_scalar_type_probes", ScalarTypeProbeRequest())

    def squareRootOfPopulationStandardDeviation_optional_float_of_scalar_type_probes_as(self, alias: str, child_request):
        query = deepcopy(child_request.query)
        query.aggregates = []
        query.squareRootOfPopulationStandardDeviation("optional_float", alias)
        self.query.relation_aggregates.append(
            RelationAggregate("scalar_type_probe_list", alias, query, True,
                QueryOperation("aggregate", "squareRootOfPopulationStandardDeviation_optional_float_of_scalar_type_probes_as", alias, "scalar_type_probe_list"))
        )
        return self
    def sampleVariance_optional_float_of_scalar_type_probes(self):
        from requests.scalar_type_probe_request import ScalarTypeProbeRequest
        return self.sampleVariance_optional_float_of_scalar_type_probes_as(
            "sampleVariance_optional_float_of_scalar_type_probes", ScalarTypeProbeRequest())

    def sampleVariance_optional_float_of_scalar_type_probes_as(self, alias: str, child_request):
        query = deepcopy(child_request.query)
        query.aggregates = []
        query.sampleVariance("optional_float", alias)
        self.query.relation_aggregates.append(
            RelationAggregate("scalar_type_probe_list", alias, query, True,
                QueryOperation("aggregate", "sampleVariance_optional_float_of_scalar_type_probes_as", alias, "scalar_type_probe_list"))
        )
        return self
    def samplePopulationVariance_optional_float_of_scalar_type_probes(self):
        from requests.scalar_type_probe_request import ScalarTypeProbeRequest
        return self.samplePopulationVariance_optional_float_of_scalar_type_probes_as(
            "samplePopulationVariance_optional_float_of_scalar_type_probes", ScalarTypeProbeRequest())

    def samplePopulationVariance_optional_float_of_scalar_type_probes_as(self, alias: str, child_request):
        query = deepcopy(child_request.query)
        query.aggregates = []
        query.samplePopulationVariance("optional_float", alias)
        self.query.relation_aggregates.append(
            RelationAggregate("scalar_type_probe_list", alias, query, True,
                QueryOperation("aggregate", "samplePopulationVariance_optional_float_of_scalar_type_probes_as", alias, "scalar_type_probe_list"))
        )
        return self
    def min_required_double_of_scalar_type_probes(self):
        from requests.scalar_type_probe_request import ScalarTypeProbeRequest
        return self.min_required_double_of_scalar_type_probes_as(
            "min_required_double_of_scalar_type_probes", ScalarTypeProbeRequest())

    def min_required_double_of_scalar_type_probes_as(self, alias: str, child_request):
        query = deepcopy(child_request.query)
        query.aggregates = []
        query.min("required_double", alias)
        self.query.relation_aggregates.append(
            RelationAggregate("scalar_type_probe_list", alias, query, True,
                QueryOperation("aggregate", "min_required_double_of_scalar_type_probes_as", alias, "scalar_type_probe_list"))
        )
        return self
    def max_required_double_of_scalar_type_probes(self):
        from requests.scalar_type_probe_request import ScalarTypeProbeRequest
        return self.max_required_double_of_scalar_type_probes_as(
            "max_required_double_of_scalar_type_probes", ScalarTypeProbeRequest())

    def max_required_double_of_scalar_type_probes_as(self, alias: str, child_request):
        query = deepcopy(child_request.query)
        query.aggregates = []
        query.max("required_double", alias)
        self.query.relation_aggregates.append(
            RelationAggregate("scalar_type_probe_list", alias, query, True,
                QueryOperation("aggregate", "max_required_double_of_scalar_type_probes_as", alias, "scalar_type_probe_list"))
        )
        return self
    def sum_required_double_of_scalar_type_probes(self):
        from requests.scalar_type_probe_request import ScalarTypeProbeRequest
        return self.sum_required_double_of_scalar_type_probes_as(
            "sum_required_double_of_scalar_type_probes", ScalarTypeProbeRequest())

    def sum_required_double_of_scalar_type_probes_as(self, alias: str, child_request):
        query = deepcopy(child_request.query)
        query.aggregates = []
        query.sum("required_double", alias)
        self.query.relation_aggregates.append(
            RelationAggregate("scalar_type_probe_list", alias, query, True,
                QueryOperation("aggregate", "sum_required_double_of_scalar_type_probes_as", alias, "scalar_type_probe_list"))
        )
        return self
    def avg_required_double_of_scalar_type_probes(self):
        from requests.scalar_type_probe_request import ScalarTypeProbeRequest
        return self.avg_required_double_of_scalar_type_probes_as(
            "avg_required_double_of_scalar_type_probes", ScalarTypeProbeRequest())

    def avg_required_double_of_scalar_type_probes_as(self, alias: str, child_request):
        query = deepcopy(child_request.query)
        query.aggregates = []
        query.avg("required_double", alias)
        self.query.relation_aggregates.append(
            RelationAggregate("scalar_type_probe_list", alias, query, True,
                QueryOperation("aggregate", "avg_required_double_of_scalar_type_probes_as", alias, "scalar_type_probe_list"))
        )
        return self
    def standardDeviation_required_double_of_scalar_type_probes(self):
        from requests.scalar_type_probe_request import ScalarTypeProbeRequest
        return self.standardDeviation_required_double_of_scalar_type_probes_as(
            "standardDeviation_required_double_of_scalar_type_probes", ScalarTypeProbeRequest())

    def standardDeviation_required_double_of_scalar_type_probes_as(self, alias: str, child_request):
        query = deepcopy(child_request.query)
        query.aggregates = []
        query.standardDeviation("required_double", alias)
        self.query.relation_aggregates.append(
            RelationAggregate("scalar_type_probe_list", alias, query, True,
                QueryOperation("aggregate", "standardDeviation_required_double_of_scalar_type_probes_as", alias, "scalar_type_probe_list"))
        )
        return self
    def squareRootOfPopulationStandardDeviation_required_double_of_scalar_type_probes(self):
        from requests.scalar_type_probe_request import ScalarTypeProbeRequest
        return self.squareRootOfPopulationStandardDeviation_required_double_of_scalar_type_probes_as(
            "squareRootOfPopulationStandardDeviation_required_double_of_scalar_type_probes", ScalarTypeProbeRequest())

    def squareRootOfPopulationStandardDeviation_required_double_of_scalar_type_probes_as(self, alias: str, child_request):
        query = deepcopy(child_request.query)
        query.aggregates = []
        query.squareRootOfPopulationStandardDeviation("required_double", alias)
        self.query.relation_aggregates.append(
            RelationAggregate("scalar_type_probe_list", alias, query, True,
                QueryOperation("aggregate", "squareRootOfPopulationStandardDeviation_required_double_of_scalar_type_probes_as", alias, "scalar_type_probe_list"))
        )
        return self
    def sampleVariance_required_double_of_scalar_type_probes(self):
        from requests.scalar_type_probe_request import ScalarTypeProbeRequest
        return self.sampleVariance_required_double_of_scalar_type_probes_as(
            "sampleVariance_required_double_of_scalar_type_probes", ScalarTypeProbeRequest())

    def sampleVariance_required_double_of_scalar_type_probes_as(self, alias: str, child_request):
        query = deepcopy(child_request.query)
        query.aggregates = []
        query.sampleVariance("required_double", alias)
        self.query.relation_aggregates.append(
            RelationAggregate("scalar_type_probe_list", alias, query, True,
                QueryOperation("aggregate", "sampleVariance_required_double_of_scalar_type_probes_as", alias, "scalar_type_probe_list"))
        )
        return self
    def samplePopulationVariance_required_double_of_scalar_type_probes(self):
        from requests.scalar_type_probe_request import ScalarTypeProbeRequest
        return self.samplePopulationVariance_required_double_of_scalar_type_probes_as(
            "samplePopulationVariance_required_double_of_scalar_type_probes", ScalarTypeProbeRequest())

    def samplePopulationVariance_required_double_of_scalar_type_probes_as(self, alias: str, child_request):
        query = deepcopy(child_request.query)
        query.aggregates = []
        query.samplePopulationVariance("required_double", alias)
        self.query.relation_aggregates.append(
            RelationAggregate("scalar_type_probe_list", alias, query, True,
                QueryOperation("aggregate", "samplePopulationVariance_required_double_of_scalar_type_probes_as", alias, "scalar_type_probe_list"))
        )
        return self
    def min_optional_double_of_scalar_type_probes(self):
        from requests.scalar_type_probe_request import ScalarTypeProbeRequest
        return self.min_optional_double_of_scalar_type_probes_as(
            "min_optional_double_of_scalar_type_probes", ScalarTypeProbeRequest())

    def min_optional_double_of_scalar_type_probes_as(self, alias: str, child_request):
        query = deepcopy(child_request.query)
        query.aggregates = []
        query.min("optional_double", alias)
        self.query.relation_aggregates.append(
            RelationAggregate("scalar_type_probe_list", alias, query, True,
                QueryOperation("aggregate", "min_optional_double_of_scalar_type_probes_as", alias, "scalar_type_probe_list"))
        )
        return self
    def max_optional_double_of_scalar_type_probes(self):
        from requests.scalar_type_probe_request import ScalarTypeProbeRequest
        return self.max_optional_double_of_scalar_type_probes_as(
            "max_optional_double_of_scalar_type_probes", ScalarTypeProbeRequest())

    def max_optional_double_of_scalar_type_probes_as(self, alias: str, child_request):
        query = deepcopy(child_request.query)
        query.aggregates = []
        query.max("optional_double", alias)
        self.query.relation_aggregates.append(
            RelationAggregate("scalar_type_probe_list", alias, query, True,
                QueryOperation("aggregate", "max_optional_double_of_scalar_type_probes_as", alias, "scalar_type_probe_list"))
        )
        return self
    def sum_optional_double_of_scalar_type_probes(self):
        from requests.scalar_type_probe_request import ScalarTypeProbeRequest
        return self.sum_optional_double_of_scalar_type_probes_as(
            "sum_optional_double_of_scalar_type_probes", ScalarTypeProbeRequest())

    def sum_optional_double_of_scalar_type_probes_as(self, alias: str, child_request):
        query = deepcopy(child_request.query)
        query.aggregates = []
        query.sum("optional_double", alias)
        self.query.relation_aggregates.append(
            RelationAggregate("scalar_type_probe_list", alias, query, True,
                QueryOperation("aggregate", "sum_optional_double_of_scalar_type_probes_as", alias, "scalar_type_probe_list"))
        )
        return self
    def avg_optional_double_of_scalar_type_probes(self):
        from requests.scalar_type_probe_request import ScalarTypeProbeRequest
        return self.avg_optional_double_of_scalar_type_probes_as(
            "avg_optional_double_of_scalar_type_probes", ScalarTypeProbeRequest())

    def avg_optional_double_of_scalar_type_probes_as(self, alias: str, child_request):
        query = deepcopy(child_request.query)
        query.aggregates = []
        query.avg("optional_double", alias)
        self.query.relation_aggregates.append(
            RelationAggregate("scalar_type_probe_list", alias, query, True,
                QueryOperation("aggregate", "avg_optional_double_of_scalar_type_probes_as", alias, "scalar_type_probe_list"))
        )
        return self
    def standardDeviation_optional_double_of_scalar_type_probes(self):
        from requests.scalar_type_probe_request import ScalarTypeProbeRequest
        return self.standardDeviation_optional_double_of_scalar_type_probes_as(
            "standardDeviation_optional_double_of_scalar_type_probes", ScalarTypeProbeRequest())

    def standardDeviation_optional_double_of_scalar_type_probes_as(self, alias: str, child_request):
        query = deepcopy(child_request.query)
        query.aggregates = []
        query.standardDeviation("optional_double", alias)
        self.query.relation_aggregates.append(
            RelationAggregate("scalar_type_probe_list", alias, query, True,
                QueryOperation("aggregate", "standardDeviation_optional_double_of_scalar_type_probes_as", alias, "scalar_type_probe_list"))
        )
        return self
    def squareRootOfPopulationStandardDeviation_optional_double_of_scalar_type_probes(self):
        from requests.scalar_type_probe_request import ScalarTypeProbeRequest
        return self.squareRootOfPopulationStandardDeviation_optional_double_of_scalar_type_probes_as(
            "squareRootOfPopulationStandardDeviation_optional_double_of_scalar_type_probes", ScalarTypeProbeRequest())

    def squareRootOfPopulationStandardDeviation_optional_double_of_scalar_type_probes_as(self, alias: str, child_request):
        query = deepcopy(child_request.query)
        query.aggregates = []
        query.squareRootOfPopulationStandardDeviation("optional_double", alias)
        self.query.relation_aggregates.append(
            RelationAggregate("scalar_type_probe_list", alias, query, True,
                QueryOperation("aggregate", "squareRootOfPopulationStandardDeviation_optional_double_of_scalar_type_probes_as", alias, "scalar_type_probe_list"))
        )
        return self
    def sampleVariance_optional_double_of_scalar_type_probes(self):
        from requests.scalar_type_probe_request import ScalarTypeProbeRequest
        return self.sampleVariance_optional_double_of_scalar_type_probes_as(
            "sampleVariance_optional_double_of_scalar_type_probes", ScalarTypeProbeRequest())

    def sampleVariance_optional_double_of_scalar_type_probes_as(self, alias: str, child_request):
        query = deepcopy(child_request.query)
        query.aggregates = []
        query.sampleVariance("optional_double", alias)
        self.query.relation_aggregates.append(
            RelationAggregate("scalar_type_probe_list", alias, query, True,
                QueryOperation("aggregate", "sampleVariance_optional_double_of_scalar_type_probes_as", alias, "scalar_type_probe_list"))
        )
        return self
    def samplePopulationVariance_optional_double_of_scalar_type_probes(self):
        from requests.scalar_type_probe_request import ScalarTypeProbeRequest
        return self.samplePopulationVariance_optional_double_of_scalar_type_probes_as(
            "samplePopulationVariance_optional_double_of_scalar_type_probes", ScalarTypeProbeRequest())

    def samplePopulationVariance_optional_double_of_scalar_type_probes_as(self, alias: str, child_request):
        query = deepcopy(child_request.query)
        query.aggregates = []
        query.samplePopulationVariance("optional_double", alias)
        self.query.relation_aggregates.append(
            RelationAggregate("scalar_type_probe_list", alias, query, True,
                QueryOperation("aggregate", "samplePopulationVariance_optional_double_of_scalar_type_probes_as", alias, "scalar_type_probe_list"))
        )
        return self

class ExecutableTypePlatformRequest:
    def __init__(self, request):
        self._request = request

    def comment(self, c: str):
        self._request.comment(c)
        return self

    def new_entity(self, context) -> TypePlatform:
        request = self._request
        if not request._comment or not request._comment.strip() or not request._purpose or not request._purpose.strip():
            raise ValueError("Security audit failure: non-empty comment() and purpose() are required before new_entity()")
        entity = context.initialize_entity("TypePlatform", TypePlatform())
        if not isinstance(entity, TypePlatform):
            raise TypeError("entity initializer returned an incompatible TypePlatform")
        return entity

    async def execute_for_result(self, context):
        self = self._request
        if not self._purpose or not self._purpose.strip() or not self._comment or not self._comment.strip():
            raise Exception("Security audit failure: comment() and purpose() must be called before execute_for_rows()")
        service = context.require_resource("dataService")
        req = QueryRequest(context.prepare_query(self.query), _comment=self._comment, _purpose=self._purpose)
        return await service.query(context, req)

    async def execute_for_rows(self, context):
        return (await self.execute_for_result(context)).rows

    async def execute_for_list(self, context) -> SmartList[TypePlatform]:
        from teaql.runtime.query_list import execute_typed_list
        request = self._request
        QueryIntent(request._comment, request._purpose)
        query = deepcopy(request.query)
        authorized = context.prepare_query(query)
        root = QueryRequest(authorized, _comment=request._comment, _purpose=request._purpose)
        operation = (QueryOperation("named-count", request._page_count_method or "count",
            request._page_count_alias if request._page_count_method == "count_as" else None)
            if request._page_count_alias is not None else None)
        return await execute_typed_list(context, root,
            lambda row: TypePlatform(_entity_root=EntityRoot(), **row),
            count_operation=operation, count_alias=request._page_count_alias)

    async def execute_for_one(self, context):
        request = deepcopy(self._request)
        request.limit(1)
        entities = await ExecutableTypePlatformRequest(request).execute_for_list(context)
        return entities[0] if entities else None

    def execute_for_stream(self, context, chunk_size: int = 1000):
        """Yield entity chunks lazily from the provider cursor."""
        request = deepcopy(self._request)
        QueryIntent(request._comment, request._purpose)
        service = context.require_resource("dataService")
        if not hasattr(service, "query_stream"):
            raise RuntimeError("dataService does not implement query_stream")
        root = QueryRequest(context.prepare_query(request.query), _comment=request._comment, _purpose=request._purpose)
        from teaql.runtime.query_stream import execute_typed_stream
        return execute_typed_stream(context, root,
            lambda row: TypePlatform(_entity_root=EntityRoot(), **row), chunk_size)
