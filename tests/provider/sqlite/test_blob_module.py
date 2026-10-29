"""The optional Blob assembly fails closed until the owner and catalog are ready."""

import os
import time
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from io import BytesIO
from types import SimpleNamespace
from urllib.request import Request, urlopen

import aiosqlite
import pytest

from teaql.core.blob_ref import BlobFieldSpec, BlobRef
from teaql.core.entity import EntityKey, EntityRoot
from teaql.core.meta import EntityDescriptor, PropertyDescriptor
from teaql.core.mutation import DeleteCommand, InsertCommand, UpdateCommand
from teaql.core.object_storage import ObjectKey
from teaql.core.value import DataType
from teaql.provider.sqlite import SimpleSchemaProvider
from teaql.provider.sqlite.dialect import SqliteDialect
from teaql.provider.sqlite.transport import SqliteTransport
from teaql.runtime import RuntimeModule, validate_capabilities
from teaql.runtime.view_preparation import (
    AuthorizedBlobSlot, AuthorizedResponseGraph, ViewOptions,
    ViewPreparationError, ViewPreparationService,
)
from teaql.sql.executor import SqlDataServiceExecutor
from teaql_blob_reference import (
    BlobReferenceModule, BlobRetentionPolicy, FileObjectStorage, SqliteBlobCatalog,
    BlobUploadInput, BlobUploadTarget, BlobVerifiedContent,
    SqliteBlobMaintenanceService, SqliteBlobUploadService,
)


class _ReadAuthority:
    allowed = True

    async def authorize(self, context, slot):
        return self.allowed


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

    async def current_policy_on_lease(self, context, lease, target):
        assert lease is not None
        return BlobRetentionPolicy("default", "server_stream", 86400, 604800, 3600)


class _MaintenanceAuthority:
    def scope(self, context):
        return "tenant-a"

    async def can_maintain(self, context, scope):
        return scope == "tenant-a"


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
    maintenance = SqliteBlobMaintenanceService(catalog, _MaintenanceAuthority())
    module = BlobReferenceModule(catalog, upload, _ReadAuthority(), _BindingAuthority(),
                                 maintenance=maintenance)
    context = RuntimeModule.new().require_capability("blob.v1").into_context()
    with pytest.raises(RuntimeError, match="BLOB_CAPABILITY_MISSING"):
        await validate_capabilities(context)
    module.install(context)
    assert context.get_resource("blob_response_contributor") is module.read
    assert context.get_resource("blob_maintenance_service") is maintenance
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
@pytest.mark.parametrize("scenario", ["other-file", "separate-memory", "non-native", "wrong-dialect", "upload-catalog-drift"])
async def test_blob_module_rejects_incompatible_business_database(tmp_path, scenario):
    path = str(tmp_path / "catalog.db")
    catalog = SqliteBlobCatalog(SqliteTransport(path))
    await catalog.ensure_schema()
    verifier = _Verifier()
    upload = SqliteBlobUploadService(catalog, _UploadAuthority(), verifier, 10_000)
    module = BlobReferenceModule(catalog, upload, _ReadAuthority(), _BindingAuthority())
    owner = SqlDataServiceExecutor(SqliteDialect(), SqliteTransport(path), SimpleSchemaProvider())
    if scenario == "other-file":
        owner.transport = SqliteTransport(str(tmp_path / "other.db"))
    elif scenario == "separate-memory":
        owner.transport = SqliteTransport(":memory:")
    elif scenario == "non-native":
        async def begin(_context):
            raise AssertionError("readiness must not open this non-native owner")
        owner = SimpleNamespace(begin=begin)
    elif scenario == "wrong-dialect":
        from teaql.provider.mysql.dialect import MysqlDialect
        owner.dialect = MysqlDialect()
    context = RuntimeModule.new().require_capability("blob.v1").into_context()
    context.insert_resource("dataService", owner)
    provider = FileObjectStorage(tmp_path / "objects", os.urandom(32))
    context.with_object_storage(provider)
    module.install(context)
    assert verifier.ready_calls == 0
    if scenario == "upload-catalog-drift":
        upload.catalog = SqliteBlobCatalog(SqliteTransport(str(tmp_path / "other.db")))
    try:
        with pytest.raises(RuntimeError, match="^BLOB_CAPABILITY_MISSING$"):
            await module.ready(context)
        assert verifier.ready_calls == 0
    finally:
        provider.close()


