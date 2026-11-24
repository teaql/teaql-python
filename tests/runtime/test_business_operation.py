"""Independent file-SQLite acceptance for the shipping operation boundary."""

import asyncio
from dataclasses import replace
import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import sys

import pytest

from teaql.runtime import BusinessOperationError, BusinessOperationCommitUnknown, GraphCommittedError


ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = ROOT / 'examples' / 'business-operation'
spec = importlib.util.spec_from_file_location('shipping_example', EXAMPLE / 'warehouse.py')
warehouse = importlib.util.module_from_spec(spec)
spec.loader.exec_module(warehouse)


@pytest.fixture
async def shipping(tmp_path):
    path = tmp_path / 'warehouse.db'
    context = await warehouse.initialize(path)
    return path, context


def state(path):
    # Independent connection, not the application's response or cached entities.
    with sqlite3.connect(path) as db:
        return {
            'stock': db.execute('SELECT on_hand,reserved,version FROM stock_data WHERE id=1').fetchone(),
            'order': db.execute('SELECT quantity,shipped,received,cancelled,version FROM transferorder_data WHERE id=1').fetchone(),
            'results': db.execute('SELECT COUNT(*) FROM teaql_operation_results').fetchone()[0],
            'audit': db.execute('SELECT COUNT(*) FROM teaql_operation_audit').fetchone()[0],
        }


async def execute(context, key='SHIP-1', quantity=10, order_id=1, operation=None):
    return await (operation or warehouse.SHIP).execute(
        context, key=key, parameters={'order_id': order_id, 'quantity': quantity}, comment='ship inventory')


@pytest.mark.asyncio
async def test_ship_replay_restart_and_immutable_historical_result(shipping):
    path, context = shipping
    assert context.require_resource('dataService').capabilities().transaction is True
    first = await execute(context)
    assert first == {'order_id': 1, 'shipped': 10, 'quantity': 10}
    assert state(path) == {'stock': (90, 20, 2), 'order': (30, 10, 0, 0, 2), 'results': 1, 'audit': 1}
    first['shipped'] = 999
    await execute(context, key='SHIP-2')
    # A genuinely new process must replay the original snapshot, not current shipped=20.
    replay = await worker(path, 'SHIP-1', 10)
    assert replay == {'ok': True, 'result': {'order_id': 1, 'shipped': 10, 'quantity': 10}}
    assert state(path) == {'stock': (80, 10, 3), 'order': (30, 20, 0, 0, 3), 'results': 2, 'audit': 2}


@pytest.mark.asyncio
@pytest.mark.parametrize('parameters', [
    {'order_id': 1, 'quantity': 11}, {'order_id': 2, 'quantity': 10},
])
async def test_same_key_different_parameters_rejected(shipping, parameters):
    path, context = shipping
    await execute(context)
    before = state(path)
    with pytest.raises(BusinessOperationError) as caught:
        await warehouse.SHIP.execute(context, key='SHIP-1', parameters=parameters, comment='retry')
    assert caught.value.code == 'IDEMPOTENCY_CONFLICT'
    assert caught.value.outcome == 'rolled_back'
    assert state(path) == before


@pytest.mark.asyncio
async def test_version_change_cannot_reexecute_existing_key(shipping):
    path, context = shipping
    await execute(context)
    before = state(path)
    with pytest.raises(BusinessOperationError, match='different business parameters'):
        await execute(context, operation=replace(warehouse.SHIP, version='2'))
    assert state(path) == before


@pytest.mark.asyncio
@pytest.mark.parametrize('quantity,order_id', [(0, 1), (-1, 1), (31, 1), (10, 0), (10, 999)])
async def test_domain_rejection_changes_nothing(shipping, quantity, order_id):
    path, context = shipping
    before = state(path)
    with pytest.raises(BusinessOperationError):
        await execute(context, quantity=quantity, order_id=order_id)
    assert state(path) == before


@pytest.mark.asyncio
@pytest.mark.parametrize('parameters', [
    {'order_id': 1}, {'order_id': 1, 'quantity': True},
    {'order_id': 1, 'quantity': '10'}, {'order_id': 1, 'quantity': 10, 'shipped': 10},
])
async def test_complete_typed_input_required(shipping, parameters):
    path, context = shipping
    before = state(path)
    with pytest.raises(BusinessOperationError) as caught:
        await warehouse.SHIP.execute(context, key='SHIP-1', parameters=parameters, comment='invalid input')
    assert caught.value.code == 'OPERATION_INPUT_INVALID'
    assert state(path) == before


