from enum import Enum, auto
from typing import List, Optional, Any, Union
from dataclasses import dataclass
from .value import Value

class BinaryOp(Enum):
    Eq = auto()
    Ne = auto()
    Gt = auto()
    Gte = auto()
    Lt = auto()
    Lte = auto()
    Like = auto()
    NotLike = auto()
    In = auto()
    NotIn = auto()
    InLarge = auto()
    NotInLarge = auto()

class ExprFunction(Enum):
    Soundex = auto()
    Gbk = auto()
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

class Expr:
    @staticmethod
    def eq(field: str, value: Any) -> 'Expr':
        return BinaryExpr(ExprBuilder.column(field), BinaryOp.Eq, ExprBuilder.value(value) if not isinstance(value, Expr) else value)
    @staticmethod
    def ne(field: str, value: Any) -> 'Expr':
        return BinaryExpr(ExprBuilder.column(field), BinaryOp.Ne, ExprBuilder.value(value) if not isinstance(value, Expr) else value)
    @staticmethod
    def gt(field: str, value: Any) -> 'Expr':
        return BinaryExpr(ExprBuilder.column(field), BinaryOp.Gt, ExprBuilder.value(value) if not isinstance(value, Expr) else value)
    @staticmethod
    def gte(field: str, value: Any) -> 'Expr':
        return BinaryExpr(ExprBuilder.column(field), BinaryOp.Gte, ExprBuilder.value(value) if not isinstance(value, Expr) else value)
    @staticmethod
    def lt(field: str, value: Any) -> 'Expr':
        return BinaryExpr(ExprBuilder.column(field), BinaryOp.Lt, ExprBuilder.value(value) if not isinstance(value, Expr) else value)
    @staticmethod
    def lte(field: str, value: Any) -> 'Expr':
        return BinaryExpr(ExprBuilder.column(field), BinaryOp.Lte, ExprBuilder.value(value) if not isinstance(value, Expr) else value)
    @staticmethod
    def like(field: str, value: Any) -> 'Expr':
        return BinaryExpr(ExprBuilder.column(field), BinaryOp.Like, ExprBuilder.value(value) if not isinstance(value, Expr) else value)
    @staticmethod
    def not_like(field: str, value: Any) -> 'Expr':
        return BinaryExpr(ExprBuilder.column(field), BinaryOp.NotLike, ExprBuilder.value(value) if not isinstance(value, Expr) else value)

    @staticmethod
    def new_and(left: 'Expr', right: 'Expr') -> 'Expr':
        return AndExpr([left, right])


@dataclass
class ColumnExpr(Expr):
    name: str

@dataclass
class ValueExpr(Expr):
    value: Value

@dataclass
class FunctionExpr(Expr):
    function: ExprFunction
    args: List[Expr]

@dataclass
class BinaryExpr(Expr):
    left: Expr
    op: BinaryOp
    right: Expr

@dataclass
class SubQueryExpr(Expr):
    left: Expr
    op: BinaryOp
    entity: Any  # EntityDescriptor
    query: Any   # SelectQuery

@dataclass
class BetweenExpr(Expr):
    expr: Expr
    lower: Expr
    upper: Expr

@dataclass
class IsNullExpr(Expr):
    expr: Expr

@dataclass
class IsNotNullExpr(Expr):
    expr: Expr

@dataclass
class AndExpr(Expr):
    exprs: List[Expr]

@dataclass
class OrExpr(Expr):
    exprs: List[Expr]

@dataclass
class NotExpr(Expr):
    expr: Expr

class ExprBuilder:
    @staticmethod
    def column(name: str) -> Expr:
        return ColumnExpr(name)

    @staticmethod
    def value(value: Any) -> Expr:
        return ValueExpr(Value.from_any(value))

    @staticmethod
    def function(function: ExprFunction, args: List[Expr]) -> Expr:
        return FunctionExpr(function, args)

    @staticmethod
    def soundex(expr: Expr) -> Expr:
        return ExprBuilder.function(ExprFunction.Soundex, [expr])

    @staticmethod
    def gbk(expr: Expr) -> Expr:
        return ExprBuilder.function(ExprFunction.Gbk, [expr])

    @staticmethod
    def count_all() -> Expr:
        return ExprBuilder.function(ExprFunction.Count, [])

    @staticmethod
    def count_expr(expr: Expr) -> Expr:
        return ExprBuilder.function(ExprFunction.Count, [expr])

    @staticmethod
    def sum_expr(expr: Expr) -> Expr:
        return ExprBuilder.function(ExprFunction.Sum, [expr])

    @staticmethod
    def avg_expr(expr: Expr) -> Expr:
        return ExprBuilder.function(ExprFunction.Avg, [expr])

    @staticmethod
    def min_expr(expr: Expr) -> Expr:
        return ExprBuilder.function(ExprFunction.Min, [expr])

    @staticmethod
    def max_expr(expr: Expr) -> Expr:
        return ExprBuilder.function(ExprFunction.Max, [expr])

    @staticmethod
    def stddev_expr(expr: Expr) -> Expr:
        return ExprBuilder.function(ExprFunction.Stddev, [expr])

    @staticmethod
    def stddev_pop_expr(expr: Expr) -> Expr:
        return ExprBuilder.function(ExprFunction.StddevPop, [expr])

    @staticmethod
    def var_samp_expr(expr: Expr) -> Expr:
        return ExprBuilder.function(ExprFunction.VarSamp, [expr])

    @staticmethod
    def var_pop_expr(expr: Expr) -> Expr:
        return ExprBuilder.function(ExprFunction.VarPop, [expr])

    @staticmethod
    def bit_and_expr(expr: Expr) -> Expr:
        return ExprBuilder.function(ExprFunction.BitAnd, [expr])

    @staticmethod
    def bit_or_expr(expr: Expr) -> Expr:
        return ExprBuilder.function(ExprFunction.BitOr, [expr])

    @staticmethod
    def bit_xor_expr(expr: Expr) -> Expr:
        return ExprBuilder.function(ExprFunction.BitXor, [expr])


