"""Generated save privacy; no generated source inspection or synthetic traces."""
import asyncio
import os
import uuid

from E import E
from Q import Q
from runtime_module import GENERATED_RUNTIME_MODULE
from teaql.provider.sqlite import create_sqlite_service
from teaql.runtime import UserContext

from main import AuditSink, ObservedService, new, reset


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
        loaded = await Q.payments().with_id_is(E.payment(payment).id().eval()).limit(1).comment(
            'reload authoritative payment').purpose('verify safe logs do not alter business data').execute_for_one(context)
        assert E.payment(loaded).reference_code().eval() == secret
        assert E.payment(loaded).version().eval() == (1 if phase == 'create' else 2)
        await Q.customer_orders().with_id_is(E.customer_order(root).id().eval()).limit(1).comment(
            f'independent {secret} {old}').purpose('ensure no ambient redaction values').execute_for_one(context)
        assert secret in context.sql_logs()[-1].comment and old in context.sql_logs()[-1].comment
        print(f'PASS: Python generated mutation privacy {phase}; 3 writes/3 reads/3 audits; independent next request')


if __name__ == '__main__':
    asyncio.run(main())
