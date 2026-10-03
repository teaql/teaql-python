"""Shared frozen SQL vectors are pure algorithm evidence, not generated proof."""
import json
from pathlib import Path

import pytest

from teaql.core.mutation import TraceNode
from teaql.core.trace import canonical_sql_trace_path, trace_intent


CASES = json.loads((Path(__file__).parents[1] / 'fixtures' / 'sql-trace-path-v1.json').read_text())['cases']


def decode(node):
    return TraceNode(kind=node['kind'][0].lower() + node['kind'][1:], name=node['name'],
                     entity_id=node['entityId'], comment=node['detail'])


def logical(node):
    return {'kind': node.kind[0].upper() + node.kind[1:], 'name': node.name,
            'entityId': node.entity_id, 'detail': node.comment}


@pytest.mark.parametrize('case', CASES, ids=[case['id'] for case in CASES])
def test_frozen_sql_path(case):
    source = [decode(node) for node in case['source']]
    assert trace_intent(source) == case['expectedIntent']
    result = canonical_sql_trace_path(source, case['backend'], case['operation'])
    assert [logical(node) for node in result] == case['expectedPath']
    assert canonical_sql_trace_path(result, case['backend'], case['operation']) == result
    assert [logical(node) for node in source] == case['source']
    if result:
        result[0].name = 'consumer-owned change'
        assert [logical(node) for node in source] == case['source']


def test_derived_query_origin_is_owned_and_survives_intent_changes():
    from teaql.core.query import SelectQuery
    from teaql.data_service import QueryRequest
    request = QueryRequest(SelectQuery('CustomerOrder'), _comment='load graph', _purpose='render graph')
    derived = request.with_query(SelectQuery('Payment')).comment('updated intent').purpose('updated purpose')
    assert derived.query.entity == 'Payment' and derived.origin_entity == 'CustomerOrder'
    with pytest.raises(AttributeError):
        derived.origin_entity = 'Shipment'


def test_readback_path_keeps_origin_not_child_and_does_not_mutate_write():
    from copy import deepcopy
    from teaql.core.trace import physical_readback_path
    source = canonical_sql_trace_path([
        TraceNode(kind='auditReason', name='CustomerOrder', entity_id=7, comment='submit'),
        TraceNode(kind='entity', name='PaymentAttempt', entity_id=7),
    ], 'sqlite', 'update')
    before = deepcopy(source)
    read = physical_readback_path(source)
    assert [(n.kind, n.name, n.comment) for n in read] == [
        ('operation', 'CustomerOrder', 'query'), ('request', 'CustomerOrder', ''),
        ('provider', 'sqlite', ''), ('sql', 'select', '')]
    read[0].name = 'consumer change'
    assert source == before


@pytest.mark.parametrize('kind', ['query', 'mutation'])
def test_untyped_trace_is_rejected_without_echoing_payload(kind):
    from teaql.core.mutation import InsertCommand, MutationRequest
    from teaql.core.query import SelectQuery
    from teaql.data_service import QueryRequest
    opaque = {'comment': 'SENSITIVE-FIXTURE-CANARY'}
    request = (QueryRequest(SelectQuery('CustomerOrder'), [opaque], _comment='load graph', _purpose='render graph')
               if kind == 'query' else MutationRequest(
                   InsertCommand('CustomerOrder', trace_chain=[opaque]), comment='save graph'))
    with pytest.raises(TypeError, match='typed TraceNode') as caught:
        request.validate()
    assert 'SENSITIVE-FIXTURE-CANARY' not in str(caught.value)
