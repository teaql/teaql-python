"""The optional-module SQL lease shares the native graph's physical owner."""

import aiosqlite
import pytest

from teaql.core.meta import EntityDescriptor, PropertyDescriptor
from teaql.core.entity import EntityKey
from teaql.core.mutation import InsertCommand
from teaql.core.value import DataType, Value
from teaql.provider.sqlite import SimpleSchemaProvider
from teaql.provider.sqlite.dialect import SqliteDialect
from teaql.provider.sqlite.transport import SqliteTransport
from teaql.runtime import RuntimeModule
from teaql.sql.executor import SqlDataServiceExecutor
from teaql.sql.types import CompiledQuery


async def fixture(tmp_path):
    path = str(tmp_path / "graph-owner.db")
    descriptor = EntityDescriptor("Asset").table_name("asset")
    descriptor.property(PropertyDescriptor("id", DataType.I64).is_id())
    descriptor.property(PropertyDescriptor("version", DataType.I64).is_version())
    descriptor.property(PropertyDescriptor("name", DataType.Text))
    schema = SimpleSchemaProvider()
    schema.register_entity(descriptor)
    context = RuntimeModule.new().entity(descriptor).into_context()
    context.insert_resource("dataService", SqlDataServiceExecutor(SqliteDialect(), SqliteTransport(path), schema))
    async with aiosqlite.connect(path) as db:
        await db.execute("CREATE TABLE asset (id INTEGER PRIMARY KEY, version INTEGER, name TEXT)")
        await db.execute("CREATE TABLE module_binding (id INTEGER PRIMARY KEY, asset_id INTEGER NOT NULL)")
        await db.commit()
    return context, path


async def rows(path, table):
    async with aiosqlite.connect(path) as db:
        async with db.execute(f"SELECT * FROM {table}") as cursor:
            return await cursor.fetchall()


@pytest.mark.asyncio
async def test_native_graph_and_module_rows_commit_or_rollback_together(tmp_path):
    context, path = await fixture(tmp_path)
    retained = []

    async def save(graph, asset_id, *, fail=False):
        command = (InsertCommand.new("Asset").value("id", asset_id)
                   .value("version", 1).value("name", "document"))
        await graph.transaction.mutate(graph.context, graph.request(command, graph.scope(EntityKey("Asset", asset_id))))

        async def bind(sql):
            retained.append(sql)
            assert not hasattr(sql, "commit_sql")
            await sql.execute_sql(CompiledQuery(
                "INSERT INTO module_binding(id, asset_id) VALUES (?, ?)",
                [Value.I64(asset_id), Value.I64(asset_id)]))
            assert len(await sql.fetch_all_sql(CompiledQuery(
                "SELECT id FROM asset WHERE id = ?", [Value.I64(asset_id)]))) == 1

        await graph.with_sql_transport(bind)
        if fail:
            raise RuntimeError("abort graph")

    await context.execute_graph_save(lambda graph: save(graph, 1), comment="save asset")
    assert len(await rows(path, "asset")) == len(await rows(path, "module_binding")) == 1
    with pytest.raises(RuntimeError, match="abort graph"):
        await context.execute_graph_save(lambda graph: save(graph, 2, fail=True), comment="save asset")
    assert len(await rows(path, "asset")) == len(await rows(path, "module_binding")) == 1
    with pytest.raises(RuntimeError, match="BLOB_TRANSACTION_REQUIRED"):
        await retained[0].execute_sql(CompiledQuery("DELETE FROM module_binding", []))


@pytest.mark.asyncio
async def test_caught_callback_or_sql_error_still_blocks_graph_commit(tmp_path):
    context, path = await fixture(tmp_path)

    async def save(graph, fail_in_sql):
        command = (InsertCommand.new("Asset").value("id", 1)
                   .value("version", 1).value("name", "document"))
        await graph.transaction.mutate(graph.context, graph.request(command, graph.scope(EntityKey("Asset", 1))))

        async def bind(sql):
            await sql.execute_sql(CompiledQuery(
                "INSERT INTO module_binding(id, asset_id) VALUES (1, 1)", []))
            if fail_in_sql:
                try:
                    await sql.execute_sql(CompiledQuery(
                        "INSERT INTO module_binding(id, asset_id) VALUES (1, 1)", []))
                except Exception:
                    pass
            else:
                raise ValueError("module rejected binding")

        try:
            await graph.with_sql_transport(bind)
        except Exception:
            pass

    for fail_in_sql in (False, True):
        with pytest.raises(RuntimeError, match="GRAPH_TRANSACTION_ROLLBACK_ONLY"):
            await context.execute_graph_save(
                lambda graph: save(graph, fail_in_sql), comment="save asset")
        assert await rows(path, "asset") == await rows(path, "module_binding") == []


@pytest.mark.asyncio
async def test_module_sql_requires_live_graph_and_transaction(tmp_path):
    context, _ = await fixture(tmp_path)
    saved = []

    async def save(graph):
        saved.append(graph)
        await graph.with_sql_transport(lambda sql: sql.fetch_all_sql(CompiledQuery("SELECT 1", [])))

    await context.execute_graph_save(save, comment="inspect graph")
    with pytest.raises(RuntimeError, match="no longer writable"):
        await saved[0].with_sql_transport(lambda sql: sql.fetch_all_sql(CompiledQuery("SELECT 1", [])))

