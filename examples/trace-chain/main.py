"""Generated Q/E/Mutation traversal observed at three real SQLite boundaries."""
import asyncio
import json
import os
import sqlite3
import uuid

from E import E
from Q import Q
from runtime_module import GENERATED_RUNTIME_MODULE
from teaql.provider.sqlite import create_sqlite_service
from teaql.runtime import UserContext, DelegatingMutationPolicyRegistry
from teaql.core.request_intent import RequestIntentError
from teaql.core.mutation import InsertCommand, UpdateCommand, DeleteCommand
from teaql.sql.executor import TransportError


def chain(nodes):
    return [(node.name or node.entity_type, node.entity_id, node.comment) for node in nodes]


def scalar(value):
    return getattr(value, 'val', value)


def graph_identities(graph):
    order, item, payment, attempt, shipment, removed = graph
    return [
        ('CustomerOrder', E.customer_order(order).id().eval()),
        ('OrderItem', E.order_item(item).id().eval()),
        ('Payment', E.payment(payment).id().eval()),
        ('PaymentAttempt', E.payment_attempt(attempt).id().eval()),
        ('Shipment', E.shipment(shipment).id().eval()),
        ('OrderItem', E.order_item(removed).id().eval()),
    ]


def check_identities(expected, actual, boundary):
    # Check lists before making dictionaries: duplicate rows must not disappear.
    assert len(expected) == len(actual) == 6, boundary + ': six identities required'
    for entity, identity in [*expected, *actual]:
        assert isinstance(entity, str) and entity, boundary + ': entity type required'
        assert type(identity) is int and 0 < identity <= 2**64 - 1, boundary + ': positive u64 ID required'
    assert len(set(expected)) == 6, boundary + ': duplicate expected identity'
    assert len(set(actual)) == 6, boundary + ': duplicate identity'
    assert set(actual) == set(expected), boundary + ': missing or unexpected identity'


def identity_controls():
    expected = [('CustomerOrder', 1), ('OrderItem', 1), ('Payment', 1),
                ('PaymentAttempt', 1), ('Shipment', 1), ('OrderItem', 2)]
    check_identities(expected, expected, 'positive control')
    controls = [expected[:-1] + [expected[1]], expected[:-1],
                [('CustomerOrder' if entity == 'Payment' else entity, identity)
                 for entity, identity in expected]]
    for actual in controls:
        try:
            check_identities(expected, actual, 'negative control')
        except AssertionError:
            pass
        else:
            raise AssertionError('identity negative control was accepted')
    print('PASS: identity controls reject duplicate, missing and equal-ID type collapse')


def physical_identities(service, context):
    """Bind actual ordered SQL facts to independently observed provider commands.

    Canonical SQL paths deliberately do not contain IDs. Readback paths name
    the operation root, not the target. Neither responsibility chain is a key.
    """
    physical = [entry for entry in context.sql_logs() if entry.mutation_lineage]
    assert len(service.requests) == len(service.results) == len(service.actions)
    assert len(physical) == 2 * len(service.requests)
    identities = []
    for index, ((entity, identity, nodes), record, action) in enumerate(
            zip(service.requests, service.results, service.actions)):
        write, read = physical[index * 2:index * 2 + 2]
        assert len(record.statements) == 2
        assert record.affected_rows == write.affected_rows == 1
        assert write.execution_outcome == read.execution_outcome == 'success'
        assert read.result_count == 1 and read.affected_rows is None
        assert [node.kind for node in write.trace_path] == ['operation', 'entity', 'provider', 'sql']
        assert write.trace_path[1].name == entity
        assert write.trace_path[-1].name == action and read.trace_path[-1].name == 'select'
        assert write.trace_path == record.statements[0].trace_chain
        assert read.trace_path == record.statements[1].trace_chain
        assert chain(write.mutation_lineage) == chain(read.mutation_lineage) == nodes
        assert write.comment == read.comment == record.comment
        identities.append((entity, identity))
    return identities


