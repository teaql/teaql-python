"""Public generated Fix lifecycle, real rollback/retry and trusted root checks."""
import argparse
import asyncio
from dataclasses import asdict, fields, FrozenInstanceError
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import inspect
import json
from pathlib import Path
import sqlite3
import sys

from python_graph_fix_probe import Meter, RecordingRegistry


class Clock:
    def __init__(self, round_number):
        self.base = datetime(2034, 1, round_number, tzinfo=timezone.utc)
        self.calls = 0

    def now(self):
        result = self.base + timedelta(milliseconds=self.calls)
        self.calls += 1
        return result


class ControlledFailure(RuntimeError):
    pass


class Control:
    mode = None
    reject_checker = False

    def __init__(self):
        self.entered, self.release = asyncio.Event(), asyncio.Event()


class FaultMeter(Meter):
    def __init__(self, delegate, control, counts=None):
        super().__init__(delegate, counts)
        self.control = control

    async def begin(self, context):
        self.counts['begins'] += 1
        return FaultMeter(await self.delegate.begin(context), self.control, self.counts)

    async def mutate(self, context, request):
        self.counts['mutations'] += 1
        result = await self.delegate.mutate(context, request)
        if self.counts['mutations'] == 2 and self.control.mode:
            mode, self.control.mode = self.control.mode, None
            if mode == 'provider':
                raise ControlledFailure('controlled rejection after real child SQL')
            assert mode == 'cancel'
            self.control.entered.set()
            await self.control.release.wait()
        return result


class Registry(RecordingRegistry):
    def __init__(self, delegate, meter, control):
        super().__init__(delegate, meter)
        self.control = control

    def checker(self, entity):
        original = super().checker(entity)
        owner = self
        if entity != 'OrderItem' or original is None:
            return original

        class Checked:
            def check_and_fix(self, context, record, location, results):
                from teaql.runtime import CheckResult, ObjectLocation
                original.check_and_fix(context, record, location, results)
                if owner.control.reject_checker:
                    results.append(CheckResult('core236_controlled_rejection',
                        ObjectLocation().property('product_name'), entity_type=entity))
        return Checked()


def storage(file):
    with sqlite3.connect(file.resolve().as_uri() + '?mode=ro&immutable=1', uri=True) as db:
        return {name: db.execute('SELECT COUNT(*) FROM ' + name + '_data').fetchone()[0]
                for name in ('purchase_order', 'order_item')}


