"""Real SQLite state transitions for explicit, fenced Blob expiry cleanup."""

import aiosqlite
import pytest
from uuid import uuid4
import os

from teaql.core.object_storage import ObjectKey, ObjectMetadata, PutOptions, WriteMode
from teaql.provider.sqlite.transport import SqliteTransport
from teaql.runtime import RuntimeModule
from teaql_blob_reference import FileObjectStorage, SqliteBlobCatalog, SqliteBlobMaintenanceService


class _MaintenanceAuthority:
    def __init__(self):
        self.current_scope = "tenant-a"
        self.allowed = True

    def scope(self, context):
        return self.current_scope

    async def can_maintain(self, context, scope):
        return self.allowed


class _ConditionalStore:
    def __init__(self):
        self.objects = {}
        self.deletes = 0

    def head(self, invocation, key):
        etag = self.objects.get(key.value)
        return ObjectMetadata(key, 1, "application/pdf", etag) if etag else None

    def delete_if_version(self, invocation, key, version):
        self.deletes += 1
        actual = self.objects.get(key.value)
        if actual is None:
            return "already_missing"
        if actual != version:
            return "version_mismatch"
        del self.objects[key.value]
        return "deleted"

    def delete(self, invocation, key):
        raise AssertionError("unconditional delete is forbidden")


