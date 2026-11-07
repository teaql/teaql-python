"""Creation must await the selected allocator without producing partial state."""
import asyncio

import pytest

from teaql.runtime import UserContext


class Allocator:
    def __init__(self, *values):
        self.values = iter(values)
        self.calls = []

    async def next_id(self, entity):
        self.calls.append(entity)
        value = next(self.values)
        if isinstance(value, BaseException):
            raise value
        return value

    async def ensure_id_floor(self, entity, floor):
        raise AssertionError("reservation must not synchronize a floor")


@pytest.mark.asyncio
async def test_selected_allocator_failure_is_exact_and_does_not_fall_back():
    failure = RuntimeError("controlled allocator failure")
    selected, fallback = Allocator(failure, 702), Allocator(999)
    context = (UserContext().with_internal_id_allocator(selected)
               .insert_resource("dataService", fallback))
    with pytest.raises(RuntimeError) as caught:
        await context.next_id("PurchaseOrder")
    assert caught.value is failure
    assert context.managed_entities() == []
    assert await context.next_id("PurchaseOrder") == 702
    assert selected.calls == ["PurchaseOrder", "PurchaseOrder"]
    assert fallback.calls == []


@pytest.mark.asyncio
@pytest.mark.parametrize("value", [0, -1, True, 1.5, "1", None, 2**64])
async def test_invalid_identity_is_rejected_without_coercion_or_fallback(value):
    allocator = Allocator(value, 703)
    context = UserContext().with_internal_id_allocator(allocator)
    with pytest.raises(ValueError, match="positive unsigned-64"):
        await context.next_id("PurchaseOrder")
    assert context.managed_entities() == []
    assert await context.next_id("PurchaseOrder") == 703


@pytest.mark.asyncio
async def test_provider_reservation_preserves_namespace_and_unsigned_boundary():
    provider = Allocator(1, 2**64 - 1)
    context = UserContext().insert_resource("dataService", provider)
    assert await context.next_id("PurchaseOrder") == 1
    assert await context.next_id("OrderItem") == 2**64 - 1
    assert provider.calls == ["PurchaseOrder", "OrderItem"]


@pytest.mark.asyncio
async def test_cancellation_propagates_and_does_not_use_another_allocator():
    selected, fallback = Allocator(asyncio.CancelledError()), Allocator(999)
    context = (UserContext().with_internal_id_allocator(selected)
               .insert_resource("dataService", fallback))
    with pytest.raises(asyncio.CancelledError):
        await context.next_id("PurchaseOrder")
    assert fallback.calls == []
    assert context.managed_entities() == []


@pytest.mark.asyncio
async def test_invalid_request_or_missing_capability_fails_before_initialization():
    allocator = Allocator(701)
    context = UserContext().with_internal_id_allocator(allocator)
    for entity in (None, "", " ", 12):
        with pytest.raises(ValueError, match="entity name"):
            await context.next_id(entity)
    assert allocator.calls == []
    sync_provider = type("SyncProvider", (), {"next_id": lambda *_: 1})()
    with pytest.raises(TypeError, match="async next_id"):
        await UserContext().insert_resource("dataService", sync_provider).next_id("PurchaseOrder")
    with pytest.raises(TypeError, match="async next_id"):
        await UserContext().insert_resource("dataService", object()).next_id("PurchaseOrder")