async def verify(args):
    sys.path.insert(0, str(args.generated.resolve()))
    from E import E
    from Q import Q
    from runtime_module import GENERATED_RUNTIME_MODULE
    from teaql.data_service import SQLiteTeaQLClient
    from teaql.runtime import CheckException, ContextEntityRef, UserContext
    client = SQLiteTeaQLClient(str(args.database))
    control, clock = Control(), Clock(args.round)
    meter = FaultMeter(client, control)
    canary = 'PRIVATE-CUSTOMER-CONTEXT-REFERENCE-CANARY'

    def context(root=ContextEntityRef('Tenant', 1)):
        current = (UserContext().install(GENERATED_RUNTIME_MODULE)
                   .insert_resource('dataService', meter).with_business_clock(clock))
        if root is not None:
            current.with_active_root(root)
        current.with_checker_registry(Registry(current.require_resource('checker_registry'), meter, control))
        return current

    primary = context()
    registry = primary.require_resource('checker_registry')

    async def graph(current, label):
        order = ((await Q.purchase_orders().comment('Prepare ' + label)
                 .purpose('Verify generated Fix boundaries').new_entity(current)))
        child = ((await Q.order_items().comment('Prepare the Fix lifecycle child')
                 .purpose('Verify repeated-child identity through real save').new_entity(current)))
        order.update_contact_phone('5550760').update_internal_note(canary)
        child.update_product_name('Fix lifecycle item').update_unit_price(Decimal('17.25'))
        order.order_item_list().extend([child, child])
        return order, child

    def reset():
        meter.counts.clear()
        registry.visits.clear()

    def clean(current):
        assert current.get_resource('fix_time') is None
        assert current.get_resource('fix_operation') is None

    def visits(current_registry, operation):
        assert [row['entity'] for row in current_registry.visits] == ['PurchaseOrder', 'OrderItem']
        assert all(row['operation'] == operation for row in current_registry.visits)
        assert len({row['instantMillis'] for row in current_registry.visits}) == 1
        assert all(not any(row['providerEffectsDuringFix'].values()) for row in current_registry.visits)

    def emit(name, observations, **facts):
        assert all(value is True for value in facts.values())
        print('PYTHON_FIX_LIFECYCLE_CASE=' + json.dumps(dict(case=name, round=args.round,
              passed=True, facts=facts, observations=observations), sort_keys=True))

    async def reload(child):
        return await (Q.order_items().with_id_is(child.id).limit(1)
                      .comment('Reload the committed Fix lifecycle child')
                      .purpose('Check the real stored value after retry').execute_for_one(primary))

    try:
        await primary.ensure_schema()
        # Bootstrap is fixture setup, not an application graph under test.
        clock.calls = 0
        before = storage(args.database)
        order, child = (await graph(primary, 'one advancing-clock graph'))
        reset()
        reads = clock.calls
        await order.audit_as('Save one repeated-child graph with a trusted root').save(primary)
        assert clock.calls - reads == 1
        visits(registry, 'insert')
        assert meter.effects() == dict(begins=1, queries=0, ids=2, mutations=2, commits=1, rollbacks=0)
        create_effects, create_visits = meter.effects(), list(registry.visits)
        created = E.purchase_order(order).create_time().eval()
        assert E.order_item(child).create_time().eval() == created
        assert E.purchase_order(order).tenant_id().eval() == E.order_item(child).tenant_id().eval() == 1
        assert E.purchase_order(order).internal_note().eval() == canary
        evidence = primary.last_fix_evidence()
        # Generated insert Fix records update_time for its absent-value fill
        # and its unconditional update rule. Both refer to the same clock;
        # the contract requires safe provenance, not one event per field.
        assert len(evidence) == 8
        assert all(tuple(field.name for field in fields(item)) == ('entity_type', 'model_path', 'source', 'source_label') for item in evidence)
        assert {item.source for item in evidence} == {'clock', 'context'}
        assert {item.model_path for item in evidence} == {'create_time', 'update_time', 'tenant'}
        assert canary not in json.dumps([asdict(item) for item in evidence])
        try:
            evidence[0].model_path = 'tampered'
            raise AssertionError('Fix provenance must be immutable')
        except FrozenInstanceError:
            pass
        evidence_snapshot = tuple(asdict(item) for item in evidence)
        clean(primary)

        order.update_contact_phone('5550761')
        child.update_product_name('Updated Fix lifecycle item')
        reset()
        reads = clock.calls
        await order.audit_as('Recheck a second save of the same graph').save(primary)
        assert clock.calls - reads == 1
        visits(registry, 'update')
        assert meter.effects() == dict(begins=1, queries=0, ids=0, mutations=2, commits=1, rollbacks=0)
        assert E.purchase_order(order).create_time().eval() == E.order_item(child).create_time().eval() == created
        assert E.purchase_order(order).update_time().eval() == E.order_item(child).update_time().eval() == created + timedelta(milliseconds=1)
        assert order.version == child.version == 2
        clean(primary)
        emit('advancing-create-update', dict(createInstantMillis=int(created.timestamp() * 1000),
             updateInstantMillis=int(E.order_item(child).update_time().eval().timestamp() * 1000),
             createEffects=create_effects, updateEffects=meter.effects(),
             createFixVisits=create_visits, updateFixVisits=list(registry.visits)),
             oneClockPerGraph=True, repeatedChildFixedOnce=True,
             createTimePreserved=True, updateTimeAdvanced=True, noFixProviderIO=True,
             typedRootInjected=True, ordinaryBusinessInputPreserved=True)
        assert tuple(asdict(item) for item in evidence) == evidence_snapshot
        emit('safe-provenance', dict(records=list(evidence_snapshot)), closedFourFieldShape=True, noBusinessValue=True,
             immutableSnapshot=True, previousSnapshotPreserved=True)

        other = context()
        second, second_child = (await graph(other, 'an independent Context'))
        other_registry = other.require_resource('checker_registry')
        meter.counts.clear()
        reads = clock.calls
        await second.audit_as('Capture a fresh instant for a separate Context').save(other)
        visits(other_registry, 'insert')
        assert clock.calls - reads == 1
        assert E.order_item(second_child).create_time().eval() == created + timedelta(milliseconds=2)
        clean(other)
        emit('independent-contexts', dict(instantMillis=int(E.order_item(second_child).create_time().eval().timestamp() * 1000),
             fixVisits=list(other_registry.visits), effects=meter.effects()),
             distinctInstant=True, oneClockPerInvocation=True, invocationStateReleased=True)

        for mode in ('checker', 'provider', 'cancel'):
            pending, leaf = (await graph(primary, mode + ' failure followed by retry'))
            baseline = storage(args.database)
            reset()
            reads = clock.calls
            control.reject_checker = mode == 'checker'
            control.mode = None if mode == 'checker' else mode
            if mode == 'cancel':
                task = asyncio.create_task(pending.audit_as('Cancel after real child SQL').save(primary))
                try:
                    await asyncio.wait_for(control.entered.wait(), 3)
                    task.cancel()
                    try:
                        await task
                        raise AssertionError('cancelled graph unexpectedly completed')
                    except asyncio.CancelledError:
                        pass
                finally:
                    if not task.done():
                        task.cancel()
                    await asyncio.gather(task, return_exceptions=True)
            else:
                try:
                    await pending.audit_as('Reject a controlled graph invocation').save(primary)
                    raise AssertionError('controlled failure was not observed')
                except (CheckException if mode == 'checker' else ControlledFailure):
                    pass
            assert clock.calls - reads == 1
            visits(registry, 'insert')
            clean(primary)
            assert storage(args.database) == baseline
            failed_effects, failed_visits = meter.effects(), list(registry.visits)
            if mode == 'checker':
                assert not any(meter.effects().values())
                assert pending.id is None and leaf.id is None
            else:
                assert meter.effects()['mutations'] == 2 and meter.effects()['rollbacks'] == 1 and meter.effects()['commits'] == 0
            control.reject_checker, control.mode = False, None
            reset()
            reads = clock.calls
            await pending.audit_as('Retry the exact graph after ' + mode).save(primary)
            assert clock.calls - reads == 1
            visits(registry, 'insert')
            effects = meter.effects()
            assert effects['mutations'] == 2 and effects['commits'] == 1 and effects['rollbacks'] == 0
            clean(primary)
            stored = await reload(leaf)
            assert stored.version == 1 and E.order_item(stored).product_name().eval() == 'Fix lifecycle item'
            assert E.order_item(stored).create_time().eval() == clock.base + timedelta(milliseconds=clock.calls - 1)
            emit(mode + '-failure-retry', dict(failureEffects=failed_effects, retryEffects=effects,
                 failureFixVisits=failed_visits, retryFixVisits=list(registry.visits),
                 storedCreateMillis=int(E.order_item(stored).create_time().eval().timestamp() * 1000)),
                 originalFailureObserved=True, storageRolledBack=True,
                 sameGraphRetry=True, freshFixOnRetry=True, freshClockOnRetry=True, invocationStateReleased=True)

        rejection_count, rejections = 0, []
        for label, root in (('missing', None), ('wrong-type', ContextEntityRef('OtherType', 1)),
                            ('zero-id', ContextEntityRef('Tenant', 0))):
            untrusted = context(root)
            candidate, _ = (await graph(untrusted, 'untrusted root admission'))
            reset()
            reads = clock.calls
            try:
                await candidate.audit_as('Reject a missing or invalid active root').save(untrusted)
                raise AssertionError('untrusted root accepted')
            except CheckException as error:
                assert any(v.rule_id == 'context_root_missing' for v in error.violations)
            assert clock.calls == reads and not any(meter.effects().values())
            rejections.append(dict(case=label, rule='context_root_missing', effects=meter.effects(), clockReads=clock.calls - reads))
            clean(untrusted)
            rejection_count += 1
        for invalid in ('explicit-create', 'wrong-update-context', 'move-existing-owner'):
            current = primary if invalid != 'wrong-update-context' else context(ContextEntityRef('Tenant', 2))
            if invalid == 'explicit-create':
                # A constructor argument is an explicit loaded field. Writing
                # an attribute on a NotLoaded field is not a generated update.
                target = type(order)(tenant=2)
                target.update_contact_phone('5550762').update_internal_note(canary)
            else:
                target = await (Q.purchase_orders().with_id_is(order.id).limit(1)
                                .comment('Reload ownership before a negative update')
                                .purpose('Preserve the authoritative owner').execute_for_one(primary))
                target.update_contact_phone('5550762')
            if invalid == 'move-existing-owner':
                target.tenant = 2  # Negative carrier injection, not a generated setter.
            reset()
            reads = clock.calls
            try:
                await target.audit_as('Reject conflicting root ownership').save(current)
                raise AssertionError('conflicting ownership accepted')
            except CheckException as error:
                assert any(v.rule_id == 'context_root_mismatch' for v in error.violations)
            assert clock.calls == reads and not any(meter.effects().values())
            rejections.append(dict(case=invalid, rule='context_root_mismatch', effects=meter.effects(), clockReads=clock.calls - reads))
            clean(current)
            rejection_count += 1
        assert rejection_count == 6
        assert all(not any(name.startswith('update_tenant') for name in dir(entity)) for entity in (order, child))
        after = storage(args.database)
        assert after == {key: value + 5 for key, value in before.items()}
        emit('root-admission', dict(rejections=rejections, rowDelta={key: after[key] - before[key] for key in before}),
             sixRejectionsBeforeIO=True, noFixClockForRejectedRoot=True,
             noPublicRootUpdater=True, noOwnershipMove=True, noRootLookup=True)
        print('PYTHON_FIX_LIFECYCLE_RESULT=' + json.dumps(dict(round=args.round, passed=True,
              cases=7, parentRowsAdded=5, childRowsAdded=5, rootRejections=6,
              runtimeFile=inspect.getfile(UserContext)), sort_keys=True))
    finally:
        await client.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--generated', type=Path, required=True)
    parser.add_argument('--database', type=Path, required=True)
    parser.add_argument('--round', type=int, choices=(1, 2), required=True)
    asyncio.run(verify(parser.parse_args()))
