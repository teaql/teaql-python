"""A small DDD shipping example using native TeaQL graph APIs.

This is a hand-written domain facade, not a claim of generated operation APIs.
The runtime supplies transaction, idempotency and serialized SQLite execution.
"""

import argparse
import asyncio
import json
from pathlib import Path
import tempfile

from teaql.core.entity import EntityKey, EntityRoot
from teaql.core.expr import Expr
from teaql.core.meta import EntityDescriptor, PropertyDescriptor
from teaql.core.mutation import InsertCommand, UpdateCommand
from teaql.core.query import SelectQuery
from teaql.core.value import Value
from teaql.data_service import QueryRequest
from teaql.provider.sqlite import create_sqlite_service, SimpleSchemaProvider
from teaql.runtime import BusinessOperation, BusinessOperationError, ContextEntityRef, RuntimeModule


def descriptors():
    result = []
    for name, fields in (
        ('Stock', ('tenant', 'on_hand', 'reserved')),
        ('TransferOrder', ('tenant', 'stock', 'quantity', 'shipped', 'received', 'cancelled')),
    ):
        entity = EntityDescriptor(name).table_name(name.lower() + '_data')
        entity.property(PropertyDescriptor('id', 'i64').is_id().required())
        entity.property(PropertyDescriptor('version', 'i64').is_version().required())
        for field in fields:
            entity.property(PropertyDescriptor(field, 'i64').required())
        result.append(entity)
    return result


def context_for(path, tenant=1):
    schema = SimpleSchemaProvider()
    module = RuntimeModule.new()
    for entity in descriptors():
        schema.register_entity(entity)
        module.entity(entity)
    service = create_sqlite_service(str(path), schema)
    context = module.into_context().insert_resource('dataService', service)
    context.with_schema_provider(service).with_active_root(ContextEntityRef('Tenant', tenant))
    context.with_user_identifier('warehouse-operator')
    context.disable_sql_log()
    return context


async def load(context, entity, identity):
    tenant = context.require_active_root('Tenant').id
    query = SelectQuery(entity).filter(Expr.new_and(Expr.eq('id', identity), Expr.eq('tenant', tenant)))
    query.comment('load shipping state').purpose('validate and execute warehouse operation')
    rows = (await context.require_resource('dataService').query(context, QueryRequest(query))).rows
    if len(rows) != 1:
        raise BusinessOperationError('REFERENCE_NOT_FOUND', f'{entity} is absent from the active tenant')
    return rows[0]


async def save_command(context, command):
    """One graph per command; the explicit operation coordinates their commit."""
    async def work(graph):
        graph.context.preflight_mutation(command)
        key = EntityKey(command.entity, command.values['id'].val if isinstance(command, InsertCommand) else command.id.val)
        ledger = EntityRoot()
        for field, value in command.values.items():
            ledger.set(key, field, value)
        result = await graph.transaction.mutate(
            graph.context, graph.request(command, graph.scope(key), ledger, key))
        if result.affected_rows != 1 or result.persisted_record is None:
            raise BusinessOperationError('VERSION_CONFLICT', 'shipping state changed; retry the whole operation')
        graph.after_commit(ledger.clear_committed)
        return result.persisted_record
    return await context.execute_graph_save(work, comment='persist shipping domain change')


async def ship(context, params):
    q = params['quantity']
    if q <= 0:
        raise BusinessOperationError('INVALID_QUANTITY', 'shipping quantity must be positive')
    order = await load(context, 'TransferOrder', params['order_id'])
    stock = await load(context, 'Stock', order['stock'])
    if (q > order['quantity'] - order['shipped'] - order['cancelled']
            or stock['reserved'] < q or stock['on_hand'] < q):
        raise BusinessOperationError('EXCEEDS_UNSHIPPED', 'quantity exceeds remaining order or reserved stock')
    if not (0 <= stock['reserved'] <= stock['on_hand'] and
            0 <= order['received'] <= order['shipped'] <= order['quantity'] - order['cancelled']):
        raise BusinessOperationError('INVALID_STATE', 'stored shipping state violates the declared invariants')

    # Domain behavior; no BEGIN, COMMIT, idempotency lookup, or retry protocol.
    await save_command(context, UpdateCommand.new('Stock', stock['id']).expected_version(stock['version'])
                       .value('on_hand', stock['on_hand'] - q).value('reserved', stock['reserved'] - q))
    updated = await save_command(context, UpdateCommand.new('TransferOrder', order['id']).expected_version(order['version'])
                                 .value('shipped', order['shipped'] + q))
    return {'order_id': updated['id'], 'shipped': updated['shipped'], 'quantity': q}


