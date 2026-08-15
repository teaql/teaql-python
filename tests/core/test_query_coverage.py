import pytest
import dataclasses
from teaql.core.query import (
    SortDirection, NamedExpr, OrderBy, AggregateFunction, Aggregate, Slice,
    RelationLoad, RelationAggregate, RawSqlProjection, ObjectGroupBy,
    AggregationCacheOptions, StreamConfig, SelectQuery
)
from teaql.core.expr import column

def test_query_builder():
    q = SelectQuery.new("User")
    assert q.entity == "User"
    
    # Simple settings
    q.with_comment("test comment")
    assert q.comment_text == "test comment"
    
    q.comment("another comment")
    assert q.comment_text == "another comment"
    
    # Projections
    q.project("id", "name")
    q.projects(["age", "email"])
    q.project_expr("name_col", column("name"))
    q.project_raw("raw", "SELECT 1")
    
    # Filters
    q.filter(column("a"))
    q.and_filter(column("b"))
    q.or_filter(column("c"))
    
    q.having(column("x"))
    q.and_having(column("y"))
    q.or_having(column("z"))
    
    # Orders
    q.order_asc("id")
    q.order_desc("name")
    q.asc("age")
    q.desc("email")
    q.order_by(OrderBy.asc("id"))
    
    q.asc_expr(column("a"))
    q.desc_expr(column("b"))
    q.asc_gbk("name")
    q.desc_gbk("name")
    
    q.order_expr_asc(column("a"))
    q.order_expr_desc(column("b"))
    q.order_gbk_asc("name")
    q.order_gbk_desc("name")
    
    # Pagination
    q.limit(10)
    q.offset(20)
    assert q.slice.limit == 10
    assert q.slice.offset == 20
    q.page(2, 50)
    assert q.slice.limit == 50
    assert q.slice.offset == 50
    
    # Aggregates
    q.count("cnt")
    q.count_field("id", "cnt_id")
    q.sum("amount", "sum_amount")
    q.avg("score", "avg_score")
    q.min("age", "min_age")
    q.max("age", "max_age")
    q.stddev("score", "stddev_s")
    q.stddev_pop("score", "stddev_p")
    q.var_samp("score", "var_s")
    q.var_pop("score", "var_p")
    q.bit_and("flags", "band")
    q.bit_or("flags", "bor")
    q.bit_xor("flags", "bxor")
    q.aggregate(Aggregate(AggregateFunction.Sum, "a", "b"))
    
    # Group By
    q.group_by("department", "team")
    q.with_object_group_by("prop", "field", SelectQuery.new("Child"))
    q.object_group_by("prop2", "field2", SelectQuery.new("Child2"))
    
    # Relations
    q.relation("Posts")
    q.relation_query("Comments", SelectQuery.new("Comment"))
    
    # Aggregation Cache
    q.enable_aggregation_cache(100)
    q.enable_aggregation_cache_for(200, True, 300)
    
    # Advanced
    q.child_enhancement(SelectQuery.new("Child"))
    q.raw_sql_query("SELECT * FROM User")
    q.raw_sql_search_criteria_add("id = 1")
    q.dynamic_property_raw("dyn", "SQL")
    
    q.stream(500)
    assert q.stream_config.chunk_size == 500
    q.stream_default()
    assert q.stream_config.chunk_size == 1000
    
def test_order_by_class():
    ob1 = OrderBy.new("id", SortDirection.Asc)
    ob2 = OrderBy.from_expr(column("name"), SortDirection.Desc)
    ob3 = OrderBy.asc("age")
    ob4 = OrderBy.desc("score")
    ob5 = OrderBy.asc_expr(column("a"))
    ob6 = OrderBy.desc_expr(column("b"))
    ob7 = OrderBy.asc_gbk("name")
    ob8 = OrderBy.desc_gbk("name")
    assert ob1.field_name == "id"
    assert ob3.field_name == "age"


def test_materialized_list_hard_limit():
    assert SelectQuery("Order").prepare_for_list().slice.limit == 10_000
    with pytest.raises(ValueError, match="QUERY_HARD_LIMIT_EXCEEDED"):
        SelectQuery("Order").limit(10_001).prepare_for_list()
    with pytest.raises(ValueError, match="QUERY_INVALID_LIMIT"):
        SelectQuery("Order").limit(0)
    with pytest.raises(ValueError, match="QUERY_INVALID_OFFSET"):
        SelectQuery("Order").offset(-1)
