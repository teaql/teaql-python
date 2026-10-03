import pytest

from teaql.core.entity import _QueryProjectionSnapshot


def test_query_projections_are_owned_and_not_entity_attributes():
    source = {'id': 7, 'order_number': 'private', 'orderNumber': 'private',
              'items': [{'id': 8}], 'summary': {'counts': [2]}, 'save': 3}
    snapshot = _QueryProjectionSnapshot(source, ('id', 'order_number', 'orderNumber', 'items'))
    source['summary']['counts'].append(99)
    returned = snapshot.get('summary')
    returned['counts'].append(100)
    assert snapshot.get('summary') == {'counts': [2]}
    assert snapshot.get('save') == 3
    assert not hasattr(snapshot, 'save')
    for field in ('id', 'order_number', 'orderNumber', 'items'):
        assert not snapshot.contains(field)
        with pytest.raises(KeyError):
            snapshot.get(field)
    assert 'private' not in repr(snapshot)


def test_query_projection_missing_is_distinct_from_null_and_zero():
    snapshot = _QueryProjectionSnapshot({'zero': 0, 'null': None}, ())
    assert snapshot.contains('zero') and snapshot.get('zero') == 0
    assert snapshot.contains('null') and snapshot.get('null') is None
    assert not snapshot.contains('missing')
    with pytest.raises(KeyError):
        snapshot.get('missing')
