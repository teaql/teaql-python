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
    pass

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
