"""Real generated graph saves; standard telemetry owns all instrumentation."""
import asyncio
import json
import logging
import os
from pathlib import Path
import sys
import tempfile
from time import monotonic
from uuid import uuid4

from E import E
from Q import Q
from runtime_module import GENERATED_RUNTIME_MODULE
from teaql.provider.sqlite import create_sqlite_service
from teaql.runtime import UserContext
from teaql.sql.executor import TransportError
from main import AuditSink, ObservedService, chain, expected_graph, make_graph, reset, scalar


class FailingService(ObservedService):
    """Fault injection at the physical transport, never synthetic telemetry."""
    inject = False

    def __init__(self, service):
        super().__init__(service)
        self.failure = RuntimeError('GRAPH-PRIVATE-TRANSPORT-' + uuid4().hex)

    async def begin(self, context):
        transaction = await super().begin(context)
        original = transaction.transport.execute_sql

        async def execute(compiled):
            if self.inject and 'payment_attempt_data' in compiled.sql:
                raise self.failure
            return await original(compiled)

        transaction.transport.execute_sql = execute
        return transaction


def facts(service, sink, phase, reason):
    statements = [statement for metadata in service.results for statement in metadata.statements]
    # The failed operation has no successful result object. Its physical span
    # and SQL completion are checked independently in the collector readback.
    return {'phase': phase, 'reason': reason, 'requests': len(service.requests),
            'successful_results': len(service.results), 'audits': len(sink.events),
            'actions': list(service.actions), 'finishes': list(service.finishes),
            'successful_statements': len(statements)}


def committed_lineage(graph, service, sink, reason, explicit):
    expected = expected_graph(graph, reason) if explicit else {
        (entity, identity): [('CustomerOrder', E.customer_order(graph[0]).id().eval(), reason)]
        for entity, identity, _ in service.requests}
    commands = {(entity, identity): nodes for entity, identity, nodes in service.requests}
    audits = {(event.entity, scalar(event.entity_id)): chain(event.trace_chain) for event in sink.events}
    assert len(commands) == len(audits) == len(service.requests) == len(sink.events) == 6
    assert commands == audits == expected, (commands, audits, expected)
    assert service.finishes == ['commit']
    assert len(service.results) == 6
    for (entity, identity, _), result in zip(service.requests, service.results):
        assert chain(result.mutation_lineage) == expected[(entity, identity)]
        assert len(result.statements) == 2
        for statement in result.statements:
            assert chain(statement.mutation_lineage) == expected[(entity, identity)]
            assert statement.execution_outcome == 'success'


