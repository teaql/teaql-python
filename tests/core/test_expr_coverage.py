import pytest
from teaql.core.expr import (
    Expr, ExprBuilder, ColumnExpr, ValueExpr, FunctionExpr, BinaryExpr, BinaryOp, ExprFunction,
    column, value, function, soundex, gbk, count_all, count_expr, sum_expr, avg_expr,
    min_expr, max_expr, stddev_expr, stddev_pop_expr, var_samp_expr, var_pop_expr,
    bit_and_expr, bit_or_expr, bit_xor_expr, binary, eq, ne, gt, gte, lt, lte, like, not_like,
    contain, not_contain, begin_with, not_begin_with, end_with, not_end_with, sound_like,
    in_list, not_in_list, in_large, not_in_large, is_null, is_not_null, between,
    compare_columns, subquery, in_subquery, not_in_subquery, negate, and_expr, or_expr, and_, or_
)
from teaql.core.value import Value

def test_expr_builder_and_functions():
    c = column("id")
    assert isinstance(c, ColumnExpr)
    
    v = value(1)
    assert isinstance(v, ValueExpr)
    
    f = function(ExprFunction.Soundex, [c])
    assert isinstance(f, FunctionExpr)
    
    assert isinstance(soundex(c), FunctionExpr)
    assert isinstance(gbk(c), FunctionExpr)
    
    assert isinstance(count_all(), FunctionExpr)
    assert isinstance(count_expr(c), FunctionExpr)
    assert isinstance(sum_expr(c), FunctionExpr)
    assert isinstance(avg_expr(c), FunctionExpr)
    assert isinstance(min_expr(c), FunctionExpr)
    assert isinstance(max_expr(c), FunctionExpr)
    
    assert isinstance(stddev_expr(c), FunctionExpr)
    assert isinstance(stddev_pop_expr(c), FunctionExpr)
    assert isinstance(var_samp_expr(c), FunctionExpr)
    assert isinstance(var_pop_expr(c), FunctionExpr)
    
    assert isinstance(bit_and_expr(c), FunctionExpr)
    assert isinstance(bit_or_expr(c), FunctionExpr)
    assert isinstance(bit_xor_expr(c), FunctionExpr)
    
def test_binary_expressions():
    assert isinstance(binary(column("a"), BinaryOp.Eq, value(1)), BinaryExpr)
    
    assert isinstance(eq("id", 1), BinaryExpr)
    assert isinstance(ne("id", 2), BinaryExpr)
    assert isinstance(gt("id", 3), BinaryExpr)
    assert isinstance(gte("id", 4), BinaryExpr)
    assert isinstance(lt("id", 5), BinaryExpr)
    assert isinstance(lte("id", 6), BinaryExpr)
    
    assert isinstance(like("name", "John%"), BinaryExpr)
    assert isinstance(not_like("name", "John%"), BinaryExpr)
    
    assert isinstance(contain("name", "oh"), BinaryExpr)
    assert isinstance(not_contain("name", "oh"), BinaryExpr)
    
    assert isinstance(begin_with("name", "Jo"), BinaryExpr)
    assert isinstance(not_begin_with("name", "Jo"), BinaryExpr)
    
    assert isinstance(end_with("name", "hn"), BinaryExpr)
    assert isinstance(not_end_with("name", "hn"), BinaryExpr)
    
    assert isinstance(sound_like("name", "John"), BinaryExpr)
    
    assert isinstance(in_list("id", [1, 2]), BinaryExpr)
    assert isinstance(not_in_list("id", [1, 2]), BinaryExpr)
    assert isinstance(in_large("id", [1, 2]), BinaryExpr)
    assert isinstance(not_in_large("id", [1, 2]), BinaryExpr)
    
def test_logical_and_other_expressions():
    c = column("test")
    assert isinstance(is_null(c), Expr)
    assert isinstance(is_not_null(c), Expr)
    
    assert isinstance(between(c, value(1), value(10)), Expr)
    assert isinstance(compare_columns("a", BinaryOp.Eq, "b"), BinaryExpr)
    
    # Subqueries
    assert isinstance(subquery(c, BinaryOp.In, "User", None), Expr)
    assert isinstance(in_subquery(c, "User", None), Expr)
    assert isinstance(not_in_subquery(c, "User", None), Expr)
    
    assert isinstance(negate(c), Expr)
    
    assert isinstance(and_expr(c, c), Expr)
    assert isinstance(or_expr(c, c), Expr)
    
    assert isinstance(and_(c, c, c), Expr)
    assert isinstance(or_(c, c, c), Expr)
    
def test_expr_static_methods():
    assert isinstance(Expr.eq("id", 1), BinaryExpr)
    assert isinstance(Expr.ne("id", 1), BinaryExpr)
    assert isinstance(Expr.gt("id", 1), BinaryExpr)
    assert isinstance(Expr.gte("id", 1), BinaryExpr)
    assert isinstance(Expr.lt("id", 1), BinaryExpr)
    assert isinstance(Expr.lte("id", 1), BinaryExpr)
    assert isinstance(Expr.like("name", "x"), BinaryExpr)
    assert isinstance(Expr.not_like("name", "x"), BinaryExpr)
    assert isinstance(Expr.new_and(column("a"), column("b")), Expr)
