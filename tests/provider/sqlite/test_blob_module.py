"""The optional Blob assembly fails closed until the owner and catalog are ready."""

import os

import aiosqlite
import pytest

from teaql.core.blob_ref import BlobFieldSpec, BlobRef
from teaql.core.entity import EntityKey
from teaql.core.meta import EntityDescriptor, PropertyDescriptor
from teaql.core.mutation import DeleteCommand, InsertCommand, UpdateCommand
from teaql.core.value import DataType
from teaql.provider.sqlite import SimpleSchemaProvider
from teaql.provider.sqlite.dialect import SqliteDialect
from teaql.provider.sqlite.transport import SqliteTransport
from teaql.runtime import RuntimeModule, validate_capabilities
from teaql.sql.executor import SqlDataServiceExecutor
from teaql_blob_reference import (
    BlobReferenceModule, FileObjectStorage, SqliteBlobCatalog, SqliteBlobUploadService,
)


class _ReadAuthority:
    async def authorize(self, context, slot):
        return True


class _UploadAuthority:
    def scope(self, context):
        return "tenant-a"

    def field(self, context, target):
        raise AssertionError("readiness must not begin an upload")

    async def authorize(self, context, target, action, input):
        return True


class _Verifier:
    def __init__(self):
        self.ready_calls = 0

    def verify(self, stream, extension, maximum_bytes):
        raise AssertionError("readiness must not parse content")

    def validate_ready(self):
        self.ready_calls += 1


class _BindingAuthority:
    allowed = True

    def scope(self, context):
        return "tenant-a"

    async def authorize(self, context, target, previous, next_ref, action):
        return self.allowed and target.entity == "Asset" and target.field == "document"


class _SafeAuditSink:
    def __init__(self):
        self.events = []

    async def on_safe_event(self, context, event):
        self.events.append(event)


@pytest.mark.asyncio
async def test_blob_module_requires_provider_owner_and_catalog(tmp_path):
    path = str(tmp_path / "module.db")
    transport = SqliteTransport(path)
    catalog = SqliteBlobCatalog(transport)
    verifier = _Verifier()
    upload = SqliteBlobUploadService(catalog, _UploadAuthority(), verifier, 10_000)
    module = BlobReferenceModule(catalog, upload, _ReadAuthority(), _BindingAuthority())
    context = RuntimeModule.new().require_capability("blob.v1").into_context()
    with pytest.raises(RuntimeError, match="BLOB_CAPABILITY_MISSING"):
        await validate_capabilities(context)
    module.install(context)
    assert context.get_resource("blob_response_contributor") is module.read
    with pytest.raises(RuntimeError, match="BLOB_CAPABILITY_MISSING"):
        await module.ready(context)
    with pytest.raises(RuntimeError, match="BLOB_CAPABILITY_MISSING"):
        module.install(context)

    context.insert_resource("dataService", SqlDataServiceExecutor(
        SqliteDialect(), SqliteTransport(path), SimpleSchemaProvider()))
    provider = FileObjectStorage(tmp_path / "private", os.urandom(32))
    context.with_object_storage(provider)
    with pytest.raises(RuntimeError, match="BLOB_SCHEMA_MISSING"):
        await module.ready(context)
    await catalog.ensure_schema()
    await module.ready(context)
    assert verifier.ready_calls == 1
    await validate_capabilities(context)
    provider.close()


def test_blob_module_rejects_an_upload_from_another_catalog(tmp_path):
    first = SqliteBlobCatalog(SqliteTransport(str(tmp_path / "first.db")))
    second = SqliteBlobCatalog(SqliteTransport(str(tmp_path / "second.db")))
    upload = SqliteBlobUploadService(second, _UploadAuthority(), _Verifier(), 10_000)
    with pytest.raises(RuntimeError, match="BLOB_CAPABILITY_MISSING"):
        BlobReferenceModule(first, upload, _ReadAuthority(), _BindingAuthority())


