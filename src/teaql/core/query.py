from enum import Enum, auto
from typing import List, Optional, Any, Dict
from copy import deepcopy
from dataclasses import dataclass, field
from .expr import Expr, ExprBuilder
from .mutation import TraceNode

class SortDirection(Enum):
    Asc = auto()
    Desc = auto()

@dataclass
class NamedExpr:
    alias: str
    expr: Expr

@dataclass
class OrderBy:
    field_name: str
    direction: SortDirection
    expr: Optional[Expr] = None

    @classmethod
    def new(cls, field_name: str, direction: SortDirection) -> 'OrderBy':
        return cls(field_name=field_name, direction=direction)

    @classmethod
    def from_expr(cls, expr: Expr, direction: SortDirection) -> 'OrderBy':
        return cls(field_name="", direction=direction, expr=expr)

    @classmethod
    def asc(cls, field_name: str) -> 'OrderBy':
        return cls.new(field_name, SortDirection.Asc)

    @classmethod
    def desc(cls, field_name: str) -> 'OrderBy':
        return cls.new(field_name, SortDirection.Desc)

    @classmethod
    def asc_expr(cls, expr: Expr) -> 'OrderBy':
        return cls.from_expr(expr, SortDirection.Asc)

    @classmethod
    def desc_expr(cls, expr: Expr) -> 'OrderBy':
        return cls.from_expr(expr, SortDirection.Desc)

    @classmethod
    def asc_gbk(cls, field_name: str) -> 'OrderBy':
        return cls.asc_expr(ExprBuilder.gbk(ExprBuilder.column(field_name)))

    @classmethod
    def desc_gbk(cls, field_name: str) -> 'OrderBy':
        return cls.desc_expr(ExprBuilder.gbk(ExprBuilder.column(field_name)))

class AggregateFunction(Enum):
    Count = auto()
    Sum = auto()
    Avg = auto()
    Min = auto()
    Max = auto()
    Stddev = auto()
    StddevPop = auto()
    VarSamp = auto()
    VarPop = auto()
    BitAnd = auto()
    BitOr = auto()
    BitXor = auto()

@dataclass
class Aggregate:
    function: AggregateFunction
    field: str
    alias: str

@dataclass
class Slice:
    offset: int
    limit: Optional[int] = None

@dataclass
class RelationLoad:
    name: str
    query: Optional['SelectQuery'] = None

@dataclass
class RelationAggregate:
    relation_name: str
    alias: str
    query: 'SelectQuery'
    single_result: bool = True


@dataclass
class RawSqlProjection:
    property_name: str
    raw_sql_segment: str

@dataclass
class ObjectGroupBy:
    property_name: str
    storage_field: str
    query: 'SelectQuery'

@dataclass
class FacetRequest:
    name: str
    relation_name: str
    query: 'SelectQuery'
    include_all_facets: bool = True

@dataclass
class AggregationCacheOptions:
    enabled: bool
    cache_expired_millis: int
    propagate: bool
    propagate_cache_expired_millis: int

@dataclass
class StreamConfig:
    chunk_size: int = 1000

@dataclass(frozen=True)
class IdSetPaginationOptions:
    namespace: str = "default"
    ttl_seconds: int = 600
    max_ids: int = 3_000_000

