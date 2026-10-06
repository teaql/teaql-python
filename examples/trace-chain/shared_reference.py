"""App-owned generated Q/E/save acceptance; no generated-source API discovery."""
import asyncio
import copy
import json
import os
import uuid

from E import E
from Q import Q
from runtime_module import GENERATED_RUNTIME_MODULE
from teaql.core.entity import EntityKey
from teaql.provider.sqlite import create_sqlite_service
from teaql.runtime import UserContext

from main import AuditSink, ObservedService, ObservedTransaction, new, reset, scalar


class VersionTransaction(ObservedTransaction):
    async def mutate(self, context, request):
        self.owner.versions.append(getattr(request._data, 'expected_version_val', None))
        return await super().mutate(context, request)


class SharedService(ObservedService):
    def __init__(self, service):
        super().__init__(service)
        self.reuse_platform = False
        self.platform_snapshot = None
        self.snapshot_uses = 0
        self.pause = None
        self.versions = []

    async def query(self, context, request):
        result = await self.service.query(context, request)
        if self.reuse_platform:
            for row in result.rows:
                candidate = row.get('platform')
                if isinstance(candidate, dict):
                    if self.platform_snapshot is None:
                        self.platform_snapshot = candidate
                    else:
                        assert candidate == self.platform_snapshot
                    row['platform'] = self.platform_snapshot
                    self.snapshot_uses += 1
        return result

    async def begin(self, context):
        pause, self.pause = self.pause, None
        if pause:
            entered, release = pause
            entered.set()
            await asyncio.wait_for(release.wait(), 10)
        self.begins += 1
        return VersionTransaction(self, await self.service.begin(context))


def pending(ledger, key):
    return key in dict(ledger.current_change_set().changes()) or key in ledger.new_keys() or key in ledger.deleted_keys()


def observe(scenario, service, sink, context):
    sql = [entry for entry in context.sql_logs() if entry.mutation_lineage]
    print('OWNERSHIP EVIDENCE ' + json.dumps({
        'scenario': scenario,
        'commands': service.requests,
        'versions': service.versions[-len(service.requests):] if service.requests else [],
        'sql': [{'outcome': entry.execution_outcome,
                 'comment': entry.comment, 'debugSQL': entry.debug_sql,
                 'path': [(node.kind, node.name, node.entity_id, node.comment) for node in entry.trace_path],
                 'lineage': [(node.kind, node.name, node.entity_id, node.comment) for node in entry.mutation_lineage]}
                for entry in sql],
        'audit': [(event.entity, scalar(event.entity_id),
                   [(node.kind, node.name, node.entity_id, node.comment) for node in event.trace_chain])
                  for event in sink.events],
    }))


async def seed(context, platform, children=1):
    label = 'OWN-' + uuid.uuid4().hex
    order = new(Q.customer_orders(), context).update_platform(platform)
    order.update_order_number(label).update_description('original ' + label)
    for index in range(children):
        child = new(Q.order_items(), context).update_customer_order(order).update_name(label + str(index))
        order.order_item_list().append(child)
    await order.audit_as('prepare ownership graph').save(context)
    return order


async def load(context, entity_id):
    return await (Q.customer_orders().with_id_is(entity_id)
        .select_order_item_list_with(Q.order_items().limit(10)).limit(1)
        .comment('load ownership graph').purpose('verify graph mutation ownership')
        .execute_for_one(context))


def assert_writes(service, sink, context, count):
    sql = [entry for entry in context.sql_logs() if entry.mutation_lineage and not entry.operation.is_select()]
    readbacks = [entry for entry in context.sql_logs() if entry.mutation_lineage and entry.operation.is_select()]
    assert len(readbacks) == count
    for write, read in zip(sql, readbacks):
        assert read.mutation_lineage == write.mutation_lineage
        assert read.trace_path[1].kind == 'request'
        assert read.trace_path[1].name == 'CustomerOrder'
    assert len(service.requests) == len(sink.events) == len(sql) == count, 'only reached changed entities emit commands'
    for request, entry, event in zip(service.requests, sql, sink.events):
        entity, identity, lineage = request
        actual = [(node.name or node.entity_type, node.entity_id, node.comment) for node in entry.mutation_lineage]
        audit = [(node.name or node.entity_type, node.entity_id, node.comment) for node in event.trace_chain]
        assert actual == audit == lineage
        assert (event.entity, scalar(event.entity_id)) == (entity, identity)
        assert entry.execution_outcome == 'success'
        assert [node.kind for node in entry.trace_path] == ['operation', 'entity', 'provider', 'sql']
        assert entry.trace_path[0].name == 'CustomerOrder'