async def _seed(path, key, *, scope="tenant-a", state="written", version="",
                written_etag=None, expires=9000, bound=False):
    async with aiosqlite.connect(path) as db:
        await db.execute("""INSERT INTO teaql_blob_catalog
            (key,scope,object_key,content_version,file_name,content_type,size_bytes,status)
            VALUES (?,?,?,?,?,?,?,?)""", (key, scope, "objects/" + key, version,
                                      "file.pdf", "", 0,
                                      "uploaded_unbound" if state == "completed" else "initiated"))
        await db.execute("""INSERT INTO teaql_blob_upload
            (upload_id,scope,replay_key,request_hash,key,entity,entity_id,field,file_name,
             extension,declared_size,expires_ms,state,written_etag)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", ("bu_" + key, scope, "replay_" + key,
                 "hash_" + key, key, "Asset", "1", "document", "file.pdf", "pdf",
                 1, expires, state, written_etag))
        if bound:
            await db.execute("""INSERT INTO teaql_blob_binding
                (scope,entity,entity_id,field,key,version) VALUES (?,?,?,?,?,?)""",
                (scope, "Asset", key, "document", key, 1))
        await db.commit()


async def _status(path, key):
    async with aiosqlite.connect(path) as db:
        async with db.execute("SELECT status FROM teaql_blob_catalog WHERE key=?", (key,)) as cursor:
            return (await cursor.fetchone())[0]


@pytest.mark.asyncio
async def test_real_sqlite_file_maintenance_recovers_receipt_and_partial_data(tmp_path):
    path = str(tmp_path / "file-maintenance.db")
    catalog = SqliteBlobCatalog(SqliteTransport(path))
    await catalog.ensure_schema()
    provider = FileObjectStorage(tmp_path / "file-objects", os.urandom(32))
    actor = RuntimeModule.new().into_context()
    actor.with_object_storage(provider).with_object_storage_observer(lambda event: None)
    store = actor.object_storage("real File expired Blob maintenance")
    service = SqliteBlobMaintenanceService(catalog, _MaintenanceAuthority(), 10, lambda: 10000)
    content = b"%PDF-"
    key = ObjectKey("objects/blob_file_receipt")
    store.put_bytes(key, content, PutOptions(len(content), WriteMode.CREATE_ONLY))
    await _seed(path, "blob_file_receipt", state="initiated")
    async with aiosqlite.connect(path) as db:
        await db.execute("""CREATE TRIGGER fail_file_receipt BEFORE UPDATE OF status ON teaql_blob_catalog
            WHEN NEW.status='deleted' BEGIN SELECT RAISE(ABORT,'receipt failure'); END""")
        await db.commit()
    failed = await service.run_batch(actor)
    assert [(o.reference.key, o.status) for o in failed.outcomes] == [("blob_file_receipt", "failed")]
    assert await _status(path, "blob_file_receipt") == "deleting"
    assert store.head(key) is None
    async with aiosqlite.connect(path) as db:
        await db.execute("DROP TRIGGER fail_file_receipt")
        await db.commit()
    retry = await service.run_batch(actor)
    assert [(o.reference.key, o.status) for o in retry.outcomes] == [
        ("blob_file_receipt", "already_missing")]
    assert await _status(path, "blob_file_receipt") == "deleted"

    stale_key = ObjectKey("objects/blob_file_stale")
    old = store.put_bytes(stale_key, content, PutOptions(len(content), WriteMode.CREATE_ONLY))
    await _seed(path, "blob_file_stale", state="initiated", version=old.etag)
    newer = store.put_bytes(stale_key, content, PutOptions(len(content), WriteMode.REPLACE))
    stale = await service.run_batch(actor)
    assert [(o.reference.key, o.status) for o in stale.outcomes] == [
        ("blob_file_stale", "version_conflict")]
    assert store.head(stale_key).etag == newer.etag

    partial_key = ObjectKey("objects/blob_file_partial")
    partial = store.put_bytes(partial_key, content, PutOptions(len(content), WriteMode.CREATE_ONLY))
    await _seed(path, "blob_file_partial", state="initiated", version=partial.etag)
    manifest = provider._manifest(provider._hash(partial_key))
    provider._data_path(provider._hash(partial_key), manifest).unlink()
    recovered = await service.run_batch(actor)
    assert ("blob_file_partial", "deleted") in [(o.reference.key, o.status) for o in recovered.outcomes]
    assert await _status(path, "blob_file_partial") == "deleted"


@pytest.mark.asyncio
async def test_expired_upload_maintenance_claim_scope_version_and_recovery(tmp_path):
    path = str(tmp_path / "maintenance.db")
    catalog = SqliteBlobCatalog(SqliteTransport(path))
    await catalog.ensure_schema()
    actor = RuntimeModule.new().into_context()
    store = _ConditionalStore()
    actor.with_object_storage(store).with_object_storage_observer(lambda event: None)
    auth = _MaintenanceAuthority()
    service = SqliteBlobMaintenanceService(catalog, auth, 2, lambda: 10000)
    await _seed(path, "blob_absent", state="initiated")
    await _seed(path, "blob_bound", state="initiated", bound=True)
    await _seed(path, "blob_completed", state="completed", written_etag="etag-completed")
    await _seed(path, "blob_future", expires=20000, written_etag="etag-future")
    await _seed(path, "blob_other", scope="tenant-b", written_etag="etag-other")
    await _seed(path, "blob_race", version="etag-old", written_etag="etag-old")
    await _seed(path, "blob_written", written_etag="etag-written")
    store.objects.update({"objects/blob_race": "etag-new",
                          "objects/blob_written": "etag-written",
                          "objects/blob_completed": "etag-completed",
                          "objects/blob_future": "etag-future",
                          "objects/blob_other": "etag-other"})
    await catalog.validate_schema()
    auth.allowed = False
    with pytest.raises(RuntimeError, match="^BLOB_MAINTENANCE_DENIED$"):
        await service.run_batch(actor)
    auth.allowed = True
    first = await service.run_batch(actor)
    assert [(o.reference.key, o.status) for o in first.outcomes] == [
        ("blob_absent", "already_missing"), ("blob_race", "version_conflict")]
    assert first.next is not None
    second = await service.run_batch(actor, first.next)
    assert [(o.reference.key, o.status) for o in second.outcomes] == [
        ("blob_written", "deleted")]
    assert store.deletes == 2  # the stale pinned version is refused by conditional deletion
    assert store.objects["objects/blob_race"] == "etag-new"
    for key, expected in {"blob_absent": "deleted", "blob_race": "deleting",
                          "blob_written": "deleted", "blob_completed": "uploaded_unbound",
                          "blob_future": "initiated", "blob_other": "initiated",
                          "blob_bound": "initiated"}.items():
        assert await _status(path, key) == expected
    auth.current_scope = "tenant-b"
    with pytest.raises(RuntimeError, match="^BLOB_MAINTENANCE_DENIED$"):
        await service.run_batch(actor, first.next)
    auth.current_scope = "tenant-a"
    await _seed(path, "blob_retry", written_etag="etag-retry")
    store.objects["objects/blob_retry"] = "etag-retry"
    async with aiosqlite.connect(path) as db:
        await db.execute("""CREATE TRIGGER fail_final_ack BEFORE UPDATE OF status ON teaql_blob_catalog
            WHEN NEW.status='deleted' AND OLD.key='blob_retry'
            BEGIN SELECT RAISE(ABORT,'private trigger detail'); END""")
        await db.commit()
    failed = await service.run_batch(actor)
    assert failed.outcomes[1].status == "failed"
    assert failed.outcomes[1].error == "BLOB_CATALOG_FAILED"
    assert "objects/blob_retry" not in store.objects
    assert await _status(path, "blob_retry") == "deleting"
    async with aiosqlite.connect(path) as db:
        await db.execute("DROP TRIGGER fail_final_ack")
        await db.commit()
    recovered = await service.run_batch(actor)
    assert recovered.outcomes[1].status == "already_missing"
    assert await _status(path, "blob_retry") == "deleted"


@pytest.mark.asyncio
async def test_expired_upload_maintenance_rejects_unfenced_store_graph_and_schema(tmp_path):
    path = str(tmp_path / "maintenance-gates.db")
    catalog = SqliteBlobCatalog(SqliteTransport(path))
    await catalog.ensure_schema()
    actor = RuntimeModule.new().into_context()
    auth = _MaintenanceAuthority()
    service = SqliteBlobMaintenanceService(catalog, auth, 2, lambda: 10000)
    actor.with_object_storage(object())
    with pytest.raises(RuntimeError, match="^BLOB_CAPABILITY_MISSING$"):
        await service.run_batch(actor)
    actor.with_object_storage(_ConditionalStore())
    token = actor._graph_save_guard.set({"active": True})
    try:
        with pytest.raises(RuntimeError, match="^BLOB_TRANSACTION_REQUIRED$"):
            await service.run_batch(actor)
    finally:
        actor._graph_save_guard.reset(token)
    async with aiosqlite.connect(path) as db:
        await db.execute("DROP INDEX teaql_blob_catalog_object_key")
        await db.commit()
    with pytest.raises(RuntimeError, match="^BLOB_SCHEMA_MISSING$"):
        await service.run_batch(actor)


@pytest.mark.asyncio
async def test_real_s3_expired_upload_maintenance_delete_recovery_and_stale_version(tmp_path):
    if os.environ.get("TEAQL_S3_TEST_BLOB_MAINTENANCE") != "1":
        pytest.skip("explicit disposable S3 maintenance gate required")
    endpoint = os.environ.get("TEAQL_S3_TEST_ENDPOINT")
    bucket = os.environ.get("TEAQL_S3_TEST_BUCKET")
    access = os.environ.get("TEAQL_S3_TEST_ACCESS_KEY")
    secret = os.environ.get("TEAQL_S3_TEST_SECRET_KEY")
    assert all((endpoint, bucket, access, secret)), "disposable S3 configuration required"
    from teaql.provider.s3 import S3ObjectStorage
    provider = S3ObjectStorage.connect(bucket, endpoint_url=endpoint,
                                       aws_access_key_id=access, aws_secret_access_key=secret)
    actor = RuntimeModule.new().into_context()
    actor.with_object_storage(provider).with_object_storage_observer(lambda event: None)
    store = actor.object_storage("real S3 expired Blob maintenance")
    path = str(tmp_path / "s3-maintenance.db")
    catalog = SqliteBlobCatalog(SqliteTransport(path))
    await catalog.ensure_schema()
    service = SqliteBlobMaintenanceService(catalog, _MaintenanceAuthority(), 10, lambda: 10000)
    prefix = uuid4().hex
    keys = []

    async def seed(suffix, content):
        reference = "blob_" + prefix + "_" + suffix
        key = ObjectKey("objects/" + reference)
        keys.append(key)
        created = store.put_bytes(key, content, PutOptions(len(content), WriteMode.CREATE_ONLY))
        await _seed(path, reference, written_etag=created.etag)
        return reference, key, created.etag

    try:
        first_ref, first_key, _ = await seed("first", b"first version")
        first = await service.run_batch(actor)
        assert [(o.reference.key, o.status) for o in first.outcomes] == [(first_ref, "deleted")]
        assert store.head(first_key) is None
        assert await _status(path, first_ref) == "deleted"

        recovery_ref, recovery_key, _ = await seed("recovery", b"recovery version")
        async with aiosqlite.connect(path) as db:
            await db.execute("""CREATE TRIGGER fail_final_ack BEFORE UPDATE OF status ON teaql_blob_catalog
                WHEN NEW.status='deleted' AND OLD.key='""" + recovery_ref + """'
                BEGIN SELECT RAISE(ABORT,'private trigger detail'); END""")
            await db.commit()
        failed = await service.run_batch(actor)
        assert [(o.reference.key, o.status, o.error) for o in failed.outcomes] == [
            (recovery_ref, "failed", "BLOB_CATALOG_FAILED")]
        assert store.head(recovery_key) is None
        assert await _status(path, recovery_ref) == "deleting"
        async with aiosqlite.connect(path) as db:
            await db.execute("DROP TRIGGER fail_final_ack")
            await db.commit()
        recovered = await service.run_batch(actor)
        assert [(o.reference.key, o.status) for o in recovered.outcomes] == [
            (recovery_ref, "already_missing")]
        assert await _status(path, recovery_ref) == "deleted"

        race_ref, race_key, _ = await seed("stale", b"old version")
        replacement_bytes = b"replacement version"
        replacement = store.put_bytes(race_key, replacement_bytes,
                                      PutOptions(len(replacement_bytes), WriteMode.REPLACE))
        conflict = await service.run_batch(actor)
        assert [(o.reference.key, o.status) for o in conflict.outcomes] == [
            (race_ref, "version_conflict")]
        assert store.head(race_key).etag == replacement.etag
        assert await _status(path, race_ref) == "deleting"
    finally:
        for key in keys:
            store.delete(key)
