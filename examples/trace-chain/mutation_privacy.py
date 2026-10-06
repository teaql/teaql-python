"""Generated save privacy; no generated source inspection or synthetic traces."""
import asyncio
import json
import os
import uuid

from E import E
from Q import Q
from runtime_module import GENERATED_RUNTIME_MODULE
from teaql.provider.sqlite import create_sqlite_service
from teaql.runtime import UserContext

from main import AuditSink, ObservedService, new, reset, readback_fact, scalar


def complete_lineage(nodes, root_id, reason, boundary):
    """Empty/redacted-away responsibility is not a successful privacy projection."""
    assert len(nodes) == 1, boundary + ': complete typed root lineage required'
    node = nodes[0]
    assert (node.kind, node.name, node.entity_id, node.comment) == (
        'auditReason', 'CustomerOrder', root_id, reason), boundary + ': wrong root responsibility'


def assert_private_lineage(service, sink, context, root_id, reason, identities, secrets,
                           expected_bindings, phase):
    safe_reason = reason
    for secret in secrets:
        safe_reason = safe_reason.replace(secret, '[REDACTED]')
    expected = set(identities)
    assert len(expected) == len(identities), 'privacy graph needs distinct typed identities'
    count = len(identities)
    assert len(service.raw_requests) == len(service.results) == len(sink.events) == count
    assert service.finishes == ['commit'], 'privacy graph must commit before audit delivery'
    assert len(context.sql_logs()) == count * 2
    commands = []
    seen = set()
    for request, result in zip(service.raw_requests, service.results):
        command = request._data
        identity = (command.entity, scalar(getattr(command, 'id', None) or command.values.get('id')))
        assert identity in expected and identity not in seen, 'actual privacy command identity mismatch'
        seen.add(identity)
        assert request.comment() == result.comment == reason, 'privacy must not rewrite command reason'
        complete_lineage(request.mutation_lineage, root_id, reason, 'raw privacy command')
        complete_lineage(result.mutation_lineage, root_id, reason, 'raw provider mutation')
        assert len(result.statements) == 2 and result.statements[0].affected_rows == 1
        for field, value in expected_bindings.get(command.entity, {}).items():
            assert scalar(command.values[field]) == value, 'privacy must not rewrite command bindings'
            assert value in [scalar(parameter) for parameter in result.statements[0].parameters], 'privacy must not rewrite provider parameters'
        commands.append({'entity': identity[0], 'id': identity[1], 'comment': request.comment(),
                         'lineage': readback_nodes(request.mutation_lineage)})
    assert seen == expected
    for index, (request, result) in enumerate(zip(service.raw_requests, service.results)):
        write, read = context.sql_logs()[index * 2:index * 2 + 2]
        for fact in (write, read):
            complete_lineage(fact.mutation_lineage, root_id, safe_reason, 'safe privacy SQL')
            assert fact.comment == fact.audit_reason == safe_reason, 'safe SQL must retain public reason'
            assert fact.execution_outcome == 'success'
            assert [node.kind for node in fact.trace_path] == [
                'operation', 'entity' if fact is write else 'request', 'provider', 'sql']
            assert fact.trace_path[0].name == 'CustomerOrder'
            assert fact.trace_path[2].name == 'sqlite'
        assert write.trace_path[1].name == request._data.entity
        assert write.trace_path[-1].name == service.actions[index]
        assert read.trace_path[-1].name == 'select'
        assert write.affected_rows == read.result_count == 1 and read.affected_rows is None
        assert read.purpose == 'verify the persisted mutation result'
        assert write.ended_at <= read.started_at
        assert not result.statements[0].statements and not result.statements[1].statements
    audits = []
    seen = set()
    for event in sink.events:
        identity = (event.entity, scalar(event.entity_id))
        assert identity in expected and identity not in seen, 'committed privacy audit identity mismatch'
        seen.add(identity)
        complete_lineage(event.trace_chain, root_id, safe_reason, 'safe privacy audit')
        audits.append({'entity': identity[0], 'id': identity[1],
                       'lineage': readback_nodes(event.trace_chain)})
    assert seen == expected
    for secret in secrets:
        assert secret not in repr(context.sql_logs()) and secret not in repr(sink.events)
    print('PRIVATE_LINEAGE_OBSERVED ' + json.dumps({
        'phase': phase, 'rootId': root_id, 'rawReason': reason, 'safeReason': safe_reason,
        'commands': commands, 'sql': [readback_fact(fact) for fact in context.sql_logs()],
        'audit': audits}, sort_keys=True))
    print('PASS Python complete private lineage: raw commands, safe SQL/readback and committed audit')


def readback_nodes(nodes):
    return [{'Kind': node.kind, 'Name': node.name, 'EntityId': node.entity_id,
             'Comment': node.comment} for node in nodes]