@pytest.mark.asyncio
async def test_authorization_is_required_on_replay_and_tenant_reference_is_scoped(shipping):
    path, context = shipping
    await execute(context)
    before = state(path)
    denied = replace(warehouse.SHIP, authorize=lambda context, params: False)
    with pytest.raises(BusinessOperationError) as caught:
        await execute(context, operation=denied)
    assert caught.value.code == 'OPERATION_DENIED'
    with pytest.raises(BusinessOperationError) as caught:
        await execute(warehouse.context_for(path, tenant=2), key='SHIP-2')
    assert caught.value.code == 'REFERENCE_NOT_FOUND'
    assert state(path) == before


@pytest.mark.asyncio
@pytest.mark.parametrize('table,verb', [
    ('stock_data', 'UPDATE'), ('transferorder_data', 'UPDATE'),
    ('teaql_operation_results', 'INSERT'), ('teaql_operation_audit', 'INSERT'),
])
async def test_real_database_failure_rolls_back_every_participant(shipping, table, verb):
    path, context = shipping
    before = state(path)
    with sqlite3.connect(path) as db:
        db.execute(f"CREATE TRIGGER reject_write BEFORE {verb} ON {table} BEGIN SELECT RAISE(ABORT, 'INDEPENDENT_INJECTED_FAILURE'); END")
    with pytest.raises(Exception, match='INDEPENDENT_INJECTED_FAILURE'):
        await execute(context)
    assert state(path) == before
    # Same context and key can be retried; no poisoned transaction or partial data.
    with sqlite3.connect(path) as db:
        db.execute('DROP TRIGGER reject_write')
    assert (await execute(context))['shipped'] == 10
    assert state(path)['stock'] == (90, 20, 2)


@pytest.mark.asyncio
async def test_caught_graph_error_still_forces_whole_operation_rollback(shipping):
    path, context = shipping
    before = state(path)
    with sqlite3.connect(path) as db:
        db.execute("CREATE TRIGGER reject_order BEFORE UPDATE ON transferorder_data BEGIN SELECT RAISE(ABORT, 'MUST_ROLL_BACK'); END")

    async def broken_handler(context, params):
        try:
            await warehouse.ship(context, params)
        except Exception:
            return {'ok': True}  # A model must not be able to turn a failed graph into success.

    with pytest.raises(BusinessOperationError) as caught:
        await execute(context, operation=replace(warehouse.SHIP, handler=broken_handler))
    assert caught.value.code == 'OPERATION_ROLLBACK_ONLY'
    assert state(path) == before


@pytest.mark.asyncio
async def test_runtime_enforces_registered_rules_when_handler_omits_order_write(shipping):
    path, context = shipping
    before = state(path)
    async def incomplete_handler(context, params):
        stock = await warehouse.load(context, 'Stock', 1)
        await warehouse.save_command(context, warehouse.UpdateCommand.new('Stock', 1)
            .expected_version(stock['version']).value('on_hand', 90).value('reserved', 20))
        return {'order_id': 1, 'shipped': 10, 'quantity': 10}
    with pytest.raises(BusinessOperationError) as caught:
        await execute(context, operation=replace(warehouse.SHIP, handler=incomplete_handler))
    assert caught.value.code == 'OPERATION_INVARIANT_FAILED'
    assert state(path) == before


@pytest.mark.asyncio
async def test_ordinary_independent_saves_do_not_implicitly_become_business_transaction(shipping):
    path, context = shipping
    with sqlite3.connect(path) as db:
        db.execute("CREATE TRIGGER reject_order BEFORE UPDATE ON transferorder_data BEGIN SELECT RAISE(ABORT, 'BASELINE_FAILURE'); END")
    with pytest.raises(Exception, match='BASELINE_FAILURE'):
        await warehouse.ship(context, {'order_id': 1, 'quantity': 10})
    # Retained unsafe baseline: demonstrates exactly why an explicit operation is needed.
    assert state(path) == {'stock': (90, 20, 2), 'order': (30, 0, 0, 0, 1), 'results': 0, 'audit': 0}


