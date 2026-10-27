"""Real SQLite catalog binding belongs to the native business graph owner."""

import aiosqlite
import os
import pytest
from datetime import datetime, timedelta, timezone
from urllib.request import urlopen

from teaql.core.blob_ref import BlobRef
from teaql.core.object_storage import ObjectKey, ObjectReadUrl, PutOptions, WriteMode
from teaql.core.entity import EntityKey
from teaql.core.meta import EntityDescriptor, PropertyDescriptor
from teaql.core.mutation import InsertCommand
from teaql.core.value import DataType
from teaql.provider.sqlite import SimpleSchemaProvider
from teaql.provider.sqlite.dialect import SqliteDialect
from teaql.provider.sqlite.transport import SqliteTransport
from teaql.runtime import RuntimeModule, UserContext
from teaql.runtime.view_preparation import (
    AuthorizedBlobSlot, AuthorizedResponseGraph, ViewOptions,
    ViewPreparationError, ViewPreparationService,
)
from teaql.sql.executor import SqlDataServiceExecutor
from teaql_blob_reference import (
    BlobBindingChange, BlobBindingTarget, BlobRetentionPolicy, FileObjectStorage, SqliteBlobCatalog,
    SqliteBlobResponseContributor,
)


class Authorization:
    def __init__(self):
        self.current_scope = "tenant-a"
        self.allowed = True

    def scope(self, _context):
        return self.current_scope

    async def authorize(self, _context, _target, _previous, _next, _action):
        return self.allowed

    async def current_policy_on_lease(self, _context, lease, _target):
        assert lease is not None
        return BlobRetentionPolicy("default", "server_stream", 86400, 604800, 3600)


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
    return context, path, SqliteBlobCatalog(SqliteTransport(path),
                                            now_ms=lambda: 1_700_000_000_000)


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
                         "(key,scope,object_key,content_version,file_name,content_type,size_bytes,status,"
                         "completed_at_ms,policy_profile,upload_mode,unbound_retention_seconds,effective_unref_seconds) "
                         "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                         (reference.key, "tenant-a", "objects/1", "v1", "asset.pdf",
                          "application/pdf", 7, "uploaded_unbound", 1_700_000_000_000,
                          "default", "server_stream", 86400, 604800))
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
    assert (await all_rows(path, "teaql_blob_catalog"))[0][-1] == "available"
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
    assert (await all_rows(path, "teaql_blob_catalog"))[0][-1] == "available"
    rebind = BlobBindingChange(BlobBindingTarget("Asset", "1", "document"), reference, 2, 3, "Update")
    await context.execute_graph_save(
        lambda graph: catalog.bind_in_graph(graph, graph.context, rebind, auth), comment="rebind")
    assert (await all_rows(path, "teaql_blob_binding"))[0][-2:] == (reference.key, 3)
    assert (await all_rows(path, "teaql_blob_catalog"))[0][-1] == "available"
    await context.execute_graph_save(lambda graph: save(graph, 2), comment="bind second asset")
    clear = BlobBindingChange(BlobBindingTarget("Asset", "1", "document"), None, 3, 4, "Update")
    await context.execute_graph_save(
        lambda graph: catalog.bind_in_graph(graph, graph.context, clear, auth), comment="clear first binding")
    assert (await all_rows(path, "teaql_blob_catalog"))[0][-1] == "available"
    clear = BlobBindingChange(BlobBindingTarget("Asset", "2", "document"), None, 1, 2, "Update")
    await context.execute_graph_save(
        lambda graph: catalog.bind_in_graph(graph, graph.context, clear, auth), comment="clear final binding")
    assert (await all_rows(path, "teaql_blob_catalog"))[0][-1] == "available"


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


