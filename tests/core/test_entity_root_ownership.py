"""Reached-key imports must not compose another graph's pending mutations."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest

from teaql.core.entity import EntityKey, EntityRoot
from teaql.core.mutation import TraceNode
from teaql.core.value import Value


def pending(root, key):
    return key in dict(root.current_change_set().changes()) or key in root.new_keys() or key in root.deleted_keys()


def test_scoped_import_keeps_unreached_and_source_changes():
    source, target = EntityRoot(), EntityRoot()
    parent, child, sibling = EntityKey('Order', 1), EntityKey('OrderItem', 1), EntityKey('OrderItem', 2)
    source.set_original_version(parent, 9)
    source.set_original_version(child, 2)
    target.set_original_version(parent, 3)
    source.set(parent, 'name', Value.Text('foreign root'))
    source.set(child, 'name', Value.Text('reached child'))
    source.set(sibling, 'name', Value.Text('foreign sibling'))
    source.set_trace_chain(child, [TraceNode('Order', 1, 'import child', kind='auditReason', name='Order')])

    target.merge_entity_from(source, child)

    assert dict(target.current_change_set().changes()) == {child: {'name': Value.Text('reached child')}}
    assert target.original_version(parent) == 3
    assert target.original_version(child) == 2
    assert not pending(target, parent) and not pending(target, sibling)
    assert target.trace_chain(child)[0].comment == 'import child'
    target.clear_entity(child)
    assert pending(source, child) and pending(source, parent) and pending(source, sibling)


def test_scoped_import_copies_lifecycle_without_pending_hydration():
    source, target = EntityRoot(), EntityRoot()
    loaded, added, removed = EntityKey('Platform', 1), EntityKey('OrderItem', -1), EntityKey('OrderItem', 2)
    source.set_original_version(loaded, 1)
    source.mark_as_new(added)
    source.set(added, 'name', Value.Text('new'))
    source.set_original_version(removed, 3)
    source.mark_as_deleted(removed)
    for key in (loaded, added, removed):
        target.merge_entity_from(source, key)
    assert not target.has_pending(loaded)
    assert added in target.new_keys() and removed in target.deleted_keys()
    assert added in source.new_keys() and removed in source.deleted_keys()


def test_version_conflict_rejects_scoped_and_whole_import_before_copying():
    source, target = EntityRoot(), EntityRoot()
    key, unrelated = EntityKey('Order', 1), EntityKey('OrderItem', 2)
    target.set_original_version(key, 1)
    target.set(key, 'name', Value.Text('original'))
    source.set_original_version(key, 2)
    source.set(key, 'name', Value.Text('replacement'))
    source.mark_as_deleted(key)
    source.mark_as_new(unrelated)
    source.set(unrelated, 'name', Value.Text('unreached'))
    source.set_trace_chain(key, [TraceNode('Order', 1, 'foreign', kind='auditReason', name='Order')])
    for operation in (lambda: target.merge_entity_from(source, key), lambda: target.merge_from(source)):
        with pytest.raises(ValueError, match='ENTITY_VERSION_CONFLICT'):
            operation()
        assert target.original_version(key) == 1
        assert target.get(key, 'name') == Value.Text('original')
        assert not pending(target, unrelated) and key not in target.deleted_keys()
        assert target.trace_chain(key) == ()
    assert key in source.deleted_keys()


def test_conflicting_rekey_preserves_both_keys():
    root = EntityRoot()
    old, new = EntityKey('Order', -1), EntityKey('Order', 1)
    root.set_original_version(old, 2)
    root.set_original_version(new, 1)
    root.mark_as_new(old)
    root.set(old, 'name', Value.Text('old'))
    root.set(new, 'name', Value.Text('new'))
    with pytest.raises(ValueError, match='ENTITY_VERSION_CONFLICT'):
        root.rekey(old, new)
    assert old in root.new_keys()
    assert root.original_version(old) == 2 and root.original_version(new) == 1
    assert root.get(old, 'name') == Value.Text('old') and root.get(new, 'name') == Value.Text('new')


def test_committed_version_requires_cleared_changes_and_keeps_typed_keys():
    root = EntityRoot()
    order, payment = EntityKey('Order', 1), EntityKey('Payment', 1)
    root.set_original_version(order, 7)
    root.set_original_version(payment, 1)
    root.set_original_version(order, 7)
    with pytest.raises(ValueError, match='ENTITY_VERSION_CONFLICT'):
        root.set_original_version(order, 8)
    root.set(order, 'name', Value.Text('pending'))
    with pytest.raises(ValueError, match='ENTITY_PENDING_CHANGES'):
        root.accept_committed_version(order, 8)
    root.clear_entity(order)
    root.accept_committed_version(order, 8)
    assert root.original_version(order) == 8 and root.original_version(payment) == 1


def test_concurrent_conflicting_version_registration_has_one_winner():
    root, key, start = EntityRoot(), EntityKey('Order', 1), Barrier(2)

    def register(version):
        start.wait(timeout=5)
        try:
            root.set_original_version(key, version)
            return True
        except ValueError as error:
            assert 'ENTITY_VERSION_CONFLICT' in str(error)
            return False

    with ThreadPoolExecutor(max_workers=2) as executor:
        first = executor.submit(register, 1)
        second = executor.submit(register, 2)
        assert sum([first.result(timeout=10), second.result(timeout=10)]) == 1
    assert root.original_version(key) in (1, 2)
