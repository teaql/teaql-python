import asyncio

import pytest

from teaql.provider.sqlite import create_sqlite_service


@pytest.mark.asyncio
async def test_sqlite_id_space_is_optimistic_and_shared_across_services(tmp_path):
    path = str(tmp_path / "ids.db")
    first = create_sqlite_service(path)
    second = create_sqlite_service(path)

    assert await first.next_id("Order") == 1
    assert await second.next_id("Order") == 2
    assert await first.next_id("Customer") == 1
    await first.ensure_id_floor("SeededType", 1001)
    assert await second.next_id("SeededType") == 1002

    ids = await asyncio.gather(*[
        (first if index % 2 == 0 else second).next_id("Order")
        for index in range(20)
    ])
    assert sorted(ids) == list(range(3, 23))
    assert len(set(ids)) == 20


@pytest.mark.asyncio
async def test_sqlite_id_space_continues_after_runtime_recreation(tmp_path):
    path = str(tmp_path / "restart.db")
    assert await create_sqlite_service(path).next_id("Order") == 1
    assert await create_sqlite_service(path).next_id("Order") == 2
