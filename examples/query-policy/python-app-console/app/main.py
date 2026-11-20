"""Run the same generated procurement query for two tenant principals."""

import asyncio
import json
from pathlib import Path
import sys

from Q import Q
from runtime_module import GENERATED_RUNTIME_MODULE
from teaql.core.expr import Expr
from teaql.provider.sqlite import create_sqlite_service
from teaql.runtime import UserContext


class TenantPolicy:
    def __init__(self, tenant_id):
        self.tenant_id = tenant_id
        self.calls = []

    def __call__(self, query):
        self.calls.append(query.entity)
        if self.tenant_id is None or query.entity not in {"PurchaseOrder", "OrderItem"}:
            raise PermissionError("The principal cannot read procurement records")
        scope = Expr.eq("tenant", self.tenant_id)
        query.filter(Expr.new_and(query.filter_expr, scope) if query.filter_expr is not None else scope)


def context(service, policy=None):
    caller = UserContext.new().install(GENERATED_RUNTIME_MODULE)
    caller.insert_resource("dataService", service)
    caller.disable_sql_log()
    if policy is not None:
        caller.with_request_policy(policy)
    return caller


async def seed(caller):
    platform = await Q.platforms().limit(1).comment("Read the regional platform").purpose(
        "Set up the procurement demonstration").execute_for_one(caller)
    assert platform is not None and platform.id == 1
    tenants = []
    for name in ("Cedar Supplies", "Harbor Services"):
        tenant = await Q.tenants().comment("Prepare one procurement tenant").purpose(
            "Give each organization a distinct scope").new_entity(caller)
        tenant.update_name(name).update_platform(platform.id)
        await tenant.audit_as("Register a procurement tenant").save(caller)
        tenants.append(tenant)
    assert [tenant.id for tenant in tenants] == [1, 2]

    orders = []
    for tenant, reference in ((tenants[0], "PO-CEDAR"), (tenants[1], "PO-HARBOR"),
                              (tenants[0], "ARCHIVED-CEDAR")):
        order = await Q.purchase_orders().comment("Prepare a receiving order").purpose(
            "Set up current and archived procurement records").new_entity(caller)
        order.update_tenant(tenant.id).update_reference(reference)
        await order.audit_as("Record a procurement order").save(caller)
        orders.append(order)
    for order, tenant, sku in ((orders[0], tenants[0], "CEDAR-LINE"),
                               (orders[0], tenants[1], "HARBOR-HANDOFF"),
                               (orders[1], tenants[1], "HARBOR-LINE")):
        line = await Q.order_items().comment("Prepare one supplier line").purpose(
            "Represent a direct order or a partner handoff").new_entity(caller)
        line.update_purchase_order(order.id).update_tenant(tenant.id).update_sku(sku)
        await line.audit_as("Register a supplier-owned order line").save(caller)


async def verify_scope(service, neutral):
    # The same prepared request and nested selection are reused for all three callers.
    child = Q.order_items().select_sku().order_by_id_ascending().limit(10).comment(
        "Read supplier-owned receiving lines")
    request = (Q.purchase_orders().with_reference_starting_with("PO-").order_by_id_ascending()
               .limit(10).select_order_item_list_with(child).comment("Read current orders")
               .purpose("Show the same procurement screen to each tenant"))

    async def read(caller):
        result = await request.execute_for_list(caller)
        return [[order.reference, [line.sku for line in order.order_item_list()]] for order in result]

    cedar, harbor, guest = TenantPolicy(1), TenantPolicy(2), TenantPolicy(None)
    a_caller, b_caller = context(service, cedar), context(service, harbor)
    a, b, both = await read(a_caller), await read(b_caller), await read(neutral)
    assert a == [["PO-CEDAR", ["CEDAR-LINE"]]]
    assert b == [["PO-HARBOR", ["HARBOR-LINE"]]]
    assert both == [["PO-CEDAR", ["CEDAR-LINE", "HARBOR-HANDOFF"]], ["PO-HARBOR", ["HARBOR-LINE"]]]
    assert await read(a_caller) == a
    walk = ["PurchaseOrder", "OrderItem"]
    assert cedar.calls == walk * 2 and harbor.calls == walk
    try:
        await read(context(service, guest))
    except PermissionError as error:
        assert str(error) == "The principal cannot read procurement records"
    else:
        raise AssertionError("Unauthorized caller received procurement data")
    assert guest.calls == ["PurchaseOrder"]
    return dict(cedar=a, harbor=b, unscoped=both, traverseCedar=cedar.calls, traverseHarbor=harbor.calls,
                denied=True, reusedRequest=True)


async def main(database: Path, phase: str):
    service = create_sqlite_service(str(database))
    try:
        neutral = context(service)
        await neutral.ensure_schema()
        if phase == "first":
            await seed(neutral)
        result = await verify_scope(service, neutral)
        print("TENANT_ORDER_POLICY=" + json.dumps(dict(phase=phase, **result)))
    finally:
        await service.close()


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[2] not in {"first", "restart"}:
        raise SystemExit("Usage: main.py DATABASE {first|restart}")
    asyncio.run(main(Path(sys.argv[1]), sys.argv[2]))