async def main():
    if os.environ.get('TEAQL_STANDARD_EXPORT_DEBUG') == 'true':
        logging.basicConfig(level=logging.DEBUG)
    database = os.environ.get('TEAQL_STANDARD_GRAPH_DB') or str(
        Path(tempfile.mkdtemp(prefix='teaql-python-graph-')) / 'graph.sqlite')
    context = UserContext.new().install(GENERATED_RUNTIME_MODULE)
    service = FailingService(create_sqlite_service(database))
    sink = AuditSink(service)
    context.insert_resource('dataService', service).with_app_audit_event_sink(sink).disable_sql_log()
    # Numeric identities are private audit inputs. Do not accidentally embed
    # those ID spellings in the public business-reason correlation label.
    nonce = uuid4().hex.translate(str.maketrans('0123456789', 'klmnopqrst'))
    observations = []
    try:
        await context.ensure_schema()
        first = len(sink.events)
        assert first in (0, 1)
        await context.ensure_schema()
        assert len(sink.events) == first, 'repeated seed must not write'
        platform = await (Q.platforms().with_id_is(1).limit(1).comment('load seeded graph platform')
                          .purpose('prepare standard graph example').execute_for_one(context))
        graph = make_graph(context, platform, 'GRAPH-' + nonce)
        order, item, payment, attempt, shipment, removed = graph
        reason = 'GRAPH-create-' + nonce
        reset(service, sink, context)
        await order.audit_as(reason).save(context)
        committed_lineage(graph, service, sink, reason, False)
        observations.append(facts(service, sink, 'create', reason))
        assert E.payment(payment).id().eval() == E.customer_order(order).id().eval(), 'same ID, distinct entity types'

        order.update_description('Submitted standard graph')
        item.update_name('Updated standard item')
        payment.update_reference_code('Authorized payment').audit_as('authorize payment')
        attempt.update_reference_code('Completed payment attempt')
        shipment.update_reference_code('Dispatched shipment').audit_as('dispatch shipment')
        removed.mark_for_deletion().audit_as('remove unavailable item')
        reason = 'GRAPH-mixed-' + nonce
        reset(service, sink, context)
        await order.audit_as(reason).save(context)
        committed_lineage(graph, service, sink, reason, True)
        assert service.actions.count('update') == 5 and service.actions.count('delete') == 1
        observations.append(facts(service, sink, 'mixed', reason))
        loaded = await (Q.customer_orders().with_id_is(E.customer_order(order).id().eval())
            .select_order_item_list_with(Q.order_items().limit(10))
            .select_payment_list_with(Q.payments().limit(10)
                .select_payment_attempt_list_with(Q.payment_attempts().limit(10)))
            .select_shipment_list_with(Q.shipments().limit(10)).limit(1)
            .comment('reload committed standard graph').purpose('verify generated loaded E').execute_for_one(context))
        assert E.customer_order(loaded).order_item_list().size().eval() == 1
        assert E.customer_order(loaded).payment_list().size().eval() == 1
        deleted = await (Q.order_items().with_id_is(E.order_item(removed).id().eval()).deleted_rows_only()
            .limit(1).comment('verify standard graph deletion').purpose('verify persisted negative version')
            .execute_for_one(context))
        assert E.order_item(deleted).version().eval() < 0

        retry = make_graph(context, platform, 'RETRY-' + nonce)
        reason = 'GRAPH-rollback-' + nonce
        reset(service, sink, context)
        service.inject = True
        try:
            await retry[0].audit_as(reason).save(context)
        except (TransportError, RuntimeError) as error:
            actual = error.error if isinstance(error, TransportError) else error
            assert actual is service.failure, 'original business exception must survive'
        else:
            raise AssertionError('physical failure was not raised')
        finally:
            service.inject = False
        assert service.finishes == ['rollback'] and not sink.events
        observations.append(facts(service, sink, 'rollback', reason))
        absent = await (Q.customer_orders().with_order_number_is('RETRY-' + nonce).limit(1)
            .comment('verify rolled back graph').purpose('verify no committed order').execute_for_list(context))
        assert len(absent) == 0
        reason = 'GRAPH-retry-' + nonce
        reset(service, sink, context)
        await retry[0].audit_as(reason).save(context)
        committed_lineage(retry, service, sink, reason, False)
        observations.append(facts(service, sink, 'retry', reason))
        assert not context.sql_logs(), 'ordinary SQL logging stays disabled'
        if os.environ.get('TEAQL_TELEMETRY_ENABLED', '').lower() != 'true':
            assert not any(name.startswith('opentelemetry') for name in sys.modules)
        await asyncio.to_thread(context.runtime_telemetry().flush)
        mode = os.environ.get('TEAQL_STANDARD_QUEUE_MODE')
        if mode:
            assert mode in ('recovery', 'backlog')
            telemetry = context.runtime_telemetry()
            baseline = telemetry.health()
            audit_count = len(sink.events)
            async def read_platform():
                rows = await (Q.platforms().with_id_is(1).limit(1).comment('read platform under queue pressure')
                    .purpose('verify default SDK admission and business continuity').execute_for_list(context))
                assert len(rows) == 1 and E.platform(rows[0]).id().eval() == 1
            for _ in range(1500):
                await read_platform()
            saturated = telemetry.health()
            assert len(sink.events) == audit_count == 6
            print('PYTHON_PRESSURE_READY ' + json.dumps({'mode': mode, 'reads': 1500,
                  'baseline': baseline, 'saturated': saturated}, sort_keys=True), flush=True)
            started = monotonic()
            if mode == 'recovery':
                await asyncio.to_thread(telemetry.flush)
                drained = telemetry.health()
                await read_platform()
                await asyncio.to_thread(telemetry.flush)
                recovered = telemetry.health()
                print('PYTHON_PRESSURE_RESULT ' + json.dumps({'mode': mode, 'elapsed_ms': (monotonic() - started) * 1000,
                      'drained': drained, 'recovered': recovered, 'audits': len(sink.events)}, sort_keys=True), flush=True)
            else:
                await asyncio.to_thread(telemetry.shutdown)
                closed = telemetry.health()
                elapsed = (monotonic() - started) * 1000
                await read_platform()
                late = telemetry.health()
                assert len(sink.events) == audit_count and not context.sql_logs()
                print('PYTHON_PRESSURE_RESULT ' + json.dumps({'mode': mode, 'elapsed_ms': elapsed,
                      'closed': closed, 'late': late, 'audits': len(sink.events)}, sort_keys=True), flush=True)
        print('PYTHON_STANDARD_GRAPH_FACTS ' + json.dumps({'first_seed_audits': first,
              'repeat_seed_audits': 0, 'phases': observations}, sort_keys=True))
        print('PYTHON_STANDARD_GRAPH PASSED create=6 mixed=6 rollback=0 retry=6 ordinary_sql_logs=0')
    finally:
        await service.close()
        await asyncio.to_thread(context.runtime_telemetry().shutdown)
        health = getattr(context.runtime_telemetry(), 'health', None)
        if health is not None:
            print('PYTHON_STANDARD_EXPORT_HEALTH ' + json.dumps(health(), sort_keys=True))


if __name__ == '__main__':
    asyncio.run(main())
