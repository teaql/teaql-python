"""Once-only Fix must retain its output and the final mutation boundary."""
from datetime import datetime, timezone

import pytest

from teaql.core.entity import EntityKey, EntityRoot
from teaql.core.meta import EntityDescriptor, PropertyDescriptor
from teaql.core.mutation import InsertCommand
from teaql.core.value import DataType, Value
from teaql.runtime import CheckException, RuntimeModule


class ControlledFixFailure(RuntimeError):
    pass


@pytest.mark.asyncio
@pytest.mark.parametrize('stage', ['checker', 'work', 'cancel'])
async def test_failed_fix_restores_user_intent_before_retry(stage):
    import asyncio
    attempts = []
    control = {'fail': stage == 'checker'}

    class Checker:
        def check_and_fix(self, context, record, location, results):
            attempts.append(context.get_resource('fix_time'))
            record['name'] = Value.Text('fixed-' + str(len(attempts)))
            record['derived'] = Value.Text('derived-' + str(len(attempts)))
            if control['fail']:
                raise ControlledFixFailure('checker failed after deriving values')

    descriptor = (EntityDescriptor('Probe')
        .property(PropertyDescriptor('id', DataType.I64).is_id())
        .property(PropertyDescriptor('name').required())
        .property(PropertyDescriptor('derived')))
    context = (RuntimeModule().entity(Probe).schema_entity(descriptor)
        .checker('Probe', Checker()).into_context().insert_resource('dataService', Provider()))
    entity = Probe()
    unrelated = EntityKey('Probe', 2)
    entity._entity_root.set(unrelated, 'name', Value.Text('unrelated intent'))

    async def prepare(session):
        session._generated.observe(entity)
        session._generated.fix(entity, 'Create', InsertCommand('Probe', entity._teaql_scalar_payload()))

    async def fail(session):
        if stage == 'cancel':
            raise asyncio.CancelledError()
        raise ControlledFixFailure('failure after preparation')

    with pytest.raises(asyncio.CancelledError if stage == 'cancel' else ControlledFixFailure):
        await context.execute_graph_save(fail, prepare=prepare, comment='fail without retaining derived intent')
    pending = entity._entity_root._pending_values(entity._teaql_entity_key())
    assert pending == {'name': Value.Text('original')}
    assert entity._entity_root.get(unrelated, 'name') == Value.Text('unrelated intent')
    assert entity._entity_root.has_pending(entity._teaql_entity_key())
    assert context.get_resource('fix_time') is None

    control['fail'] = False

    async def success(session):
        current = entity._entity_root._pending_values(entity._teaql_entity_key())
        assert current['name'] == Value.Text('fixed-2')
        assert current['derived'] == Value.Text('derived-2')
        return True

    assert await context.execute_graph_save(success, prepare=prepare, comment='derive fresh values on retry')
    assert len(attempts) == 2


@pytest.mark.asyncio
@pytest.mark.parametrize('variant', ['explicit-null', 'rekey', 'late-user-edit', 'outer-change-set'])
async def test_fix_rollback_preserves_null_identity_late_edits_and_outer_scope(variant):
    context, calls = fixture()
    entity = Probe()
    key = entity._teaql_entity_key()
    if variant == 'explicit-null':
        entity._entity_root.set(key, 'name', Value.Null())
    if variant == 'outer-change-set':
        entity._entity_root.set(key, 'name', Value.Text('outer intent'))
        entity._entity_root.push_change_set()

    async def prepare(session):
        session._generated.observe(entity)
        session._generated.fix(entity, 'Create', InsertCommand('Probe', entity._teaql_scalar_payload()))

    async def fail(session):
        if variant == 'rekey':
            entity.id = 42
            entity._entity_root.rekey(key, entity._teaql_entity_key())
            entity._entity_root.set(entity._teaql_entity_key(), 'id', Value.I64(42))
        if variant == 'late-user-edit':
            entity.name = 'later user intent'
            entity._entity_root.set(key, 'name', Value.Text(entity.name))
        raise ControlledFixFailure('restore only unchanged derived fields')

    with pytest.raises(ControlledFixFailure):
        await context.execute_graph_save(fail, prepare=prepare, comment='preserve original mutation boundaries')
    pending = entity._entity_root._pending_values(entity._teaql_entity_key())
    expected = {'name': Value.Null() if variant == 'explicit-null' else
        Value.Text('later user intent' if variant == 'late-user-edit' else
                   'outer intent' if variant == 'outer-change-set' else 'original')}
    if variant == 'rekey':
        expected['id'] = Value.I64(42)
        assert entity.id == 42 and not entity._entity_root.has_pending(key)
    assert pending == expected
    if variant == 'outer-change-set':
        assert entity._entity_root.current_change_set().is_empty()
    assert len(calls) == 1


class Probe:
    def __init__(self, identity=1):
        self.id = identity
        self._action = 'Create'
        self.name = 'original'
        self._entity_root = EntityRoot()
        self._entity_root.mark_as_new(self._teaql_entity_key())
        self._entity_root.set(self._teaql_entity_key(), 'name', Value.Text(self.name))
        self.children = []

    def _teaql_entity_key(self):
        return EntityKey('Probe', self.id)

    def _teaql_scalar_payload(self):
        return {'id': Value.I64(self.id), 'name': Value.Text(self.name)}

    def _teaql_graph_relations(self):
        return {'children': tuple(self.children)}


class Provider:
    async def begin(self, context):
        return self

    async def commit(self, context):
        pass

    async def rollback(self, context):
        pass


