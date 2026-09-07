import pytest
from teaql.core.query import SelectQuery, OrderBy, SortDirection
from teaql.core.expr import eq, gte

def test_select_query_builder():
    query = SelectQuery.new("User")
    assert query.entity == "User"
    assert len(query.projection) == 0
    
def test_order_by_builder():
    ob = OrderBy.asc("age")
    assert ob.field_name == "age"
    assert ob.direction == SortDirection.Asc
    
    ob_desc = OrderBy.desc("created_at")
    assert ob_desc.field_name == "created_at"
    assert ob_desc.direction == SortDirection.Desc

    query = SelectQuery.new("User").order_by("created_at", "desc")
    assert query.order_by_items == [ob_desc]
    with pytest.raises(ValueError, match="unsupported order direction"):
        query.order_by("id", "sideways")

def test_id_set_pagination_is_explicit_local_and_validated():
    query = SelectQuery.new("Order")
    assert query.id_set_pagination is None
    query.optimize_pagination_with_id_set_config("orders", 30, 1000)
    assert query.id_set_pagination.namespace == "orders"
    assert query.id_set_pagination.ttl_seconds == 30
    assert query.id_set_pagination.max_ids == 1000
    with pytest.raises(ValueError):
        SelectQuery.new("Order").optimize_pagination_with_id_set_config(" ", 30, 1)
    with pytest.raises(ValueError):
        SelectQuery.new("Order").optimize_pagination_with_id_set_config("orders", 0, 1)
    with pytest.raises(ValueError):
        SelectQuery.new("Order").optimize_pagination_with_id_set_config("orders", 30, 0)


def test_deleted_rows_preserves_application_filters():
    query = SelectQuery.new("Order").and_filter(gte("version", 1)).and_filter(eq("tenant", 7))
    query.with_deleted_rows()
    assert query.filter_expr is not None
    assert "tenant" in repr(query.filter_expr)
    query.deleted_rows_only()
    assert "version" in repr(query.filter_expr)
    assert "tenant" in repr(query.filter_expr)
