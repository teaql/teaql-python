from teaql.core.query import SelectQuery, OrderBy, SortDirection

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