def readback_fact(entry):
    """Project actual safe SQL observations, omitting all parameter values."""
    def nodes(values):
        return [{'Kind': node.kind, 'Name': node.name, 'EntityId': node.entity_id,
                 'Comment': node.comment} for node in values]
    return {'Operation': entry.operation.name, 'Comment': entry.comment,
            'Purpose': entry.purpose, 'AuditReason': entry.audit_reason,
            'ExecutionOutcome': entry.execution_outcome,
            'AffectedRows': entry.affected_rows, 'ResultCount': entry.result_count,
            'StartedAt': entry.started_at.isoformat(), 'EndedAt': entry.ended_at.isoformat(),
            'ParameterizedSQL': entry.sql, 'TraceChain': nodes(entry.trace_path),
            'MutationLineage': nodes(entry.mutation_lineage)}


class ObservedService:
    """Transparent observer, not a replacement planner or provider."""
    def __init__(self, service):
        self.service = service
        self.requests = []
        self.results = []
        self.actions = []
        self.finishes = []
        self.queries = []
        self.raw_requests = []
        self.begins = 0
        self.fault = None

    def __getattr__(self, name):
        return getattr(self.service, name)

    async def query(self, context, request):
        result = await self.service.query(context, request)
        self.queries.append((request, result.metadata))
        return result

    async def begin(self, context):
        self.begins += 1
        transaction = await self.service.begin(context)
        return ObservedTransaction(self, transaction)


class ObservedTransaction:
    def __init__(self, owner, transaction):
        self.owner, self.transaction = owner, transaction
        for method_name in ('execute_sql', 'fetch_all_sql'):
            original = getattr(transaction.transport, method_name)
            async def intercepted(compiled, original=original, method_name=method_name):
                if self.owner.fault == method_name and 'payment_attempt_data' in compiled.sql:
                    raise RuntimeError('synthetic payment attempt failure')
                return await original(compiled)
            setattr(transaction.transport, method_name, intercepted)

    def __getattr__(self, name):
        return getattr(self.transaction, name)

    async def mutate(self, context, request):
        command = request._data
        self.owner.raw_requests.append(request)
        identity = scalar(getattr(command, 'id', None) or command.values.get('id'))
        self.owner.requests.append((command.entity, identity, chain(request.mutation_lineage)))
        self.owner.actions.append({InsertCommand: 'insert', UpdateCommand: 'update',
                                   DeleteCommand: 'delete'}[type(command)])
        result = await self.transaction.mutate(context, request)
        self.owner.results.append(result.metadata)
        return result

    async def commit(self, context):
        await self.transaction.commit(context)
        self.owner.finishes.append('commit')

    async def rollback(self, context):
        await self.transaction.rollback(context)
        self.owner.finishes.append('rollback')


class AuditSink:
    def __init__(self, service):
        self.service, self.events = service, []

    def on_safe_event(self, context, event):
        assert self.service.finishes[-1] == 'commit', 'audit escaped before database commit'
        self.events.append(event)


def new(request, context):
    return request.comment('what: construct a trace example entity').purpose(
        'why: verify generated graph behavior').new_entity(context)


def make_graph(context, platform, label):
    order = new(Q.customer_orders(), context).update_platform(platform)
    order.update_order_number(label).update_description('Trace example draft')
    available = new(Q.order_items(), context).update_customer_order(order).update_name('Available item')
    removed = new(Q.order_items(), context).update_customer_order(order).update_name('Unavailable item')
    payment = new(Q.payments(), context).update_customer_order(order).update_reference_code(label + '-payment')
    attempt = new(Q.payment_attempts(), context).update_payment(payment).update_reference_code(label + '-attempt')
    shipment = new(Q.shipments(), context).update_customer_order(order).update_reference_code(label + '-shipment')
    payment.payment_attempt_list().append(attempt)
    order.order_item_list().extend([available, removed])
    order.payment_list().append(payment)
    order.shipment_list().append(shipment)
    return order, available, payment, attempt, shipment, removed