@pytest.mark.asyncio
async def test_blob_module_accepts_same_database_through_native_file_uri(tmp_path):
    path = tmp_path / "module.db"
    catalog = SqliteBlobCatalog(SqliteTransport(str(path)))
    await catalog.ensure_schema()
    verifier = _Verifier()
    upload = SqliteBlobUploadService(catalog, _UploadAuthority(), verifier, 10_000)
    module = BlobReferenceModule(catalog, upload, _ReadAuthority(), _BindingAuthority())
    owner = SqlDataServiceExecutor(SqliteDialect(), SqliteTransport(path.as_uri() + "?mode=rwc"), SimpleSchemaProvider())
    context = RuntimeModule.new().require_capability("blob.v1").into_context()
    context.insert_resource("dataService", owner)
    provider = FileObjectStorage(tmp_path / "objects", os.urandom(32))
    context.with_object_storage(provider)
    try:
        module.install(context)
        await module.ready(context)
        assert verifier.ready_calls == 1
    finally:
        provider.close()


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
                "(key,scope,object_key,content_version,file_name,content_type,size_bytes,status,"
                "completed_at_ms,policy_profile,upload_mode,unbound_retention_seconds,effective_unref_seconds) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (key, "tenant-a", f"objects/{key}", "v1", "report.pdf",
                 "application/pdf", 7, "uploaded_unbound", time.time_ns() // 1_000_000,
                 "default", "server_stream", 86400, 604800))
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
            assert await cursor.fetchall() == [(first.key, "available"),
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
            assert await cursor.fetchone() == ("available",)
    await save(InsertCommand.new("Asset").value("id", 2), "create empty", asset_id=2)
    async with aiosqlite.connect(path) as db:
        async with db.execute("SELECT key,version FROM teaql_blob_binding WHERE entity_id='2'") as cursor:
            assert await cursor.fetchone() == (None, 1)
    await save(DeleteCommand.new("Asset", 2).expected_version(1).hard_delete(),
               "delete empty", asset_id=2)

    ledger_ref = BlobRef("blob_native_ledger")
    async with aiosqlite.connect(path) as db:
        await db.execute("INSERT INTO teaql_blob_catalog "
            "(key,scope,object_key,content_version,file_name,content_type,size_bytes,status,"
            "completed_at_ms,policy_profile,upload_mode,unbound_retention_seconds,effective_unref_seconds) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (ledger_ref.key, "tenant-a", "objects/ledger", "v1", "ledger.pdf",
             "application/pdf", 7, "uploaded_unbound", time.time_ns() // 1_000_000,
             "default", "server_stream", 86400, 604800))
        await db.commit()

    async def save_allocated_ledger(abort):
        ledger = EntityRoot()
        provisional = EntityKey("Asset", -1)
        ledger.mark_as_new(provisional)
        ledger.set(provisional, "document", ledger_ref)

        async def work(graph):
            allocated = await graph.transaction.next_id("Asset")
            assert type(allocated) is int and allocated > 0
            actual = EntityKey("Asset", allocated)
            ledger.rekey(provisional, actual)
            command = (InsertCommand.new("Asset").value("id", allocated)
                       .value("document", ledger_ref))
            result = await graph.transaction.mutate(graph.context,
                graph.request(command, graph.scope(actual), ledger, actual))
            assert getattr(result.generated_values["id"], "val") == allocated
            assert ledger.get(actual, "document") == ledger_ref
            if abort:
                raise RuntimeError("outer owner rejected")
            return allocated

        return await context.execute_graph_save(work, comment="save allocated ledger Blob")

    with pytest.raises(RuntimeError, match="outer owner rejected"):
        await save_allocated_ledger(True)
    async with aiosqlite.connect(path) as db:
        async with db.execute("SELECT COUNT(*) FROM asset WHERE document=?",
                              (ledger_ref.key,)) as cursor:
            assert await cursor.fetchone() == (0,)
        async with db.execute("SELECT COUNT(*) FROM teaql_blob_binding WHERE key=?",
                              (ledger_ref.key,)) as cursor:
            assert await cursor.fetchone() == (0,)
        async with db.execute("SELECT status FROM teaql_blob_catalog WHERE key=?",
                              (ledger_ref.key,)) as cursor:
            assert await cursor.fetchone() == ("uploaded_unbound",)
    allocated = await save_allocated_ledger(False)
    async with aiosqlite.connect(path) as db:
        async with db.execute("SELECT document FROM asset WHERE id=?", (allocated,)) as cursor:
            assert await cursor.fetchone() == (ledger_ref.key,)
        async with db.execute("SELECT key FROM teaql_blob_binding WHERE entity_id=?",
                              (str(allocated),)) as cursor:
            assert await cursor.fetchone() == (ledger_ref.key,)
        async with db.execute("SELECT status FROM teaql_blob_catalog WHERE key=?",
                              (ledger_ref.key,)) as cursor:
            assert await cursor.fetchone() == ("available",)
    store.close()