@pytest.mark.asyncio
async def test_native_mutation_binds_blob_in_same_sqlite_graph(tmp_path):
    path = str(tmp_path / "native.db")
    descriptor = EntityDescriptor("Asset").table_name("asset")
    descriptor.property(PropertyDescriptor("id", DataType.I64).is_id())
    descriptor.property(PropertyDescriptor("version", DataType.I64).is_version())
    descriptor.property(PropertyDescriptor("document", DataType.Text).blob(
        BlobFieldSpec("Asset", "document", ["pdf"], True, "default")))
    schema = SimpleSchemaProvider()
    schema.register_entity(descriptor)
    context = RuntimeModule.new().entity(descriptor).require_capability("blob.v1").into_context()
    context.insert_resource("dataService", SqlDataServiceExecutor(
        SqliteDialect(), SqliteTransport(path), schema))
    audit = _SafeAuditSink()
    context.with_app_audit_event_sink(audit)
    store = FileObjectStorage(tmp_path / "native-private", os.urandom(32))
    context.with_object_storage(store)
    catalog = SqliteBlobCatalog(SqliteTransport(path))
    await catalog.ensure_schema()
    async with aiosqlite.connect(path) as db:
        await db.execute("CREATE TABLE asset (id INTEGER PRIMARY KEY, version INTEGER, document TEXT)")
        for key in ("blob_native_one", "blob_native_two"):
            await db.execute("INSERT INTO teaql_blob_catalog "
                "(key,scope,object_key,content_version,file_name,content_type,size_bytes,status) "
                "VALUES (?,?,?,?,?,?,?,?)",
                (key, "tenant-a", f"objects/{key}", "v1", "report.pdf",
                 "application/pdf", 7, "uploaded_unbound"))
        await db.commit()
    authority = _BindingAuthority()
    upload = SqliteBlobUploadService(catalog, _UploadAuthority(), _Verifier(), 10_000)
    module = BlobReferenceModule(catalog, upload, _ReadAuthority(), authority)
    module.install(context)
    await module.ready(context)

    async def save(command, comment, asset_id=1):
        async def work(graph):
            return await graph.transaction.mutate(graph.context,
                graph.request(command, graph.scope(EntityKey("Asset", asset_id))))
        return await context.execute_graph_save(work, comment=comment)

    first, second = BlobRef("blob_native_one"), BlobRef("blob_native_two")
    await save(InsertCommand.new("Asset").value("id", 1).value("document", first), "create")
    assert audit.events and any(field.field == "document" and field.value == "[REDACTED]"
                                for field in audit.events[-1].fields)
    async with aiosqlite.connect(path) as db:
        async with db.execute("SELECT document,version FROM asset WHERE id=1") as cursor:
            assert await cursor.fetchone() == (first.key, 1)
        async with db.execute("SELECT key,version FROM teaql_blob_binding") as cursor:
            assert await cursor.fetchone() == (first.key, 1)

    await save(UpdateCommand.new("Asset", 1).expected_version(1)
               .value("document", second), "replace")
    async with aiosqlite.connect(path) as db:
        async with db.execute("SELECT document,version FROM asset WHERE id=1") as cursor:
            assert await cursor.fetchone() == (second.key, 2)
        async with db.execute("SELECT key,version FROM teaql_blob_binding") as cursor:
            assert await cursor.fetchone() == (second.key, 2)
        async with db.execute("SELECT key,status FROM teaql_blob_catalog ORDER BY key") as cursor:
            assert await cursor.fetchall() == [(first.key, "uploaded_unbound"),
                                              (second.key, "available")]

    authority.allowed = False
    with pytest.raises(RuntimeError, match="BLOB_BIND_DENIED"):
        await save(UpdateCommand.new("Asset", 1).expected_version(2)
                   .value("document", first), "deny replacement")
    authority.allowed = True
    with pytest.raises(RuntimeError, match="BLOB_REFERENCE_INVALID"):
        await save(UpdateCommand.new("Asset", 1).expected_version(2)
                   .value("document", second.key), "reject raw Key")
    async with aiosqlite.connect(path) as db:
        async with db.execute("SELECT document,version FROM asset WHERE id=1") as cursor:
            assert await cursor.fetchone() == (second.key, 2)
        async with db.execute("SELECT key,version FROM teaql_blob_binding") as cursor:
            assert await cursor.fetchone() == (second.key, 2)
    await save(UpdateCommand.new("Asset", 1).expected_version(2)
               .value("document", None), "clear")
    async with aiosqlite.connect(path) as db:
        async with db.execute("SELECT key,version FROM teaql_blob_binding") as cursor:
            assert await cursor.fetchone() == (None, 3)
    await save(UpdateCommand.new("Asset", 1).expected_version(3)
               .value("document", second), "rebind")
    await save(DeleteCommand.new("Asset", 1).expected_version(4).hard_delete(), "delete")
    async with aiosqlite.connect(path) as db:
        async with db.execute("SELECT id FROM asset") as cursor:
            assert await cursor.fetchone() is None
        async with db.execute("SELECT key,version FROM teaql_blob_binding") as cursor:
            assert await cursor.fetchone() == (None, 5)
        async with db.execute("SELECT status FROM teaql_blob_catalog WHERE key=?",
                              (second.key,)) as cursor:
            assert await cursor.fetchone() == ("uploaded_unbound",)
    await save(InsertCommand.new("Asset").value("id", 2), "create empty", asset_id=2)
    async with aiosqlite.connect(path) as db:
        async with db.execute("SELECT key,version FROM teaql_blob_binding WHERE entity_id='2'") as cursor:
            assert await cursor.fetchone() == (None, 1)
    await save(DeleteCommand.new("Asset", 2).expected_version(1).hard_delete(),
               "delete empty", asset_id=2)
    store.close()
