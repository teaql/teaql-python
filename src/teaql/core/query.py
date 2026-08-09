from enum import Enum, auto
from typing import List, Optional, Any, Dict
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
class RawSqlProjection:
    property_name: str
    raw_sql_segment: str

@dataclass
class ObjectGroupBy:
    property_name: str
    storage_field: str
    query: 'SelectQuery'

@dataclass
class AggregationCacheOptions:
    enabled: bool
    cache_expired_millis: int
    propagate: bool
    propagate_cache_expired_millis: int

@dataclass
class StreamConfig:
    chunk_size: int = 1000

@dataclass
class SelectQuery:
    entity: str
    projection: List[str] = field(default_factory=list)
    expr_projection: List[NamedExpr] = field(default_factory=list)
    search_with_text: Optional[str] = None
    filter: Optional[Expr] = None
    having: Optional[Expr] = None
    order_by: List[OrderBy] = field(default_factory=list)
    slice: Optional[Slice] = None
    aggregates: List[Aggregate] = field(default_factory=list)
    group_by: List[str] = field(default_factory=list)
    relations: List[RelationLoad] = field(default_factory=list)
    aggregation_cache: Optional[AggregationCacheOptions] = None
    comment: Optional[str] = None
    trace_chain: List[TraceNode] = field(default_factory=list)
    raw_sql: Optional[str] = None
    raw_sql_search_criteria: List[str] = field(default_factory=list)
    dynamic_properties: List[RawSqlProjection] = field(default_factory=list)
    raw_projections: List[RawSqlProjection] = field(default_factory=list)
    object_group_bys: List[ObjectGroupBy] = field(default_factory=list)
    child_enhancements: List['SelectQuery'] = field(default_factory=list)
    stream_config: Optional[StreamConfig] = None

    @classmethod
    def new(cls, entity: str) -> 'SelectQuery':
        return cls(entity=entity)
    def with_object_group_by(self, property_name: str, storage_field: str, query: 'SelectQuery') -> 'SelectQuery':
        self.object_group_bys.append(ObjectGroupBy(property_name, storage_field, query))
        return self
    
    def with_comment(self, comment: str) -> 'SelectQuery':
        self.comment = comment
        return self
    
    def count(self, alias: str) -> 'SelectQuery':
        self.aggregates.append(Aggregate(AggregateFunction.Count, "id", alias))
        return self
    
    def and_filter(self, expr: Expr) -> 'SelectQuery':
        if self.filter:
            self.filter = Expr.new_and(self.filter, expr)
        else:
            self.filter = expr
        return self
    
    def order_asc(self, field: str) -> 'SelectQuery':
        self.order_by.append(OrderBy.asc(field))
        return self

    def order_desc(self, field: str) -> 'SelectQuery':
        self.order_by.append(OrderBy.desc(field))
        return self
