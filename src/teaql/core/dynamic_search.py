"""Local UI-search input; not a permissive TFP decoder or authorization policy."""
import json
import logging
import math
import re
from copy import deepcopy
from datetime import date
from .expr import Expr
from .query import OrderBy

_LOG = logging.getLogger(__name__)
_OPS = {'$eq', '$ne', '$gt', '$gte', '$lt', '$lte', '$in', '$notIn', '$contains'}


def _reject_json_constant(_):
    raise ValueError('Non-standard JSON number')


def _warning(warning):
    _LOG.warning('%s entity=%s clause=%s fieldPath=%s', warning['code'],
                 warning['entity'], warning['clause'], warning['fieldPath'])


def normalize_dynamic_search(source, entity, models, warn=_warning, max_clauses=100):
    """models and limits come from trusted setup, never the submitted JSON."""
    if type(max_clauses) is not int or max_clauses < 1:
        raise ValueError('Invalid search limit')
    if entity not in models:
        raise ValueError('Unknown search entity')
    try:
        value = json.loads(source, parse_constant=_reject_json_constant) if isinstance(source, str) else source
    except (ValueError, TypeError):
        raise ValueError('Dynamic search requires valid JSON') from None
    if not isinstance(value, dict) or set(value) - {'filter', 'orderBy'}:
        raise ValueError('Unsupported dynamic search input or control')
    filters, orders = value.get('filter', {}), value.get('orderBy', [])
    if not isinstance(filters, dict) or not isinstance(orders, list):
        raise ValueError('Invalid search filter or ordering')
    if len(filters) + len(orders) > max_clauses:
        raise ValueError('Dynamic search exceeds clause limit')
    result, warnings = {'filter': {}, 'orderBy': []}, []

    def field_type(path):
        if not isinstance(path, str):
            raise ValueError('Invalid search field path')
        parts = path.split('.')
        if len(parts) > 16 or any(not p or p.startswith('$') or p in
                                 {'__proto__', 'prototype', 'constructor'} for p in parts):
            raise ValueError('Invalid search field path')
        model = models[entity]
        for part in parts[:-1]:
            target = model['relations'].get(part)
            if target is None:
                return None
            if target not in models:
                raise ValueError('Invalid trusted search relation metadata')
            model = models[target]
        return model['fields'].get(parts[-1])

    def missing(path, clause):
        warnings.append(dict(code='DYNAMIC_SEARCH_UNKNOWN_FIELD', entity=entity,
                             clause=clause, fieldPath=path))

    def scalar(item, kind):
        if item is None:
            return
        valid = False
        if kind in ('integer', 'timestamp'):
            valid = (type(item) in (int, float) and abs(item) <= 9007199254740991
                     and math.isfinite(item) and item == int(item))
        elif kind == 'number':
            valid = type(item) in (int, float) and math.isfinite(item)
        elif kind == 'string':
            valid = isinstance(item, str)
        elif kind == 'boolean':
            valid = type(item) is bool
        elif kind == 'decimal':
            valid = (isinstance(item, str) and re.fullmatch(r'[+-]?[0-9]+(?:\.[0-9]+)?', item) is not None
                     or type(item) in (int, float) and math.isfinite(item))
        elif kind == 'date' and isinstance(item, str) and re.fullmatch(r'\d{4}-\d{2}-\d{2}', item):
            try:
                valid = date.fromisoformat(item).isoformat() == item
            except ValueError:
                pass
        if not valid:
            raise ValueError('Invalid value for known search field')

    for path, predicate in filters.items():
        predicate = predicate if isinstance(predicate, dict) else {'$eq': predicate}
        if len(predicate) != 1 or next(iter(predicate)) not in _OPS:
            raise ValueError('Unsupported or malformed dynamic search operator')
        operator, item = next(iter(predicate.items()))
        if operator in ('$in', '$notIn') and (not isinstance(item, list) or len(item) > 1000):
            raise ValueError('Invalid or oversized search value list')
        kind = field_type(path)
        if kind is None:
            missing(path, 'FILTER')
            continue
        if operator == '$contains' and kind != 'string':
            raise ValueError('String operator requires a string field')
        if isinstance(item, list):
            if operator not in ('$in', '$notIn'):
                raise ValueError('Unexpected search value list')
            for element in item:
                scalar(element, kind)
        else:
            scalar(item, kind)
        result['filter'][path] = deepcopy(predicate)
    for order in orders:
        if (not isinstance(order, dict) or set(order) != {'field', 'direction'}
                or order['direction'] not in ('asc', 'desc')):
            raise ValueError('Invalid dynamic search ordering')
        if field_type(order['field']) is None:
            missing(order['field'], 'ORDER_BY')
        else:
            result['orderBy'].append(dict(order))
    for warning in warnings:
        warn(dict(warning))
    return result, warnings


def merge_dynamic_search(base, source, models, filter_binding, order_binding, warn=_warning):
    """Bindings are trusted native-API adapters; preserve the original scoped request."""
    search, warnings = normalize_dynamic_search(source, base.entity, models, lambda _: None)
    filters = [filter_binding(path, predicate) for path, predicate in search['filter'].items()]
    orders = [order_binding(order['field'], order['direction']) for order in search['orderBy']]
    if any(not isinstance(expr, Expr) for expr in filters) or any(not isinstance(order, OrderBy) for order in orders):
        raise ValueError('Invalid trusted search binding')
    query = deepcopy(base)
    for expr in filters:
        query.filter_expr = Expr.new_and(query.filter_expr, expr) if query.filter_expr is not None else expr
    query.order_by_items.extend(orders)
    for warning in warnings:
        warn(dict(warning))
    return query, warnings
