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


def test_business_snapshot_includes_unchanged_scalars_without_identity_or_version():
    from teaql.core.entity import _LoadedScalarSnapshot
    snapshot = _LoadedScalarSnapshot({'id': Value.from_any(1), 'version': Value.from_any(2),
                                      'name': Value.from_any('PRIVATE-UNCHANGED'),
                                      'config': Value.from_any({'secret': ['original']})})
    values = snapshot.business_values()
    assert set(values) == {'name', 'config'}
    values['config'].val['secret'].clear()
    assert snapshot.business_values()['config'].val == {'secret': ['original']}


def test_delete_and_recover_capture_old_private_values_without_altering_bindings():
    from teaql.core.mutation import DeleteCommand, RecoverCommand
    descriptor = EntityDescriptor('Payment').audit_mask_fields(['name'])
    descriptor.property(PropertyDescriptor('name', DataType.Text).log_policy('plain'))
    descriptor.property(PropertyDescriptor('public_note', DataType.Text).log_policy('plain'))
    for command in (DeleteCommand.new('Payment', 73), RecoverCommand.new('Payment', 73, -2)):
        command.old_values = {'name': Value.from_any('PRIVATE-OLD'),
                              'public_note': Value.from_any('ordinary prose')}
        privacy = _MutationIntentPrivacy.capture(command, lambda _: descriptor)
        command.old_values.clear()
        assert set(privacy.secrets(False)) == {'PRIVATE-OLD', '73'}
        assert set(privacy.secrets(True)) == {'73'}
        assert command.id.val == 73
        assert not hasattr(command, 'values')
