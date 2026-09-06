import asyncio
from datetime import date, datetime
from decimal import Decimal
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python-lib-core"))

from Q import Q
from models.commerce_platform import CommercePlatform
from models.customer import Customer
from models.customer_order import CustomerOrder
from models.order_search_preset import OrderSearchPreset
from models.order_status import OrderStatus
from runtime_module import GENERATED_RUNTIME_MODULE
from teaql.data_service import SQLiteTeaQLClient
from teaql.runtime import UserContext


class StandardAudit:
    async def on_event(self, _ctx, event):
        print(f"[audit/immutable] {event.kind} {event.entity}#{event.entity_id}")


class AppAudit:
    async def on_safe_event(self, _ctx, event):
        print(f"[audit/app] {event.kind} {event.entity}#{event.entity_id}; safe_fields={len(event.fields)}")


async def save(entity, context, reason):
    await entity.audit_as(reason).save(context)
    return entity


async def seed(context):
    existing = await (Q.customer_orders()
        .with_order_number_is("WEB-2026-001")
        .comment("Check whether deterministic quick-start data exists")
        .purpose("Initialize the local order-management example")
        .execute_for_list(context))
    if existing:
        print("[seed] deterministic data already exists; no duplicate rows added")
        return

    now = datetime(2026, 8, 13, 9, 0, 0)
    platform = await (Q.commerce_platforms().with_id_is(1)
        .comment("Load generated commerce root").purpose("Seed quick-start data")
        .execute_for_one(context))
    assert platform is not None
    customer = await save(Customer(name="Acme Retail", email="masked-in-quick-start",
                                   commercePlatform=platform.id, createTime=now, updateTime=now), context,
                          "Create masked quick-start customer")
    pending = await (Q.order_statuses().with_id_is(1001)
        .comment("Load generated pending status").purpose("Seed quick-start data")
        .execute_for_one(context))
    assert pending is not None
    await save(CustomerOrder(orderNumber="WEB-2026-001", orderDate=date(2026, 8, 12),
                             totalAmount=Decimal("129.95"), status=pending.id,
                             customer=customer.id, commercePlatform=platform.id,
                             createTime=now, updateTime=now), context,
               "Create deterministic quick-start order")
    print("[seed] inserted deterministic platform, customer, status, and order")


async def main():
    database = Path(os.environ.get("TEAQL_ORDER_MANAGEMENT_DB", ROOT / ".local" / "order.db"))
    if not database.exists():
        print(f"[database] {database} was not found; TeaQL will create it")
    database.parent.mkdir(parents=True, exist_ok=True)
    client = SQLiteTeaQLClient(str(database))
    context = (UserContext.new().install(GENERATED_RUNTIME_MODULE)
           .insert_resource("dataService", client)
           .initialize_audit(StandardAudit(), AppAudit())
           .configure_audit_policy("Customer", mask_fields=("email",))
           .configure_audit_policy("OrderSearchPreset", mask_fields=("filter_json",)))
    await context.ensure_schema()
    print("[schema] ensured 7 generated entity tables")
    await seed(context)

    result = await (Q.customer_orders()
        .with_order_number_containing("WEB-")
        .order_by_id_ascending()
        .comment("List WEB orders for the terminal quick start")
        .purpose("Show the operator a deterministic order list")
        .execute_for_list(context))
    rows = result
    print(f"[query] matched {len(rows)} order(s)")
    for row in rows:
        print(f"  {row.orderNumber}  {row.orderDate}  {row.totalAmount}")

    request_id = "quick-start-pending-orders"
    preset = await (Q.order_search_presets()
        .with_request_id_is(request_id)
        .comment("Check idempotent quick-start preset")
        .purpose("Persist the operator's reusable search")
        .execute_for_one(context))
    if preset is None:
        preset = OrderSearchPreset(name="Pending web orders", filterJson='{"order_number":"WEB-"}',
                                   requestId=request_id, ownerUserId="quick-start-user",
                                   commercePlatform=rows[0].commercePlatform,
                                   createTime=datetime.now(), updateTime=datetime.now())
        await save(preset, context, "Save idempotent quick-start search preset")
        print(f"[mutation] saved preset #{preset.id}")
    else:
        print(f"[mutation] preset #{preset.id} already exists")
    await client.close()


if __name__ == "__main__":
    asyncio.run(main())