@pytest.mark.asyncio
async def test_binding_enforces_retention_deadline_and_longest_accepted_floor(tmp_path):
    context, path, catalog = await fixture(tmp_path)
    await catalog.ensure_schema()
    clock = [1_700_000_000_000]
    catalog.now_ms = lambda: clock[0]
    expired, live = BlobRef("blob_expired_policy"), BlobRef("blob_live_policy")
    async with aiosqlite.connect(path) as db:
        for reference, completed in ((expired, clock[0] - 86_400_000),
                                     (live, clock[0] - 1000)):
            await db.execute("INSERT INTO teaql_blob_catalog "
                "(key,scope,object_key,content_version,file_name,content_type,size_bytes,status,"
                "completed_at_ms,policy_profile,upload_mode,unbound_retention_seconds,effective_unref_seconds) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (reference.key, "tenant-a", "objects/" + reference.key, "v1", "report.pdf",
                 "application/pdf", 7, "uploaded_unbound", completed,
                 "default", "server_stream", 86400, 3600))
        await db.commit()

    class ChangingAuthorization(Authorization):
        def __init__(self):
            super().__init__()
            self.policy = BlobRetentionPolicy("default", "server_stream", 86400, 604800, 3600)

        async def current_policy_on_lease(self, _context, lease, _target):
            assert lease is not None
            return self.policy

    authority = ChangingAuthorization()
    first = BlobBindingTarget("Asset", "1", "document")
    second = BlobBindingTarget("Asset", "2", "document")

    async def change(target, next_ref, before, after, action):
        return await context.execute_graph_save(
            lambda graph: catalog.bind_in_graph(graph, graph.context,
                BlobBindingChange(target, next_ref, before, after, action), authority),
            comment="retention binding")

    with pytest.raises(RuntimeError, match="BLOB_REFERENCE_EXPIRED"):
        await change(first, expired, 0, 1, "Create")
    await change(first, live, 0, 1, "Create")
    authority.policy = BlobRetentionPolicy("longer", "server_stream", 86400, 2592000, 2678400)
    await change(second, live, 0, 1, "Create")
    await change(first, None, 1, 2, "Update")
    async with aiosqlite.connect(path) as db:
        async with db.execute("SELECT effective_unref_seconds,retention_floor_until_ms,"
                              "last_unbound_at_ms FROM teaql_blob_catalog WHERE key=?",
                              (live.key,)) as cursor:
            seconds, floor, last_unbound = await cursor.fetchone()
            assert seconds == 2592000 and floor == clock[0] + 2_678_400_000
            assert last_unbound is None
    await change(second, None, 1, 2, "Update")
    async with aiosqlite.connect(path) as db:
        async with db.execute("SELECT status,last_unbound_at_ms FROM teaql_blob_catalog WHERE key=?",
                              (live.key,)) as cursor:
            assert await cursor.fetchone() == ("available", clock[0])
    authority.policy = BlobRetentionPolicy("shorter", "server_stream", 86400, 3600, 0)
    clock[0] = floor - 1
    await change(first, live, 2, 3, "Update")
    await change(first, None, 3, 4, "Update")
    clock[0] = floor
    # The accepted maximum still protects this object beyond the old floor.
    await change(first, live, 4, 5, "Update")
    await change(first, None, 5, 6, "Update")
    clock[0] += 2_592_000_000
    with pytest.raises(RuntimeError, match="BLOB_REFERENCE_EXPIRED"):
        await change(first, live, 6, 7, "Update")


@pytest.mark.asyncio
async def test_new_binding_rejects_legacy_unknown_policy_row(tmp_path):
    context, path, catalog = await fixture(tmp_path)
    await catalog.ensure_schema()
    reference = BlobRef("blob_legacy_unknown")
    async with aiosqlite.connect(path) as db:
        await db.execute("INSERT INTO teaql_blob_catalog "
                         "(key,scope,object_key,content_version,file_name,content_type,size_bytes,status) "
                         "VALUES (?,?,?,?,?,?,?,?)",
                         (reference.key, "tenant-a", "objects/legacy", "v1", "legacy.pdf",
                          "application/pdf", 5, "uploaded_unbound"))
        await db.commit()
    with pytest.raises(RuntimeError, match="^BLOB_BIND_DENIED$"):
        await context.execute_graph_save(
            lambda graph: catalog.bind_in_graph(graph, graph.context,
                BlobBindingChange(BlobBindingTarget("Asset", "1", "document"),
                                  reference, 0, 1, "Create"), Authorization()),
            comment="deny legacy unknown policy")
    assert await all_rows(path, "teaql_blob_binding") == []