async def shared(context, platform, service, sink):
    a, b = await seed(context, platform), await seed(context, platform)
    revised = await load(context, E.customer_order(a).id().eval())
    await revised.update_description('prior revision').audit_as('advance one root').save(context)
    service.reuse_platform = True
    try:
        roots = await (Q.customer_orders().with_id_in(E.customer_order(a).id().eval(), E.customer_order(b).id().eval())
            .order_by_id_ascending().select_platform_with(Q.platforms().limit(1))
            .select_order_item_list_with(Q.order_items().limit(10)).limit(2)
            .comment('load two independent roots').purpose('verify shared read-only provider record')
            .execute_for_list(context))
    finally:
        service.reuse_platform = False
    first, second = roots
    assert service.snapshot_uses == 2, 'two roots must use the same actual provider-returned record'
    before = copy.deepcopy(service.platform_snapshot)
    first_platform, second_platform = E.customer_order(first).platform().eval(), E.customer_order(second).platform().eval()
    assert first._entity_root is not second._entity_root, 'independent loaded roots must not share a mutable ledger'
    assert first_platform is not second_platform and first_platform._entity_root is not second_platform._entity_root
    versions = [E.customer_order(row).version().eval() for row in roots]
    assert versions == [2, 1]
    child_versions = [E.order_item(row.order_item_list()[0]).version().eval() for row in roots]
    platform_version = E.platform(first_platform).version().eval()
    first.update_description('saved first root')
    second.update_description('saved second root')
    reset(service, sink, context)
    entered, release = asyncio.Event(), asyncio.Event()
    service.pause = (entered, release)
    first_task = asyncio.create_task(first.audit_as('save shared first').save(context))
    await asyncio.wait_for(entered.wait(), 10)
    second_task = asyncio.create_task(second.audit_as('save shared second').save(context))
    await asyncio.sleep(0)
    assert not first_task.done() and not second_task.done()
    assert context._graph_save_lock.locked(), 'first save holds the actual Context graph gate'
    release.set()
    await asyncio.wait_for(asyncio.gather(first_task, second_task), 15)
    observe('shared', service, sink, context)
    assert_writes(service, sink, context, 2)
    assert all(entity == 'CustomerOrder' for entity, _, _ in service.requests)
    assert service.platform_snapshot == before
    for index, row in enumerate(roots):
        persisted = await load(context, E.customer_order(row).id().eval())
        assert E.customer_order(persisted).version().eval() == versions[index] + 1
        assert E.order_item(persisted.order_item_list()[0]).version().eval() == child_versions[index]
    assert E.platform(first_platform).version().eval() == platform_version


async def scoped(context, platform, service, sink):
    foreign_seed, target_seed = await seed(context, platform, 2), await seed(context, platform, 0)
    foreign = await load(context, E.customer_order(foreign_seed).id().eval())
    # The public save composes the loaded reverse graph even on the old producer.
    await foreign.audit_as('prepare loaded source graph').save(context)
    target = await load(context, E.customer_order(target_seed).id().eval())
    reached, sibling = foreign.order_item_list()
    source = foreign._entity_root
    assert reached._entity_root is source and sibling._entity_root is source
    foreign.update_description('foreign pending root')
    sibling.update_name('unreached pending sibling')
    reached.update_name('reached changed child').audit_as('adopt reached child')
    target.update_description('target changed root')
    target.order_item_list().append(reached)
    reset(service, sink, context)
    await target.audit_as('save target graph').save(context)
    observe('scoped', service, sink, context)
    foreign_key = EntityKey('CustomerOrder', E.customer_order(foreign).id().eval())
    sibling_key = EntityKey('OrderItem', E.order_item(sibling).id().eval())
    reached_key = EntityKey('OrderItem', E.order_item(reached).id().eval())
    assert not pending(target._entity_root, foreign_key), 'foreign root must not be imported'
    assert not pending(target._entity_root, sibling_key), 'unreached sibling must not be imported'
    assert all(pending(source, key) for key in [foreign_key, sibling_key, reached_key])
    assert_writes(service, sink, context, 2)
    persisted = await load(context, E.customer_order(target).id().eval())
    assert E.order_item(persisted.order_item_list()[0]).name().eval() == 'reached changed child'
    assert E.order_item(persisted.order_item_list()[0]).customer_order_id().eval() == E.customer_order(target).id().eval()
    foreign_persisted = await load(context, E.customer_order(foreign).id().eval())
    assert E.customer_order(foreign_persisted).description().eval() != 'foreign pending root'
    assert E.order_item(foreign_persisted.order_item_list()[0]).name().eval() != 'unreached pending sibling'


