"""Real SQLite/File upload confirmation; parser remains test-only."""

from hashlib import sha256
from io import BytesIO
from threading import Event
from uuid import uuid4
import asyncio
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
async def test_upload_real_sqlite_s3_create_only_confirm_and_replay(tmp_path):
    if os.environ.get("TEAQL_S3_TEST_BLOB_UPLOAD") != "1":
        pytest.skip("explicit S3-compatible Blob upload gate required")
    endpoint = os.environ.get("TEAQL_S3_TEST_ENDPOINT")
    bucket = os.environ.get("TEAQL_S3_TEST_BUCKET")
    access = os.environ.get("TEAQL_S3_TEST_ACCESS_KEY")
    secret = os.environ.get("TEAQL_S3_TEST_SECRET_KEY")
    assert all((endpoint, bucket, access, secret)), "explicit S3 test configuration required"
    from teaql.provider.s3 import S3ObjectStorage

    provider = S3ObjectStorage.connect(bucket, endpoint_url=endpoint,
                                       aws_access_key_id=access, aws_secret_access_key=secret)
    actor = RuntimeModule.new().into_context().with_object_storage(provider)
    actor.with_object_storage_observer(lambda event: None)
    path = str(tmp_path / "s3-upload.db")
    catalog = SqliteBlobCatalog(SqliteTransport(path))
    authority, verifier = UploadAuthority(), FixturePDFVerifier()
    service = SqliteBlobUploadService(catalog, authority, verifier, 10_000)
    data = b"%PDF-1.7\nreal S3 Blob upload\n%%EOF"
    object_key = None
    try:
        await catalog.ensure_schema()
        session = await service.begin(actor, BlobUploadTarget("Asset", "1", "document"),
                                      BlobUploadInput("report.pdf", len(data), "application/pdf"),
                                      uuid4().hex)
        async with aiosqlite.connect(path) as db:
            async with db.execute("SELECT object_key FROM teaql_blob_catalog WHERE key=?",
                                  (session.reference.key,)) as cursor:
                object_key = ObjectKey((await cursor.fetchone())[0])
        assert await service.write(actor, session.upload_id, BytesIO(data)) == len(data)
        authority.allowed = False
        with pytest.raises(RuntimeError, match="BLOB_UPLOAD_DENIED"):
            await service.complete(actor, session.upload_id)
        authority.allowed = True
        assert await service.complete(actor, session.upload_id) == session.reference
        assert await service.complete(actor, session.upload_id) == session.reference
        assert verifier.calls == 1
        assert await service.write(actor, session.upload_id, BytesIO(data)) == len(data)
        store = actor.object_storage("verify completed S3 Blob upload")
        assert store.get_bytes(object_key, 10_000) == data
        head = store.head(object_key)
        async with aiosqlite.connect(path) as db:
            async with db.execute(
                "SELECT status, content_type, size_bytes, content_version "
                "FROM teaql_blob_catalog WHERE key=?", (session.reference.key,)
            ) as cursor:
                status, mime, size, version = await cursor.fetchone()
        assert (status, mime, size, version) == (
            "uploaded_unbound", "application/pdf", len(data), head.etag)
    finally:
        try:
            if object_key is not None:
                actor.object_storage("clean S3 Blob upload fixture").delete(object_key)
        finally:
            provider.close()


@pytest.mark.asyncio
async def test_expired_replay_key_cannot_recover_upload_session(tmp_path):
    catalog = SqliteBlobCatalog(SqliteTransport(str(tmp_path / "expired.db")))
    await catalog.ensure_schema()
    clock = [1_700_000_000_000]
    service = SqliteBlobUploadService(catalog, UploadAuthority(), FixturePDFVerifier(),
                                      10_000, lease_seconds=1, now_ms=lambda: clock[0])
    context = RuntimeModule.new().into_context()
    target = BlobUploadTarget("Asset", "1", "document")
    input = BlobUploadInput("report.pdf", 42)
    first = await service.begin(context, target, input, "expired-request")
    assert (await service.begin(context, target, input, "expired-request")).upload_id == first.upload_id
    clock[0] = int(first.expires_at.timestamp() * 1000)
    with pytest.raises(RuntimeError, match="BLOB_UPLOAD_EXPIRED"):
        await service.begin(context, target, input, "expired-request")
    second = await service.begin(context, target, input, "fresh-request")
    assert second.upload_id != first.upload_id
    with pytest.raises(RuntimeError, match="BLOB_UPLOAD_EXPIRED"):
        await service.write(context, first.upload_id, BytesIO(b"x" * 42))