def fixture():
    calls = []
    class Checker:
        def check_and_fix(self, context, record, location, results):
            calls.append(context.get_resource('fix_time'))
            record['name'] = Value.Text('fixed once')
    descriptor = (EntityDescriptor('Probe')
        .property(PropertyDescriptor('id', DataType.I64).is_id())
        .property(PropertyDescriptor('name').required()))
    context = (RuntimeModule().entity(Probe).schema_entity(descriptor)
               .checker('Probe', Checker()).into_context().insert_resource('dataService', Provider()))
    return context, calls


@pytest.mark.asyncio
async def test_fixed_values_are_retained_without_running_checker_twice():
    context, calls = fixture()
    entity = Probe()
    async def prepare(session):
        state = session._generated
        state.observe(entity)
        state.fix(entity, 'Create', InsertCommand('Probe', entity._teaql_scalar_payload()))
        action, command = state.finalize(entity, 'Create', InsertCommand('Probe', entity._teaql_scalar_payload()))
        assert action == 'Create' and command.values['name'].val == 'fixed once'
        session._remember_prepared_mutation(entity, action, command)
        assert state.visit('plan', entity) and not state.visit('plan', entity)
        assert state.visit('write', entity) and not state.visit('write', entity)
        session._seal_generated_plan()
        state.validate()
    async def work(session):
        return 42
    assert await context.execute_graph_save(work, prepare=prepare, comment='retain one fixed input') == 42
    assert len(calls) == 1
    assert context.get_resource('fix_time') is None


@pytest.mark.asyncio
@pytest.mark.parametrize('target', ['carrier', 'ledger', 'list', 'action'])
async def test_late_changes_to_fixed_input_or_graph_reject(target):
    context, calls = fixture()
    entity = Probe()
    async def prepare(session):
        state = session._generated
        state.observe(entity)
        state.fix(entity, 'Create', InsertCommand('Probe', entity._teaql_scalar_payload()))
        action, command = state.finalize(entity, 'Create', InsertCommand('Probe', entity._teaql_scalar_payload()))
        session._remember_prepared_mutation(entity, action, command)
        session._seal_generated_plan()
        if target == 'carrier':
            entity.name = 'unreviewed'
        elif target == 'ledger':
            entity._entity_root.set(entity._teaql_entity_key(), 'name', Value.Text('unreviewed'))
        elif target == 'list':
            entity.children.append(Probe(2))
        else:
            entity._action = 'Delete'
        with pytest.raises(CheckException) as error:
            state.validate()
        assert error.value.violations[0].rule_id == 'mutation_changed_after_preparation'
    async def work(session):
        pass
    await context.execute_graph_save(work, prepare=prepare, comment='retain final graph admission')
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_distinct_mutable_instances_are_not_deduplicated_by_id():
    context, calls = fixture()
    first, second = Probe(), Probe()
    async def prepare(session):
        session._generated.fix(first, 'Create', InsertCommand('Probe', first._teaql_scalar_payload()))
        with pytest.raises(CheckException) as error:
            session._generated.fix(second, 'Create', InsertCommand('Probe', second._teaql_scalar_payload()))
        assert error.value.violations[0].rule_id == 'ambiguous_mutation_view'
    async def work(session):
        pass
    await context.execute_graph_save(work, prepare=prepare, comment='reject ambiguous mutable views')
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_failed_or_successful_invocation_does_not_reuse_fixed_state():
    context, calls = fixture()
    entity = Probe()
    retained = []
    async def prepare(session):
        retained.append(session._generated)
        session._generated.observe(entity)
        session._generated.fix(entity, 'Create', InsertCommand('Probe', entity._teaql_scalar_payload()))
    async def failure(session):
        raise ValueError('controlled failure')
    async def success(session):
        return True
    with pytest.raises(ValueError, match='controlled failure'):
        await context.execute_graph_save(failure, prepare=prepare, comment='fail one prepared graph')
    assert await context.execute_graph_save(success, prepare=prepare, comment='retry with fresh preparation')
    assert len(calls) == 2
    assert retained[0] is not retained[1]
    assert all(not state.fixed and not state.views for state in retained)


@pytest.mark.asyncio
async def test_graph_admission_rejects_two_pending_views_before_any_fix():
    context, calls = fixture()
    root = Probe(9)
    root.children = [Probe(1), Probe(1)]
    original = [child._entity_root for child in root.children]
    async def prepare(session):
        with pytest.raises(CheckException) as error:
            session._generated.admit_graph(root)
        assert error.value.violations[0].rule_id == 'ambiguous_mutation_view'
        assert all(child._entity_root is ledger for child, ledger in zip(root.children, original))
    async def work(session):
        pass
    await context.execute_graph_save(work, prepare=prepare, comment='admit before merging views')
    assert not calls


@pytest.mark.asyncio
async def test_equal_text_does_not_hide_a_changed_value_type_hint():
    context, _ = fixture()
    entity = Probe()
    async def prepare(session):
        state = session._generated
        state.fix(entity, 'Create', InsertCommand('Probe', entity._teaql_scalar_payload()))
        entity._entity_root.set(entity._teaql_entity_key(), 'name', Value.Json('fixed once'))
        with pytest.raises(CheckException):
            state.finalize(entity, 'Create', InsertCommand('Probe', entity._teaql_scalar_payload()))
    async def work(session):
        pass
    await context.execute_graph_save(work, prepare=prepare, comment='preserve the checked representation')
