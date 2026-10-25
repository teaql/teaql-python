"""Behavioral vectors mirrored from conformance; no provider mocks certify SQLite."""
from decimal import Decimal
import json
from pathlib import Path

import pytest

from teaql.core.list import SmartList, group_by, identity_map, ids, map_by_id, versions

VECTORS = json.loads((Path(__file__).parents[1] / 'fixtures/smart-list-semantics.json').read_text())


def source_list():
    values = VECTORS['metadata']
    return SmartList(VECTORS['transform']['rows'], total_count=VECTORS['transform']['total'],
                     aggregations=values['aggregations'], summary=values['summary'],
                     facets={name: SmartList(rows) for name, rows in values['facets'].items()})


@pytest.mark.parametrize('case', VECTORS['states'], ids=lambda case: case['name'])
def test_state_and_exact_count(case):
    result = (SmartList(case['rows'], total_count=case['total'])
              if case['loaded'] else SmartList.empty())
    assert list(result) == case['rows']
    assert result.is_loaded is case['loaded']
    assert result.total_count == case['total']
    assert result.total_count_or_len() == (len(result) if case['total'] is None else case['total'])
    assert result.total_count == case['total'], 'fallback must not manufacture exact count'


@pytest.mark.parametrize('value', [-1, 1.5, float('nan'), float('inf'), True, '3'])
def test_invalid_count_is_rejected(value):
    with pytest.raises(ValueError, match='exact non-negative integer'):
        SmartList(total_count=value)


def test_map_preserves_query_metadata_and_recursively_isolates_mutations():
    source = source_list()
    decimal = Decimal(VECTORS['metadata']['decimal']['value'])
    source.aggregations['decimal'] = decimal
    mapped = source.map(lambda item: item * 10)
    assert mapped == VECTORS['transform']['mapTimesTen']
    assert mapped.total_count == source.total_count and mapped.is_loaded
    assert mapped.aggregations == source.aggregations
    assert mapped.summary == source.summary and mapped.facets == source.facets
    assert mapped.aggregations['decimal'] == decimal
    assert mapped.aggregations['nullable'] is None and 'missing' not in mapped.aggregations

    mapped.aggregations['nested']['values'].append(99)
    mapped.summary['nested']['values'].append(99)
    mapped.facets['status'][0]['count'] = 99
    mapped.facets['status'].summary['new'] = True
    mapped.facets.pop('empty')
    assert source.aggregations['nested']['values'] == [1, 2]
    assert source.summary['nested']['values'] == [3]
    assert source.facets['status'][0]['count'] == 3
    assert source.facets['status'].summary == {} and 'empty' in source.facets


def test_constructor_owns_metadata_and_native_conversion_owns_positions():
    metadata = {'nested': [1]}
    facet = SmartList([{'values': [2]}])
    source = SmartList([1, 2], aggregations=metadata, facets={'nested': facet})
    metadata['nested'].append(3)
    facet[0]['values'].append(4)
    native = source.into_vec()
    native[0] = 9
    assert source == [1, 2]
    assert source.aggregations == {'nested': [1]}
    assert source.facets['nested'][0] == {'values': [2]}


def test_cardinality_changing_derivations_clear_source_statistics_even_if_rows_match():
    source = source_list()
    filtered = source.filter(lambda item: item % 2 == 1)
    expanded = source.flat_map(lambda item: [item, item])
    assert filtered == VECTORS['transform']['filterOdd']
    assert expanded == VECTORS['transform']['flatMapTwice']
    for result in (filtered, expanded, source.filter(lambda item: True)):
        assert result.total_count is None
        assert result.aggregations == result.summary == result.facets == {}
        assert result.is_loaded
    assert source.total_count == 9 and len(source) == 3
    for result in (SmartList.empty().map(str), SmartList.empty().filter(bool),
                   SmartList.empty().flat_map(lambda item: [item])):
        assert not result.is_loaded


def test_merge_duplicate_positions_index_group_and_in_place_snapshot():
    case = VECTORS['merge']
    source = SmartList(case['target'], total_count=9, summary={'original': True})
    source.merge_by(case['incoming'], lambda item: item['key'])
    assert source == case['expected']
    assert source.total_count == 9 and source.summary == {'original': True}
    index = identity_map(source, lambda item: item['key'])
    assert index['a'] == {'key': 'a', 'value': 4}
    assert group_by(source, lambda item: item['key'])['a'] == [source[0], source[1]]
    source.retain(lambda item: item['key'] == 'a')
    assert len(source) == 2 and source.total_count == 9
    assert identity_map(SmartList([1, 2, 1])) == {1: 1, 2: 2}


def test_ids_versions_and_missing_id_indexing():
    case = VECTORS['identity']
    source = SmartList(case['rows'])
    assert ids(source) == case['ids'] and versions(source) == case['versions']
    index = map_by_id(source)
    assert None not in index and len(index) == 4
    assert [index[key] for key in (0, 1, '1', '')] == [source[i] for i in case['indexedPositions']]


def test_safe_access_and_facets_transfer():
    source = source_list()
    assert all(source.get(index) is None for index in VECTORS['transform']['safeMissingIndexes'])
    assert source.first() == 1 and source.last() == 3
    assert SmartList().first() is None and SmartList().last() is None
    assert source.facet('missing') is None
    assert source.facet('empty') == [] and source.facet('empty').is_loaded
    assert source.remove_facet('missing') is None
    removed = source.remove_facet('empty')
    assert removed == [] and source.facet('empty') is None
    taken = source.take_facets()
    assert 'status' in taken and source.facets == {}


def test_loaded_state_has_no_new_public_write_entry():
    with pytest.raises(AttributeError):
        SmartList().is_loaded = False
    with pytest.raises(TypeError):
        SmartList(is_loaded=False)