@pytest.mark.asyncio
async def test_native_blob_multi_entity_graph_rolls_back_together(tmp_path):
    path = str(tmp_path / "multi-native.db")
    descriptor = EntityDescriptor("Asset").table_name("asset")
    descriptor.property(PropertyDescriptor("id", DataType.I64).is_id())
    descriptor.property(PropertyDescriptor("version", DataType.I64).is_version())
    for field in ("document", "legacy_document"):
        descriptor.property(PropertyDescriptor(field, DataType.Text).blob(
            BlobFieldSpec("Asset", field, ["pdf"], True, "default")))
    schema = SimpleSchemaProvider()
    schema.register_entity(descriptor)
    context = RuntimeModule.new().entity(descriptor).require_capability("blob.v1").into_context()
    context.insert_resource("dataService", SqlDataServiceExecutor(
        SqliteDialect(), SqliteTransport(path), schema))
    context.disable_sql_log()
    store = FileObjectStorage(tmp_path / "multi-private", os.urandom(32))
    context.with_object_storage(store)
    catalog = SqliteBlobCatalog(SqliteTransport(path))
    await catalog.ensure_schema()
    refs = [BlobRef(f"blob_multi_{suffix}") for suffix in ("first", "second", "third")]
    async with aiosqlite.connect(path) as db:
        await db.execute("CREATE TABLE asset (id INTEGER PRIMARY KEY, version INTEGER, "
                         "document TEXT, legacy_document TEXT)")
        for ref in refs:
            await db.execute("INSERT INTO teaql_blob_catalog "
                "(key,scope,object_key,content_version,file_name,content_type,size_bytes,status,"
                "completed_at_ms,policy_profile,upload_mode,unbound_retention_seconds,effective_unref_seconds) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (ref.key, "tenant-a", f"objects/{ref.key}", "v1", f"{ref.key}.pdf",
                 "application/pdf", 7, "uploaded_unbound", time.time_ns() // 1_000_000,
                 "default", "server_stream", 86400, 604800))
        await db.commit()

    class MultiBindingAuthority(_BindingAuthority):
        def __init__(self):
            self.denied_id = None
            self.denied = False
            self.visited = []

        async def authorize(self, context, target, previous, next_ref, action):
            self.visited.append((target.entity_id, target.field))
            if target.entity_id == self.denied_id and target.field == "legacy_document":
                self.denied = True
                return False
            return target.entity == "Asset"

    authority = MultiBindingAuthority()
    upload = SqliteBlobUploadService(catalog, _UploadAuthority(), _Verifier(), 10_000)
    module = BlobReferenceModule(catalog, upload, _ReadAuthority(), authority)
    module.install(context)
    await module.ready(context)
    allocated = []

    async def save(*, catch_denial=False, outer_reject=False):
        allocated.clear()
        authority.visited.clear()
        authority.denied_id = None
        authority.denied = False
        ledger = EntityRoot()
        provisional = [EntityKey("Asset", -1), EntityKey("Asset", -2)]
        for key in provisional:
            ledger.mark_as_new(key)
        ledger.set(provisional[0], "document", refs[0])
        ledger.set(provisional[1], "document", refs[1])
        ledger.set(provisional[1], "legacy_document", refs[2])

        async def work(graph):
            for _ in provisional:
                allocated.append(await graph.transaction.next_id("Asset"))
            if catch_denial:
                authority.denied_id = str(allocated[1])
            for index, old in enumerate(provisional):
                actual = EntityKey("Asset", allocated[index])
                ledger.rekey(old, actual)
                assert ledger.get(actual, "document") == refs[index]
                command = (InsertCommand.new("Asset").value("id", allocated[index])
                           .value("document", ledger.get(actual, "document")))
                if index == 1:
                    command.value("legacy_document", ledger.get(actual, "legacy_document"))
                try:
                    await graph.transaction.mutate(graph.context,
                        graph.request(command, graph.scope(actual), ledger, actual))
                except RuntimeError:
                    if catch_denial:
                        return
                    raise
            if outer_reject:
                raise RuntimeError("outer owner rejected")

        await context.execute_graph_save(work, comment="save multi-entity Blob graph")
        return tuple(allocated)

    async def assert_rollback(ids):
        async with aiosqlite.connect(path) as db:
            async with db.execute("SELECT COUNT(*) FROM asset WHERE id IN (?,?)", ids) as cursor:
                assert await cursor.fetchone() == (0,)
            async with db.execute("SELECT COUNT(*) FROM teaql_blob_binding") as cursor:
                assert await cursor.fetchone() == (0,)
            async with db.execute("SELECT key,status FROM teaql_blob_catalog ORDER BY key") as cursor:
                assert await cursor.fetchall() == [(ref.key, "uploaded_unbound") for ref in refs]

    try:
        with pytest.raises(RuntimeError, match="GRAPH_TRANSACTION_ROLLBACK_ONLY"):
            await save(catch_denial=True)
        assert authority.denied
        assert authority.visited == [
            (str(allocated[0]), "document"), (str(allocated[0]), "legacy_document"),
            (str(allocated[1]), "document"), (str(allocated[1]), "legacy_document")]
        await assert_rollback(tuple(allocated))

        with pytest.raises(RuntimeError, match="outer owner rejected"):
            await save(outer_reject=True)
        await assert_rollback(tuple(allocated))

        committed = await save()
        assert authority.visited == [
            (str(committed[0]), "document"), (str(committed[0]), "legacy_document"),
            (str(committed[1]), "document"), (str(committed[1]), "legacy_document")]
        async with aiosqlite.connect(path) as db:
            async with db.execute("SELECT id,document,legacy_document FROM asset ORDER BY id") as cursor:
                assert await cursor.fetchall() == [
                    (committed[0], refs[0].key, None),
                    (committed[1], refs[1].key, refs[2].key)]
            async with db.execute("SELECT entity_id,field,key FROM teaql_blob_binding "
                                  "ORDER BY entity_id,field") as cursor:
                assert await cursor.fetchall() == [
                    (str(committed[0]), "document", refs[0].key),
                    (str(committed[0]), "legacy_document", None),
                    (str(committed[1]), "document", refs[1].key),
                    (str(committed[1]), "legacy_document", refs[2].key)]
            async with db.execute("SELECT key,status FROM teaql_blob_catalog ORDER BY key") as cursor:
                assert await cursor.fetchall() == [(ref.key, "available") for ref in refs]
    finally:
        store.close()


