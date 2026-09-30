import asyncio
from datetime import date

import pytest

from teaql.core import (
    BusinessIdDefinition,
    BusinessIdError,
    BusinessIdErrorCode,
    BusinessIdPlan,
    BusinessIdScope,
)
from teaql.provider.sqlite import create_sqlite_service
from teaql.runtime import UserContext
from teaql.sql import SqlBusinessIdAllocator


def plan(scope, maximum=100):
    definition = BusinessIdDefinition.daily_permuted(
        "order_number", "ORD", "order_number"
    )
    return BusinessIdPlan(
        definition,
        scope,
        date(2026, 10, 1),
        "20261001",
        0,
        maximum,
    )


@pytest.mark.asyncio
async def test_sqlite_business_id_allocator_requires_explicit_schema(tmp_path):
    service = create_sqlite_service(str(tmp_path / "explicit.db"))
    allocator = SqlBusinessIdAllocator(service.dialect, service.transport)

    with pytest.raises(RuntimeError, match="explicit ensure_schema"):
        await allocator.allocate(plan(BusinessIdScope(
            "root", "commerce_order", "order_number", "20261001"
        )))


@pytest.mark.asyncio
async def test_sqlite_business_id_allocator_is_shared_concurrent_and_restart_safe(tmp_path):
    path = str(tmp_path / "business-ids.db")
    first_service = create_sqlite_service(path)
    second_service = create_sqlite_service(path)
    await UserContext.new().insert_resource("dataService", first_service).ensure_schema()
    first = SqlBusinessIdAllocator(first_service.dialect, first_service.transport)
    second = SqlBusinessIdAllocator(second_service.dialect, second_service.transport)
    shared = plan(BusinessIdScope(
        "root", "commerce_order", "order_number", "20261001"
    ))

    allocated = await asyncio.gather(*[
        (first if index % 2 == 0 else second).allocate(shared)
        for index in range(40)
    ])
    assert sorted(value.sequence for value in allocated) == list(range(40))

    restarted_service = create_sqlite_service(path)
    restarted = SqlBusinessIdAllocator(
        restarted_service.dialect, restarted_service.transport
    )
    assert (await restarted.allocate(shared)).sequence == 40

    other_scope = plan(BusinessIdScope(
        "other-root", "commerce_order", "order_number", "20261001"
    ))
    assert (await restarted.allocate(other_scope)).sequence == 0


@pytest.mark.asyncio
async def test_sqlite_business_id_allocator_reports_capacity_exhaustion(tmp_path):
    service = create_sqlite_service(str(tmp_path / "capacity.db"))
    await UserContext.new().insert_resource("dataService", service).ensure_schema()
    allocator = SqlBusinessIdAllocator(service.dialect, service.transport)
    bounded = plan(BusinessIdScope(
        "root", "commerce_order", "tiny", "20261001"
    ), maximum=1)

    assert (await allocator.allocate(bounded)).sequence == 0
    assert (await allocator.allocate(bounded)).sequence == 1
    with pytest.raises(BusinessIdError) as failure:
        await allocator.allocate(bounded)
    assert failure.value.code == BusinessIdErrorCode.RANGE_EXHAUSTED