@pytest.mark.asyncio
async def test_upload_write_holds_sql_owner_across_file_io(tmp_path):
    path = str(tmp_path / "locked.db")
    catalog = SqliteBlobCatalog(SqliteTransport(path))
    await catalog.ensure_schema()
    entered, release = Event(), Event()
    file_store = FileObjectStorage(tmp_path / "private", os.urandom(32))

    class BlockingStore:
        puts = 0

        def __getattr__(self, name):
            return getattr(file_store, name)

        def put(self, invocation, key, content, options):
            self.puts += 1
            result = file_store.put(invocation, key, content, options)
            entered.set()
            if not release.wait(5):
                raise AssertionError("test did not release File write")
            return result

    store = BlockingStore()
    actor = RuntimeModule.new().into_context().with_object_storage(store)
    actor.with_object_storage_observer(lambda event: None)
    service = SqliteBlobUploadService(catalog, UploadAuthority(), FixturePDFVerifier(), 10_000)
    data = b"%PDF-1.7\nlocked upload\n%%EOF"
    session = await service.begin(actor, BlobUploadTarget("Asset", "1", "document"),
                                  BlobUploadInput("report.pdf", len(data)), "lock-request")
    first = asyncio.create_task(service.write(actor, session.upload_id, BytesIO(data)))
    second = None
    try:
        assert await asyncio.to_thread(entered.wait, 5)
        second = asyncio.create_task(service.write(actor, session.upload_id, BytesIO(data)))
        await asyncio.sleep(0.05)
        assert not second.done(), "second writer bypassed the physical SQL owner"
    finally:
        release.set()
    assert await first == len(data)
    assert await second == len(data)
    assert store.puts == 1
    async with aiosqlite.connect(path) as db:
        async with db.execute("SELECT state FROM teaql_blob_upload WHERE upload_id=?",
                              (session.upload_id,)) as cursor:
            assert (await cursor.fetchone())[0] == "written"


@pytest.mark.asyncio
async def test_upload_confirmation_holds_sql_owner_through_parser_io(tmp_path):
    path = str(tmp_path / "confirm-locked.db")
    catalog = SqliteBlobCatalog(SqliteTransport(path))
    await catalog.ensure_schema()
    entered, release = Event(), Event()

    class BlockingVerifier(FixturePDFVerifier):
        def verify(self, stream, extension, maximum_bytes):
            result = super().verify(stream, extension, maximum_bytes)
            entered.set()
            if not release.wait(5):
                raise AssertionError("test did not release parser")
            return result

    verifier = BlockingVerifier()
    actor = RuntimeModule.new().into_context().with_object_storage(
        FileObjectStorage(tmp_path / "private", os.urandom(32)))
    actor.with_object_storage_observer(lambda event: None)
    service = SqliteBlobUploadService(catalog, UploadAuthority(), verifier, 10_000)
    data = b"%PDF-1.7\nlocked confirmation\n%%EOF"
    session = await service.begin(actor, BlobUploadTarget("Asset", "1", "document"),
                                  BlobUploadInput("report.pdf", len(data)), "confirm-request")
    await service.write(actor, session.upload_id, BytesIO(data))
    first = asyncio.create_task(service.complete(actor, session.upload_id))
    second = None
    try:
        assert await asyncio.to_thread(entered.wait, 5)
        second = asyncio.create_task(service.complete(actor, session.upload_id))
        await asyncio.sleep(0.05)
        assert not second.done(), "second confirmation bypassed the physical SQL owner"
    finally:
        release.set()
    assert await first == session.reference
    assert await second == session.reference
    assert await service.complete(actor, session.upload_id) == session.reference
    assert verifier.calls == 1


