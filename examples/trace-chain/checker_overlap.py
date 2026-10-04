"""Real generated Checker overlap; app observers never synthesize validation or traces."""
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
from teaql.runtime.i18n import CheckException

from main import AuditSink, ObservedTransaction, chain, reset, scalar
from shared_reference import SharedService, pending, seed


class ObservedContext(UserContext):
    def __init__(self):
        super().__init__()
        self.observation = dict(active=0, peak=0, callbacks=0, callback_peak=0, checks=[])

    async def execute_graph_save(self, work, *, comment=None):
        state = self.observation
        state['active'] += 1
        state['peak'] = max(state['peak'], state['active'])

        async def observed(session):
            state['callbacks'] += 1
            state['callback_peak'] = max(state['callback_peak'], state['callbacks'])
            session.transaction.entry['reason'] = comment
            try:
                return await work(session)
            finally:
                state['callbacks'] -= 1

        try:
            return await super().execute_graph_save(observed, comment=comment)
        finally:
            state['active'] -= 1


class ObservedRegistry:
    def __init__(self, delegate, state):
        self.delegate, self.state = delegate, state

    def checker(self, entity):
        delegate = self.delegate.checker(entity)
        if delegate is None:
            return None
        state = self.state

        class Checker:
            def check_and_fix(self, context, record, location, results):
                before = len(results)
                delegate.check_and_fix(context, record, location, results)
                state['checks'].append({
                    'entity': entity,
                    'reason': context._graph_session.intent.comment,
                    'violations': [result.to_wire() for result in results[before:]],
                })

        return Checker()


class Transaction(ObservedTransaction):
    def __init__(self, owner, transaction):
        super().__init__(owner, transaction)
        self.entry = dict(reason=None, outcome='pending', physical=[])
        owner.transactions.append(self.entry)
        for name in ('execute_sql', 'fetch_all_sql'):
            delegate = getattr(transaction.transport, name)

            async def observed(compiled, delegate=delegate, name=name):
                self.entry['physical'].append(dict(
                    method=name, sql=compiled.sql, params=[scalar(value) for value in compiled.params]))
                return await delegate(compiled)

            setattr(transaction.transport, name, observed)

    async def mutate(self, context, request):
        self.owner.request_comments.append(request.comment())
        return await super().mutate(context, request)

    async def commit(self, context):
        await super().commit(context)
        self.entry['outcome'] = 'commit'

    async def rollback(self, context):
        await super().rollback(context)
        self.entry['outcome'] = 'rollback'


class Service(SharedService):
    def __init__(self, service):
        super().__init__(service)
        self.transactions = []
        self.request_comments = []

    async def begin(self, context):
        pause, self.pause = self.pause, None
        if pause:
            entered, release = pause
            entered.set()
            await asyncio.wait_for(release.wait(), 10)
        self.begins += 1
        return Transaction(self, await self.service.begin(context))


async def load(context, identity):
    return await (Q.customer_orders().with_id_is(identity)
        .select_platform_with(Q.platforms().limit(1))
        .select_order_item_list_with(Q.order_items().limit(10)).limit(1)
        .comment('load complete Checker graph').purpose('preserve versions and readonly references')
        .execute_for_one(context))


def clear(context, service, sink):
    reset(service, sink, context)
    service.transactions.clear()
    service.request_comments.clear()
    state = context.observation
    assert state['active'] == state['callbacks'] == 0
    state['peak'] = state['callback_peak'] = 0
    state['checks'].clear()