async def subprocess_code(code, *args):
    paths = [str(ROOT / 'src'), str(EXAMPLE)]
    if extra_paths := os.environ.get('PYTHONPATH'):
        paths.append(extra_paths)
    env = dict(os.environ, PYTHONPATH=os.pathsep.join(paths))
    process = await asyncio.create_subprocess_exec(
        sys.executable, '-c', code, *(str(arg) for arg in args), env=env,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=30)
    return process.returncode, stdout.decode(), stderr.decode()


async def worker(path, key, quantity, gate=None):
    if gate is not None:
        code = '''
import asyncio, json, os, sys
from pathlib import Path
import warehouse
from teaql.runtime import BusinessOperationError
async def main():
    context = warehouse.context_for(sys.argv[1])
    transport = context.require_resource('dataService').transport
    begin = transport.begin_sql
    gate = Path(sys.argv[4])
    async def barrier_begin():
        gate.with_name(gate.name + '.ready.' + str(os.getpid())).touch()
        while not gate.exists(): await asyncio.sleep(0.01)
        return await begin()
    transport.begin_sql = barrier_begin
    try:
        result = await warehouse.SHIP.execute(context, key=sys.argv[2], parameters={'order_id':1,'quantity':int(sys.argv[3])}, comment='concurrent ship')
        print(json.dumps({'ok':True,'result':result}))
    except BusinessOperationError as error:
        print(json.dumps({'ok':False,'code':error.code,'outcome':error.outcome}))
asyncio.run(main())
'''
        status, stdout, stderr = await subprocess_code(code, path, key, quantity, gate)
        assert status == 0, stderr
        return json.loads(stdout)
    process = await asyncio.create_subprocess_exec(
        sys.executable, str(EXAMPLE / 'warehouse.py'), '--worker', str(path), '--key', key,
        '--quantity', str(quantity), stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=30)
    assert process.returncode == 0, stderr.decode()
    return json.loads(stdout)


async def concurrent_workers(path, requests):
    gate = path.with_name('start-gate')
    tasks = [asyncio.create_task(worker(path, key, quantity, gate)) for key, quantity in requests]
    try:
        async def wait_ready():
            while len(list(path.parent.glob('start-gate.ready.*'))) != len(tasks):
                await asyncio.sleep(0.01)
        await asyncio.wait_for(wait_ready(), timeout=15)
        gate.touch()
        return await asyncio.gather(*tasks)
    finally:
        gate.touch()
        await asyncio.gather(*tasks, return_exceptions=True)


@pytest.mark.asyncio
async def test_concurrent_processes_same_key_execute_once(shipping):
    path, _ = shipping
    results = await concurrent_workers(path, [('SAME', 10)] * 4)
    assert results == [{'ok': True, 'result': {'order_id': 1, 'shipped': 10, 'quantity': 10}}] * 4
    assert state(path) == {'stock': (90, 20, 2), 'order': (30, 10, 0, 0, 2), 'results': 1, 'audit': 1}


@pytest.mark.asyncio
async def test_concurrent_processes_different_keys_cannot_overship(shipping):
    path, _ = shipping
    results = await concurrent_workers(path, [('A', 20), ('B', 20)])
    assert sorted(result['ok'] for result in results) == [False, True]
    assert [result['code'] for result in results if not result['ok']] == ['EXCEEDS_UNSHIPPED']
    current = state(path)
    assert current == {'stock': (80, 10, 2), 'order': (30, 20, 0, 0, 2), 'results': 1, 'audit': 1}
    assert current['stock'][0] + current['order'][1] - current['order'][2] == 100


@pytest.mark.asyncio
@pytest.mark.parametrize('after_commit,exit_code', [(False, 21), (True, 22)])
async def test_process_exit_before_or_after_commit_recovers_by_same_key(shipping, after_commit, exit_code):
    path, context = shipping
    code = '''
import asyncio, os, sys
from dataclasses import replace
import warehouse
async def main():
    context = warehouse.context_for(sys.argv[1])
    if sys.argv[2] == 'True':
        transport = context.require_resource('dataService').transport
        begin = transport.begin_sql
        async def observed_begin():
            tx = await begin()
            commit = tx.commit_sql
            async def die_after_commit():
                await commit()
                os._exit(22)
            tx.commit_sql = die_after_commit
            return tx
        transport.begin_sql = observed_begin
        operation = warehouse.SHIP
    else:
        save = warehouse.save_command
        async def die_after_stock(context, command):
            result = await save(context, command)
            if command.entity == 'Stock': os._exit(21)
            return result
        warehouse.save_command = die_after_stock
        operation = warehouse.SHIP
    await operation.execute(context, key='CRASH', parameters={'order_id':1,'quantity':10}, comment='crash probe')
asyncio.run(main())
'''
    status, stdout, stderr = await subprocess_code(code, path, after_commit)
    assert status == exit_code, (stdout, stderr)
    assert state(path)['results'] == (1 if after_commit else 0)
    assert state(path)['stock'] == ((90, 20, 2) if after_commit else (100, 30, 1))
    assert (await execute(context, key='CRASH'))['shipped'] == 10
    assert state(path)['stock'] == (90, 20, 2)