@pytest.mark.asyncio
async def test_upload_write_commit_unknown_replays_only_same_bytes_and_generation(tmp_path):
    path = str(tmp_path / "commit-unknown.db")
    catalog = SqliteBlobCatalog(SqliteTransport(path))
    await catalog.ensure_schema()
    file_store = FileObjectStorage(tmp_path / "private", os.urandom(32))

    class CountingStore:
        puts = 0

        def __getattr__(self, name):
            return getattr(file_store, name)

        def put(self, invocation, key, content, options):
            self.puts += 1
            return file_store.put(invocation, key, content, options)

    store = CountingStore()
    actor = RuntimeModule.new().into_context().with_object_storage(store)
    actor.with_object_storage_observer(lambda event: None)
    authority, verifier = UploadAuthority(), FixturePDFVerifier()
    service = SqliteBlobUploadService(catalog, authority, verifier, 10_000)
    data = b"%PDF-1.7\nSQL commit succeeded, reply lost\n%%EOF"
    session = await service.begin(actor, BlobUploadTarget("Asset", "1", "document"),
                                  BlobUploadInput("report.pdf", len(data)), "unknown-write")
    begin_sql = catalog.transport.begin_sql

    class CommitThenFail:
        def __init__(self, tx):
            self.tx = tx

        def __getattr__(self, name):
            return getattr(self.tx, name)

        async def commit_sql(self):
            await self.tx.commit_sql()
            raise OSError("PRIVATE-COMMIT-CANARY")

    async def uncertain_begin():
        return CommitThenFail(await begin_sql())

    catalog.transport.begin_sql = uncertain_begin
    try:
        with pytest.raises(RuntimeError, match="^BLOB_CATALOG_FAILED$"):
            await service.write(actor, session.upload_id, BytesIO(data))
    finally:
        catalog.transport.begin_sql = begin_sql
    async with aiosqlite.connect(path) as db:
        async with db.execute("SELECT u.state,c.status,c.object_key,u.written_etag "
                              "FROM teaql_blob_upload u JOIN teaql_blob_catalog c ON c.key=u.key "
                              "WHERE u.upload_id=?", (session.upload_id,)) as cursor:
            state, catalog_state, object_key, etag = await cursor.fetchone()
    assert state == "written" and catalog_state == "initiated" and etag
    assert store.puts == 1
    authority.allowed = False
    with pytest.raises(RuntimeError, match="^BLOB_UPLOAD_DENIED$"):
        await service.write(actor, session.upload_id, BytesIO(data))
    authority.allowed = True
    with pytest.raises(RuntimeError, match="^BLOB_IDEMPOTENCY_CONFLICT$"):
        await service.write(actor, session.upload_id, BytesIO(b"x" * len(data)))
    class FailingSource(BytesIO):
        def read(self, *_):
            raise OSError("PRIVATE-SOURCE-CANARY")

    with pytest.raises(RuntimeError, match="^BLOB_STORE_FAILED$") as failed:
        await service.write(actor, session.upload_id, FailingSource(data))
    assert "CANARY" not in str(failed.value)
    assert await service.write(actor, session.upload_id, BytesIO(data)) == len(data)
    assert store.puts == 1
    assert actor.object_storage("check unchanged version").head(ObjectKey(object_key)).etag == etag
    catalog.transport.begin_sql = uncertain_begin
    try:
        with pytest.raises(RuntimeError, match="^BLOB_CATALOG_FAILED$"):
            await service.complete(actor, session.upload_id)
    finally:
        catalog.transport.begin_sql = begin_sql
    async with aiosqlite.connect(path) as db:
        async with db.execute("SELECT state FROM teaql_blob_upload WHERE upload_id=?",
                              (session.upload_id,)) as cursor:
            assert (await cursor.fetchone())[0] == "completed"
    authority.allowed = False
    with pytest.raises(RuntimeError, match="^BLOB_UPLOAD_DENIED$"):
        await service.complete(actor, session.upload_id)
    authority.allowed = True
    assert await service.complete(actor, session.upload_id) == session.reference
    assert verifier.calls == 1
    assert await service.write(actor, session.upload_id, BytesIO(data)) == len(data)
    assert verifier.calls == 1 and store.puts == 1
    actor.object_storage("replace generation").put_bytes(ObjectKey(object_key), data,
        PutOptions(len(data), WriteMode.REPLACE, "application/pdf"))
    with pytest.raises(RuntimeError, match="^BLOB_IDEMPOTENCY_CONFLICT$"):
        await service.write(actor, session.upload_id, BytesIO(data))


