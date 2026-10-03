"""Assist-guided generated Q/E/save: root and nested aggregate provenance."""
import asyncio
import json
import os
import uuid
from types import SimpleNamespace

from E import E
from Q import Q
from runtime_module import GENERATED_RUNTIME_MODULE
from teaql.provider.sqlite import create_sqlite_service
from teaql.runtime import UserContext, DelegatingMutationPolicyRegistry

from main import AuditSink, new, reset
from page_stream import RecordingPolicy, log_row
from shared_reference import SharedService


async def main():
    context = UserContext.new().install(GENERATED_RUNTIME_MODULE)
    native = create_sqlite_service(os.environ['TEAQL_TRACE_CHAIN_AGGREGATE_DB'])
    service = SharedService(native)
    sink, policy = AuditSink(service), RecordingPolicy()
    context.insert_resource('dataService', service).with_app_audit_event_sink(sink)
    context.with_mutation_policy_registry(DelegatingMutationPolicyRegistry(lambda _: policy))
    diagnostic = []
    context.set_diagnostic_sql_log_sink(SimpleNamespace(write=diagnostic.append))
    await context.ensure_schema()
    native.schema_provider.get_entity('OrderItem').audit_mask_fields(['name'])
    platform = await (Q.platforms().with_id_is(1).limit(1).comment('reuse bootstrap root')
                      .purpose('prepare aggregate example').execute_for_one(context))
    secret = 'PRIVATE-AGGREGATE-' + uuid.uuid4().hex
    order = new(Q.customer_orders(), context).update_platform(platform)
    order.update_order_number('AGG-' + uuid.uuid4().hex).update_description('aggregate original')
    for name in (secret, 'public item'):
        order.order_item_list().append(new(Q.order_items(), context)
            .update_customer_order(order).update_name(name))
    payment = (new(Q.payments(), context).update_customer_order(order)
               .update_reference_code('AGG-PAY-' + uuid.uuid4().hex))
    order.payment_list().append(payment)
    await order.audit_as('seed aggregate graph').save(context)
    order_id, payment_id = E.customer_order(order).id().eval(), E.payment(payment).id().eval()
    reads, fault = [], [False]
    original_fetch = native.transport.fetch_all_sql

    async def capture(compiled):
        reads.append(compiled.sql)
        if fault[0] and 'COUNT(' in compiled.sql.upper():
            raise RuntimeError('synthetic aggregate failure')
        return await original_fetch(compiled)

    native.transport.fetch_all_sql = capture

    def query(nested, filtered=secret):
        # Each aggregate has its own child builder; no hand-written application SQL.
        request = (Q.customer_orders().with_id_is(order_id).limit(1)
            .count_order_items_with('filtered_count', Q.order_items().with_name_is(filtered).limit(10))
            .count_order_items_as('save')
            .select_order_item_list_with(Q.order_items().limit(10)))
        if nested:
            request = (Q.payments().with_id_is(payment_id).limit(1)
                       .select_customer_order_with(request))
        return request.comment('inspect ' + secret).purpose('verify aggregate provenance')

    def clear():
        reset(service, sink, context)
        diagnostic.clear()
        reads.clear()
        policy.plans.clear()

    for logging in (True, False):
        context.enable_all_sql_log() if logging else context.disable_sql_log()
        for nested in (False, True):
            clear()
            rows = await query(nested).execute_for_list(context)
            assert len(rows) == 1
            loaded = E.payment(rows[0]).customer_order().eval() if nested else rows[0]
            assert E.customer_order(loaded).id().eval() == order_id
            assert E.customer_order(loaded).order_item_list().size().eval() == 2
            assert loaded.has_query_projection('filtered_count')
            assert loaded.query_projection('filtered_count') == 1
            assert loaded.query_projection('save') == 2 and callable(loaded.save)
            assert not loaded.has_query_projection('id')
            try:
                loaded.query_projection('absent')
            except KeyError:
                pass
            else:
                raise AssertionError('missing aggregate silently became a value')
            assert len(reads) == (5 if nested else 4), reads
            assert service.requests == [] and policy.plans == [] and sink.events == []
            if logging:
                assert len(context.sql_logs()) == len(diagnostic) == len(reads)
                for entry in context.sql_logs():
                    assert entry.trace_path[0].name == ('Payment' if nested else 'CustomerOrder')
                    assert entry.purpose == 'verify aggregate provenance'
                    assert secret not in json.dumps(log_row(entry))
                aggregates = [entry for entry in context.sql_logs() if 'COUNT(' in entry.sql.upper()]
                assert len(aggregates) == 2
                for entry in aggregates:
                    relations = [node.name for node in entry.trace_path if node.kind == 'relation']
                    assert relations == (['customer_order', 'order_item_list'] if nested else ['order_item_list']), relations
                    assert entry.trace_path[-1].kind == 'sql'
            else:
                assert context.sql_logs() == diagnostic == []
            print('AGGREGATE_OBSERVED ' + json.dumps({'nested': nested, 'logging': logging,
                'count': loaded.query_projection('filtered_count'), 'provider_calls': len(reads),
                'sql': [log_row(entry) for entry in context.sql_logs()]}))
            clear()
            await loaded.update_description('aggregate saved ' + uuid.uuid4().hex).audit_as(
                'save model field without projection aliases').save(context)
            assert len(service.requests) == len(sink.events) == len(policy.plans) == 1
            operation = policy.plans[0].operations[0]
            assert set(operation.changed_values) == {'description'}, operation.changed_values
            assert loaded.query_projection('save') == 2
            print('AGGREGATE_SAVE ' + json.dumps({'nested': nested, 'logging': logging,
                'commands': len(service.requests), 'audits': len(sink.events),
                'fields': sorted(operation.changed_values), 'projection': loaded.query_projection('save')}))
            fresh = (await query(nested, 'NO-MATCH-' + uuid.uuid4().hex).execute_for_list(context))[0]
            fresh = E.payment(fresh).customer_order().eval() if nested else fresh
            assert E.customer_order(fresh).description().eval() == E.customer_order(loaded).description().eval()
            assert fresh.has_query_projection('filtered_count') and fresh.query_projection('filtered_count') == 0

        clear()
        fault[0] = True
        try:
            await query(False).execute_for_list(context)
        except Exception as error:
            assert 'synthetic aggregate failure' in str(error), error
        else:
            raise AssertionError('aggregate provider failure was swallowed')
        finally:
            fault[0] = False
        assert len(reads) == 2 and service.requests == [] and sink.events == []
        if logging:
            assert context.sql_logs()[-1].execution_outcome == 'failure'
            assert all(secret not in json.dumps(log_row(entry)) for entry in context.sql_logs())
        else:
            assert context.sql_logs() == diagnostic == []
        print('AGGREGATE_FAILURE ' + json.dumps({'logging': logging, 'provider_calls': len(reads),
            'sql': [log_row(entry) for entry in context.sql_logs()]}))
        clear()
        await (Q.platforms().with_id_is(1).limit(1).comment('independent next query')
               .purpose('prove scope restored').execute_for_list(context))
        assert len(reads) == 1
        assert all(entry.comment == 'independent next query' and entry.trace_path[0].name == 'Platform'
                   for entry in context.sql_logs())
    print('PASS: Python generated aggregates; 4 root/nested/logging cases; isolated save; 2 failures restored')


if __name__ == '__main__':
    asyncio.run(main())