def column(name: str) -> Expr:
    return ExprBuilder.column(name)

def value(val: Any) -> Expr:
    return ExprBuilder.value(val)

def function(func: ExprFunction, args: List[Expr]) -> Expr:
    return ExprBuilder.function(func, args)

def soundex(expr: Expr) -> Expr:
    return ExprBuilder.soundex(expr)

def gbk(expr: Expr) -> Expr:
    return ExprBuilder.gbk(expr)

def count_all() -> Expr:
    return ExprBuilder.count_all()

def count_expr(expr: Expr) -> Expr:
    return ExprBuilder.count_expr(expr)

def sum_expr(expr: Expr) -> Expr:
    return ExprBuilder.sum_expr(expr)

def avg_expr(expr: Expr) -> Expr:
    return ExprBuilder.avg_expr(expr)

def min_expr(expr: Expr) -> Expr:
    return ExprBuilder.min_expr(expr)

def max_expr(expr: Expr) -> Expr:
    return ExprBuilder.max_expr(expr)

def stddev_expr(expr: Expr) -> Expr:
    return ExprBuilder.stddev_expr(expr)

def stddev_pop_expr(expr: Expr) -> Expr:
    return ExprBuilder.stddev_pop_expr(expr)

def var_samp_expr(expr: Expr) -> Expr:
    return ExprBuilder.var_samp_expr(expr)

def var_pop_expr(expr: Expr) -> Expr:
    return ExprBuilder.var_pop_expr(expr)

def bit_and_expr(expr: Expr) -> Expr:
    return ExprBuilder.bit_and_expr(expr)

def bit_or_expr(expr: Expr) -> Expr:
    return ExprBuilder.bit_or_expr(expr)

def bit_xor_expr(expr: Expr) -> Expr:
    return ExprBuilder.bit_xor_expr(expr)

def binary(left: Expr, op: BinaryOp, right: Expr) -> Expr:
    return BinaryExpr(left, op, right)

def eq(field: str, val: Any) -> Expr:
    return Expr.eq(field, val)

def ne(field: str, val: Any) -> Expr:
    return Expr.ne(field, val)

def gt(field: str, val: Any) -> Expr:
    return Expr.gt(field, val)

def gte(field: str, val: Any) -> Expr:
    return Expr.gte(field, val)

def lt(field: str, val: Any) -> Expr:
    return Expr.lt(field, val)

def lte(field: str, val: Any) -> Expr:
    return Expr.lte(field, val)

def like(field: str, val: Any) -> Expr:
    return Expr.like(field, val)

def not_like(field: str, val: Any) -> Expr:
    return Expr.not_like(field, val)

def contain(field: str, val: Any) -> Expr:
    return Expr.like(field, f"%{val}%")

def not_contain(field: str, val: Any) -> Expr:
    return Expr.not_like(field, f"%{val}%")

def begin_with(field: str, val: Any) -> Expr:
    return Expr.like(field, f"{val}%")

def not_begin_with(field: str, val: Any) -> Expr:
    return Expr.not_like(field, f"{val}%")

def end_with(field: str, val: Any) -> Expr:
    return Expr.like(field, f"%{val}")

def not_end_with(field: str, val: Any) -> Expr:
    return Expr.not_like(field, f"%{val}")

def sound_like(field: str, val: Any) -> Expr:
    return eq(soundex(column(field)), soundex(value(val)))

def in_list(field: str, vals: List[Any]) -> Expr:
    return BinaryExpr(column(field), BinaryOp.In, value(vals))

def not_in_list(field: str, vals: List[Any]) -> Expr:
    return BinaryExpr(column(field), BinaryOp.NotIn, value(vals))

def in_large(field: str, vals: List[Any]) -> Expr:
    return BinaryExpr(column(field), BinaryOp.InLarge, value(vals))

def not_in_large(field: str, vals: List[Any]) -> Expr:
    return BinaryExpr(column(field), BinaryOp.NotInLarge, value(vals))

def is_null(expr: Expr) -> Expr:
    return IsNullExpr(expr)

def is_not_null(expr: Expr) -> Expr:
    return IsNotNullExpr(expr)

def between(expr: Expr, lower: Expr, upper: Expr) -> Expr:
    return BetweenExpr(expr, lower, upper)

def compare_columns(left: str, op: BinaryOp, right: str) -> Expr:
    return BinaryExpr(column(left), op, column(right))

def subquery(left: Expr, op: BinaryOp, entity: Any, query: Any) -> Expr:
    return SubQueryExpr(left, op, entity, query)

def in_subquery(left: Expr, entity: Any, query: Any) -> Expr:
    return subquery(left, BinaryOp.In, entity, query)

def not_in_subquery(left: Expr, entity: Any, query: Any) -> Expr:
    return subquery(left, BinaryOp.NotIn, entity, query)

def negate(expr: Expr) -> Expr:
    return NotExpr(expr)

def and_expr(left: Expr, right: Expr) -> Expr:
    return Expr.new_and(left, right)

def or_expr(left: Expr, right: Expr) -> Expr:
    return OrExpr([left, right])

def and_(*exprs: Expr) -> Expr:
    return AndExpr(list(exprs))

def or_(*exprs: Expr) -> Expr:
    return OrExpr(list(exprs))

