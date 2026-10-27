"""Real SQLite/File upload confirmation; parser remains test-only."""

from hashlib import sha256
from io import BytesIO
import os

import aiosqlite
import pytest

from teaql.core.blob_ref import BlobFieldSpec
from teaql.core.entity import EntityKey
from teaql.core.meta import EntityDescriptor, PropertyDescriptor
from teaql.core.mutation import InsertCommand
from teaql.core.object_storage import ObjectKey, PutOptions, WriteMode
from teaql.core.value import DataType
from teaql.provider.sqlite import SimpleSchemaProvider
from teaql.provider.sqlite.dialect import SqliteDialect
from teaql.provider.sqlite.transport import SqliteTransport
from teaql.runtime import RuntimeModule
from teaql.sql.executor import SqlDataServiceExecutor
from teaql_blob_reference import (
    BlobBindingChange, BlobBindingTarget, BlobUploadInput, BlobUploadTarget,
    BlobVerifiedContent, FileObjectStorage, SqliteBlobCatalog, SqliteBlobUploadService,
)


class UploadAuthority:
    def __init__(self):
        self.current_scope = "tenant-a"
        self.allowed = True

    def scope(self, _context):
        return self.current_scope

    def field(self, _context, _target):
        return BlobFieldSpec("Asset", "document", ["pdf"], True, "default")

    async def authorize(self, _context, target, action, _input):
        return (self.allowed and target.entity == "Asset" and target.field == "document"
                and action in ("Begin", "Write", "Confirm"))


class BindingAuthority:
    def scope(self, _context):
        return "tenant-a"

    async def authorize(self, _context, target, _previous, _next, action):
        return target.entity == "Asset" and target.field == "document" and action == "Create"


class FixturePDFVerifier:
    def __init__(self, early=False):
        self.early = early
        self.calls = 0

    def verify(self, stream, extension, maximum_bytes):
        self.calls += 1
        if self.early:
            return BlobVerifiedContent(1, "0" * 64, "application/pdf")
        data = stream.read(maximum_bytes + 1)
        assert len(data) <= maximum_bytes and extension == "pdf"
        assert data.startswith(b"%PDF-") and b"%%EOF" in data
        assert stream.read(1) == b""
        return BlobVerifiedContent(len(data), sha256(data).hexdigest(), "application/pdf")


