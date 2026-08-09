from teaql.core.expr import ExprBuilder, ExprFunction, ColumnExpr, FunctionExpr

def test_expr_builder():
    expr = ExprBuilder.count_all()
    assert isinstance(expr, FunctionExpr)
    assert expr.function == ExprFunction.Count
    
    col = ExprBuilder.column("id")
    assert isinstance(col, ColumnExpr)
    assert col.name == "id"