@pytest.mark.asyncio
async def test_commit_exception_is_unknown_and_original_key_recovers(shipping, monkeypatch):
    path, context = shipping
    transport = context.require_resource('dataService').transport
    begin = transport.begin_sql

    async def observed_begin():
        tx = await begin()
        commit = tx.commit_sql
        async def lost_acknowledgement():
            await commit()
            raise ConnectionError('commit acknowledgement lost')
        tx.commit_sql = lost_acknowledgement
        return tx

    monkeypatch.setattr(transport, 'begin_sql', observed_begin)
    with pytest.raises(BusinessOperationCommitUnknown) as caught:
        await execute(context)
    assert caught.value.outcome == 'unknown'
    assert state(path)['stock'] == (90, 20, 2)
    assert (await execute(warehouse.context_for(path)))['shipped'] == 10
    assert state(path)['results'] == state(path)['audit'] == 1


@pytest.mark.asyncio
async def test_postcommit_sink_failure_is_committed_and_replay_is_safe(shipping):
    path, context = shipping
    class Sink:
        def on_safe_event(self, context, event):
            raise RuntimeError('sink unavailable')
    context.with_app_audit_event_sink(Sink())
    with pytest.raises(GraphCommittedError) as caught:
        await execute(context)
    assert caught.value.committed is True
    assert state(path)['stock'] == (90, 20, 2)
    assert (await execute(context))['shipped'] == 10


@pytest.mark.asyncio
async def test_explicit_operation_context_cannot_escape_or_change_provider(shipping):
    path, context = shipping
    captured = []
    async def handler(owned, params):
        captured.append(owned)
        with pytest.raises(RuntimeError, match='participant'):
            owned.insert_resource('dataService', context.require_resource('dataService'))
        with pytest.raises(RuntimeError, match='participant'):
            owned.with_schema_provider(context.require_resource('dataService'))
        with pytest.raises(RuntimeError, match='participant'):
            owned.with_active_root(warehouse.ContextEntityRef('Tenant', 2))
        with pytest.raises(RuntimeError, match='schema changes'):
            await owned.ensure_schema()
        async def child():
            with pytest.raises(BusinessOperationError, match='another task'):
                await warehouse.load(owned, 'Stock', 1)
        await asyncio.create_task(child())
        return await warehouse.ship(owned, params)
    await execute(context, operation=replace(warehouse.SHIP, handler=handler))
    with pytest.raises(BusinessOperationError, match='closed'):
        await warehouse.load(captured[0], 'Stock', 1)
    assert state(path)['results'] == 1


@pytest.mark.asyncio
async def test_cancelled_handler_rolls_back_and_keeps_original_key_retryable(shipping):
    path, context = shipping
    before = state(path)
    staged = asyncio.Event()
    async def handler(owned, params):
        await warehouse.ship(owned, params)
        staged.set()
        await asyncio.Future()
    task = asyncio.create_task(execute(context, operation=replace(warehouse.SHIP, handler=handler)))
    await asyncio.wait_for(staged.wait(), timeout=5)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert state(path) == before
    assert (await execute(context))['shipped'] == 10


@pytest.mark.asyncio
async def test_unqualified_provider_rejects_before_handler(shipping):
    _, context = shipping
    service = context.require_resource('dataService')
    service.transport.serializes_business_operations = False
    async def handler(context, params):
        pytest.fail('handler must not run without qualified serialization')
    with pytest.raises(BusinessOperationError) as caught:
        await execute(context, operation=replace(warehouse.SHIP, handler=handler))
    assert caught.value.code == 'OPERATION_UNSUPPORTED'


