"""No invalid input disappears merely because Python compares it as equal."""
from decimal import Decimal
from types import SimpleNamespace

import pytest

from teaql.core.entity import EntityKey, EntityRoot
from teaql.core.meta import EntityDescriptor, PropertyDescriptor
from teaql.core.mutation import TraceNode
from teaql.core.value import DataType, Timestamp, Value
from teaql.runtime import CheckException, RuntimeModule
from teaql.runtime.loaded_scalar_snapshot import LoadedScalarSnapshots, _same_representation


class Entity:
    def __init__(self, key, values, root=None, action='Update'):
        self._key, self._action = key, action
        self._entity_root = root or EntityRoot()
        self._loaded_fields = frozenset(values)
        if action == 'Create':
            self._entity_root.mark_as_new(key)
        else:
            self._entity_root.set_original_version(key, 7)
        LoadedScalarSnapshots.capture(self, {"id": Value.I64(key.id), "version": Value.I64(7), **values})

    def _teaql_entity_key(self):
        return self._key


def context():
    descriptor = (EntityDescriptor('Order')
        .property(PropertyDescriptor('id', DataType.I64).is_id())
        .property(PropertyDescriptor('version', DataType.I64).is_version())
        .property(PropertyDescriptor('name', DataType.Text))
        .property(PropertyDescriptor('quantity', DataType.Decimal))
        .property(PropertyDescriptor('other', DataType.Text)))
    return RuntimeModule().schema_entity(descriptor).into_context()


@pytest.mark.parametrize('original', [Value.Text('first'), Value.Text(None), Value.Decimal(Decimal('37.00')),
                                      Value.F64(0.0), Value.Bool(False), Value.I64(0)])
def test_known_value_or_null_cancels_only_its_field_and_retains_all_other_state(original):
    key, sibling = EntityKey('Order', 1), EntityKey('Payment', 1)
    entity = Entity(key, {'name': original})
    ledger = entity._entity_root
    ledger.set_original_version(sibling, 2)
    ledger.set(sibling, 'name', Value.Text('another entity type'))
    ledger.set(key, 'other', Value.Text('real remaining edit'))
    ledger.set_trace_chain(key, [TraceNode('Order', 1, 'retained reason', kind='auditReason', name='Order')])
    ledger.set(key, 'name', Value.Text('temporary'))
    ledger.push_change_set()
    ledger.set(key, 'name', original)
    loaded = entity._loaded_fields
    assert LoadedScalarSnapshots.discard_restored_fields(entity, context()) == ('name',)
    assert ledger.get(key, 'name') is None
    assert ledger.get(key, 'other') == Value.Text('real remaining edit')
    assert ledger.get(sibling, 'name') == Value.Text('another entity type')
    assert ledger.original_version(key) == 7 and ledger.original_version(sibling) == 2
    assert ledger.trace_chain(key)[0].comment == 'retained reason'
    assert entity._loaded_fields is loaded and entity._action == 'Update'
    ledger.pop_change_set()
    assert ledger.get(key, 'name') is None and ledger.has_pending(key)


def test_unknown_backing_null_and_structural_version_are_not_restored():
    key = EntityKey('Order', 1)
    entity = Entity(key, {})
    entity._entity_root.set(key, 'name', Value.Null())
    entity._entity_root.set(key, 'version', Value.I64(7))
    assert LoadedScalarSnapshots.discard_restored_fields(entity, context()) == ()
    assert entity._entity_root.has_pending(key)
    assert set(entity._entity_root._pending_values(key)) == {'name', 'version'}


@pytest.mark.parametrize('lifecycle', ['Create', 'Delete'])
def test_creation_or_pending_deletion_is_not_cancelled(lifecycle):
    entity = Entity(EntityKey('Order', 1), {'name': Value.Text('original')}, action=lifecycle)
    if lifecycle == 'Delete':
        entity._entity_root.mark_as_deleted(entity._key)
    entity._entity_root.set(entity._key, 'name', Value.Text('original'))
    assert LoadedScalarSnapshots.discard_restored_fields(entity, context()) == ()
    assert entity._entity_root.has_pending(entity._key)


