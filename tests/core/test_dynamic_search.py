import json
import pytest
from teaql.core.dynamic_search import normalize_dynamic_search, merge_dynamic_search
from teaql.core.query import SelectQuery, OrderBy
from teaql.core.expr import Expr

MODELS = {
    'Order': {'fields': {'id': 'integer', 'name': 'string', 'amount': 'decimal', 'tenant': 'integer'},
              'relations': {'customer': 'Customer'}},
    'Customer': {'fields': {'name': 'string'}, 'relations': {}},
}


def test_unknown_clauses_are_atomic_and_value_free():
    recorded = []
    search, warnings = normalize_dynamic_search({'filter': {
        'removed': 'SECRET', 'missing.name': 'SECRET', 'customer.removed': 'SECRET',
        'name': 'valid', 'customer.name': {'$eq': 'Ada'}},
        'orderBy': [{'field': 'removed', 'direction': 'asc'}, {'field': 'id', 'direction': 'desc'}]},
        'Order', MODELS, recorded.append)
    assert search['filter'] == {'name': {'$eq': 'valid'}, 'customer.name': {'$eq': 'Ada'}}
    assert search['orderBy'] == [{'field': 'id', 'direction': 'desc'}]
    assert len(warnings) == 4
    assert all(w['code'] == 'DYNAMIC_SEARCH_UNKNOWN_FIELD' and w['entity'] == 'Order' for w in warnings)
    assert 'SECRET' not in json.dumps(recorded)


@pytest.mark.parametrize('source', ['{', '[]', 'null', '{} {}', '{"tenant":1}', '{"hardLimit":1}',
                                    '{"filter":{"removed":NaN}}',
                                    {'filter': {'name': {'$invented': 1}}},
                                    {'filter': {'id': True}}, {'filter': {'id': 1.5}},
                                    {'filter': {'amount': 'NaN'}}])
def test_fatal_inputs_are_not_schema_drift(source):
    with pytest.raises(ValueError):
        normalize_dynamic_search(source, 'Order', MODELS)


def test_native_composition_preserves_scope_limit_and_order():
    base = SelectQuery('Order').filter(Expr.eq('tenant', 1)).limit(10)
    base.order_by_items.append(OrderBy.asc('id'))
    original = repr(base)
    query, warnings = merge_dynamic_search(base, {'filter': {'name': 'valid', 'removed': 'secret'}}, MODELS,
        lambda path, predicate: Expr.eq(path, predicate['$eq']),
        lambda path, direction: OrderBy.asc(path) if direction == 'asc' else OrderBy.desc(path), lambda _: None)
    assert query.filter_expr == Expr.new_and(base.filter_expr, Expr.eq('name', 'valid'))
    assert query.slice == base.slice
    assert query.order_by_items == base.order_by_items
    assert repr(base) == original
    assert len(warnings) == 1


def test_date_timestamp_decimal_validation():
    models = {'Entry': {'fields': {'date': 'date', 'created': 'timestamp', 'amount': 'decimal'}, 'relations': {}}}
    search, _ = normalize_dynamic_search({'filter': {'date': '2024-02-29', 'created': 1709164800000,
                                                   'amount': '9007199254740993.01'}}, 'Entry', models)
    assert search['filter']['amount'] == {'$eq': '9007199254740993.01'}
    for filters in [{'date': '2025-02-29'}, {'created': '2024-02-29'}]:
        with pytest.raises(ValueError):
            normalize_dynamic_search({'filter': filters}, 'Entry', models)


def test_fatal_sibling_does_not_publish_warnings():
    warnings = []
    with pytest.raises(ValueError):
        normalize_dynamic_search({'filter': {'removed': 'secret', 'id': 'bad'}}, 'Order', MODELS, warnings.append)
    assert warnings == []


def test_shared_json_number_and_decimal_lexical_boundaries():
    result, _ = normalize_dynamic_search('{"filter":{"id":1.0}}', 'Order', MODELS)
    assert result['filter']['id'] == {'$eq': 1.0}
    with pytest.raises(ValueError):
        normalize_dynamic_search({'filter': {'amount': '١٢'}}, 'Order', MODELS)