async def verify(context, platform, service, sink, logging, invalid_first):
    if logging:
        context.enable_all_sql_log()
    else:
        context.disable_sql_log()
    accepted, rejected = await seed(context, platform), await seed(context, platform)
    accepted_id, rejected_id = E.customer_order(accepted).id().eval(), E.customer_order(rejected).id().eval()
    service.platform_snapshot = None
    service.snapshot_uses = 0
    service.reuse_platform = True
    try:
        accepted, rejected = await load(context, accepted_id), await load(context, rejected_id)
    finally:
        service.reuse_platform = False
    assert service.snapshot_uses == 2
    snapshot = copy.deepcopy(service.platform_snapshot)
    left = E.customer_order(accepted).platform().eval()
    right = E.customer_order(rejected).platform().eval()
    assert accepted._entity_root is not rejected._entity_root
    assert left is not right and left._entity_root is not right._entity_root
    platform_version = E.platform(left).version().eval()
    original_description = E.customer_order(rejected).description().eval()
    original_version = E.customer_order(rejected).version().eval()
    nonce = uuid.uuid4().hex.translate(str.maketrans('0123456789', 'ghijklmnop'))
    accepted_secret, rejected_secret = 'PRIVATE-ACCEPT-' + nonce, 'PRIVATE-REJECT-' + nonce
    accepted_reason = f'accept {accepted_secret}; unrelated {rejected_secret}'
    rejected_reason = f'reject {rejected_secret}'
    accepted.update_description(accepted_secret)
    child = accepted.order_item_list()[0]
    child.update_name('accepted-child-' + nonce).audit_as('accepted child responsibility')
    rejected.update_description(rejected_secret)
    # An existing child avoids unrelated ID allocation before validation.
    rejected.order_item_list()[0].update_name(None).audit_as('rejected child responsibility')
    clear(context, service, sink)
    entered, release = asyncio.Event(), asyncio.Event()
    service.pause = (entered, release)
    ordered = [(rejected, rejected_reason), (accepted, accepted_reason)] if invalid_first else [
        (accepted, accepted_reason), (rejected, rejected_reason)]
    first = asyncio.create_task(ordered[0][0].audit_as(ordered[0][1]).save(context))
    await asyncio.wait_for(entered.wait(), 10)
    second = asyncio.create_task(ordered[1][0].audit_as(ordered[1][1]).save(context))
    await asyncio.sleep(0)
    assert not first.done() and not second.done()
    assert context._graph_save_lock.locked()
    assert context.observation['peak'] == 2, 'two real public Save calls must be live'
    release.set()
    results = await asyncio.wait_for(asyncio.gather(first, second, return_exceptions=True), 15)
    valid_result, invalid_result = (results[1], results[0]) if invalid_first else results
    assert not isinstance(valid_result, BaseException), repr(valid_result)
    assert isinstance(invalid_result, CheckException), repr(invalid_result)
    assert any(result.rule_id.upper() == 'REQUIRED' and result.location.native_path == 'order_item_list[0].name'
               for result in invalid_result.violations), str(invalid_result)
    assert context.observation['callback_peak'] == 1, 'the existing graph gate serializes Checker callbacks'
    checks = context.observation['checks']
    assert any(check['reason'] == rejected_reason and check['entity'] == 'OrderItem'
               and check['violations'] for check in checks)
    assert any(check['reason'] == accepted_reason and check['entity'] == 'OrderItem'
               and not check['violations'] for check in checks)
    expected = [[('CustomerOrder', accepted_id, accepted_reason)],
                [('CustomerOrder', accepted_id, accepted_reason),
                 ('OrderItem', E.order_item(child).id().eval(), 'accepted child responsibility')]]
    assert service.requests == [('CustomerOrder', accepted_id, expected[0]),
                                ('OrderItem', E.order_item(child).id().eval(), expected[1])]
    assert service.request_comments == [accepted_reason, accepted_reason]
    assert len(service.results) == len(sink.events) == 2
    physical = [statement for result in service.results for statement in result.statements]
    assert len(physical) == 4
    assert [chain(statement.mutation_lineage) for statement in physical] == [
        expected[0], expected[0], expected[1], expected[1]]
    assert all(statement.comment == accepted_reason and statement.execution_outcome == 'success'
               for statement in physical)
    for index, statement in enumerate(physical):
        assert [node.kind for node in statement.trace_chain] == [
            'operation', 'request' if index % 2 else 'entity', 'provider', 'sql']
        assert statement.trace_chain[0].name == 'CustomerOrder'
        assert [node.name for node in statement.trace_chain[-2:]] == ['sqlite', 'select' if index % 2 else 'update']
        assert statement.result_count == 1 if index % 2 else statement.affected_rows == 1
    assert len(service.transactions) == 2
    failed = next(item for item in service.transactions if item['reason'] == rejected_reason)
    committed = next(item for item in service.transactions if item['reason'] == accepted_reason)
    assert failed['outcome'] == 'rollback' and failed['physical'] == [], failed
    assert committed['outcome'] == 'commit' and len(committed['physical']) == 4
    assert accepted_secret in committed['physical'][0]['params'], 'real SQL values are unchanged'
    assert [(event.entity, scalar(event.entity_id)) for event in sink.events] == [
        ('CustomerOrder', accepted_id), ('OrderItem', E.order_item(child).id().eval())]
    safe_expected = []
    for event, lineage in zip(sink.events, expected):
        reason = chain(event.trace_chain)[0][2]
        assert accepted_secret not in repr(event) and rejected_secret in reason
        safe_lineage = [('CustomerOrder', accepted_id, reason), *lineage[1:]]
        assert chain(event.trace_chain) == safe_lineage
        safe_expected.append(safe_lineage)
    logs = list(context.sql_logs())
    assert len(logs) == (4 if logging else 0)
    for index, entry in enumerate(logs):
        assert accepted_secret not in repr(entry) and rejected_secret in entry.comment
        assert entry.trace_path[0].name == 'CustomerOrder'
        assert chain(entry.mutation_lineage) == safe_expected[index // 2]
    assert service.platform_snapshot == snapshot
    assert E.platform(left).version().eval() == E.platform(right).version().eval() == platform_version
    for reference in (left, right):
        assert not pending(reference._entity_root, EntityKey('Platform', E.platform(reference).id().eval()))
    assert context.get_resource('fix_time') is None and context._graph_session is None
    assert context._checked_mutations == set() and context._fix_evidence_current == []
    proof = dict(logging=logging, invalidFirst=invalid_first, publicOverlap=context.observation['peak'],
                 serializedCallbacks=context.observation['callback_peak'], checks=copy.deepcopy(checks),
                 commands=copy.deepcopy(service.requests), transactions=copy.deepcopy(service.transactions),
                 committedAudit=[dict(entity=event.entity, identity=scalar(event.entity_id),
                                      lineage=chain(event.trace_chain)) for event in sink.events],
                 sql=[dict(comment=entry.comment, lineage=chain(entry.mutation_lineage)) for entry in logs])
    stored_valid, stored_invalid = await load(context, accepted_id), await load(context, rejected_id)
    assert E.customer_order(stored_valid).description().eval() == accepted_secret
    assert E.order_item(stored_valid.order_item_list()[0]).name().eval() == 'accepted-child-' + nonce
    assert E.customer_order(stored_invalid).description().eval() == original_description
    assert E.customer_order(stored_invalid).version().eval() == original_version
    assert len(stored_invalid.order_item_list()) == 1
    assert E.platform(E.customer_order(stored_invalid).platform().eval()).version().eval() == platform_version
    assert pending(rejected._entity_root, EntityKey('CustomerOrder', rejected_id))
    assert E.customer_order(rejected).description().eval() == rejected_secret
    clear(context, service, sink)
    next_reason = f'independent after rejection {accepted_secret} {rejected_secret}'
    stored_invalid.update_description('independent committed value')
    await stored_invalid.audit_as(next_reason).save(context)
    next_lineage = [('CustomerOrder', rejected_id, next_reason)]
    assert service.requests == [('CustomerOrder', rejected_id, next_lineage)]
    assert service.request_comments == [next_reason]
    assert len(sink.events) == 1 and chain(sink.events[0].trace_chain) == next_lineage
    assert [chain(item.mutation_lineage) for item in service.results[0].statements] == [next_lineage, next_lineage]
    assert len(context.sql_logs()) == (2 if logging else 0)
    for entry in context.sql_logs():
        assert entry.comment == next_reason
    assert E.customer_order(await load(context, rejected_id)).description().eval() == 'independent committed value'
    print('CHECKER EVIDENCE ' + json.dumps(dict(proof, nextIndependentSave='committed', sharedReadonlyReference=True)))


async def main():
    context = ObservedContext().install(GENERATED_RUNTIME_MODULE)
    registry = context.get_resource('checker_registry')
    assert registry.checker('CustomerOrder') is not None and registry.checker('OrderItem') is not None
    context.set_checker_registry(ObservedRegistry(registry, context.observation))
    service = Service(create_sqlite_service(os.environ['TEAQL_TRACE_CHAIN_DB']))
    sink = AuditSink(service)
    context.insert_resource('dataService', service).with_app_audit_event_sink(sink)
    context.set_diagnostic_sql_log_sink(type('Silent', (), {'write': lambda self, entry: None})())
    context.configure_audit_policy('CustomerOrder', ['description'])
    await context.ensure_schema()
    platform = await Q.platforms().with_id_is(1).limit(1).comment('reuse generated root').purpose(
        'attach generated Checker fixtures').execute_for_one(context)
    for logging in (False, True):
        for invalid_first in (False, True):
            await verify(context, platform, service, sink, logging, invalid_first)
    print('PASS: Python generated Checker overlap 4 scenarios; accepted-only command/SQL/audit; serialized callbacks')


if __name__ == '__main__':
    asyncio.run(main())