@pytest.mark.asyncio
async def test_native_shared_blob_final_unbind_controls_file_retention(tmp_path):
    store = FileObjectStorage(tmp_path / "shared-private", os.urandom(32))
    await _run_native_shared_blob_final_unbind(tmp_path, store, real_s3=False)


@pytest.mark.asyncio
async def test_native_shared_blob_final_unbind_controls_real_s3_retention(tmp_path):
    if os.environ.get("TEAQL_S3_TEST_SHARED_BLOB") != "1":
        pytest.skip("explicit shared-reference S3 gate required")
    endpoint = os.environ.get("TEAQL_S3_TEST_ENDPOINT")
    bucket = os.environ.get("TEAQL_S3_TEST_BUCKET")
    access = os.environ.get("TEAQL_S3_TEST_ACCESS_KEY")
    secret = os.environ.get("TEAQL_S3_TEST_SECRET_KEY")
    assert all((endpoint, bucket, access, secret)), "explicit S3 test configuration required"
    from teaql.provider.s3 import S3ObjectStorage
    store = S3ObjectStorage.connect(bucket, endpoint_url=endpoint,
                                    aws_access_key_id=access, aws_secret_access_key=secret)
    await _run_native_shared_blob_final_unbind(tmp_path, store, real_s3=True)


