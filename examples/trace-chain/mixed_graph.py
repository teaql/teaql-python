"""ML-09/ML-11: generated Q/E/save with actual mixed SQLite mutations.

Business rows are written only by generated mutation APIs. SQL is limited to
read-only storage oracles and test-only deferred-constraint fault injection.
"""
import asyncio
import json
import os
from pathlib import Path
import sqlite3
from uuid import uuid4

from E import E
from Q import Q
from runtime_module import GENERATED_RUNTIME_MODULE
from teaql.core.entity import EntityKey
from teaql.provider.sqlite import create_sqlite_service
from teaql.runtime import UserContext
from teaql.runtime.mutation_policy import DelegatingMutationPolicyRegistry

from main import AuditSink, ObservedService, ObservedTransaction, new, reset, scalar
from page_stream import RecordingPolicy
from shared_reference import pending


class MixedTransaction(ObservedTransaction):
    async def mutate(self, context, request):
        command = request._data
        self.owner.versions.append(getattr(command, 'expected_version_val', None))
        result = await super().mutate(context, request)
        # These are returned by the real SQLite executor, including its actual
        # persisted-row readback; attempted calls alone are not proof of a write.
        assert result.affected_rows == 1 and len(result.metadata.statements) == 2
        write, read = result.metadata.statements
        assert write.affected_rows == 1 and read.result_count == 1
        assert write.execution_outcome == read.execution_outcome == 'success'
        if self.owner.observing:
            assert not self.owner.sink.events, 'audit must wait for commit'
        self.owner.writes.append({
            'entity': command.entity, 'id': self.owner.requests[-1][1],
            'action': self.owner.actions[-1], 'original_version': self.owner.versions[-1],
            'affected_rows': write.affected_rows, 'readback_count': read.result_count,
            'write_outcome': write.execution_outcome, 'readback_outcome': read.execution_outcome,
        })
        if self.owner.reject_after_write and len(self.owner.writes) == 1:
            raise self.owner.failure
        return result

    async def commit(self, context):
        self.owner.commit_attempts += 1
        if self.owner.observing:
            assert not self.owner.sink.events
        try:
            await super().commit(context)
        except BaseException as error:
            self.owner.commit_error = error
            raise


class MixedService(ObservedService):
    def __init__(self, service):
        super().__init__(service)
        self.versions, self.writes = [], []
        self.reject_after_write = False
        self.failure = RuntimeError('mixed graph provider rejected after real write')
        self.commit_attempts = 0
        self.commit_error = None
        self.sink = None
        self.observing = False
        original = service.transport._prepare

        async def prepare(connection):
            await original(connection)
            # Test fixture only: enforce the deferred auxiliary constraint on
            # every real driver connection, before BEGIN, not inside it.
            await connection.execute('PRAGMA foreign_keys=ON')
        service.transport._prepare = prepare

    async def begin(self, context):
        self.begins += 1
        return MixedTransaction(self, await self.service.begin(context))


def clear(service, sink, context, policy):
    reset(service, sink, context)
    service.versions.clear()
    service.writes.clear()
    service.commit_attempts = 0
    service.commit_error = None
    policy.plans.clear()
    service.observing = True


def snapshot(database, owner, old, added):
    with sqlite3.connect('file:' + str(Path(database).resolve()) + '?mode=ro', uri=True) as db:
        assert db.execute('PRAGMA integrity_check').fetchall() == [('ok',)]
        assert db.execute('PRAGMA foreign_key_check').fetchall() == []
        return {
            'parent': db.execute('SELECT version,description FROM customer_order_data WHERE id=?', (owner,)).fetchone(),
            'old': db.execute('SELECT version,customer_order,name FROM order_item_data WHERE id=?', (old,)).fetchone(),
            'added': db.execute('SELECT version,customer_order,name FROM order_item_data WHERE id=?', (added,)).fetchone(),
        }


def operations(policy):
    assert len(policy.plans) == 1, 'review one complete mixed plan, not per-command fragments'
    return sorted([{'kind': op.kind.value, 'entity': op.entity, 'id': scalar(op.entity_id),
                    'original_version': op.original_version} for op in policy.plans[0].operations],
                  key=lambda v: v['kind'])