@pytest.mark.asyncio
async def test_upload_retry_recovers_only_identical_file_after_journal_rollback(tmp_path):
    path = str(tmp_path / "recover.db")
    catalog = SqliteBlobCatalog(SqliteTransport(path))
    await catalog.ensure_schema()
    actor = RuntimeModule.new().into_context().with_object_storage(
        FileObjectStorage(tmp_path / "private", os.urandom(32)))
    actor.with_object_storage_observer(lambda event: None)
    verifier = FixturePDFVerifier()
    service = SqliteBlobUploadService(catalog, UploadAuthority(), verifier, 10_000)
    data = b"%PDF-1.7\nrecover committed File content\n%%EOF"
    session = await service.begin(actor, BlobUploadTarget("Asset", "1", "document"),
                                  BlobUploadInput("report.pdf", len(data)), "recovery-request")
    async with aiosqlite.connect(path) as db:
        await db.execute("""CREATE TRIGGER reject_upload_write BEFORE UPDATE ON teaql_blob_upload
            WHEN NEW.state='written' BEGIN SELECT RAISE(ABORT, 'injected'); END""")
        await db.commit()
    with pytest.raises(RuntimeError, match="BLOB_CATALOG_FAILED"):
        await service.write(actor, session.upload_id, BytesIO(data))
    async with aiosqlite.connect(path) as db:
        async with db.execute("SELECT c.object_key,u.state FROM teaql_blob_upload u "
                              "JOIN teaql_blob_catalog c ON c.key=u.key WHERE u.upload_id=?",
                              (session.upload_id,)) as cursor:
            object_key, state = await cursor.fetchone()
        assert state == "initiated"
        await db.execute("DROP TRIGGER reject_upload_write")
        await db.commit()
    stored = actor.object_storage("check recovery candidate").head(ObjectKey(object_key))
    assert stored is not None and stored.size == len(data)
    with pytest.raises(RuntimeError, match="BLOB_STORE_FAILED"):
        await service.write(actor, session.upload_id, BytesIO(b"x" * len(data)))
    assert await service.write(actor, session.upload_id, BytesIO(data)) == len(data)
    assert actor.object_storage("check recovered generation").head(
        ObjectKey(object_key)).etag == stored.etag
    assert await service.complete(actor, session.upload_id) == session.reference
    assert verifier.calls == 1


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
    assert await service.complete(context, session.upload_id) == reference
    assert verifier.calls == 1
    authority.allowed = False
    with pytest.raises(RuntimeError, match="BLOB_UPLOAD_DENIED"):
        await service.complete(context, session.upload_id)
    authority.allowed = True

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
    assert await service.complete(context, session.upload_id) == reference
    assert verifier.calls == 1
    async with aiosqlite.connect(path) as db:
        async with db.execute("SELECT object_key FROM teaql_blob_catalog WHERE key=?",
                              (reference.key,)) as cursor:
            completed_key = (await cursor.fetchone())[0]
    context.object_storage("replace completed generation").put_bytes(
        ObjectKey(completed_key), data, PutOptions(len(data), WriteMode.REPLACE, "application/pdf"))
    with pytest.raises(RuntimeError, match="BLOB_UPLOAD_INCOMPLETE"):
        await service.complete(context, session.upload_id)
    assert verifier.calls == 1

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
