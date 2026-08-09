from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, Tuple
from teaql.core.query import (
    SelectQuery, OrderBy, SortDirection, Aggregate, AggregateFunction
)
from teaql.core.mutation import (
    InsertCommand, UpdateCommand, DeleteCommand, RecoverCommand,
    BatchInsertCommand, BatchUpdateCommand, MutationRequest
)
from teaql.core.expr import (
    Expr, ColumnExpr, ValueExpr, FunctionExpr, BinaryExpr, SubQueryExpr,
    BetweenExpr, IsNullExpr, IsNotNullExpr, AndExpr, OrExpr, NotExpr,
    BinaryOp, ExprFunction
)
from teaql.core.value import Value, DataType
from teaql.core.meta import EntityDescriptor, PropertyDescriptor
from .types import (
    DatabaseKind, CompiledQuery, SqlCompileError,
    UnknownEntityError, UnknownFieldError, EmptyInListError,
    MissingIdPropertyError, MissingVersionPropertyError,
    EmptyMutationError, InvalidRecoverVersionError,
    UnsupportedSchemaTypeError, InvalidFunctionArgumentsError,
    InvalidSubQueryOperatorError
)

SQL_KEYWORDS = {
    "all", "alter", "and", "as", "asc", "between", "by", "case", "create", "delete", "desc",
    "distinct", "drop", "exists", "false", "from", "group", "having", "in", "insert", "into", "is",
    "join", "like", "limit", "not", "null", "offset", "on", "or", "order", "select", "set",
    "table", "true", "type", "union", "update", "values", "where",
}

def is_wrapped_identifier(ident: str) -> bool:
    return (ident.startswith('"') and ident.endswith('"')) or \
           (ident.startswith('`') and ident.endswith('`')) or \
           (ident.startswith('[') and ident.endswith(']'))

def needs_quoted_identifier(ident: str) -> bool:
    if not ident or ident.lower() in SQL_KEYWORDS:
        return True
    if not (ident[0] == '_' or ident[0].isalpha()):
        return True
    return any(not (ch == '_' or ch.isalnum()) for ch in ident)

def quote_identifier_if_needed(ident: str, quote: str) -> str:
    if is_wrapped_identifier(ident):
        return ident
    if needs_quoted_identifier(ident):
        escaped = ident.replace(quote, quote + quote)
        return f"{quote}{escaped}{quote}"
    return ident

