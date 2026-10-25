"""Metadata-owned native scalar restoration, never text-content guessing."""
from teaql.core.expr import ColumnExpr, ExprFunction, FunctionExpr
from teaql.core.query import AggregateFunction
from teaql.core.value import DataType


def normalize_loaded_booleans(rows, descriptor, query=None):
    properties = {prop.name: prop for prop in descriptor.properties
                  if prop.property_type == DataType.Bool
                  or str(prop.property_type).lower() in ("bool", "boolean")}
    if not properties:
        return
    aliases = set()
    result_fields = {}
    if query is not None:
        aliases.update(aggregate.alias for aggregate in query.aggregates)
        aliases.update(projection.alias for projection in query.expr_projection)
        aliases.update(projection.property_name for projection in query.raw_projections + query.dynamic_properties)
        for aggregate in query.aggregates:
            if aggregate.function in (AggregateFunction.Min, AggregateFunction.Max) and aggregate.field in properties:
                result_fields[aggregate.alias] = properties[aggregate.field]
        for projection in query.expr_projection:
            expression = projection.expr
            argument = (expression.args[0] if isinstance(expression, FunctionExpr) and len(expression.args) == 1
                        and expression.function in (ExprFunction.Min, ExprFunction.Max)
                        else expression if isinstance(expression, ColumnExpr) else None)
            if isinstance(argument, ColumnExpr) and argument.name in properties:
                result_fields[projection.alias] = properties[argument.name]
    for prop in properties.values():
        for name in {prop.name, prop.column_name_val} - aliases:
            result_fields[name] = prop
    for row in rows:
        for name, prop in result_fields.items():
            if name not in row or row[name] is None:
                continue
            value = row[name]
            if type(value) is bool:
                continue
            if type(value) is int and value in (0, 1):
                row[name] = bool(value)
            else:
                raise ValueError(f"invalid loaded Boolean field {descriptor._name}.{prop.name}")