def expected_graph(graph, reason):
    order, item, payment, attempt, shipment, removed = graph
    root = ('CustomerOrder', E.customer_order(order).id().eval(), reason)
    payment_node = ('Payment', E.payment(payment).id().eval(), 'authorize payment')
    shipment_node = ('Shipment', E.shipment(shipment).id().eval(), 'dispatch shipment')
    deleted_node = ('OrderItem', E.order_item(removed).id().eval(), 'remove unavailable item')
    return {
        ('CustomerOrder', root[1]): [root],
        ('OrderItem', E.order_item(item).id().eval()): [root],
        ('Payment', payment_node[1]): [root, payment_node],
        ('PaymentAttempt', E.payment_attempt(attempt).id().eval()): [root, payment_node],
        ('Shipment', shipment_node[1]): [root, shipment_node],
        ('OrderItem', deleted_node[1]): [root, deleted_node],
    }


def reset(service, sink, context):
    service.requests.clear()
    service.results.clear()
    service.actions.clear()
    service.finishes.clear()
    service.queries.clear()
    service.raw_requests.clear()
    service.begins = 0
    sink.events.clear()
    context.clear_sql_logs()


async def verify_bootstrap(path, logging):
    """Observe generated startup without supplying caller intent or trace frames."""
    context = UserContext.new().install(GENERATED_RUNTIME_MODULE)
    context.with_user_identifier('trace-example-user')
    service = ObservedService(create_sqlite_service(path))
    sink = AuditSink(service)
    context.insert_resource('dataService', service).with_app_audit_event_sink(sink)
    context.set_diagnostic_sql_log_sink(type('Silent', (), {'write': lambda self, entry: None})())
    if not logging:
        context.disable_sql_log()
    await context.ensure_schema()
    first_queries = tuple(service.queries)
    first_requests = tuple(service.raw_requests)
    first_results = tuple(service.results)
    first_audits = tuple(sink.events)
    first_sql = tuple(context.sql_logs())
    assert first_queries, 'observe generated bootstrap lookup even with logging disabled'
    first_intent = first_queries[0][1].comment
    first_purpose = first_queries[0][1].purpose
    assert first_intent and first_intent.strip(), 'bootstrap owns a nonblank lookup comment'
    assert first_purpose and first_purpose.strip(), 'bootstrap owns a nonblank lookup purpose'
    assert len(first_requests) == len(first_results) == len(first_audits) <= 1
    for request, result, event in zip(first_requests, first_results, first_audits):
        assert request.comment() and request.comment().strip()
        assert chain(request.mutation_lineage) == [('Platform', 1, request.comment())]
        assert result.comment == request.comment()
        assert len(result.statements) == 2 and result.affected_rows == 1
        assert event.actor == 'teaql-generated-bootstrap' and event.category == 'runtime-bootstrap'
        assert event.entity == 'Platform' and scalar(event.entity_id) == 1
        assert chain(event.trace_chain) == [('Platform', 1, request.comment().replace('1', '[REDACTED]'))], 'safe bootstrap audit preserves responsibility while redacting identity text'
        for statement in result.statements:
            assert statement.comment == request.comment()
            assert statement.execution_outcome == 'success'
            assert chain(statement.mutation_lineage) == chain(request.mutation_lineage)
        assert result.statements[1].result_count == 1
        assert result.statements[1].purpose and result.statements[1].purpose.strip()
    # The sink already checks that audit followed commit. Independently verify
    # the resulting row through a read-only connection, not the runtime cache.
    with sqlite3.connect('file:' + os.path.abspath(path) + '?mode=ro', uri=True) as connection:
        assert connection.execute('SELECT id, version FROM platform_data WHERE id = 1').fetchall() == [(1, 1)]
    reset(service, sink, context)
    await context.ensure_schema()
    assert service.raw_requests == [] and service.results == [] and sink.events == [], 'repeat bootstrap cannot write or audit'
    assert service.queries, 'repeat bootstrap must inspect persisted root'
    for _, metadata in (*first_queries, *service.queries):
        assert metadata.comment == first_intent, 'generated bootstrap lookup intent is stable'
        assert metadata.purpose == first_purpose
        assert metadata.execution_outcome == 'success'
        assert [node.kind for node in metadata.trace_chain] == ['operation', 'request', 'provider', 'sql']
        assert metadata.trace_chain[0].name == 'Platform'
    if logging:
        assert len(first_sql) == len(first_queries) + 2 * len(first_requests)
        assert len(context.sql_logs()) == len(service.queries)
        for entry in (*first_sql, *context.sql_logs()):
            select = entry.operation.name.lower() == 'select'
            assert [node.kind for node in entry.trace_path] == ['operation', 'request' if select else 'entity', 'provider', 'sql']
            assert entry.comment and entry.comment.strip()
            if select:
                assert entry.purpose and entry.purpose.strip()
            if entry.mutation_lineage:
                assert len(first_audits) == 1
                assert chain(entry.mutation_lineage) == chain(first_audits[0].trace_chain)
                assert entry.audit_reason == first_audits[0].trace_chain[0].comment
    else:
        assert first_sql == () and context.sql_logs() == []
    assert context.user_identifier() == 'trace-example-user', 'bootstrap must restore caller identity'
    print('BOOTSTRAP INTENT EVIDENCE ' + json.dumps({'logging': logging,
          'first_writes': len(first_requests), 'repeat_writes': 0,
          'comment': first_intent, 'purpose': first_purpose,
          'queries': len(first_queries) + len(service.queries)}))
    reset(service, sink, context)
    return context, service, sink