async def _run_native_shared_blob_final_unbind(tmp_path, store, real_s3):
    path = str(tmp_path / "shared-native.db")
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
    context.disable_sql_log()
    context.with_object_storage(store).with_object_storage_observer(lambda event: None)
    clock = [1_700_000_000_000]
    catalog = SqliteBlobCatalog(SqliteTransport(path), now_ms=lambda: clock[0])
    policy = BlobRetentionPolicy("default", "server_stream", 10, 20, 0)

    class UploadAuthority:
        def scope(self, _context):
            return "tenant-a"

        def field(self, _context, _target):
            return BlobFieldSpec("Asset", "document", ["pdf"], True, "default")

        async def authorize(self, _context, target, action, _input):
            return target.entity == "Asset" and target.field == "document" and action in (
                "Begin", "Write", "Confirm")

        async def current_policy_on_lease(self, _context, lease, _target):
            assert lease is not None
            return policy

    class BindingAuthority(_BindingAuthority):
        async def current_policy_on_lease(self, _context, lease, _target):
            assert lease is not None
            return policy

    class FixtureVerifier:
        def verify(self, stream, extension, maximum_bytes):
            data = stream.read(maximum_bytes + 1)
            assert extension == "pdf" and len(data) <= maximum_bytes
            assert data.startswith(b"%PDF-") and b"%%EOF" in data
            assert stream.read(1) == b""
            return BlobVerifiedContent(len(data), sha256(data).hexdigest(), "application/pdf")

    upload = SqliteBlobUploadService(catalog, UploadAuthority(), FixtureVerifier(), 10_000,
                                     now_ms=lambda: clock[0])
    maintenance = SqliteBlobMaintenanceService(catalog, _MaintenanceAuthority(),
                                               now_ms=lambda: clock[0])
    read_permission = _ReadAuthority()
    module = BlobReferenceModule(catalog, upload, read_permission, BindingAuthority(),
                                 maintenance=maintenance)
    async with aiosqlite.connect(path) as db:
        await db.execute("CREATE TABLE asset (id INTEGER PRIMARY KEY, version INTEGER, document TEXT)")
        await db.commit()
    await catalog.ensure_schema()
    module.install(context)
    await module.ready(context)

    async def row(sql, params=()):
        async with aiosqlite.connect(path) as db:
            async with db.execute(sql, params) as cursor:
                return await cursor.fetchone()

    object_key = None
    try:
        data = b"%PDF-1.7\nshared native Blob\n%%EOF"
        session = await upload.begin(context, BlobUploadTarget("Asset", "1", "document"),
                                     BlobUploadInput("shared.pdf", len(data), "application/pdf"),
                                     "shared-native-blob")
        assert await upload.write(context, session.upload_id, BytesIO(data)) == len(data)
        assert await upload.complete(context, session.upload_id) == session.reference
        object_key = ObjectKey((await row("SELECT object_key FROM teaql_blob_catalog WHERE key=?",
                                          (session.reference.key,)))[0])
        object_store = context.object_storage("shared native Blob graph")
        assert object_store.head(object_key) is not None

        ledger = EntityRoot()
        provisional = [EntityKey("Asset", -1), EntityKey("Asset", -2)]
        for key in provisional:
            ledger.mark_as_new(key)
            ledger.set(key, "document", session.reference)

        async def bind(graph):
            ids = []
            for key in provisional:
                allocated = await graph.transaction.next_id("Asset")
                actual = EntityKey("Asset", allocated)
                ledger.rekey(key, actual)
                command = (InsertCommand.new("Asset").value("id", allocated)
                           .value("document", ledger.get(actual, "document")))
                await graph.transaction.mutate(graph.context,
                    graph.request(command, graph.scope(actual), ledger, actual))
                ids.append(allocated)
            return ids

        ids = await context.execute_graph_save(bind, comment="bind shared Blob in two native rows")
        assert len(ids) == 2
        assert await row("SELECT COUNT(*) FROM teaql_blob_binding WHERE key=?",
                         (session.reference.key,)) == (2,)
        assert await row("SELECT status,last_unbound_at_ms FROM teaql_blob_catalog WHERE key=?",
                         (session.reference.key,)) == ("available", None)

        clock[0] += 40_000

        async def unbind(id, outer_reject=False):
            async def work(graph):
                command = UpdateCommand.new("Asset", id).value("document", None)
                await graph.transaction.mutate(graph.context,
                    graph.request(command, graph.scope(EntityKey("Asset", id))))
                if outer_reject:
                    raise RuntimeError("outer owner rejected final unbind")
            await context.execute_graph_save(work, comment="unbind shared Blob row")

        await unbind(ids[0])
        assert await row("SELECT COUNT(*) FROM teaql_blob_binding WHERE key=?",
                         (session.reference.key,)) == (1,)
        assert await row("SELECT last_unbound_at_ms FROM teaql_blob_catalog WHERE key=?",
                         (session.reference.key,)) == (None,)
        assert (await maintenance.run_batch(context)).outcomes == ()
        assert object_store.head(object_key) is not None

        if real_s3:
            class Authorizer:
                async def authorize(self, _context, _result, _options):
                    slot = AuthorizedBlobSlot(("document",), "Asset", str(ids[1]), "document",
                                              "tenant-a", 1, session.reference)
                    return AuthorizedResponseGraph({"document": session.reference}, (slot,))

            context.insert_resource("response_graph_authorizer", Authorizer())
            options = ViewOptions("ordinary", "read_only",
                                  datetime.now(timezone.utc) + timedelta(seconds=60))
            view = await ViewPreparationService().prepare(context, None, options)
            link = view.presentation["document"]
            assert link.startswith("http") and view.cache_control == "private, no-store"
            with urlopen(Request(link, headers={"Range": "bytes=0-7"}), timeout=5) as response:
                assert response.status == 206 and response.read() == data[:8]
            read_permission.allowed = False
            with pytest.raises(ViewPreparationError) as denied:
                await ViewPreparationService().prepare(context, None, options)
            assert denied.value.code == "BLOB_READ_DENIED"
            read_permission.allowed = True

        with pytest.raises(RuntimeError, match="outer owner rejected final unbind"):
            await unbind(ids[1], outer_reject=True)
        assert await row("SELECT document FROM asset WHERE id=?", (ids[1],)) == (session.reference.key,)
        assert await row("SELECT COUNT(*) FROM teaql_blob_binding WHERE key=?",
                         (session.reference.key,)) == (1,)
        assert await row("SELECT last_unbound_at_ms FROM teaql_blob_catalog WHERE key=?",
                         (session.reference.key,)) == (None,)
        assert (await maintenance.run_batch(context)).outcomes == ()

        await unbind(ids[1])
        assert await row("SELECT COUNT(*) FROM teaql_blob_binding WHERE key=?",
                         (session.reference.key,)) == (0,)
        assert await row("SELECT last_unbound_at_ms FROM teaql_blob_catalog WHERE key=?",
                         (session.reference.key,)) == (clock[0],)
        if real_s3:
            with pytest.raises(ViewPreparationError) as stale_view:
                await ViewPreparationService().prepare(context, None, options)
            assert stale_view.value.code == "BLOB_READ_DENIED"
        clock[0] += 19_999
        assert (await maintenance.run_batch(context)).outcomes == ()
        assert object_store.head(object_key) is not None
        clock[0] += 1
        batch = await maintenance.run_batch(context)
        assert [(item.reference.key, item.status) for item in batch.outcomes] == [
            (session.reference.key, "deleted")]
        assert object_store.head(object_key) is None
        assert await row("SELECT status FROM teaql_blob_catalog WHERE key=?",
                         (session.reference.key,)) == ("deleted",)
        if real_s3:
            print("PASS Python shared S3 native graph/final unbind/authorized Range/retention GC")
    finally:
        try:
            if real_s3 and object_key is not None:
                context.object_storage("clean shared S3 Blob").delete(object_key)
        finally:
            store.close()
