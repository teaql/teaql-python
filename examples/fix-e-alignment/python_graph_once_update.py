"""Public generated save regression for retained Fix values and late policy edits."""
import argparse
import asyncio
from datetime import timedelta
from decimal import Decimal
import json
from pathlib import Path
import sys

from python_graph_fix_probe import AdvancingClock, Meter, RecordingRegistry


class IncrementRegistry(RecordingRegistry):
    def checker(self, entity):
        original = super().checker(entity)
        if entity != 'OrderItem' or original is None:
            return original
        class IncrementChecker:
            def check_and_fix(self, context, record, location, results):
                from teaql.core.value import Value
                if 'unit_price' in record and not record['unit_price'].is_null():
                    record['unit_price'] = Value.Decimal(record['unit_price'].val + Decimal('0.01'))
                original.check_and_fix(context, record, location, results)
        return IncrementChecker()


async def verify(args):
    sys.path.insert(0, str(args.generated.resolve()))
    from Q import Q
    from E import E
    from runtime_module import GENERATED_RUNTIME_MODULE
    from teaql.data_service import SQLiteTeaQLClient
    from teaql.runtime import UserContext, ContextEntityRef, CheckException
    from teaql.runtime.mutation_policy import MutationPolicyIdentity, MutationDecision, DelegatingMutationPolicyRegistry
    client = SQLiteTeaQLClient(str(args.database))
    meter = Meter(client)
    context = (UserContext().install(GENERATED_RUNTIME_MODULE).insert_resource('dataService', meter)
               .with_active_root(ContextEntityRef('Tenant', 1)))
    try:
        await context.ensure_schema()
        clock = AdvancingClock(args.round)
        context.with_business_clock(clock)
        registry = IncrementRegistry(context.require_resource('checker_registry'), meter)
        context.with_checker_registry(registry)
        parent = (Q.purchase_orders().comment('Prepare one repeated-child graph')
                  .purpose('Verify checked business corrections survive planning').new_entity(context))
        child = (Q.order_items().comment('Prepare the repeated child')
                 .purpose('Apply the customer price correction once per save').new_entity(context))
        parent.update_contact_phone('5550720').update_internal_note(None)
        child.update_product_name('Retained Fix item').update_unit_price(Decimal('12.34'))
        parent.order_item_list().extend([child, child])
        await parent.audit_as('Create a graph with a retained customer correction').save(context)
        assert E.order_item(child).unit_price().eval() == Decimal('12.35')
        assert len(registry.visits) == 2
        assert child.version == parent.version == 1
        first = E.order_item(child).create_time().eval()

        registry.visits.clear()
        meter.counts.clear()
        reads = clock.calls
        parent.update_contact_phone('5550721')
        child.update_unit_price(Decimal('23.44'))
        await parent.audit_as('Update the same repeated-child graph once').save(context)
        assert clock.calls - reads == 1
        assert len(registry.visits) == 2
        assert [row['entity'] for row in registry.visits] == ['PurchaseOrder', 'OrderItem']
        assert meter.effects() == {'begins': 1, 'commits': 1, 'rollbacks': 0,
                                  'mutations': 2, 'queries': 0, 'ids': 0}
        assert child.version == parent.version == 2
        assert E.order_item(child).unit_price().eval() == Decimal('23.45')
        assert E.order_item(child).create_time().eval() == first
        assert E.order_item(child).update_time().eval() == first + timedelta(milliseconds=1)
        print('PYTHON_GRAPH_ONCE_UPDATE=' + json.dumps({'round': args.round, 'passed': True,
              'parentId': parent.id, 'childId': child.id, 'version': 2,
              'retainedPrice': str(E.order_item(child).unit_price().eval()),
              'fixCalls': len(registry.visits), 'clockCaptures': clock.calls - reads,
              'effects': meter.effects()}))

        class MutatingPolicy:
            identity = MutationPolicyIdentity('core236.graph.once', '1', 'reviewed-input-shape')
            calls = 0
            def review(self, current, plan):
                self.calls += 1
                child.update_unit_price(Decimal('99.00'))
                return MutationDecision.allowed()
        policy = MutatingPolicy()
        context.with_mutation_policy_registry(DelegatingMutationPolicyRegistry(lambda _: policy))
        parent.update_contact_phone('5550722')
        child.update_unit_price(Decimal('45.66'))
        meter.counts.clear()
        registry.visits.clear()
        try:
            await parent.audit_as('Reject a policy callback changing reviewed values').save(context)
            raise AssertionError('late carrier edit was accepted')
        except CheckException as error:
            assert any(v.rule_id == 'mutation_changed_after_preparation' for v in error.violations)
        effects = meter.effects()
        assert policy.calls == 1 and effects['commits'] == 0 and effects['rollbacks'] == 1
        assert len(registry.visits) == 2
        loaded = await (Q.order_items().with_id_is(child.id).limit(1)
                        .comment('Inspect the child after rejected callback changes')
                        .purpose('Verify value and optimistic version remain committed baseline')
                        .execute_for_one(context))
        assert loaded.version == 2 and E.order_item(loaded).unit_price().eval() == Decimal('23.45')
        assert context.get_resource('fix_time') is None
        print('PYTHON_GRAPH_ONCE_POLICY=' + json.dumps({'round': args.round, 'passed': True,
              'policyCalls': policy.calls, 'fixCalls': len(registry.visits),
              'effectsBeforeRead': effects, 'storedVersion': loaded.version,
              'storedPrice': str(E.order_item(loaded).unit_price().eval())}))
    finally:
        await client.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--generated', type=Path, required=True)
    parser.add_argument('--database', type=Path, required=True)
    parser.add_argument('--round', type=int, choices=(1, 2), required=True)
    asyncio.run(verify(parser.parse_args()))
