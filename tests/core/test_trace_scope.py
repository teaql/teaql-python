"""Shared graph fixture/token evidence; not generated traversal proof."""
import json
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from teaql.core.entity import EntityKey, EntityRoot
from teaql.core.mutation import InsertCommand, MutationRequest, TraceNode
from teaql.core.trace_scope import TraceScope


CASES = json.loads((Path(__file__).parents[1] / 'fixtures' / 'graph-mutation-lineage-v1.json').read_text())['cases']


def logical(node):
    return {'kind': 'AuditReason', 'name': node.name or node.entity_type,
            'entityId': node.entity_id, 'detail': node.comment}


@pytest.mark.parametrize('case', CASES, ids=[case['id'] for case in CASES])
def test_shared_graph_scope_recovery(case):
    owner, scopes, recovered = object(), {}, {}
    ledger = EntityRoot()
    for node in case['nodes']:
        key = EntityKey(node['entityType'], node.get('assignedEntityId') or node['entityId'])
        scope = (TraceScope.root(owner, key, case['requestComment']) if node['parent'] is None
                 else scopes[node['parent']].child(key, node['localComment']))
        scopes[node['nodeId']] = scope
        if 'ledgerLineage' in node:
            ledger.set_trace_chain(key, [TraceNode(kind='auditReason', name=item['name'],
                entity_id=item['entityId'], comment=item['detail']) for item in node['ledgerLineage']])
        request = MutationRequest(InsertCommand(key.entity), comment=case['requestComment']).with_mutation_lineage(
            ledger.trace_chain(key) or scope.recover())
        recovered[node['nodeId']] = [logical(item) for item in request.mutation_lineage]
        copied = request.mutation_lineage
        copied[0].comment = 'consumer changed the recovered snapshot'
        assert [logical(item) for item in request.mutation_lineage] == recovered[node['nodeId']]
    assert recovered == {item['nodeId']: item['lineage'] for item in case['expected']}


def test_persistent_scope_is_immutable_and_blank_child_shares_parent():
    root = TraceScope.root(object(), EntityKey('CustomerOrder', 1), 'submit order')
    assert root.child(EntityKey('OrderItem', 2), ' \t') is root
    with pytest.raises(FrozenInstanceError):
        root._node.reason = 'changed ancestor'
    with pytest.raises(FrozenInstanceError):
        root._parent = root
    child = root.child(EntityKey('Payment', 1), 'authorize payment')
    assert child._parent is root
    assert child.recover()[0].entity_type == 'CustomerOrder'


def test_ledger_trace_is_typed_owned_and_rekeys_matching_ancestors_only():
    ledger = EntityRoot()
    old, new, payment = EntityKey('CustomerOrder', -1), EntityKey('CustomerOrder', 100), EntityKey('Payment', -1)
    source = [TraceNode(kind='auditReason', name='CustomerOrder', entity_id=-1, comment='submit order'),
              TraceNode(kind='auditReason', name='Payment', entity_id=-1, comment='authorize payment')]
    ledger.set_trace_chain(payment, source)
    source[0].comment = 'caller changed source'
    ledger.rekey(old, new)
    chain = ledger.trace_chain(payment)
    assert [(node.name, node.entity_id) for node in chain] == [('CustomerOrder', 100), ('Payment', -1)]
    assert chain[0].comment == 'submit order'
    chain[0].entity_id = 999
    assert ledger.trace_chain(payment)[0].entity_id == 100
    merged = EntityRoot()
    merged.merge_from(ledger)
    ledger.clear_entity(payment)
    assert len(merged.trace_chain(payment)) == 2
    merged.clear_committed()
    assert merged.trace_chain(payment) == ()
    with pytest.raises(TypeError, match='typed AuditReason'):
        ledger.set_trace_chain(payment, ['opaque sensitive input'])
