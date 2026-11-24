import asyncio
from datetime import datetime, timezone
import json
import re

from Q import Q
from teaql.core.request_intent import RequestIntentError
import os
from teaql.provider.sqlite import create_sqlite_service
from teaql.core import BusinessIdEncodingKey
from teaql.runtime import (
    DefaultBusinessIdProfileFactory,
    DefaultBusinessIdService,
    FixedBusinessClock,
    StaticBusinessIdKeyProvider,
)
from teaql.sql import SqlBusinessIdAllocator
from teaql.runtime import UserContext
from runtime_module import GENERATED_RUNTIME_MODULE


def create_context() -> UserContext:
    context = UserContext.new().install(GENERATED_RUNTIME_MODULE)
    database_url = os.environ["TEAQL_DATABASE_CONNECTION_STRING"]
    data_service = create_sqlite_service(database_url)
    context.insert_resource("dataService", data_service)
    key_text = os.environ.get("TEAQL_BUSINESS_ID_KEY_V1_HEX", "")
    if len(key_text) != 64:
        raise RuntimeError("TEAQL_BUSINESS_ID_KEY_V1_HEX must contain exactly 64 hexadecimal characters")
    try:
        key = bytes.fromhex(key_text)
    except ValueError as error:
        raise RuntimeError("TEAQL_BUSINESS_ID_KEY_V1_HEX must contain exactly 64 hexadecimal characters") from error
    try:
        key_version = int(os.environ.get("TEAQL_BUSINESS_ID_KEY_VERSION", "1"))
    except ValueError as error:
        raise RuntimeError("TEAQL_BUSINESS_ID_KEY_VERSION must be a positive integer") from error
    if key_version < 1:
        raise RuntimeError("TEAQL_BUSINESS_ID_KEY_VERSION must be a positive integer")
    allocator = SqlBusinessIdAllocator(data_service.dialect, data_service.transport)
    context.with_business_id_profile_factory(DefaultBusinessIdProfileFactory())
    context.with_business_id_key_provider(StaticBusinessIdKeyProvider(
        BusinessIdEncodingKey(key_version, key)
    ))
    context.with_business_id_service(DefaultBusinessIdService(allocator))
    return context.with_business_clock(FixedBusinessClock(
        datetime(2026, 10, 1, 8, 30, tzinfo=timezone.utc)
    ))


async def main() -> None:
    context = create_context()
    await context.ensure_schema()
    round_label = os.environ["TEAQL_PURCHASE_NUMBERING_ROUND"]
    first = await create_order(context, f"Northwind-{round_label}")
    second = await create_order(context, f"Contoso-{round_label}")
    first_number, second_number = first.orderNumber, second.orderNumber
    assert first_number is not None and second_number is not None
    assert first.id != second.id and first_number != second_number
    assert all(re.fullmatch(r"ORD-20261001-[0-9A-Z]{6}", number.value)
               for number in (first_number, second_number))

    first_id = first.id
    await first.audit_as("Retry recording Northwind's purchase order").save(context)
    assert first.id == first_id and first.orderNumber == first_number
    for order in (first, second):
        persisted = await (
            Q.purchase_order_by_order_number(order.orderNumber)
            .comment("Read a purchase order by its assigned number")
            .purpose("Verify the procurement record and allocation")
            .execute_for_one(context)
        )
        assert persisted is not None and persisted.id == order.id
        assert persisted.orderNumber == order.orderNumber and persisted.supplier == order.supplier

    rejected = await prepare_order(context, "Unaudited Supplier")
    try:
        await rejected.audit_as(" ").save(context)
    except RequestIntentError as error:
        assert error.code == "REQUEST_COMMENT_REQUIRED" and error.request_kind == "mutation"
        rejection = error.code
    else:
        raise AssertionError("Unaudited purchase order was accepted")
    found = await (
        Q.purchase_orders().with_supplier_is("Unaudited Supplier").limit(2)
        .comment("Look for the unaudited purchase order")
        .purpose("Prove the rejected operation stored no order")
        .execute_for_one(context)
    )
    assert found is None
    print("PURCHASE_ORDER_NUMBERING=" + json.dumps(dict(
        round=round_label, firstId=first.id, firstNumber=first_number.value,
        secondId=second.id, secondNumber=second_number.value,
        retryNumber=first.orderNumber.value, rejection=rejection, typedReadback=True,
    )))


async def prepare_order(context, supplier):
    order = await (
        Q.purchase_orders().comment("Initialize the purchase order")
        .purpose("Record a procurement commitment").new_entity(context)
    )
    return order.update_platform(1).update_supplier(supplier)


async def create_order(context, supplier):
    order = await prepare_order(context, supplier)
    await order.audit_as("Record the approved purchase order").save(context)
    return order


if __name__ == "__main__":
    asyncio.run(main())