class SqlDialect(ABC):
    @abstractmethod
    def kind(self) -> DatabaseKind:
        pass

    @abstractmethod
    def quote_ident(self, ident: str) -> str:
        pass

    @abstractmethod
    def placeholder(self, index: int) -> str:
        pass

    def schema_setup_sqls(self) -> List[str]:
        return []

    def schema_type_sql(self, data_type: DataType, property_desc: PropertyDescriptor) -> str:
        if data_type == DataType.Bool: return "BOOLEAN"
        if data_type in (DataType.I64, DataType.U64): return "INTEGER"
        if data_type == DataType.F64: return "REAL"
        if data_type == DataType.Decimal: return "NUMERIC"
        if data_type == DataType.Text: return "VARCHAR(255)"
        if data_type in (DataType.LargeText, DataType.Json, DataType.Date, DataType.Timestamp): return "TEXT"
        raise UnsupportedSchemaTypeError(data_type)

    def column_definition_sql(self, property_desc: PropertyDescriptor) -> str:
        parts = [
            self.quote_ident(getattr(property_desc, 'column_name_val', property_desc.name)),
            self.schema_type_sql(property_desc.property_type, property_desc)
        ]
        is_id = getattr(property_desc, '_is_id', False)
        if is_id:
            parts.append("PRIMARY KEY")
        
        nullable = getattr(property_desc, 'nullable', True)
        if is_id or not nullable:
            parts.append("NOT NULL")
            
        return " ".join(parts)

    def compile_create_table(self, entity: EntityDescriptor) -> str:
        columns = [self.column_definition_sql(p) for p in getattr(entity, 'properties', [])]
        columns_str = ", ".join(columns)
        table_name = getattr(entity, 'table_name_val', entity._name)
        return f"CREATE TABLE IF NOT EXISTS {self.quote_ident(table_name)} ({columns_str})"

    def compile_select(self, entity: EntityDescriptor, query: SelectQuery) -> CompiledQuery:
        params: List[Value] = []
        sql = self.compile_select_sql(entity, query, params)
        return CompiledQuery(sql=sql, params=params, comment=query.comment)

    def compile_select_sql(self, entity: EntityDescriptor, query: SelectQuery, params: List[Value]) -> str:
        if query.raw_sql is not None:
            return query.raw_sql

        projection = self.compile_projection(entity, query, params)
        table_name = getattr(entity, 'table_name_val', entity._name)

        
        sql = f"SELECT {projection} FROM {self.quote_ident(table_name)}"
        where_parts = []
        if query.filter is not None:
            where_parts.append(self.compile_expr(entity, query.filter, params))
        
        if query.search_with_text is not None:
            or_parts = []
            like_value = f"%{query.search_with_text}%"
            for prop in getattr(entity, 'properties', []):
                ptype = getattr(prop, 'property_type', None) or getattr(prop, 'data_type', None)
                if ptype in (DataType.Text, DataType.LargeText, "String", "Text"):
                    params.append(Value.from_any(like_value))
                    or_parts.append(f"{self.quote_ident(prop.column_name_val)} LIKE {self.placeholder(len(params))}")
            if or_parts:
                where_parts.append(f"({' OR '.join(or_parts)})")
                
        where_parts.extend(query.raw_sql_search_criteria)
        if where_parts:
            sql += " WHERE " + " AND ".join(where_parts)
            
        if query.group_by:
            group_by = ", ".join(self.column_sql(entity, field) for field in query.group_by)
            sql += f" GROUP BY {group_by}"
            
        if query.having is not None:
            having_sql = self.compile_expr(entity, query.having, params)
            sql += f" HAVING {having_sql}"
            
        if query.order_by:
            order_by = ", ".join(self.order_by_sql(entity, order, params) for order in query.order_by)
            sql += f" ORDER BY {order_by}"
            
        if query.slice is not None:
            if query.slice.limit is not None:
                sql += f" LIMIT {query.slice.limit}"
            if query.slice.offset > 0:
                sql += f" OFFSET {query.slice.offset}"
                
        return sql

    def compile_insert(self, entity: EntityDescriptor, command: InsertCommand) -> CompiledQuery:
        columns = []
        placeholders = []
        params = []
        for prop in getattr(entity, 'properties', []):
            prop_name = getattr(prop, 'name', None)
            if prop_name in command.values:
                columns.append(self.quote_ident(prop.column_name_val))
                val = Value.from_any(command.values[prop_name])
                if val._data is None:
                    ptype = getattr(prop, 'property_type', None) or getattr(prop, 'data_type', DataType.Text)
                    val = Value.TypedNull(ptype)
                params.append(val)
                placeholders.append(self.placeholder(len(params)))
                
        if not columns:
            raise EmptyMutationError("insert")
            
        table_name = getattr(entity, 'table_name_val', entity._name)
        sql = f"INSERT INTO {self.quote_ident(table_name)} ({', '.join(columns)}) VALUES ({', '.join(placeholders)})"
        return CompiledQuery(sql=sql, params=params)

    def compile_update(self, entity: EntityDescriptor, command: UpdateCommand) -> CompiledQuery:
        id_property = next((p for p in getattr(entity, 'properties', []) if getattr(p, '_is_id', False)), None)
        if not id_property:
            raise MissingIdPropertyError(entity._name)
            
        assignments = []
        params = []
        for prop in getattr(entity, 'properties', []):
            if getattr(prop, '_is_id', False):
                continue
            is_version = getattr(prop, '_is_version', False)
            if is_version and command.expected_version is not None:
                continue
            prop_name = getattr(prop, 'name', None)
            if prop_name in command.values:
                val = Value.from_any(command.values[prop_name])
                if val._data is None:
                    ptype = getattr(prop, 'property_type', None) or getattr(prop, 'data_type', DataType.Text)
                    val = Value.TypedNull(ptype)
                params.append(val)
                assignments.append(f"{self.quote_ident(prop.column_name_val)} = {self.placeholder(len(params))}")
        version_property = next((p for p in getattr(entity, 'properties', []) if getattr(p, '_is_version', False)), None)
        if command.expected_version is not None:
            if not version_property:
                raise MissingVersionPropertyError(entity._name)
            params.append(Value.I64(command.expected_version + 1))
            assignments.append(f"{self.quote_ident(version_property.column_name_val)} = {self.placeholder(len(params))}")
            
        if not assignments:
            raise EmptyMutationError("update")
            
        params.append(command.id)
        predicates = [f"{self.quote_ident(id_property.column_name_val)} = {self.placeholder(len(params))}"]
        
        if command.expected_version is not None:
            params.append(Value.I64(command.expected_version))
            predicates.append(f"{self.quote_ident(version_property.column_name_val)} = {self.placeholder(len(params))}")
            
        table_name = getattr(entity, 'table_name_val', entity._name)
        sql = f"UPDATE {self.quote_ident(table_name)} SET {', '.join(assignments)} WHERE {' AND '.join(predicates)}"
        return CompiledQuery(sql=sql, params=params)
        
    def compile_delete(self, entity: EntityDescriptor, command: DeleteCommand) -> CompiledQuery:
        id_property = next((p for p in getattr(entity, 'properties', []) if getattr(p, 'is_id_val', False) or (callable(getattr(p, 'is_id', None)) and p.is_id())), None)
        if not id_property:
            raise MissingIdPropertyError(entity._name)
            
        params = []
        table_name = getattr(entity, 'table_name_val', entity._name)
        version_property = next((p for p in getattr(entity, 'properties', []) if getattr(p, 'is_version_val', False) or (callable(getattr(p, 'is_version', None)) and p.is_version())), None)
        
        if command.soft_delete:
            if not version_property:
                raise MissingVersionPropertyError(entity._name)
            if command.expected_version is not None:
                params.append(Value.I64(-(command.expected_version + 1)))
            else:
                params.append(Value.I64(-1))
                
            params.append(command.id)
            predicates = [f"{self.quote_ident(id_property.column_name_val)} = {self.placeholder(len(params))}"]
            
            if command.expected_version is not None:
                params.append(Value.I64(command.expected_version))
                predicates.append(f"{self.quote_ident(version_property.column_name_val)} = {self.placeholder(len(params))}")
                
            sql = f"UPDATE {self.quote_ident(table_name)} SET {self.quote_ident(version_property.column_name_val)} = {self.placeholder(1)} WHERE {' AND '.join(predicates)}"
            return CompiledQuery(sql=sql, params=params)
            
        params.append(command.id)
        predicates = [f"{self.quote_ident(id_property.column_name_val)} = {self.placeholder(len(params))}"]
        
        if command.expected_version is not None:
            if not version_property:
                raise MissingVersionPropertyError(entity._name)
            params.append(Value.I64(command.expected_version))
            predicates.append(f"{self.quote_ident(version_property.column_name_val)} = {self.placeholder(len(params))}")
            
        sql = f"DELETE FROM {self.quote_ident(table_name)} WHERE {' AND '.join(predicates)}"
        return CompiledQuery(sql=sql, params=params)
        
    def compile_recover(self, entity: EntityDescriptor, command: RecoverCommand) -> CompiledQuery:
        if command.expected_version >= 0:
            raise InvalidRecoverVersionError(command.expected_version)
            
        id_property = next((p for p in getattr(entity, 'properties', []) if getattr(p, 'is_id_val', False) or (callable(getattr(p, 'is_id', None)) and p.is_id())), None)
        if not id_property:
            raise MissingIdPropertyError(entity._name)
            
        version_property = next((p for p in getattr(entity, 'properties', []) if getattr(p, 'is_version_val', False) or (callable(getattr(p, 'is_version', None)) and p.is_version())), None)
        if not version_property:
            raise MissingVersionPropertyError(entity._name)
            
        params = [
            Value.I64(-command.expected_version + 1),
            command.id,
            Value.I64(command.expected_version)
        ]
        
        table_name = getattr(entity, 'table_name_val', entity._name)
        sql = f"UPDATE {self.quote_ident(table_name)} SET {self.quote_ident(version_property.column_name_val)} = {self.placeholder(1)} WHERE {self.quote_ident(id_property.column_name_val)} = {self.placeholder(2)} AND {self.quote_ident(version_property.column_name_val)} = {self.placeholder(3)}"
        return CompiledQuery(sql=sql, params=params)
        
    def column_sql(self, entity: EntityDescriptor, field: str) -> str:
        prop = next((p for p in getattr(entity, 'properties', []) if getattr(p, 'name', None) == field), None)
        if not prop:
            raise UnknownFieldError(field)
        return self.quote_ident(prop.column_name_val)

    def order_by_sql(self, entity: EntityDescriptor, order_by: OrderBy, params: List[Value]) -> str:
        if order_by.expr is not None:
            field = self.compile_expr(entity, order_by.expr, params)
        else:
            field = self.column_sql(entity, order_by.field_name)
        direction = "ASC" if order_by.direction == SortDirection.Asc else "DESC"
        return f"{field} {direction}"
        
    def select_projection(self, entity: EntityDescriptor, query: SelectQuery, params: List[Value]) -> str:
        def property_projection(p):
            column = self.quote_ident(p.column_name_val)
            return column if p.column_name_val == p.name else f"{column} AS {self.quote_ident(p.name)}"
            
        if not query.projection and not query.expr_projection and not query.raw_projections and not query.dynamic_properties:
            return ", ".join(property_projection(p) for p in getattr(entity, 'properties', []))
            
        parts = []
        for field in query.projection:
            prop = next((p for p in getattr(entity, 'properties', []) if getattr(p, 'name', None) == field), None)
            if not prop:
                raise UnknownFieldError(field)
            parts.append(property_projection(prop))
            
        for proj in query.expr_projection:
            expr = self.compile_expr(entity, proj.expr, params)
            parts.append(f"{expr} AS {self.quote_ident(proj.alias)}")
            
        for proj in query.raw_projections + query.dynamic_properties:
            parts.append(f"{proj.raw_sql_segment} AS {self.quote_ident(proj.property_name)}")
            
        return ", ".join(parts)

    def aggregate_projection(self, entity: EntityDescriptor, query: SelectQuery, params: List[Value]) -> str:
        parts = []
        for field in query.group_by + query.projection:
            column = self.column_sql(entity, field)
            if column not in parts:
                parts.append(column)
                
        for proj in query.expr_projection:
            expr = self.compile_expr(entity, proj.expr, params)
            aliased = f"{expr} AS {self.quote_ident(proj.alias)}"
            if aliased not in parts:
                parts.append(aliased)
                
        for proj in query.raw_projections + query.dynamic_properties:
            aliased = f"{proj.raw_sql_segment} AS {self.quote_ident(proj.property_name)}"
            if aliased not in parts:
                parts.append(aliased)
                
        for agg in query.aggregates:
            field = "*" if agg.function == AggregateFunction.Count and agg.field == "*" else self.column_sql(entity, agg.field)
            func_sql = {
                AggregateFunction.Count: "COUNT",
                AggregateFunction.Sum: "SUM",
                AggregateFunction.Avg: "AVG",
                AggregateFunction.Min: "MIN",
                AggregateFunction.Max: "MAX",
                AggregateFunction.Stddev: "STDDEV",
                AggregateFunction.StddevPop: "STDDEV_POP",
                AggregateFunction.VarSamp: "VAR_SAMP",
                AggregateFunction.VarPop: "VAR_POP",
                AggregateFunction.BitAnd: "BIT_AND",
                AggregateFunction.BitOr: "BIT_OR",
                AggregateFunction.BitXor: "BIT_XOR",
            }[agg.function]
            call = f"{func_sql}({field})"
            parts.append(f"{call} AS {self.quote_ident(agg.alias)}")
            
        return ", ".join(parts)
        
    def compile_projection(self, entity: EntityDescriptor, query: SelectQuery, params: List[Value]) -> str:
        if not query.aggregates:
            return self.select_projection(entity, query, params)
        else:
            return self.aggregate_projection(entity, query, params)
            
    def compile_expr(self, entity: EntityDescriptor, expr: Expr, params: List[Value]) -> str:
        if isinstance(expr, ColumnExpr):
            return self.column_sql(entity, expr.name)
        elif isinstance(expr, ValueExpr):
            params.append(expr.value)
            return self.placeholder(len(params))
        elif isinstance(expr, FunctionExpr):
            return self.compile_function(entity, expr.function, expr.args, params)
        elif isinstance(expr, BinaryExpr):
            if expr.op in (BinaryOp.In, BinaryOp.NotIn, BinaryOp.InLarge, BinaryOp.NotInLarge):
                return self.compile_in(entity, expr.left, expr.op, expr.right, params)
            lhs = self.compile_expr(entity, expr.left, params)
            rhs = self.compile_expr(entity, expr.right, params)
            op_str = {
                BinaryOp.Eq: "=", BinaryOp.Ne: "!=", BinaryOp.Gt: ">", BinaryOp.Gte: ">=",
                BinaryOp.Lt: "<", BinaryOp.Lte: "<=", BinaryOp.Like: "LIKE", BinaryOp.NotLike: "NOT LIKE"
            }[expr.op]
            return f"({lhs} {op_str} {rhs})"
        elif isinstance(expr, SubQueryExpr):
            return self.compile_subquery(entity, expr.left, expr.op, expr.entity, expr.query, params)
        elif isinstance(expr, BetweenExpr):
            e = self.compile_expr(entity, expr.expr, params)
            l = self.compile_expr(entity, expr.lower, params)
            u = self.compile_expr(entity, expr.upper, params)
            return f"({e} BETWEEN {l} AND {u})"
        elif isinstance(expr, IsNullExpr):
            return f"({self.compile_expr(entity, expr.expr, params)} IS NULL)"
        elif isinstance(expr, IsNotNullExpr):
            return f"({self.compile_expr(entity, expr.expr, params)} IS NOT NULL)"
        elif isinstance(expr, AndExpr):
            return self.compile_joined(entity, expr.exprs, "AND", params)
        elif isinstance(expr, OrExpr):
            return self.compile_joined(entity, expr.exprs, "OR", params)
        elif isinstance(expr, NotExpr):
            return f"(NOT {self.compile_expr(entity, expr.expr, params)})"
        return ""

    def compile_function(self, entity: EntityDescriptor, function: ExprFunction, args: List[Expr], params: List[Value]) -> str:
        if function == ExprFunction.Soundex:
            if len(args) != 1: raise InvalidFunctionArgumentsError("SOUNDEX expects exactly one argument")
            return f"SOUNDEX({self.compile_expr(entity, args[0], params)})"
        elif function == ExprFunction.Gbk:
            return self.compile_gbk_function(entity, args, params)
        elif function == ExprFunction.Count and not args:
            return "COUNT(*)"
        else:
            func_map = {
                ExprFunction.Count: "COUNT", ExprFunction.Sum: "SUM", ExprFunction.Avg: "AVG",
                ExprFunction.Min: "MIN", ExprFunction.Max: "MAX", ExprFunction.Stddev: "STDDEV",
                ExprFunction.StddevPop: "STDDEV_POP", ExprFunction.VarSamp: "VAR_SAMP",
                ExprFunction.VarPop: "VAR_POP", ExprFunction.BitAnd: "BIT_AND",
                ExprFunction.BitOr: "BIT_OR", ExprFunction.BitXor: "BIT_XOR"
            }
            if function not in func_map:
                raise InvalidFunctionArgumentsError(f"Unsupported function: {function}")
            if len(args) != 1:
                raise InvalidFunctionArgumentsError(f"{func_map[function]} expects exactly one argument")
            return f"{func_map[function]}({self.compile_expr(entity, args[0], params)})"
            
    def compile_gbk_function(self, entity: EntityDescriptor, args: List[Expr], params: List[Value]) -> str:
        if len(args) != 1:
            raise InvalidFunctionArgumentsError("GBK expects exactly one argument")
        return self.compile_expr(entity, args[0], params)
        
    def compile_subquery(self, entity: EntityDescriptor, left: Expr, op: BinaryOp, sub_entity: EntityDescriptor, query: SelectQuery, params: List[Value]) -> str:
        lhs = self.compile_expr(entity, left, params)
        if op in (BinaryOp.In, BinaryOp.InLarge): operator = "IN"
        elif op in (BinaryOp.NotIn, BinaryOp.NotInLarge): operator = "NOT IN"
        else: raise InvalidSubQueryOperatorError(str(op))
        subquery = self.compile_select_sql(sub_entity, query, params)
        return f"({lhs} {operator} ({subquery}))"
        
    def compile_joined(self, entity: EntityDescriptor, parts: List[Expr], joiner: str, params: List[Value]) -> str:
        compiled = [self.compile_expr(entity, p, params) for p in parts]
        return f"({' '.join([f' {joiner} ']*len(compiled)).join(compiled)})" if len(compiled) == 1 else f"({f' {joiner} '.join(compiled)})"

    def compile_in(self, entity: EntityDescriptor, left: Expr, op: BinaryOp, right: Expr, params: List[Value]) -> str:
        lhs = self.compile_expr(entity, left, params)
        operator = "IN" if op in (BinaryOp.In, BinaryOp.InLarge) else "NOT IN"
        if isinstance(right, ValueExpr) and right.value._type_hint == DataType.Json and isinstance(right.value._data, list):
            values = right.value._data
            if not values:
                raise EmptyInListError()
            placeholders = []
            for v in values:
                val_to_append = v if isinstance(v, Value) else Value.from_any(v)
                params.append(val_to_append)
                placeholders.append(self.placeholder(len(params)))
            return f"({lhs} {operator} ({', '.join(placeholders)}))"
        else:
            rhs = self.compile_expr(entity, right, params)
            return f"({lhs} {operator} ({rhs}))"
