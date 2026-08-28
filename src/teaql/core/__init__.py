from .value import Value, DataType, Timestamp
from .entity import BaseEntityData, EntityKey, EntityChangeSet, EntityRoot
from .expr import (
    Expr, ExprBuilder, BinaryOp, ExprFunction,
    ColumnExpr, ValueExpr, FunctionExpr, BinaryExpr,
    SubQueryExpr, BetweenExpr, IsNullExpr, IsNotNullExpr,
    AndExpr, OrExpr, NotExpr
)
from .query import (
    SelectQuery, SortDirection, OrderBy, Aggregate, AggregateFunction,
    Slice, RelationLoad, RawSqlProjection, ObjectGroupBy, FacetRequest,
    AggregationCacheOptions, StreamConfig, NamedExpr
)
from .mutation import (
    InsertCommand, UpdateCommand, DeleteCommand, RecoverCommand,
    BatchInsertCommand, BatchUpdateCommand, TraceNode,
    InsertCommand, UpdateCommand, DeleteCommand, RecoverCommand,
    BatchInsertCommand, BatchUpdateCommand, MutationRequest
)
from .graph import GraphNode

from .meta import EntityDescriptor, PropertyDescriptor
from .list import SmartList, TeaQLPage
from .eval import LoadState, EvalResult
from .safe_expression import SafeExpression
from .xls import XlsWorkbook, XlsPage, XlsBlock, XlsBlockBuildContext

__all__ = [
    "Value", "DataType", "Timestamp",
    "BaseEntityData", "EntityKey", "EntityChangeSet", "EntityRoot",
    "Expr", "ExprBuilder", "BinaryOp", "ExprFunction",
    "SelectQuery", "SortDirection", "OrderBy", "Aggregate", "AggregateFunction",
    "Slice", "RelationLoad", "RawSqlProjection", "ObjectGroupBy", "FacetRequest",
    "AggregationCacheOptions", "StreamConfig", "NamedExpr",
    "InsertCommand", "UpdateCommand", "DeleteCommand", "RecoverCommand",
    "BatchInsertCommand", "BatchUpdateCommand", "TraceNode",
    "InsertCommand", "UpdateCommand", "DeleteCommand", "RecoverCommand",
    "BatchInsertCommand", "BatchUpdateCommand", "MutationRequest",
    "GraphNode",
    "EntityDescriptor", "PropertyDescriptor", "SmartList", "TeaQLPage",
    "LoadState", "EvalResult", "SafeExpression",
    "XlsWorkbook", "XlsPage", "XlsBlock", "XlsBlockBuildContext"
]
import builtins
builtins.uint64 = int
builtins.int64 = int
builtins.string = str
builtins.time = type('time', (), {'Time': str})
builtins.typing = __import__('typing')
builtins.decimal = __import__('decimal')
TypeU64 = "U64"
TypeI64 = "I64"
TypeText = "Text"
TypeTimestamp = "Timestamp"
TypeDecimal = "Decimal"
TypeJson = "Json"
TypeBool = "Bool"
TypeDate = "Date"
def NewInsertCommand(entity: str):
    return InsertCommand(entity=entity)

def NewUpdateCommand(entity: str, id_val):
    return UpdateCommand(entity=entity, id=Value.from_any(id_val))