@dataclass
class SelectQuery:
    entity: str
    projection: List[str] = field(default_factory=list)
    expr_projection: List[NamedExpr] = field(default_factory=list)
    search_with_text: Optional[str] = None
    filter_expr: Optional[Expr] = None
    having_expr: Optional[Expr] = None
    order_by_items: List[OrderBy] = field(default_factory=list)
    slice: Optional[Slice] = None
    partition_by: Optional[str] = None
    aggregates: List[Aggregate] = field(default_factory=list)
    group_by_items: List[str] = field(default_factory=list)
    relations: List[RelationLoad] = field(default_factory=list)
    relation_aggregates: List[RelationAggregate] = field(default_factory=list)
    aggregation_cache: Optional[AggregationCacheOptions] = None
    comment_text: Optional[str] = None
    trace_chain: List[TraceNode] = field(default_factory=list)
    raw_sql: Optional[str] = None
    raw_sql_search_criteria: List[str] = field(default_factory=list)
    dynamic_properties: List[RawSqlProjection] = field(default_factory=list)
    raw_projections: List[RawSqlProjection] = field(default_factory=list)
    object_group_bys: List[ObjectGroupBy] = field(default_factory=list)
    facets: List[FacetRequest] = field(default_factory=list)
    child_enhancements: List['SelectQuery'] = field(default_factory=list)
    stream_config: Optional[StreamConfig] = None
    id_set_pagination: Optional[IdSetPaginationOptions] = field(default=None, repr=False)
    top_n_probe_threshold_value: Optional[int] = field(default=None, repr=False)

    def __post_init__(self) -> None:
        # Local runtime policy: intentionally excluded from federation serialization.
        self.hard_limit_value = 10_000

    @classmethod
    def new(cls, entity: str) -> 'SelectQuery':
        return cls(entity=entity)
    def with_object_group_by(self, property_name: str, storage_field: str, query: 'SelectQuery') -> 'SelectQuery':
        self.object_group_bys.append(ObjectGroupBy(property_name, storage_field, query))
        return self
    
    def with_comment(self, comment: str) -> 'SelectQuery':
        self.comment_text = comment
        return self
    
    def count(self, alias: str) -> 'SelectQuery':
        self.aggregates.append(Aggregate(AggregateFunction.Count, "id", alias))
        return self

    def project(self, *fields: str) -> 'SelectQuery':
        self.projection.extend(fields)
        return self

    def prepare_for_list(self) -> 'SelectQuery':
        self._apply_list_limit(self.hard_limit_value)
        return self

    def _apply_list_limit(self, ceiling: int) -> None:
        if self.slice is None:
            self.slice = Slice(offset=0, limit=ceiling)
        elif self.slice.limit is None:
            self.slice.limit = ceiling
        elif self.slice.limit > ceiling:
            raise ValueError(
                f"QUERY_HARD_LIMIT_EXCEEDED: requested limit {self.slice.limit} "
                f"exceeds hard limit {ceiling}"
            )
        for relation in self.relations:
            if relation.query is not None:
                relation.query._apply_list_limit(10_000)
        for child in self.child_enhancements:
            child._apply_list_limit(10_000)

    def for_exact_count(self, alias: str = "__teaql_total") -> 'SelectQuery':
        count_query = deepcopy(self)
        count_query.projection = []
        count_query.expr_projection = []
        count_query.order_by_items = []
        count_query.slice = None
        count_query.relations = []
        count_query.child_enhancements = []
        count_query.object_group_bys = []
        count_query.facets = []
        count_query.dynamic_properties = []
        count_query.raw_projections = []
        count_query.group_by_items = []
        count_query.aggregates = [Aggregate(AggregateFunction.Count, "id", alias)]
        return count_query

    def partition_by_field(self, field_name: str) -> 'SelectQuery':
        self.partition_by = field_name
        return self

    def top_n_probe_parent_threshold(self, parent_count: int) -> 'SelectQuery':
        if parent_count < 0:
            raise ValueError("Top-N probe parent threshold must not be negative")
        self.top_n_probe_threshold_value = parent_count
        return self

    def optimize_pagination_with_id_set(self) -> 'SelectQuery':
        return self.optimize_pagination_with_id_set_config("default", 600, 3_000_000)

    def optimize_pagination_with_id_set_config(
            self, namespace: str, ttl_seconds: int, max_ids: int) -> 'SelectQuery':
        if not isinstance(namespace, str) or not namespace.strip():
            raise ValueError("ID set pagination namespace must not be empty")
        if ttl_seconds <= 0:
            raise ValueError("ID set pagination ttl_seconds must be positive")
        if max_ids <= 0:
            raise ValueError("ID set pagination max_ids must be positive")
        self.id_set_pagination = IdSetPaginationOptions(namespace, ttl_seconds, max_ids)
        return self

    def relation_query(self, name: str, query: Optional['SelectQuery'] = None) -> 'SelectQuery':
        self.relations.append(RelationLoad(name, query))
        return self
    
    def and_filter(self, expr: Expr) -> 'SelectQuery':
        if self.filter_expr:
            self.filter_expr = Expr.new_and(self.filter_expr, expr)
        else:
            self.filter_expr = expr
        return self
    
    def order_asc(self, field: str) -> 'SelectQuery':
        self.order_by_items.append(OrderBy.asc(field))
        return self

    def order_desc(self, field: str) -> 'SelectQuery':
        self.order_by_items.append(OrderBy.desc(field))
        return self

    def comment(self, text: str) -> 'SelectQuery':
        self.comment_text = text
        return self

    def project(self, *fields: str) -> 'SelectQuery':
        self.projection.extend(fields)
        return self

    def projects(self, fields: List[str]) -> 'SelectQuery':
        self.projection.extend(fields)
        return self

    def project_expr(self, alias: str, expr: Expr) -> 'SelectQuery':
        self.expr_projection.append(NamedExpr(alias, expr))
        return self

    def project_raw(self, property_name: str, raw_sql_segment: str) -> 'SelectQuery':
        self.raw_projections.append(RawSqlProjection(property_name, raw_sql_segment))
        return self

    def filter(self, expr: Expr) -> 'SelectQuery':
        self.filter_expr = expr
        return self

    def or_filter(self, expr: Expr) -> 'SelectQuery':
        if self.filter_expr:
            self.filter_expr = Expr.new_or(self.filter_expr, expr)
        else:
            self.filter_expr = expr
        return self

    def having(self, expr: Expr) -> 'SelectQuery':
        self.having_expr = expr
        return self

    def and_having(self, expr: Expr) -> 'SelectQuery':
        if self.having_expr:
            self.having_expr = Expr.new_and(self.having_expr, expr)
        else:
            self.having_expr = expr
        return self

    def or_having(self, expr: Expr) -> 'SelectQuery':
        if self.having_expr:
            self.having_expr = Expr.new_or(self.having_expr, expr)
        else:
            self.having_expr = expr
        return self

    def order_by(self, order: OrderBy) -> 'SelectQuery':
        self.order_by_items.append(order)
        return self

    def asc(self, field: str) -> 'SelectQuery':
        self.order_by_items.append(OrderBy.asc(field))
        return self

    def desc(self, field: str) -> 'SelectQuery':
        self.order_by_items.append(OrderBy.desc(field))
        return self

    def asc_expr(self, expr: Expr) -> 'SelectQuery':
        self.order_by_items.append(OrderBy.asc_expr(expr))
        return self

    def desc_expr(self, expr: Expr) -> 'SelectQuery':
        self.order_by_items.append(OrderBy.desc_expr(expr))
        return self

    def asc_gbk(self, field: str) -> 'SelectQuery':
        self.order_by_items.append(OrderBy.asc_gbk(field))
        return self

    def desc_gbk(self, field: str) -> 'SelectQuery':
        self.order_by_items.append(OrderBy.desc_gbk(field))
        return self

    def order_expr_asc(self, expr: Expr) -> 'SelectQuery':
        return self.asc_expr(expr)

    def order_expr_desc(self, expr: Expr) -> 'SelectQuery':
        return self.desc_expr(expr)

    def order_gbk_asc(self, field: str) -> 'SelectQuery':
        return self.asc_gbk(field)

    def order_gbk_desc(self, field: str) -> 'SelectQuery':
        return self.desc_gbk(field)

    def limit(self, l: int) -> 'SelectQuery':
        if not isinstance(l, int) or isinstance(l, bool) or l < 1:
            raise ValueError("QUERY_INVALID_LIMIT: limit must be a positive integer")
        if not self.slice:
            self.slice = Slice(0, l)
        else:
            self.slice.limit = l
        return self

    def offset(self, o: int) -> 'SelectQuery':
        if not isinstance(o, int) or isinstance(o, bool) or o < 0:
            raise ValueError("QUERY_INVALID_OFFSET: offset must be a non-negative integer")
        if not self.slice:
            self.slice = Slice(o, None)
        else:
            self.slice.offset = o
        return self

    def page(self, page_no: int, page_size: int) -> 'SelectQuery':
        if not isinstance(page_no, int) or page_no < 1:
            raise ValueError("page_no must be a positive integer")
        if not isinstance(page_size, int) or page_size < 1:
            raise ValueError("QUERY_INVALID_LIMIT: page_size must be a positive integer")
        self.slice = Slice((page_no - 1) * page_size, page_size)
        return self

    def aggregate(self, agg: Aggregate) -> 'SelectQuery':
        self.aggregates.append(agg)
        return self

    def count_field(self, field: str, alias: str) -> 'SelectQuery':
        self.aggregates.append(Aggregate(AggregateFunction.Count, field, alias))
        return self

    def sum(self, field: str, alias: str) -> 'SelectQuery':
        self.aggregates.append(Aggregate(AggregateFunction.Sum, field, alias))
        return self

    def avg(self, field: str, alias: str) -> 'SelectQuery':
        self.aggregates.append(Aggregate(AggregateFunction.Avg, field, alias))
        return self

    def min(self, field: str, alias: str) -> 'SelectQuery':
        self.aggregates.append(Aggregate(AggregateFunction.Min, field, alias))
        return self

    def max(self, field: str, alias: str) -> 'SelectQuery':
        self.aggregates.append(Aggregate(AggregateFunction.Max, field, alias))
        return self

    def stddev(self, field: str, alias: str) -> 'SelectQuery':
        self.aggregates.append(Aggregate(AggregateFunction.Stddev, field, alias))
        return self

    def stddev_pop(self, field: str, alias: str) -> 'SelectQuery':
        self.aggregates.append(Aggregate(AggregateFunction.StddevPop, field, alias))
        return self

    def var_samp(self, field: str, alias: str) -> 'SelectQuery':
        self.aggregates.append(Aggregate(AggregateFunction.VarSamp, field, alias))
        return self

    def var_pop(self, field: str, alias: str) -> 'SelectQuery':
        self.aggregates.append(Aggregate(AggregateFunction.VarPop, field, alias))
        return self

    def bit_and(self, field: str, alias: str) -> 'SelectQuery':
        self.aggregates.append(Aggregate(AggregateFunction.BitAnd, field, alias))
        return self

    def bit_or(self, field: str, alias: str) -> 'SelectQuery':
        self.aggregates.append(Aggregate(AggregateFunction.BitOr, field, alias))
        return self

    def bit_xor(self, field: str, alias: str) -> 'SelectQuery':
        self.aggregates.append(Aggregate(AggregateFunction.BitXor, field, alias))
        return self

    def group_by(self, *fields: str) -> 'SelectQuery':
        self.group_by_items.extend(fields)
        return self

    def object_group_by(self, property_name: str, storage_field: str, query: 'SelectQuery') -> 'SelectQuery':
        self.object_group_bys.append(ObjectGroupBy(property_name, storage_field, query))
        return self

    def facet_by(self, name: str, relation_name: str, query: 'SelectQuery',
                 include_all_facets: bool = True) -> 'SelectQuery':
        self.facets.append(FacetRequest(name, relation_name, query, include_all_facets))
        return self

    def relation(self, name: str) -> 'SelectQuery':
        self.relations.append(RelationLoad(name, None))
        return self

    def relation_query(self, name: str, query: 'SelectQuery') -> 'SelectQuery':
        self.relations.append(RelationLoad(name, query))
        return self

    def enable_aggregation_cache(self, expire_millis: int) -> 'SelectQuery':
        self.aggregation_cache = AggregationCacheOptions(True, expire_millis, False, 0)
        return self

    def enable_aggregation_cache_for(self, expire_millis: int, propagate: bool, propagate_expire_millis: int) -> 'SelectQuery':
        self.aggregation_cache = AggregationCacheOptions(True, expire_millis, propagate, propagate_expire_millis)
        return self

    def child_enhancement(self, query: 'SelectQuery') -> 'SelectQuery':
        self.child_enhancements.append(query)
        return self

    def raw_sql_query(self, sql: str) -> 'SelectQuery':
        self.raw_sql = sql
        return self

    def raw_sql_search_criteria_add(self, criteria: str) -> 'SelectQuery':
        self.raw_sql_search_criteria.append(criteria)
        return self

    def dynamic_property_raw(self, property_name: str, raw_sql_segment: str) -> 'SelectQuery':
        self.dynamic_properties.append(RawSqlProjection(property_name, raw_sql_segment))
        return self

    def stream(self, chunk_size: int) -> 'SelectQuery':
        self.stream_config = StreamConfig(chunk_size)
        return self

    def stream_default(self) -> 'SelectQuery':
        self.stream_config = StreamConfig(1000)
        return self