@pytest.mark.asyncio
async def test_current_sqlite_binding_is_reread_before_view_url_signing(tmp_path):
    context, path, catalog = await fixture(tmp_path)
    await catalog.ensure_schema()
    reference = BlobRef("blob_python_read_1")
    async with aiosqlite.connect(path) as db:
        await db.execute("INSERT INTO teaql_blob_catalog "
                         "(key,scope,object_key,content_version,file_name,content_type,size_bytes,status,"
                         "completed_at_ms,last_unbound_at_ms,policy_profile,upload_mode,"
                         "unbound_retention_seconds,effective_unref_seconds) "
                         "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                         (reference.key, "tenant-a", "objects/read-1", "v1", "report.pdf",
                          "application/pdf", 7, "available", 1_700_000_000_000,
                          1_700_000_000_000, "default", "server_stream", 86400, 604800))
        await db.commit()
    auth = Authorization()
    change = BlobBindingChange(BlobBindingTarget("Asset", "1", "document"), reference, 0, 1, "Create")
    await context.execute_graph_save(
        lambda graph: catalog.bind_in_graph(graph, graph.context, change, auth), comment="bind read fixture")
    slot = AuthorizedBlobSlot(("document",), "Asset", "1", "document", "tenant-a", 1, reference)
    record = await catalog.current_read(slot)
    assert (record.object_key, record.content_version, record.size_bytes) == ("objects/read-1", "v1", 7)
    for invalid in (
        AuthorizedBlobSlot(slot.path, slot.entity, slot.entity_id, slot.field,
                           slot.scope, 2, slot.reference),
        AuthorizedBlobSlot(slot.path, slot.entity, slot.entity_id, slot.field,
                           "tenant-b", 1, slot.reference),
        AuthorizedBlobSlot(slot.path, slot.entity, slot.entity_id, slot.field,
                           slot.scope, 1, BlobRef("blob_old")),
    ):
        with pytest.raises(RuntimeError, match="BLOB_READ_DENIED"):
            await catalog.current_read(invalid)

    class ReadAuthorization:
        allowed = True

        async def authorize(self, _context, _slot):
            return self.allowed

    class Authorizer:
        async def authorize(self, _context, _result, _options):
            return AuthorizedResponseGraph({"document": reference}, (slot,))

    class SigningStore:
        calls = 0
        key = None
        header = None

        def get_read_url(self, _invocation, key, options):
            self.calls += 1
            self.key = key.value
            self.header = options.content_disposition()
            return ObjectReadUrl("https://example.invalid/opaque-ticket",
                                 datetime.now(timezone.utc) + timedelta(seconds=30))

    read_authorization = ReadAuthorization()
    store = SigningStore()
    context.with_object_storage(store)
    context.insert_resource("response_graph_authorizer", Authorizer())
    context.insert_resource("blob_response_contributor",
                            SqliteBlobResponseContributor(catalog, read_authorization))
    view = await ViewPreparationService().prepare(context, None,
        ViewOptions("ordinary", "read_only", datetime.now(timezone.utc) + timedelta(seconds=60)))
    assert view.presentation == {"document": "https://example.invalid/opaque-ticket"}
    assert (store.calls, store.key, store.header) == \
        (1, "objects/read-1", 'inline; filename="report.pdf"')

    read_authorization.allowed = False
    with pytest.raises(ViewPreparationError) as denied:
        await ViewPreparationService().prepare(context, None,
            ViewOptions("ordinary", "read_only", datetime.now(timezone.utc) + timedelta(seconds=60)))
    assert denied.value.code == "BLOB_READ_DENIED"
    assert store.calls == 1

    async with aiosqlite.connect(path) as db:
        await db.execute("UPDATE teaql_blob_catalog SET status = 'deleted' WHERE key = ?", (reference.key,))
        await db.commit()
    with pytest.raises(RuntimeError, match="BLOB_READ_DENIED"):
        await catalog.current_read(slot)


@pytest.mark.asyncio
async def test_authorized_sqlite_view_projects_real_file_http_bytes_and_denies_revoked_refresh(tmp_path):
    context, path, catalog = await fixture(tmp_path)
    await catalog.ensure_schema()
    provider = FileObjectStorage(tmp_path / "private", os.urandom(32))
    try:
        assert provider.start().startswith("http://127.0.0.1:")
        context.with_object_storage(provider)
        key = ObjectKey("objects/read-real")
        data = b"%PDF-1x"
        context.object_storage("publish current Blob").put_bytes(
            key, data, PutOptions(len(data), WriteMode.CREATE_ONLY, "application/pdf"))
        reference = BlobRef("blob_python_real_1")
        async with aiosqlite.connect(path) as db:
            await db.execute("INSERT INTO teaql_blob_catalog "
                             "(key,scope,object_key,content_version,file_name,content_type,size_bytes,status,"
                             "completed_at_ms,policy_profile,upload_mode,unbound_retention_seconds,effective_unref_seconds) "
                             "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                             (reference.key, "tenant-a", key.value, "v1", "report.pdf",
                              "application/pdf", len(data), "uploaded_unbound", 1_700_000_000_000,
                              "default", "server_stream", 86400, 604800))
            await db.commit()
        change = BlobBindingChange(BlobBindingTarget("Asset", "1", "document"),
                                   reference, 0, 1, "Create")
        await context.execute_graph_save(
            lambda graph: catalog.bind_in_graph(graph, graph.context, change, Authorization()),
            comment="bind real file")
        slot = AuthorizedBlobSlot(("document",), "Asset", "1", "document", "tenant-a", 1, reference)

        class ReadAuthorization:
            allowed = True

            async def authorize(self, _context, _slot):
                return self.allowed

        class Authorizer:
            async def authorize(self, _context, _result, _options):
                return AuthorizedResponseGraph({"document": reference}, (slot,))

        read_permission = ReadAuthorization()
        context.insert_resource("response_graph_authorizer", Authorizer())
        context.insert_resource("blob_response_contributor",
                                SqliteBlobResponseContributor(catalog, read_permission))
        options = ViewOptions("ordinary", "read_only",
                              datetime.now(timezone.utc) + timedelta(seconds=60))
        view = await ViewPreparationService().prepare(context, None, options)
        link = view.presentation["document"]
        assert link.startswith("http://127.0.0.1:") and key.value not in link
        with urlopen(link, timeout=5) as response:
            assert response.status == 200
            assert response.read() == data
            assert response.headers["Content-Type"] == "application/pdf"
            assert response.headers["Content-Disposition"] == 'inline; filename="report.pdf"'
        read_permission.allowed = False
        with pytest.raises(ViewPreparationError) as denied:
            await ViewPreparationService().prepare(context, None, options)
        assert denied.value.code == "BLOB_READ_DENIED"
    finally:
        provider.close()
