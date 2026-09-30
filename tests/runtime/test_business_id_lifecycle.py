from datetime import datetime, timezone

import pytest

from teaql.core import (
    BusinessIdDefinition,
    BusinessIdEncodingKey,
    BusinessIdError,
    BusinessIdErrorCode,
)
from teaql.runtime import (
    DefaultBusinessIdProfileFactory,
    DefaultBusinessIdService,
    FixedBusinessClock,
    InMemoryBusinessIdAllocator,
    StaticBusinessIdKeyProvider,
    UserContext,
)


class Slot:
    def __init__(self, value=None, new=True):
        self.value = value
        self.new = new

    def current_value(self):
        return self.value

    def new_aggregate(self):
        return self.new

    def assign_canonical_value(self, value):
        self.value = value


def context_with(allocator):
    return (
        UserContext.new()
        .with_business_clock(
            FixedBusinessClock(datetime(2026, 10, 1, 8, 30, tzinfo=timezone.utc))
        )
        .with_business_id_key_provider(
            StaticBusinessIdKeyProvider(BusinessIdEncodingKey(1, bytes(range(32))))
        )
        .with_business_id_profile_factory(DefaultBusinessIdProfileFactory())
        .with_business_id_service(DefaultBusinessIdService(allocator))
    )


@pytest.mark.asyncio
async def test_context_owned_business_id_lifecycle_is_idempotent_and_uses_business_date():
    allocator = InMemoryBusinessIdAllocator()
    context = context_with(allocator)
    definition = BusinessIdDefinition.daily_permuted(
        "order_number", "ORD", "order_number"
    )
    slot = Slot()

    first = await context.ensure_business_id(
        definition, "commerce", "commerce_order", slot
    )
    retry = await context.ensure_business_id(
        definition, "commerce", "commerce_order", slot
    )
    following = await context.ensure_business_id(
        definition, "commerce", "commerce_order", Slot()
    )

    assert first == retry
    assert slot.value == first.value
    assert first.value.startswith("ORD-20261001-")
    assert following.value != first.value


@pytest.mark.asyncio
async def test_established_aggregate_cannot_acquire_missing_business_id():
    context = context_with(InMemoryBusinessIdAllocator())
    definition = BusinessIdDefinition.daily_permuted(
        "order_number", "ORD", "order_number"
    )

    with pytest.raises(BusinessIdError) as failure:
        await context.ensure_business_id(
            definition, "commerce", "commerce_order", Slot(new=False)
        )

    assert failure.value.code == BusinessIdErrorCode.IMMUTABLE
