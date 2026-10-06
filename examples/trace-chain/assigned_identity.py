"""TC-MUT-07: observe assigned identities from generated graph saves, not fixtures."""
import asyncio
import json
import os
import uuid

from E import E
from Q import Q
from runtime_module import GENERATED_RUNTIME_MODULE
from teaql.core.entity import EntityKey
from teaql.provider.sqlite import create_sqlite_service
from teaql.runtime import UserContext

from main import AuditSink, ObservedService, chain, new, reset, scalar


async def load(context, identity):
    return await (Q.customer_orders().with_id_is(identity).limit(1)
        .select_order_item_list_with(Q.order_items().limit(10))
        .comment('load assigned identity graph').purpose('verify generated persistence and lineage')
        .execute_for_one(context))


def verify_sinks(service, sink, context, expected, reason, operation, logging):
    assert service.finishes == ['commit']
    assert len(service.requests) == len(service.results) == len(sink.events) == len(expected)
    assert {(entity, identity): nodes for entity, identity, nodes in service.requests} == expected
    assert {(event.entity, scalar(event.entity_id)): chain(event.trace_chain)
            for event in sink.events} == expected
    for (entity, identity, nodes), metadata in zip(service.requests, service.results):
        assert identity > 0 and chain(metadata.mutation_lineage) == expected[(entity, identity)]
        assert metadata.comment == reason and len(metadata.statements) == 2
        for index, statement in enumerate(metadata.statements):
            assert statement.execution_outcome == 'success'
            assert statement.comment == reason and chain(statement.mutation_lineage) == nodes
            assert statement.result_count == 1 if index else statement.affected_rows == 1
            assert all(node.kind == 'auditReason' and node.entity_id > 0
                       for node in statement.mutation_lineage)
            path = statement.trace_chain
            assert [node.kind for node in path] == [
                'operation', 'request' if index else 'entity', 'provider', 'sql']
            assert [node.name for node in path] == [
                'CustomerOrder', 'CustomerOrder' if index else entity, 'sqlite',
                'select' if index else operation]
    logs = list(context.sql_logs())
    assert len(logs) == (2 * len(expected) if logging else 0)
    if logging:
        assert [chain(entry.mutation_lineage) for entry in logs] == [
            nodes for _, _, nodes in service.requests for _ in range(2)]
        assert all(entry.comment == reason and entry.execution_outcome == 'success' for entry in logs)


async def verify(context, platform, service, sink, logging):
    if logging:
        context.enable_all_sql_log()
    else:
        context.disable_sql_log()
    label = 'ASSIGNED-' + uuid.uuid4().hex
    root = new(Q.customer_orders(), context).update_platform(platform)
    root.update_order_number(label).update_description('new assigned graph')
    annotated = new(Q.order_items(), context).update_customer_order(root).update_name('annotated ' + label)
    sibling = new(Q.order_items(), context).update_customer_order(root).update_name('ordinary ' + label)
    annotated.audit_as('annotated newly allocated child')
    root.order_item_list().extend([annotated, sibling])
    # Observe only native ledger state. No explicit ID assignment or trace injection.
    temporary = [entity._teaql_entity_key() for entity in (root, annotated, sibling)]
    assert all(isinstance(key.id, int) and key.id < 0 for key in temporary)
    assert len(set(temporary)) == 3
    assert all(key in entity._entity_root.new_keys()
               for entity, key in zip((root, annotated, sibling), temporary))
    reset(service, sink, context)
    await root.audit_as('create graph with allocated identities').save(context)
    identities = [E.customer_order(root).id().eval(), E.order_item(annotated).id().eval(),
                  E.order_item(sibling).id().eval()]
    assert all(isinstance(identity, int) and identity > 0 for identity in identities)
    assert identities[1] != identities[2]
    reason = 'create graph with allocated identities'
    root_node = ('CustomerOrder', identities[0], reason)
    expected = {
        ('CustomerOrder', identities[0]): [root_node],
        ('OrderItem', identities[1]): [root_node, ('OrderItem', identities[1], 'annotated newly allocated child')],
        ('OrderItem', identities[2]): [root_node],
    }
    verify_sinks(service, sink, context, expected, reason, 'insert', logging)
    for entity, old, identity in zip((root, annotated, sibling), temporary, identities):
        ledger = entity._entity_root
        assert old not in ledger.new_keys() and not ledger.has_pending(old)
        assert not ledger.has_pending(EntityKey(old.entity, identity))
    print('ASSIGNED_IDENTITY_OBSERVED ' + json.dumps(dict(
        logging=logging, temporary=[(key.entity, key.id) for key in temporary],
        commands=service.requests,
        sql=[dict(comment=item.comment, sql=item.parameterized_sql,
                  parameters=[scalar(value) for value in item.parameters],
                  outcome=item.execution_outcome, result_count=item.result_count,
                  affected_rows=item.affected_rows, lineage=chain(item.mutation_lineage),
                  path=[(node.kind, node.name) for node in item.trace_chain])
             for metadata in service.results for item in metadata.statements],
        audit=[dict(entity=event.entity, id=scalar(event.entity_id), lineage=chain(event.trace_chain))
               for event in sink.events]), sort_keys=True))
    loaded = await load(context, identities[0])
    assert E.customer_order(loaded).order_number().eval() == label
    assert E.customer_order(loaded).version().eval() == 1
    children = {E.order_item(item).id().eval(): item for item in loaded.order_item_list()}
    assert set(children) == set(identities[1:])
    for identity in identities[1:]:
        assert E.order_item(children[identity]).version().eval() == 1
        assert E.order_item(children[identity]).customer_order_id().eval() == identities[0]
    assert E.order_item(children[identities[1]]).name().eval() == 'annotated ' + label
    assert E.order_item(children[identities[2]]).name().eval() == 'ordinary ' + label

    # A fresh loaded graph has no previous operation's local comments.
    loaded.update_description('independent loaded update')
    for item in loaded.order_item_list():
        item.update_name('revised ' + label)
    reset(service, sink, context)
    reason = 'update independently loaded graph'
    await loaded.audit_as(reason).save(context)
    next_expected = {key: [('CustomerOrder', identities[0], reason)] for key in expected}
    verify_sinks(service, sink, context, next_expected, reason, 'update', logging)
    reloaded = await load(context, identities[0])
    assert E.customer_order(reloaded).version().eval() == 2
    assert E.customer_order(reloaded).description().eval() == 'independent loaded update'
    assert {E.order_item(item).id().eval() for item in reloaded.order_item_list()} == set(identities[1:])
    assert all(E.order_item(item).version().eval() == 2 and
               E.order_item(item).name().eval() == 'revised ' + label
               for item in reloaded.order_item_list())
    print(f'PASS: assigned identity logging={logging}; 3 inserts then 3 independent updates')


async def main():
    context = UserContext.new().install(GENERATED_RUNTIME_MODULE)
    service = ObservedService(create_sqlite_service(os.environ['TEAQL_TRACE_CHAIN_DB']))
    sink = AuditSink(service)
    context.insert_resource('dataService', service).with_app_audit_event_sink(sink)
    context.set_diagnostic_sql_log_sink(type('Silent', (), {'write': lambda self, entry: None})())
    await context.ensure_schema()
    platform = await Q.platforms().with_id_is(1).limit(1).comment('reuse bootstrap root').purpose(
        'attach generated assigned identity graph').execute_for_one(context)
    assert platform is not None
    for logging in (False, True):
        await verify(context, platform, service, sink, logging)
    print('PASS: Python generated assigned identity 2 scenarios; command/SQL/audit and independent reload')


if __name__ == '__main__':
    asyncio.run(main())
