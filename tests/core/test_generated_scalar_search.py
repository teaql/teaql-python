from copy import deepcopy
import pytest
from teaql.core.dynamic_search import merge_generated_scalar_search
from teaql.core.expr import Expr, column, contain, eq, gte, is_null, is_not_null
from teaql.core.query import OrderBy, SelectQuery

MODELS = {
    'Invoice': {'fields': {'referenceCode': 'string', 'reference_code': 'string',
                           'totalAmount': 'decimal', 'active': 'boolean', 'payload': 'unsupported'},
                'query_fields': {'referenceCode': 'reference_code', 'reference_code': 'reference_code',
                                 'totalAmount': 'total_amount', 'active': 'active', 'payload': 'payload'},
                'relations': {'owner': 'Owner'}},
    'Owner': {'fields': {'name': 'string'}, 'query_fields': {'name': 'name'}, 'relations': {}},
}


def test_generated_search_merges_all_siblings_without_mutating_scope_or_input():
    base = SelectQuery('Invoice').filter(Expr.eq('tenant', 1)).limit(4)
    base.comment('load scoped invoices').purpose('verify generated search')
    base.order_by_items.append(OrderBy.asc('id'))
    before = deepcopy(base)
    source = {'filter': {'referenceCode': {'$contains': 'KEEP'}, 'totalAmount': {'$gte': '50.00'},
                         'active': True, 'removed': 'PRIVATE'},
              'orderBy': [{'field': 'referenceCode', 'direction': 'desc'}]}
    recorded = []
    query, warnings = merge_generated_scalar_search(base, source, MODELS, recorded.append)
    source['filter']['referenceCode']['$contains'] = 'changed'
    assert base == before
    assert query.slice == base.slice
    assert query.comment_text == base.comment_text and query.purpose_text == base.purpose_text
    assert query.order_by_items == [OrderBy.asc('id'), OrderBy.desc('reference_code')]
    assert 'reference_code' in repr(query.filter_expr) and 'total_amount' in repr(query.filter_expr)
    expected = Expr.new_and(Expr.new_and(Expr.new_and(base.filter_expr,
        contain('reference_code', 'KEEP')), gte('total_amount', '50.00')), eq('active', True))
    assert query.filter_expr == expected
    assert len(recorded) == len(warnings) == 1 and 'PRIVATE' not in repr(recorded)


def test_known_relation_path_fails_atomically_without_dropping_it_or_emitting_partial_warnings():
    base = SelectQuery('Invoice').filter(eq('tenant', 1))
    before = deepcopy(base)
    warnings = []
    with pytest.raises(ValueError, match='trusted relation binding'):
        merge_generated_scalar_search(base, {'filter': {'removed': 'secret', 'owner.name': 'Ada'}}, MODELS, warnings.append)
    assert base == before and warnings == []


@pytest.mark.parametrize('operator, expected', [('$eq', is_null(column('reference_code'))),
                                              ('$ne', is_not_null(column('reference_code')))])
def test_null_uses_native_sql_null_predicates(operator, expected):
    query, _ = merge_generated_scalar_search(SelectQuery('Invoice'),
        {'filter': {'referenceCode': {operator: None}}}, MODELS)
    assert query.filter_expr == expected


@pytest.mark.parametrize('source', [
    {'filter': {'active': 'true'}}, {'filter': {'totalAmount': {'$contains': '1'}}},
    {'filter': {'referenceCode': {'$rawSQL': 'true'}}}, {'context': {'actor': 'admin'}},
    {'filter': {'payload': None}}, {'orderBy': [{'field': 'payload', 'direction': 'asc'}]},
    {'filter': {'referenceCode': {'$contains': None}}}, {'filter': {'totalAmount': {'$gt': None}}},
])
def test_invalid_known_values_and_trusted_controls_stay_fatal(source):
    base = SelectQuery('Invoice').filter(eq('tenant', 1))
    before = deepcopy(base)
    with pytest.raises(ValueError):
        merge_generated_scalar_search(base, source, MODELS)
    assert base == before