@pytest.mark.asyncio
async def test_nested_operation_and_original_context_save_are_rejected(shipping):
    path, context = shipping
    async def handler(owned, params):
        with pytest.raises(BusinessOperationError) as caught:
            await execute(owned, key='NESTED')
        assert caught.value.code == 'OPERATION_NESTING_UNSUPPORTED'
        with pytest.raises(RuntimeError, match='re-enter'):
            await warehouse.ship(context, params)
        return await warehouse.ship(owned, params)
    await execute(context, operation=replace(warehouse.SHIP, handler=handler))
    assert state(path)['stock'] == (90, 20, 2)
    assert state(path)['results'] == 1


@pytest.mark.asyncio
async def test_independent_operations_on_same_context_serialize(shipping):
    path, context = shipping
    result = await asyncio.gather(execute(context, key='ONE'), execute(context, key='TWO'))
    assert sorted(row['shipped'] for row in result) == [10, 20]
    assert state(path)['stock'] == (80, 10, 3)
    assert state(path)['results'] == state(path)['audit'] == 2


@pytest.mark.asyncio
async def test_real_generated_entities_join_only_explicit_operation_context(tmp_path):
    # Isolate generated Q/models imports from other generated fixtures in this suite.
    code = '''
import asyncio, json, sqlite3, sys
from dataclasses import replace
from pathlib import Path
sys.path.insert(0, sys.argv[2])
from runtime_module import GENERATED_RUNTIME_MODULE
from Q import Q
from teaql.data_service import SQLiteTeaQLClient
from teaql.runtime import UserContext, ContextEntityRef, BusinessOperation, BusinessOperationError
async def main():
    path = sys.argv[1]
    client = SQLiteTeaQLClient(path)
    context = UserContext.new().install(GENERATED_RUNTIME_MODULE).insert_resource('dataService', client)
    context.disable_sql_log()
    await context.ensure_schema()
    await client.ensure_business_operation_schema()
    context.with_active_root(ContextEntityRef('Platform', 1))
    captured = []
    async def prepare(ctx, params): return None
    async def validate(ctx, params, before, result): return True
    async def create_work_item(ctx, title):
        item = await (Q.work_items().comment('Allocate work item')
                      .purpose('Create a graph in the business operation').new_entity(ctx))
        return item.update_title(title).update_platform(1)
    async def handler(ctx, params):
        first = await create_work_item(ctx, 'first')
        captured.append(first)
        await first.audit_as('create first graph').save(ctx)
        second = await create_work_item(ctx, params['title'])
        await second.audit_as('create second graph').save(ctx)
        return {'ids':[first.id,second.id]}
    operation = BusinessOperation('CreatePair','1','Platform',{'title':str},lambda c,p:True,prepare,handler,validate)
    with sqlite3.connect(path) as db:
        db.execute("CREATE TRIGGER reject_second BEFORE INSERT ON work_item_data WHEN NEW.title='reject' BEGIN SELECT RAISE(ABORT,'GENERATED_SECOND_FAILED'); END")
    try:
        await operation.execute(context,key='PAIR',parameters={'title':'reject'},comment='create pair')
        raise AssertionError('must fail')
    except BusinessOperationError as error:
        assert 'GENERATED_SECOND_FAILED' in str(error)
    with sqlite3.connect(path) as db:
        assert db.execute('SELECT COUNT(*) FROM work_item_data').fetchone()[0] == 0
        assert db.execute('SELECT COUNT(*) FROM teaql_operation_results').fetchone()[0] == 0
    # The generated graph must retain the intent of its reserved entity after rollback.
    assert captured[0].id is not None and captured[0]._action == 'Create'
    assert captured[0]._entity_root.has_pending(captured[0]._teaql_entity_key())
    with sqlite3.connect(path) as db: db.execute('DROP TRIGGER reject_second')
    result = await operation.execute(context,key='PAIR',parameters={'title':'second'},comment='create pair')
    with sqlite3.connect(path) as db:
        assert db.execute('SELECT COUNT(*) FROM work_item_data').fetchone()[0] == 2
    assert len(set(result['ids'])) == 2
    assert not captured[-1]._entity_root.has_pending(captured[-1]._teaql_entity_key())
    print(json.dumps({'generated_graphs':2,'rollback':True,'retry':True,'ledger_cleanup':True}))
asyncio.run(main())
'''
    generated_library = ROOT / 'examples' / 'conformance' / 'python-lib-core'
    status, stdout, stderr = await subprocess_code(code, tmp_path / 'generated.db', generated_library)
    assert status == 0, (stdout, stderr)
    assert json.loads(stdout)['ledger_cleanup'] is True
