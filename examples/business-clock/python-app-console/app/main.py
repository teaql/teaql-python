"""Place delivery orders on opposite sides of a controlled business-day cutover."""
import asyncio
from datetime import datetime, timezone
import json
import os

from E import E
from Q import Q
from runtime_module import GENERATED_RUNTIME_MODULE
from teaql.provider.sqlite import create_sqlite_service
from teaql.runtime import FixedBusinessClock, UserContext


class UnavailableBusinessClock:
    def now(self):
        raise RuntimeError("BUSINESS_CLOCK_UNAVAILABLE")


def create_context() -> UserContext:
    context = UserContext.new().install(GENERATED_RUNTIME_MODULE)
    service = create_sqlite_service(os.environ["TEAQL_DATABASE_CONNECTION_STRING"])
    return context.insert_resource("dataService", service)


async def place_order(context, reference):
    order_date = context.business_date()
    order = await (
        Q.delivery_orders().comment("Initialize the delivery order")
        .purpose("Record a delivery on the current business day").new_entity(context)
    )
    order.update_platform(1).update_reference(reference).update_order_date(order_date)
    await order.audit_as("Record the delivery date chosen by the business clock").save(context)
    return order


async def load_order(context, reference):
    return await (
        Q.delivery_orders().with_reference_is(reference).limit(2)
        .comment("Read the delivery order by its reference")
        .purpose("Check the persisted business-day assignment").execute_for_one(context)
    )


async def main() -> None:
    context = create_context()
    await context.ensure_schema()

    label = os.environ["TEAQL_DELIVERY_ORDER_ROUND"]
    before_ref, after_ref = f"DEL-{label}-before", f"DEL-{label}-after"
    before = datetime(2026, 10, 1, 23, 59, tzinfo=timezone.utc)
    after = datetime(2026, 10, 2, 0, 1, tzinfo=timezone.utc)
    context.with_business_clock(FixedBusinessClock(before))
    first = await place_order(context, before_ref)
    context.with_business_clock(FixedBusinessClock(after))
    second = await place_order(context, after_ref)
    assert first.id != second.id

    rows = []
    for identity, reference, expected in (
        (first.id, before_ref, before.date()),
        (second.id, after_ref, after.date()),
    ):
        stored = await load_order(context, reference)
        assert stored is not None and stored.id == identity
        actual = E.delivery_order(stored).order_date().eval()
        assert actual == expected
        rows.append(dict(id=identity, reference=reference, date=actual.isoformat()))

    rejected_ref = f"DEL-{label}-unavailable"
    context.with_business_clock(UnavailableBusinessClock())
    try:
        await place_order(context, rejected_ref)
    except RuntimeError as error:
        assert str(error) == "BUSINESS_CLOCK_UNAVAILABLE"
    else:
        raise AssertionError("An order was accepted without a business day")
    context.with_business_clock(FixedBusinessClock(after))
    assert await load_order(context, rejected_ref) is None
    print("DELIVERY_ORDER_CUTOVER=" + json.dumps(dict(round=label, orders=rows, rejected=rejected_ref)))


if __name__ == "__main__":
    asyncio.run(main())