@pytest.mark.parametrize('bad_field', ['unknown', 'Name', '_result_count'])
def test_raw_equal_invalid_keys_reject_before_any_field_is_discarded(bad_field):
    entity = Entity(EntityKey('Order', 1), {'name': Value.Text('original')})
    entity._entity_root.set(entity._key, 'name', Value.Text('original'))
    entity._entity_root.set(entity._key, bad_field, Value.Null())
    before = entity._entity_root._pending_values(entity._key)
    with pytest.raises(CheckException):
        LoadedScalarSnapshots.discard_restored_fields(entity, context())
    assert entity._entity_root._pending_values(entity._key) == before


@pytest.mark.parametrize('key', [EntityKey('Payment', 1), EntityKey('Order', 2), EntityKey('Order', True)])
def test_a_snapshot_cannot_be_borrowed_by_a_different_typed_identity(key):
    entity = Entity(EntityKey('Order', 1), {'name': Value.Text('original')})
    entity._key = key
    entity._entity_root.set(key, 'name', Value.Text('original'))
    with pytest.raises(ValueError, match='ENTITY_BASELINE_OWNER'):
        LoadedScalarSnapshots.discard_restored_fields(entity, context())
    assert entity._entity_root.get(key, 'name') == Value.Text('original')


@pytest.mark.parametrize('left,right', [
    (Value.Decimal(Decimal('1.0')), Value.Decimal(Decimal('1.00'))),
    (Value.F64(-0.0), Value.F64(0.0)),
    (Value.Bool(True), Value.I64(1)),
    (Value.I64(1), Value.Text('1')),
    (Value.I64(1), Value.Decimal(Decimal('1'))),
    (Value.U64(1), Value.I64(1)),
    (Value.F64(float('nan')), Value.F64(float('nan'))),
    (Value.F64(float('inf')), Value.F64(float('inf'))),
    (Value.JSON({'a': [True]}), Value.JSON({'a': [1]})),
])
def test_representational_changes_and_nonfinite_input_are_not_normalized(left, right):
    assert not _same_representation(left, right)
    entity = Entity(EntityKey('Order', 1), {'name': left})
    entity._entity_root.set(entity._key, 'name', right)
    assert LoadedScalarSnapshots.discard_restored_fields(entity, context()) == ()


def test_exact_timestamp_and_nested_json_are_supported_without_arbitrary_equality_hooks():
    assert _same_representation(Value.Timestamp(Timestamp(1001)), Value.Timestamp(Timestamp(1001)))
    assert not _same_representation(Value.Timestamp(Timestamp(1001)), Value.I64(1001))
    assert _same_representation(Value.JSON({'a': [0, False, None]}), Value.JSON({'a': [0, False, None]}))
    cycle = []; cycle.append(cycle)
    assert not _same_representation(Value.JSON(cycle), Value.JSON(cycle))
    class Dangerous:
        def __eq__(self, other):
            raise AssertionError('arbitrary equality must not run')
    assert not _same_representation(Value(Dangerous()), Value(Dangerous()))


def test_an_empty_ledger_keeps_original_values_for_later_real_changes():
    entity = Entity(EntityKey('Order', 1), {'name': Value.Text('original')})
    entity._entity_root.set(entity._key, 'name', Value.Text('original'))
    assert LoadedScalarSnapshots.discard_restored_fields(entity, context()) == ('name',)
    assert not entity._entity_root.has_pending(entity._key)
    assert LoadedScalarSnapshots.values(entity)['name'] == Value.Text('original')
    entity._entity_root.set(entity._key, 'name', Value.Text('real edit'))
    assert LoadedScalarSnapshots.discard_restored_fields(entity, context()) == ()
