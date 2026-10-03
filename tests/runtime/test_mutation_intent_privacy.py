"""Owned provenance and debug rules, independent from graph acceptance."""
from teaql.core.meta import EntityDescriptor, PropertyDescriptor
from teaql.core.mutation import UpdateCommand
from teaql.core.value import DataType, Value
from teaql.runtime.log_privacy import _MutationIntentPrivacy


def test_snapshot_owns_old_and_new_values_and_debug_never_reveals_credentials():
    descriptor = EntityDescriptor('Payment').audit_mask_fields(['name'])
    descriptor.property(PropertyDescriptor('name', DataType.Text).log_policy('plain'))
    descriptor.property(PropertyDescriptor('password_hash', DataType.Text).log_policy('plain'))
    command = UpdateCommand.new('Payment', 73).value('name', 'PRIVATE-NEW')
    command.value('password_hash', 'CREDENTIAL-CANARY')
    command.old_values = {'name': Value.from_any('PRIVATE-OLD')}
    privacy = _MutationIntentPrivacy.capture(command, lambda _: descriptor)
    command.values['name'] = Value.from_any('changed after snapshot')
    command.old_values.clear()
    descriptor.audit_mask_fields([])
    assert set(privacy.secrets(False)) == {'PRIVATE-NEW', 'PRIVATE-OLD', 'CREDENTIAL-CANARY', '73'}
    assert set(privacy.secrets(True)) == {'CREDENTIAL-CANARY', '73'}
    assert 'PRIVATE-NEW' not in repr(privacy)


def test_loaded_scalar_snapshot_owns_values_and_returns_detached_changed_fields():
    from teaql.core.entity import _LoadedScalarSnapshot
    source = {'name': Value.from_any('original'), 'config': Value.from_any({'nested': ['original']})}
    snapshot = _LoadedScalarSnapshot(source)
    source['name'] = Value.from_any('caller changed')
    source['config'].val['nested'].append('caller changed')
    selected = snapshot.select(['name', 'config', 'not_loaded'])
    assert selected['name'].val == 'original'
    assert selected['config'].val == {'nested': ['original']}
    assert 'not_loaded' not in selected
    selected['config'].val['nested'].clear()
    assert snapshot.select(['config'])['config'].val == {'nested': ['original']}