async def main():
    identity_controls()
    path = os.environ['TEAQL_TRACE_CHAIN_DB']
    label = 'TRACE-' + uuid.uuid4().hex[:16]
    await verify_bootstrap(path + '.bootstrap-off', False)
    context, service, sink = await verify_bootstrap(path, True)
    policy_calls = []
    def resolve_policy(request_key):
        policy_calls.append(request_key)
        return None  # Observe the configured resolver; retain generated-default governance.
    context.with_mutation_policy_registry(DelegatingMutationPolicyRegistry(resolve_policy))
    platforms = await Q.platforms().with_id_is(1).limit(1).comment(
        'what: reuse bootstrap root').purpose('why: attach trace example').execute_for_list(context)
    assert len(platforms) == 1
    platform = platforms[0]

    rejected = make_graph(context, platform, label + '-rejected')
    rejected[2].audit_as('valid child reason cannot substitute for root')
    reset(service, sink, context)
    policy_calls.clear()
    for reason in (None, '', ' \t'):
        try:
            if reason is None:
                await rejected[0].save(context)
            else:
                await rejected[0].audit_as(reason).save(context)
        except RequestIntentError as error:
            assert error.code == 'REQUEST_COMMENT_REQUIRED'
        else:
            raise AssertionError('missing root reason was accepted')
    assert service.begins == 0 and service.requests == [] and sink.events == [] and policy_calls == []
    print('PASS: missing/empty/blank root intent rejected before any transaction, despite valid child intent')

    graph = make_graph(context, platform, label)
    order, item, payment, attempt, shipment, removed = graph
    reset(service, sink, context)
    await order.audit_as('prepare complete graph').save(context)
    created = graph_identities(graph)
    check_identities(created, [(entity, identity) for entity, identity, _ in service.requests], 'created commands')
    check_identities(created, physical_identities(service, context), 'created physical SQL')
    check_identities(created, [(event.entity, scalar(event.entity_id)) for event in sink.events], 'created audit')
    assert E.payment(payment).id().eval() == E.customer_order(order).id().eval(), 'fixture must exercise equal IDs of different types'
    order.update_description('Submitted trace example')
    item.update_name('Verified available item')
    payment.update_reference_code(label + '-payment-authorized').audit_as('authorize payment')
    attempt.update_reference_code(label + '-attempt-authorized')
    shipment.update_reference_code(label + '-shipment-dispatched').audit_as('dispatch shipment')
    removed.mark_for_deletion().audit_as('remove unavailable item')
    reset(service, sink, context)
    await order.audit_as('submit order').save(context)
    want_identities = graph_identities(graph)
    command_identities = [(entity, identity) for entity, identity, _ in service.requests]
    statement_identities = physical_identities(service, context)
    committed_identities = [(event.entity, scalar(event.entity_id)) for event in sink.events]
    check_identities(want_identities, command_identities, 'actual commands')
    check_identities(want_identities, statement_identities, 'command-bound physical SQL')
    check_identities(want_identities, committed_identities, 'committed audit')
    print('GRAPH IDENTITY EVIDENCE ' + json.dumps({
        name: [{'entity': entity, 'id': identity} for entity, identity in values]
        for name, values in [('expected', want_identities), ('commands', command_identities),
                             ('physical', statement_identities), ('audit', committed_identities)]
    }, sort_keys=True))
    expected = expected_graph(graph, 'submit order')
    commands = {(entity, identity): nodes for entity, identity, nodes in service.requests}
    metadata = {(entity, identity): chain(item.mutation_lineage)
                for (entity, identity, _), item in zip(service.requests, service.results)}
    audits = {(event.entity, scalar(event.entity_id)): chain(event.trace_chain) for event in sink.events}
    assert len(service.raw_requests) == len(service.requests) == len(service.results) == len(sink.events) == 6
    assert commands == metadata == audits == expected
    for request, record in zip(service.raw_requests, service.results):
        assert record.trace_chain[0].name == 'CustomerOrder'
        assert [node.kind for node in record.trace_chain] == ['operation', 'entity', 'provider', 'sql']
        assert all(node.kind == 'auditReason' for node in record.mutation_lineage)
        assert len(record.statements) == 2
        write, read = record.statements
        assert not write.statements and not read.statements
        assert request.comment() == 'submit order'
        assert read.comment == write.comment == request.comment(), 'derived readback inherits actual mutation comment'
        assert read.audit_reason == write.audit_reason == request.comment(), 'derived readback inherits root audit reason'
        assert read.purpose == 'verify the persisted mutation result', 'derived readback owns verification purpose'
        assert read.mutation_lineage == write.mutation_lineage == record.mutation_lineage
        assert read.result_count == 1 and read.affected_rows is None
        assert read.execution_outcome == 'success'
        assert [node.kind for node in read.trace_chain] == ['operation', 'request', 'provider', 'sql']
        assert [node.name for node in read.trace_chain] == ['CustomerOrder', 'CustomerOrder', 'sqlite', 'select']
        assert read.trace_chain[0].comment == 'query'
        assert write.ended_at <= read.started_at, 'physical write precedes its authoritative readback'
    print('TC-REQ-10 PYTHON READBACK EVIDENCE ' + json.dumps({
        'case': 'TC-REQ-10', 'writes': 6, 'readbacks': 6,
        'statements': [readback_fact(entry) for entry in context.sql_logs()],
    }, sort_keys=True))
    print('PASS: six writes plus six successful readbacks; root request paths; no duplicate SQL facts')
    print('PASS: normative six items; assigned typed identity; branch/deletion reasons; request/SQL/audit boundaries')

    loaded = await (Q.customer_orders().with_id_is(E.customer_order(order).id().eval())
        .select_order_item_list_with(Q.order_items().limit(10))
        .select_payment_list_with(Q.payments().limit(10)
            .select_payment_attempt_list_with(Q.payment_attempts().limit(10)))
        .select_shipment_list_with(Q.shipments().limit(10)).limit(1)
        .comment('what: reload committed trace graph').purpose('why: verify generated Q and loaded E').execute_for_one(context))
    assert E.customer_order(loaded).order_number().eval() == label
    assert E.customer_order(loaded).order_item_list().size().eval() == 1
    assert E.customer_order(loaded).payment_list().size().eval() == 1
    deleted = await Q.order_items().with_id_is(E.order_item(removed).id().eval()).deleted_rows_only().limit(1).comment(
        'what: verify retained deletion').purpose('why: test graph save soft deletion').execute_for_one(context)
    assert E.order_item(deleted).version().eval() < 0
    print('PASS: generated Q graph reload; loaded E; deleted row retained and hidden')

    reset(service, sink, context)
    deep = await (Q.payment_attempts().with_id_is(E.payment_attempt(attempt).id().eval())
        .select_payment_with(Q.payments().limit(1).select_customer_order_with(
            Q.customer_orders().limit(1).select_platform_with(Q.platforms().limit(1))))
        .limit(1).comment('what: inspect three relation levels').purpose('why: retain root query intent').execute_for_one(context))
    assert E.payment_attempt(deep).reference_code().eval() == label + '-attempt-authorized'
    entries = context.sql_logs()
    assert len(entries) == 4
    for depth, entry in enumerate(entries):
        assert entry.comment == 'what: inspect three relation levels'
        assert entry.purpose == 'why: retain root query intent'
        assert entry.trace_path[0].name == 'PaymentAttempt'
        assert [node.name for node in entry.trace_path[2:-2]] == ['payment', 'customer_order', 'platform'][:depth]
        route = [('payment', 'PaymentAttempt.payment'), ('customer_order', 'Payment.customer_order'),
                 ('platform', 'CustomerOrder.platform')]
        assert [(node.kind, node.name, node.comment) for node in entry.trace_path] == [
            ('operation', 'PaymentAttempt', 'query'), ('request', 'PaymentAttempt', ''),
            *[('relation', name, detail) for name, detail in route[:depth]],
            ('provider', 'sqlite', ''), ('sql', 'select', '')], 'canonical generated path at every physical boundary'
    print('PASS: generated query traverses three actual relations with inherited intent')

    graphs = [make_graph(context, platform, label + '-' + name) for name in ('first', 'second')]
    reset(service, sink, context)
    await asyncio.gather(*(g[0].audit_as('independent ' + name).save(context)
        for g, name in zip(graphs, ('first', 'second'))))
    assert service.finishes == ['commit', 'commit'] and len(sink.events) == 12
    roots = {E.customer_order(g[0]).id().eval(): 'independent ' + name
             for g, name in zip(graphs, ('first', 'second'))}
    assert all(chain(event.trace_chain) == [('CustomerOrder', chain(event.trace_chain)[0][1],
                roots[chain(event.trace_chain)[0][1]])] for event in sink.events)
    concurrent_physical = physical_identities(service, context)
    for graph in graphs:
        root_id = E.customer_order(graph[0]).id().eval()
        expected = graph_identities(graph)
        indices = [index for index, (_, _, nodes) in enumerate(service.requests) if nodes[0][1] == root_id]
        check_identities(expected, [service.requests[index][:2] for index in indices], 'concurrent commands')
        check_identities(expected, [concurrent_physical[index] for index in indices], 'concurrent physical SQL')
        check_identities(expected, [(event.entity, scalar(event.entity_id)) for event in sink.events
                                   if chain(event.trace_chain)[0][1] == root_id], 'concurrent audit')
    assert context.require_resource('dataService') is service
    print('PASS: two concurrent generated graph saves in one real Context remain isolated')

    for failure in ('execute_sql', 'fetch_all_sql'):
        failed = make_graph(context, platform, label + '-' + failure)
        failed[2].audit_as('authorize failing payment')
        reset(service, sink, context)
        service.fault = failure
        try:
            await failed[0].audit_as('attempt failing graph').save(context)
        except (TransportError, RuntimeError) as error:
            actual = error.error if isinstance(error, TransportError) else error
            assert str(actual) == 'synthetic payment attempt failure'
        else:
            raise AssertionError('injected failure did not interrupt graph')
        finally:
            service.fault = None
        assert service.finishes == ['rollback'] and sink.events == []
        evidence = context.sql_logs()
        assert evidence[-1].execution_outcome == 'failure'
        assert evidence[-1].mutation_lineage[-1].comment == 'authorize failing payment'
        if failure == 'fetch_all_sql':
            assert evidence[-2].execution_outcome == 'success'
            assert evidence[-2].trace_path[-1].name == 'insert'
            assert evidence[-1].trace_path[-1].name == 'select'
        print('PASS: ' + failure + ' failure retains lineage, rolls back and emits zero committed audit')
    print('PASS: generated library unchanged; all trace example checks passed')


if __name__ == '__main__':
    asyncio.run(main())