async def scenario(context, service, sink, policy, platform, database, logging, name, round_number):
    service.observing = False
    order = (await new(Q.customer_orders(), context)).update_platform(platform)
    order.update_order_number('MIX-' + uuid4().hex).update_description('original mixed owner')
    old = (await new(Q.order_items(), context)).update_customer_order(order).update_name('old mixed child')
    order.order_item_list().append(old)
    await order.audit_as('prepare the mixed owner and existing child').save(context)
    owner_id, old_id = E.customer_order(order).id().eval(), E.order_item(old).id().eval()
    added = (await new(Q.order_items(), context)).update_customer_order(order).update_name('new mixed child')
    added_id = E.order_item(added).id().eval()
    order.order_item_list().append(added)
    order.update_description('updated mixed owner')
    # Same Context and same numeric ID, different entity type: must stay pending.
    unrelated = await new(Q.payments(), context)
    unrelated.update_reference_code('unrelated pending payment')
    unrelated_key = unrelated._teaql_entity_key()
    assert E.payment(unrelated).id().eval() == owner_id
    before_mark = (service.begins, len(service.requests), len(service.queries))
    old.mark_for_deletion()
    assert (service.begins, len(service.requests), len(service.queries)) == before_mark
    ledger = order._entity_root
    root_key, old_key, new_key = EntityKey('CustomerOrder', owner_id), EntityKey('OrderItem', old_id), EntityKey('OrderItem', added_id)
    expected_plan = sorted([
        {'kind': 'create', 'entity': 'OrderItem', 'id': added_id, 'original_version': None},
        {'kind': 'delete', 'entity': 'OrderItem', 'id': old_id, 'original_version': 1},
        {'kind': 'update', 'entity': 'CustomerOrder', 'id': owner_id, 'original_version': 1},
    ], key=lambda v: v['kind'])
    original = snapshot(database, owner_id, old_id, added_id)
    assert original == {'parent': (1, 'original mixed owner'), 'old': (1, owner_id, 'old mixed child'), 'added': None}
    if name == 'commit-failure':
        with sqlite3.connect(database) as db:
            db.execute('PRAGMA foreign_keys=ON')
            db.execute('CREATE TABLE IF NOT EXISTS mixed_commit_parent(id INTEGER PRIMARY KEY)')
            db.execute('CREATE TABLE IF NOT EXISTS mixed_commit_guard(id INTEGER PRIMARY KEY, missing_parent INTEGER NOT NULL, '
                       'FOREIGN KEY(missing_parent) REFERENCES mixed_commit_parent(id) DEFERRABLE INITIALLY DEFERRED)')
            db.execute('CREATE TRIGGER mixed_commit_fault AFTER UPDATE ON customer_order_data WHEN NEW.id=' + str(owner_id)
                       + ' BEGIN INSERT INTO mixed_commit_guard(missing_parent) VALUES(1); END')
    failure = None
    if name != 'commit':
        clear(service, sink, context, policy)
        service.reject_after_write = name == 'provider-failure'
        try:
            await order.audit_as('attempt the mixed graph before injected failure').save(context)
        except Exception as error:
            if name == 'provider-failure':
                assert getattr(error, 'error', error) is service.failure
            else:
                assert isinstance(service.commit_error, sqlite3.IntegrityError)
                assert str(service.commit_error) == 'FOREIGN KEY constraint failed'
                if hasattr(service.commit_error, 'sqlite_errorcode'):
                    assert service.commit_error.sqlite_errorcode == sqlite3.SQLITE_CONSTRAINT_FOREIGNKEY
        else:
            raise AssertionError('armed physical failure did not reject the mixed save')
        finally:
            service.reject_after_write = False
        assert operations(policy) == expected_plan
        assert len(service.writes) == (1 if name == 'provider-failure' else 3)
        assert service.finishes == ['rollback'] and sink.events == []
        assert snapshot(database, owner_id, old_id, added_id) == original
        assert ledger.original_version(root_key) == ledger.original_version(old_key) == 1
        assert new_key in ledger.new_keys() and old_key in ledger.deleted_keys() and pending(ledger, root_key)
        assert pending(unrelated._entity_root, unrelated_key)
        failure = {'stage': name, 'plan': operations(policy), 'actual_writes': list(service.writes),
                   'stored_after_rollback': original, 'audits': 0, 'finishes': list(service.finishes),
                   'commit_attempts': service.commit_attempts, 'pending_create': True, 'pending_delete': True,
                   'pending_update': True, 'original_versions_retained': True}
        if name == 'commit-failure':
            with sqlite3.connect(database) as db:
                assert db.execute('SELECT count(*) FROM mixed_commit_guard').fetchone() == (0,)
                db.execute('DROP TRIGGER mixed_commit_fault')
    clear(service, sink, context, policy)
    await order.audit_as('commit insertion update and deletion in one save').save(context)
    assert operations(policy) == expected_plan
    assert sorted(service.actions) == ['delete', 'insert', 'update']
    assert len(service.requests) == len(service.writes) == len(sink.events) == 3
    assert service.finishes == ['commit'] and service.commit_attempts == 1
    assert all(not pending(ledger, key) for key in [root_key, old_key, new_key])
    assert pending(unrelated._entity_root, unrelated_key)
    committed = snapshot(database, owner_id, old_id, added_id)
    assert committed == {'parent': (2, 'updated mixed owner'), 'old': (-2, owner_id, 'old mixed child'),
                         'added': (1, owner_id, 'new mixed child')}
    loaded = await (Q.customer_orders().with_id_is(owner_id).limit(1)
        .select_order_item_list_with(Q.order_items().limit(10)).comment('reload the committed mixed graph')
        .purpose('verify generated E after atomic mixed save').execute_for_one(context))
    assert E.customer_order(loaded).description().eval() == 'updated mixed owner'
    assert E.customer_order(loaded).version().eval() == 2
    assert len(loaded.order_item_list()) == 1
    assert E.order_item(loaded.order_item_list()[0]).id().eval() == added_id
    absent = await (Q.payments().with_id_is(owner_id).limit(1).comment('verify independent pending payment is absent')
        .purpose('verify type-qualified isolation within the same Context').execute_for_list(context))
    assert len(absent) == 0
    result = {'case': name, 'logging': logging, 'round': round_number, 'passed': True,
              'owner_id': owner_id, 'old_id': old_id, 'added_id': added_id, 'plan': operations(policy),
              'writes': list(service.writes), 'audits': len(sink.events), 'finishes': list(service.finishes),
              'failure': failure, 'stored': committed, 'unrelated_same_id_pending': True}
    clear(service, sink, context, policy)
    await order.audit_as('repeat an unchanged mixed graph save').save(context)
    assert service.begins == 0 and service.requests == [] and sink.events == [] and policy.plans == []
    assert pending(unrelated._entity_root, unrelated_key)
    result['unchanged_save_begins'] = result['unchanged_save_commands'] = result['unchanged_save_audits'] = 0
    print('PYTHON_MIXED_GRAPH ' + json.dumps(result, sort_keys=True))


async def main():
    database = os.environ['TEAQL_MIXED_GRAPH_DB']
    round_number = int(os.environ['TEAQL_MIXED_GRAPH_ROUND'])
    for logging in [False, True]:
        context = UserContext.new().install(GENERATED_RUNTIME_MODULE)
        service = MixedService(create_sqlite_service(database))
        sink, policy = AuditSink(service), RecordingPolicy()
        service.sink = sink
        context.insert_resource('dataService', service).with_app_audit_event_sink(sink)
        context.with_mutation_policy_registry(DelegatingMutationPolicyRegistry(lambda _: policy))
        if not logging:
            context.disable_sql_log()
        try:
            await context.ensure_schema()
            platform = await (Q.platforms().with_id_is(1).limit(1).comment('load seeded platform for mixed mutation')
                .purpose('prepare generated mixed graph acceptance').execute_for_one(context))
            for name in ['commit', 'provider-failure', 'commit-failure']:
                await scenario(context, service, sink, policy, platform, database, logging, name, round_number)
        finally:
            await service.close()
            await asyncio.to_thread(context.runtime_telemetry().shutdown)


if __name__ == '__main__':
    asyncio.run(main())
