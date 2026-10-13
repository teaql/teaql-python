import gc
import weakref
from teaql.core.value import Value
from teaql.runtime.loaded_scalar_snapshot import LoadedScalarSnapshots


class Entity:
    pass


def test_snapshot_copies_input_and_output_and_is_not_entity_state():
    entity = Entity()
    source = {'name': Value.Text('original'), 'json': Value.JSON({'nested': ['original']})}
    LoadedScalarSnapshots.capture(entity, source)
    source['json'].val['nested'].append('outside mutation')
    source['name'] = Value.Text('changed')
    first = LoadedScalarSnapshots.values(entity)
    assert first['name'].val == 'original' and first['json'].val == {'nested': ['original']}
    first['json'].val['nested'].append('output mutation')
    assert LoadedScalarSnapshots.values(entity)['json'].val == {'nested': ['original']}
    assert vars(entity) == {}


def test_snapshot_rollback_is_independent_and_gc_releases_owner():
    entity, another = Entity(), Entity()
    LoadedScalarSnapshots.capture(entity, {'secret': Value.Text('first')})
    LoadedScalarSnapshots.capture(another, {'secret': Value.Text('other')})
    old = LoadedScalarSnapshots.values(entity)
    LoadedScalarSnapshots.capture(entity, {'secret': Value.Text('persisted')})
    LoadedScalarSnapshots.restore(entity, old)
    assert LoadedScalarSnapshots.values(entity)['secret'].val == 'first'
    assert LoadedScalarSnapshots.values(another)['secret'].val == 'other'
    reference = weakref.ref(entity)
    del entity
    gc.collect()
    assert reference() is None
