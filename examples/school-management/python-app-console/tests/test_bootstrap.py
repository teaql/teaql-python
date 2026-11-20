import asyncio
import sys
from pathlib import Path

import aiosqlite
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from Q import Q
from runtime_module import GENERATED_RUNTIME_MODULE
from teaql.data_service import SQLiteTeaQLClient
from teaql.runtime import UserContext


async def new_context(path):
    client = SQLiteTeaQLClient(str(path))
    context = UserContext().install(GENERATED_RUNTIME_MODULE).insert_resource("dataService", client)
    return client, context


@pytest.mark.asyncio
async def test_generated_bootstrap_converges_across_contexts(tmp_path):
    path = tmp_path / "concurrent-bootstrap.sqlite"
    initial_client, initial = await new_context(path)
    await initial.ensure_schema()
    await initial_client.close()

    async with aiosqlite.connect(path) as database:
        await database.execute("DELETE FROM school_type_data")
        await database.execute("DELETE FROM platform_data")
        await database.commit()

    left_client, left = await new_context(path)
    right_client, right = await new_context(path)
    try:
        await asyncio.gather(left.ensure_schema(), right.ensure_schema())
        roots = await Q.platforms().comment("read root").purpose("verify concurrent bootstrap").execute_for_list(left)
        constants = await Q.school_types().comment("read constants").purpose("verify concurrent bootstrap").execute_for_list(left)
        assert len(roots) == 1
        assert [(value.id, value.code) for value in constants] == [(1001, "PRIMARY"), (1002, "SECONDARY")]

        async with aiosqlite.connect(path) as database:
            await database.execute("UPDATE school_type_data SET name = 'DRIFT' WHERE id = 1001")
            await database.commit()

        await asyncio.gather(left.ensure_schema(), right.ensure_schema())
        reconciled = await Q.school_types().with_id_is(1001).comment("read constant").purpose("verify concurrent reconcile").execute_for_one(left)
        assert reconciled.name == "Primary"
        assert reconciled.version == 2
    finally:
        await left_client.close()
        await right_client.close()
