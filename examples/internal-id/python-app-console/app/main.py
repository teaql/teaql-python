"""Receive a purchase order using IDs supplied by the warehouse Context."""

import asyncio
import json
from pathlib import Path
import sys

from Q import Q
from runtime_module import GENERATED_RUNTIME_MODULE
from teaql.core.mutation import InsertCommand, MutationRequest
from teaql.provider.sqlite import create_sqlite_service
from teaql.runtime import UserContext


class AllocationUnavailable(Exception):
    pass


class WarehouseAllocator:
    def __init__(self):
        self.level = {"PurchaseOrder": 99, "OrderItem": 199}
        self.floors = []
        self.fail_next_item = False
        self.lock = asyncio.Lock()

    async def next_id(self, entity: str) -> int:
        async with self.lock:
            if entity == "OrderItem" and self.fail_next_item:
                self.fail_next_item = False
                raise AllocationUnavailable("warehouse ID service unavailable for OrderItem")
            self.level[entity] += 1
            return self.level[entity]

    async def ensure_id_floor(self, entity: str, floor: int) -> None:
        async with self.lock:
            self.floors.append((entity, floor))
            self.level[entity] = max(self.level[entity], floor)


def order_request(warehouse, reference, identity=None):
    command = InsertCommand.new("PurchaseOrder").value("warehouse", warehouse).value("reference", reference)
    if identity is not None:
        command.value("id", identity)
    return MutationRequest(command, comment="Receive the numbered purchase order")


async def new_order(context, warehouse, reference):
    order = await Q.purchase_orders().comment("Prepare an incoming purchase order").purpose(
        "Reserve its warehouse identity").new_entity(context)
    return order.update_warehouse(warehouse).update_reference(reference)


async def new_item(context, order, sku, units):
    item = await Q.order_items().comment("Prepare an order item").purpose(
        "Reserve an item identity before graph save").new_entity(context)
    return item.update_purchase_order(order).update_sku(sku).update_quantity(units)


async def load_orders(context):
    return await Q.purchase_orders().order_by_id_ascending().limit(10).select_order_item_list().comment(
        "Read assigned order IDs and items").purpose("Reconcile the warehouse ledger").execute_for_list(context)


async def receive(context, service, warehouse, allocator):
    direct = await new_order(context, warehouse, "DIRECT")
    assert direct.id == 100
    await direct.audit_as("Receive one purchase order").save(context)

    await service.mutate(context, MutationRequest.Batch([
        order_request(warehouse, "BATCH"),
        MutationRequest.Batch([order_request(warehouse, "NESTED")], comment="receive a nested dispatch"),
    ], comment="receive a batch of purchase orders"))
    await service.mutate(context, order_request(warehouse, "EXPLICIT", 500))
    assert ("PurchaseOrder", 500) in allocator.floors

    graph = await new_order(context, warehouse, "GRAPH")
    assert graph.id == 501
    first = await new_item(context, graph.id, "FILTER", 2)
    assert first.id == 200
    allocator.fail_next_item = True
    try:
        await new_item(context, graph.id, "GASKET", 3)
    except AllocationUnavailable as error:
        assert str(error).endswith("for OrderItem")
    else:
        raise AssertionError("Item allocator failure was bypassed")
    assert [order.id for order in await load_orders(context)] == [100, 101, 102, 500]
    assert len(await Q.order_items().limit(5).comment("Check for partial receiving").purpose(
        "Allocator refusal must precede any graph write").execute_for_list(context)) == 0

    second = await new_item(context, graph.id, "GASKET", 3)
    assert (graph.id, second.id) == (501, 201)
    for item in (first, second):
        graph.order_item_list().append(item)
    await graph.audit_as("Receive purchase order and two stocked items").save(context)
    await graph.audit_as("Retry the same accepted purchase order").save(context)
    assert graph.id == 501


async def main(database: Path, phase: str):
    service = create_sqlite_service(str(database))
    try:
        context = UserContext.new().install(GENERATED_RUNTIME_MODULE)
        context.insert_resource("dataService", service)
        context.disable_sql_log()
        await context.ensure_schema()
        warehouse = await Q.warehouses().limit(1).comment("Read the seeded distribution center").purpose(
            "Associate orders with the warehouse").execute_for_one(context)
        assert warehouse is not None and warehouse.id == 1
        allocator = WarehouseAllocator()
        context.with_internal_id_allocator(allocator)
        if phase == "first":
            await receive(context, service, warehouse.id, allocator)
        orders = await load_orders(context)
        assert [order.id for order in orders] == [100, 101, 102, 500, 501]
        assert [order.reference for order in orders] == ["DIRECT", "BATCH", "NESTED", "EXPLICIT", "GRAPH"]
        items = sorted((item.id, item.sku, item.quantity) for item in orders[-1].order_item_list())
        assert items == [(200, "FILTER", 2), (201, "GASKET", 3)]
        print("WAREHOUSE_ORDER_IDS=" + json.dumps(dict(phase=phase, orders=[order.id for order in orders],
            items=[item[0] for item in items], failureRejected=phase == "first", rootId=warehouse.id)))
    finally:
        await service.close()


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[2] not in {"first", "restart"}:
        raise SystemExit("Usage: main.py DATABASE {first|restart}")
    asyncio.run(main(Path(sys.argv[1]), sys.argv[2]))