@pytest.mark.asyncio
async def test_upload_real_sqlite_file_verifier_and_native_bind(tmp_path):
    path = str(tmp_path / "upload.db")
    descriptor = EntityDescriptor("Asset").table_name("asset")
    descriptor.property(PropertyDescriptor("id", DataType.I64).is_id())
    descriptor.property(PropertyDescriptor("version", DataType.I64).is_version())
    descriptor.property(PropertyDescriptor("name", DataType.Text))
    schema = SimpleSchemaProvider()
    schema.register_entity(descriptor)
    context = RuntimeModule.new().entity(descriptor).into_context()
    context.insert_resource("dataService", SqlDataServiceExecutor(
        SqliteDialect(), SqliteTransport(path), schema))
    provider = FileObjectStorage(tmp_path / "private", os.urandom(32))
    context.with_object_storage(provider).with_object_storage_observer(lambda event: None)
    catalog = SqliteBlobCatalog(SqliteTransport(path))
    async with aiosqlite.connect(path) as db:
        await db.execute("CREATE TABLE asset (id INTEGER PRIMARY KEY, version INTEGER, name TEXT)")
        await db.commit()
    await catalog.ensure_schema()
    await catalog.validate_schema()
    authority = UploadAuthority()
    verifier = FixturePDFVerifier()
    service = SqliteBlobUploadService(catalog, authority, verifier, 10_000)
    target = BlobUploadTarget("Asset", "1", "document")
    data = b"%PDF-1.7\nreal file bytes\n%%EOF"
    input = BlobUploadInput("path/report.pdf", len(data), "application/pdf")

    session = await service.begin(context, target, input, "request-1")
    replay = await service.begin(context, target, input, "request-1")
    assert replay.upload_id == session.upload_id
    with pytest.raises(RuntimeError, match="BLOB_IDEMPOTENCY_CONFLICT"):
        await service.begin(context, target, BlobUploadInput("other.pdf", len(data)), "request-1")
    with pytest.raises(RuntimeError, match="BLOB_UPLOAD_INCOMPLETE"):
        await service.complete(context, session.upload_id)
    authority.current_scope = "tenant-b"
    with pytest.raises(RuntimeError, match="BLOB_UPLOAD_DENIED"):
        await service.write(context, session.upload_id, BytesIO(data))
    authority.current_scope = "tenant-a"
    assert await service.write(context, session.upload_id, BytesIO(data)) == len(data)
    async with aiosqlite.connect(path) as db:
        async with db.execute("SELECT status FROM teaql_blob_catalog WHERE key=?",
                              (session.reference.key,)) as cursor:
            assert (await cursor.fetchone())[0] == "initiated"
    authority.allowed = False
    with pytest.raises(RuntimeError, match="BLOB_UPLOAD_DENIED"):
        await service.complete(context, session.upload_id)
    authority.allowed = True
    reference = await service.complete(context, session.upload_id)
    assert reference == session.reference and verifier.calls == 1

    async def bind(graph):
        command = (InsertCommand.new("Asset").value("id", 1)
                   .value("version", 1).value("name", "document"))
        await graph.transaction.mutate(graph.context,
            graph.request(command, graph.scope(EntityKey("Asset", 1))))
        await catalog.bind_in_graph(graph, graph.context,
            BlobBindingChange(BlobBindingTarget("Asset", "1", "document"),
                              reference, 0, 1, "Create"), BindingAuthority())

    await context.execute_graph_save(bind, comment="bind verified upload")
    async with aiosqlite.connect(path) as db:
        async with db.execute("SELECT status FROM teaql_blob_catalog WHERE key=?",
                              (reference.key,)) as cursor:
            assert (await cursor.fetchone())[0] == "available"

    second = await service.begin(context, target, input, "request-2")
    await service.write(context, second.upload_id, BytesIO(data))
    async with aiosqlite.connect(path) as db:
        async with db.execute("SELECT object_key FROM teaql_blob_catalog WHERE key=?",
                              (second.reference.key,)) as cursor:
            object_key = (await cursor.fetchone())[0]
    context.object_storage("replace generation").put_bytes(
        ObjectKey(object_key), data, PutOptions(len(data), WriteMode.REPLACE, "application/pdf"))
    with pytest.raises(RuntimeError, match="BLOB_UPLOAD_INCOMPLETE"):
        await service.complete(context, second.upload_id)

    third = await service.begin(context, target, input, "request-3")
    await service.write(context, third.upload_id, BytesIO(data))
    early = SqliteBlobUploadService(catalog, authority, FixturePDFVerifier(early=True), 10_000)
    with pytest.raises(RuntimeError, match="BLOB_UPLOAD_INCOMPLETE"):
        await early.complete(context, third.upload_id)

    fourth = await service.begin(context, target, input, "request-4")
    with pytest.raises(RuntimeError, match="BLOB_STORE_FAILED"):
        await service.write(context, fourth.upload_id, BytesIO(data + b"x"))
    with pytest.raises(RuntimeError, match="BLOB_UPLOAD_INCOMPLETE"):
        await service.complete(context, fourth.upload_id)
    fifth = await service.begin(context, target, input, "request-5")
    with pytest.raises(RuntimeError, match="BLOB_STORE_FAILED"):
        await service.write(context, fifth.upload_id, BytesIO(data[:-1]))
    with pytest.raises(RuntimeError, match="BLOB_UPLOAD_INCOMPLETE"):
        await service.complete(context, fifth.upload_id)
