"""Real SQLite catalog binding belongs to the native business graph owner."""

import aiosqlite
import pytest

from teaql.core.blob_ref import BlobRef
from teaql.core.entity import EntityKey
from teaql.core.meta import EntityDescriptor, PropertyDescriptor
from teaql.core.mutation import InsertCommand
from teaql.core.value import DataType
from teaql.provider.sqlite import SimpleSchemaProvider
from teaql.provider.sqlite.dialect import SqliteDialect
from teaql.provider.sqlite.transport import SqliteTransport
from teaql.runtime import RuntimeModule, UserContext
from teaql.sql.executor import SqlDataServiceExecutor
from teaql_blob_reference import BlobBindingChange, BlobBindingTarget, SqliteBlobCatalog


class Authorization:
    def __init__(self):
        self.current_scope = "tenant-a"
        self.allowed = True

    def scope(self, _context):
        return self.current_scope

    async def authorize(self, _context, _target, _previous, _next, _action):
        return self.allowed


async def fixture(tmp_path):
    path = str(tmp_path / "blob-catalog.db")
    descriptor = EntityDescriptor("Asset").table_name("asset")
    descriptor.property(PropertyDescriptor("id", DataType.I64).is_id())
    descriptor.property(PropertyDescriptor("version", DataType.I64).is_version())
    descriptor.property(PropertyDescriptor("name", DataType.Text))
    schema = SimpleSchemaProvider()
    schema.register_entity(descriptor)
    context = RuntimeModule.new().entity(descriptor).into_context()
    context.insert_resource("dataService", SqlDataServiceExecutor(
        SqliteDialect(), SqliteTransport(path), schema))
    async with aiosqlite.connect(path) as db:
        await db.execute("CREATE TABLE asset (id INTEGER PRIMARY KEY, version INTEGER, name TEXT)")
        await db.commit()
    return context, path, SqliteBlobCatalog(SqliteTransport(path))


async def all_rows(path, table):
    async with aiosqlite.connect(path) as db:
        async with db.execute(f"SELECT * FROM {table}") as cursor:
            return await cursor.fetchall()


@pytest.mark.asyncio
async def test_catalog_binding_same_graph_rollback_authority_tombstone_and_rebind(tmp_path):
    context, path, catalog = await fixture(tmp_path)
    with pytest.raises(RuntimeError, match="BLOB_SCHEMA_MISSING"):
        await catalog.validate_schema()
    await catalog.ensure_schema()
    await catalog.validate_schema()
    reference = BlobRef("blob_python_catalog_1")
    async with aiosqlite.connect(path) as db:
        await db.execute("INSERT INTO teaql_blob_catalog "
                         "(key,scope,object_key,content_version,file_name,content_type,size_bytes,status) "
                         "VALUES (?,?,?,?,?,?,?,?)",
                         (reference.key, "tenant-a", "objects/1", "v1", "asset.pdf",
                          "application/pdf", 7, "available"))
        await db.commit()
    auth = Authorization()

    async def save(graph, asset_id, *, abort=False, catch_denial=False, foreign_actor=False):
        command = (InsertCommand.new("Asset").value("id", asset_id)
                   .value("version", 1).value("name", "document"))
        await graph.transaction.mutate(graph.context,
            graph.request(command, graph.scope(EntityKey("Asset", asset_id))))
        change = BlobBindingChange(BlobBindingTarget("Asset", str(asset_id), "document"),
                                   reference, 0, 1, "Create")
        if catch_denial:
            try:
                await catalog.bind_in_graph(graph, UserContext.new() if foreign_actor else graph.context,
                                            change, auth)
            except RuntimeError:
                return
        else:
            assert await catalog.bind_in_graph(graph, graph.context, change, auth) == 1
        if abort:
            raise RuntimeError("abort graph")

    await context.execute_graph_save(lambda graph: save(graph, 1), comment="save asset")
    assert len(await all_rows(path, "asset")) == len(await all_rows(path, "teaql_blob_binding")) == 1
    with pytest.raises(RuntimeError, match="abort graph"):
        await context.execute_graph_save(lambda graph: save(graph, 2, abort=True), comment="save asset")
    assert len(await all_rows(path, "asset")) == len(await all_rows(path, "teaql_blob_binding")) == 1

    auth.allowed = False
    with pytest.raises(RuntimeError, match="GRAPH_TRANSACTION_ROLLBACK_ONLY"):
        await context.execute_graph_save(
            lambda graph: save(graph, 3, catch_denial=True), comment="save asset")
    auth.allowed = True
    with pytest.raises(RuntimeError, match="GRAPH_TRANSACTION_ROLLBACK_ONLY"):
        await context.execute_graph_save(
            lambda graph: save(graph, 4, catch_denial=True, foreign_actor=True), comment="save asset")
    assert len(await all_rows(path, "asset")) == len(await all_rows(path, "teaql_blob_binding")) == 1

    stale = BlobBindingChange(BlobBindingTarget("Asset", "1", "document"), reference, 0, 2, "Update")
    with pytest.raises(RuntimeError, match="BLOB_BIND_DENIED"):
        await context.execute_graph_save(
            lambda graph: catalog.bind_in_graph(graph, graph.context, stale, auth),
            comment="reject stale bind")
    auth.current_scope = "tenant-b"
    with pytest.raises(RuntimeError, match="BLOB_BIND_DENIED"):
        await context.execute_graph_save(
            lambda graph: catalog.bind_in_graph(graph, graph.context,
                BlobBindingChange(BlobBindingTarget("Asset", "2", "document"), reference, 0, 1, "Create"), auth),
            comment="reject wrong scope")
    auth.current_scope = "tenant-a"
    clear = BlobBindingChange(BlobBindingTarget("Asset", "1", "document"), None, 1, 2, "Update")
    await context.execute_graph_save(
        lambda graph: catalog.bind_in_graph(graph, graph.context, clear, auth), comment="clear binding")
    assert (await all_rows(path, "teaql_blob_binding"))[0][-2:] == (None, 2)
    rebind = BlobBindingChange(BlobBindingTarget("Asset", "1", "document"), reference, 2, 3, "Update")
    await context.execute_graph_save(
        lambda graph: catalog.bind_in_graph(graph, graph.context, rebind, auth), comment="rebind")
    assert (await all_rows(path, "teaql_blob_binding"))[0][-2:] == (reference.key, 3)


@pytest.mark.asyncio
async def test_catalog_rejects_old_not_null_binding_schema(tmp_path):
    _, path, catalog = await fixture(tmp_path)
    async with aiosqlite.connect(path) as db:
        await db.execute("CREATE TABLE teaql_blob_binding (scope TEXT NOT NULL, entity TEXT NOT NULL, "
                         "entity_id TEXT NOT NULL, field TEXT NOT NULL, key TEXT NOT NULL, "
                         "version BIGINT NOT NULL, PRIMARY KEY (scope,entity,entity_id,field))")
        await db.commit()
    await catalog.ensure_schema()
    with pytest.raises(RuntimeError, match="BLOB_SCHEMA_MISSING"):
        await catalog.validate_schema()