async def main():
    context = UserContext.new().install(GENERATED_RUNTIME_MODULE)
    service = ObservedService(create_sqlite_service(os.environ['TEAQL_TRACE_CHAIN_DB']))
    sink = AuditSink(service)
    context.insert_resource('dataService', service).with_app_audit_event_sink(sink)
    context.set_diagnostic_sql_log_sink(type('Silent', (), {'write': lambda self, entry: None})())
    context.configure_audit_policy('Payment', ['reference_code'])
    await context.ensure_schema()
    platform = await Q.platforms().with_id_is(1).limit(1).comment('reuse seeded root').purpose(
        'attach generated privacy graph').execute_for_one(context)
    label = 'PRIVACY-' + uuid.uuid4().hex[:16]
    # Alphabetic canaries prevent numeric identity redaction from accidentally
    # making a missing old-value snapshot appear private.
    alphabetic_nonce = lambda: uuid.uuid4().hex[:16].translate(str.maketrans('0123456789', 'ghijklmnop'))
    secret = 'PRIVATE-PAYMENT-' + alphabetic_nonce()
    root = new(Q.customer_orders(), context).update_platform(platform)
    root.update_order_number(label).update_description('privacy graph')
    item = new(Q.order_items(), context).update_customer_order(root).update_name('ordinary sibling')
    payment = new(Q.payments(), context).update_customer_order(root).update_reference_code(secret)
    root.order_item_list().append(item)
    root.payment_list().append(payment)
    for phase in ('create', 'update'):
        old = secret
        if phase == 'update':
            secret = 'PRIVATE-REVISED-' + alphabetic_nonce()
            root.update_description('revised privacy graph')
            item.update_name('revised ordinary sibling')
            payment.update_reference_code(secret)
        reset(service, sink, context)
        reason = f'{phase} payment {secret} previous {old}'
        await root.audit_as(reason).save(context)
        assert len(service.requests) == len(sink.events) == 3
        logs = context.sql_logs()
        assert len(logs) == 6
        for value in (secret, old):
            assert value not in repr(logs)
            assert value not in repr(sink.events)
        for metadata in service.results:
            assert len(metadata.statements) == 2
            assert metadata.comment == reason  # raw owned intent is not rewritten
        assert_private_lineage(service, sink, context, E.customer_order(root).id().eval(), reason,
            [('CustomerOrder', E.customer_order(root).id().eval()),
             ('OrderItem', E.order_item(item).id().eval()), ('Payment', E.payment(payment).id().eval())],
            [secret, old], {'Payment': {'reference_code': secret}}, phase)
        loaded = await Q.payments().with_id_is(E.payment(payment).id().eval()).limit(1).comment(
            'reload authoritative payment').purpose('verify safe logs do not alter business data').execute_for_one(context)
        assert E.payment(loaded).reference_code().eval() == secret
        assert E.payment(loaded).version().eval() == (1 if phase == 'create' else 2)
        await Q.customer_orders().with_id_is(E.customer_order(root).id().eval()).limit(1).comment(
            f'independent {secret} {old}').purpose('ensure no ambient redaction values').execute_for_one(context)
        assert secret in context.sql_logs()[-1].comment and old in context.sql_logs()[-1].comment
        print(f'PASS: Python generated mutation privacy {phase}; 3 writes/3 reads/3 audits; independent next request')

    # Deletion binds identity/version, not the private business scalar. Its
    # loaded original must still protect the whole graph's audit prose.
    root = await Q.customer_orders().with_id_is(E.customer_order(root).id().eval()).limit(1).select_payment_list_with(
        Q.payments().limit(2)).comment('reload deletion graph').purpose('retain loaded private scalars').execute_for_one(context)
    payment = root.payment_list()[0]
    payment_id = E.payment(payment).id().eval()
    root.update_description('delete the private payment')
    payment.mark_for_deletion()
    reset(service, sink, context)
    reason = f'delete payment {secret}'
    await root.audit_as(reason).save(context)
    assert len(service.requests) == len(sink.events) == 2
    assert len(context.sql_logs()) == 4
    assert secret not in repr(context.sql_logs()), 'loaded delete value leaked into SQL intent'
    assert secret not in repr(sink.events), 'loaded delete value leaked into committed audit'
    assert all(metadata.comment == reason for metadata in service.results)
    assert_private_lineage(service, sink, context, E.customer_order(root).id().eval(), reason,
        [('CustomerOrder', E.customer_order(root).id().eval()), ('Payment', payment_id)],
        [secret], {}, 'delete')
    missing = await Q.payments().with_id_is(payment_id).limit(1).comment('verify deleted payment').purpose(
        'prove soft delete hides the row').execute_for_one(context)
    assert missing is None
    await Q.customer_orders().with_id_is(E.customer_order(root).id().eval()).limit(1).comment(
        f'independent {secret}').purpose('ensure delete privacy stays invocation-local').execute_for_one(context)
    assert secret in context.sql_logs()[-1].comment
    print('PASS: Python generated loaded delete privacy; 2 writes/2 reads/2 audits; independent next request')

    # Changing one field must not lose privacy for another loaded scalar.
    context.configure_audit_policy('CustomerOrder', ['description'])
    private_description = 'PRIVATE-DESCRIPTION-' + alphabetic_nonce()
    root.update_description(private_description)
    await root.audit_as('prepare unchanged scalar privacy').save(context)
    root = await Q.customer_orders().with_id_is(E.customer_order(root).id().eval()).limit(1).comment(
        'load all order fields').purpose('retain an unchanged private description').execute_for_one(context)
    root.update_order_number(label + '-revised')
    reset(service, sink, context)
    reason = f'renumber {private_description}'
    await root.audit_as(reason).save(context)
    assert len(service.requests) == len(sink.events) == 1
    assert private_description not in repr(context.sql_logs()), 'unchanged loaded scalar leaked into SQL intent'
    assert private_description not in repr(sink.events), 'unchanged loaded scalar leaked into audit'
    assert_private_lineage(service, sink, context, E.customer_order(root).id().eval(), reason,
        [('CustomerOrder', E.customer_order(root).id().eval())], [private_description],
        {'CustomerOrder': {'order_number': label + '-revised'}}, 'unchanged')
    reloaded = await Q.customer_orders().with_id_is(E.customer_order(root).id().eval()).limit(1).comment(
        'verify unchanged description').purpose('prove provenance did not alter business values').execute_for_one(context)
    assert E.customer_order(reloaded).description().eval() == private_description
    assert E.customer_order(reloaded).order_number().eval() == label + '-revised'
    print('PASS: Python generated unchanged scalar privacy; 1 write/1 read/1 audit')


if __name__ == '__main__':
    asyncio.run(main())