async def shipping_snapshot(context, params):
    order = await load(context, 'TransferOrder', params['order_id'])
    stock = await load(context, 'Stock', order['stock'])
    return {'order': order, 'stock': stock}


async def validate_shipping(context, params, before, result):
    """Reviewed domain contract, invoked by runtime even if handler omits checks."""
    after = await shipping_snapshot(context, params)
    order, stock = before['order'], before['stock']
    q = params['quantity']
    if not (q > 0 and q <= order['quantity'] - order['shipped'] - order['cancelled']
            and 0 <= order['received'] <= order['shipped']
            and stock['on_hand'] >= stock['reserved'] >= q):
        return False
    expected_stock = dict(stock, on_hand=stock['on_hand'] - q, reserved=stock['reserved'] - q,
                          version=stock['version'] + 1)
    expected_order = dict(order, shipped=order['shipped'] + q, version=order['version'] + 1)
    return (after['stock'] == expected_stock and after['order'] == expected_order
            and result == {'order_id': order['id'], 'shipped': order['shipped'] + q, 'quantity': q})


SHIP = BusinessOperation(
    name='ShipTransfer', version='1', root_type='Tenant',
    parameters={'order_id': int, 'quantity': int},
    authorize=lambda context, params: context.user_identifier() == 'warehouse-operator',
    prepare=shipping_snapshot, handler=ship, validate=validate_shipping,
)


async def initialize(path):
    context = context_for(path)
    await context.ensure_schema()
    await context.require_resource('dataService').ensure_business_operation_schema()
    await save_command(context, InsertCommand.new('Stock').value('id', 1).value('version', 1)
                       .value('tenant', 1).value('on_hand', 100).value('reserved', 30))
    await save_command(context, InsertCommand.new('TransferOrder').value('id', 1).value('version', 1)
                       .value('tenant', 1).value('stock', 1).value('quantity', 30)
                       .value('shipped', 0).value('received', 0).value('cancelled', 0))
    return context


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--worker', type=Path)
    parser.add_argument('--key')
    parser.add_argument('--quantity', type=int, default=10)
    args = parser.parse_args()
    if args.worker:
        try:
            result = await SHIP.execute(context_for(args.worker), key=args.key,
                                        parameters={'order_id': 1, 'quantity': args.quantity}, comment='ship transfer')
            print(json.dumps({'ok': True, 'result': result}))
        except BusinessOperationError as error:
            print(json.dumps({'ok': False, 'code': error.code, 'outcome': error.outcome}))
        return
    with tempfile.TemporaryDirectory() as directory:
        context = await initialize(Path(directory) / 'stock.db')
        first = await SHIP.execute(context, key='SHIP-1', parameters={'order_id': 1, 'quantity': 10}, comment='ship transfer')
        replay = await SHIP.execute(context_for(Path(directory) / 'stock.db'), key='SHIP-1',
                                    parameters={'order_id': 1, 'quantity': 10}, comment='retry ship transfer')
        assert first == replay == {'order_id': 1, 'shipped': 10, 'quantity': 10}
        stock = await load(context, 'Stock', 1)
        assert (stock['on_hand'], stock['reserved']) == (90, 20)
        print(json.dumps({'smoke': 'passed', 'result': first, 'replay_equal': True}))


if __name__ == '__main__':
    asyncio.run(main())
