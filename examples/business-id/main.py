import asyncio
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from teaql.core import BusinessIdDefinition, BusinessIdEncodingKey
from teaql.provider.sqlite import create_sqlite_service
from teaql.runtime import (
    DefaultBusinessIdProfileFactory,
    DefaultBusinessIdService,
    FixedBusinessClock,
    StaticBusinessIdKeyProvider,
    UserContext,
)
from teaql.sql import SqlBusinessIdAllocator


class OrderNumberSlot:
    def __init__(self):
        self.value = None

    def current_value(self):
        return self.value

    def new_aggregate(self):
        return True

    def assign_canonical_value(self, value):
        self.value = value


async def main():
    with TemporaryDirectory() as directory:
        service = create_sqlite_service(str(Path(directory) / "business-id.db"))
        allocator = SqlBusinessIdAllocator(service.dialect, service.transport)
        context = (
            UserContext.new()
            .insert_resource("dataService", service)
            .with_business_clock(FixedBusinessClock(
                datetime(2026, 10, 1, 8, 30, tzinfo=timezone.utc)
            ))
            .with_business_id_key_provider(StaticBusinessIdKeyProvider(
                BusinessIdEncodingKey(1, bytes(range(32)))
            ))
            .with_business_id_profile_factory(DefaultBusinessIdProfileFactory())
            .with_business_id_service(DefaultBusinessIdService(allocator))
        )
        await context.ensure_schema()
        slot = OrderNumberSlot()
        definition = BusinessIdDefinition.daily_permuted(
            "order_number", "ORD", "order_number"
        )
        first = await context.ensure_business_id(
            definition, "commerce", "commerce_order", slot
        )
        retry = await context.ensure_business_id(
            definition, "commerce", "commerce_order", slot
        )
        assert first == retry and slot.value.startswith("ORD-20261001-")
        print("PASS Python governed Business ID lifecycle example")


asyncio.run(main())