async def descendant(context, platform, service, sink):
    seeded = await seed(context, platform)
    order = await load(context, E.customer_order(seeded).id().eval())
    child = order.order_item_list()[0]
    parent_version = E.customer_order(order).version().eval()
    child.update_name('changed descendant only').audit_as('repair descendant')
    reset(service, sink, context)
    await order.audit_as('save clean ancestor').save(context)
    observe('descendant', service, sink, context)
    assert_writes(service, sink, context, 1)
    assert service.requests[0][2][-1][2] == 'repair descendant'
    assert E.customer_order(order).version().eval() == parent_version
    persisted = await load(context, E.customer_order(order).id().eval())
    assert E.customer_order(persisted).version().eval() == parent_version
    assert E.order_item(persisted.order_item_list()[0]).name().eval() == 'changed descendant only'


async def conflict(context, platform, service, sink):
    seeded = await seed(context, platform)
    old = await load(context, E.customer_order(seeded).id().eval())
    old_child = old.order_item_list()[0]
    advance = await Q.order_items().with_id_is(E.order_item(old_child).id().eval()).limit(1).comment(
        'load child to create a new version').purpose('verify mixed loaded version rejection').execute_for_one(context)
    await advance.update_name('committed newer child').audit_as('advance child independently').save(context)
    current = await load(context, E.customer_order(seeded).id().eval())
    current_child = current.order_item_list()[0]
    assert E.order_item(old_child).version().eval() != E.order_item(current_child).version().eval()
    old_ledger, current_ledger = old_child._entity_root, current_child._entity_root
    old_child.update_name('old pending value')
    current_child.update_name('current pending value')
    old.order_item_list().append(current_child)
    reset(service, sink, context)
    try:
        await old.audit_as('reject conflicting loaded graph').save(context)
    except ValueError as error:
        assert 'ENTITY_VERSION_CONFLICT' in str(error)
    except BaseException:
        observe('conflict', service, sink, context)
        raise
    else:
        raise AssertionError('conflicting loaded versions must be rejected')
    assert service.requests == [] and sink.events == []
    key = EntityKey('OrderItem', E.order_item(old_child).id().eval())
    assert pending(old_ledger, key) and pending(current_ledger, key)
    assert scalar(old_ledger.get(key, 'name')) == 'old pending value'
    assert scalar(current_ledger.get(key, 'name')) == 'current pending value'
    observe('conflict', service, sink, context)


async def main():
    context = UserContext.new().install(GENERATED_RUNTIME_MODULE)
    service = SharedService(create_sqlite_service(os.environ['TEAQL_TRACE_CHAIN_DB']))
    sink = AuditSink(service)
    context.insert_resource('dataService', service).with_app_audit_event_sink(sink)
    context.set_diagnostic_sql_log_sink(type('Silent', (), {'write': lambda self, entry: None})())
    await context.ensure_schema()
    platform = await Q.platforms().with_id_is(1).limit(1).comment('reuse generated root').purpose('attach ownership fixtures').execute_for_one(context)
    checks = {'shared': shared, 'scoped': scoped, 'descendant': descendant, 'conflict': conflict}
    selected = os.environ.get('TEAQL_TRACE_CHAIN_SCENARIO')
    assert selected is None or selected in checks
    for name, check in checks.items():
        if selected is None or selected == name:
            await check(context, platform, service, sink)
            print('PASS TC-OWN-' + name + ': generated Q/E/save, actual SQL and committed audit')
    if selected is None:
        print('PASS: Python shared ownership 4 scenarios')


if __name__ == '__main__':
    asyncio.run(main())
