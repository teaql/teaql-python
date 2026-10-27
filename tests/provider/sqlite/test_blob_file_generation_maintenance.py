"""Catalog-scoped scheduling for real fenced File old-generation cleanup."""

import os

import aiosqlite
import pytest

from teaql.core.object_storage import ObjectKey, PutOptions, WriteMode
from teaql.provider.sqlite.transport import SqliteTransport
from teaql.runtime import RuntimeModule
from teaql_blob_reference import (
    BlobMaintenanceCursor, FileObjectStorage, SqliteBlobCatalog,
    SqliteBlobFileGenerationSweepService,
)


class FailOnceFileStorage(FileObjectStorage):
    fail_next_sweep = False

    def sweep_old_generations(self, key):
        if self.fail_next_sweep:
            self.fail_next_sweep = False
            raise OSError("transient File failure")
        return super().sweep_old_generations(key)


class MaintenanceAuthority:
    scope_value = "tenant-a"
    allowed = True

    def scope(self, _actor):
        return self.scope_value

    async def can_maintain(self, _actor, _scope):
        return self.allowed


async def seed(path, reference, scope, object_key, version, status):
    async with aiosqlite.connect(path) as db:
        await db.execute("""INSERT INTO teaql_blob_catalog
            (key,scope,object_key,content_version,file_name,content_type,size_bytes,
             completed_at_ms,policy_profile,upload_mode,unbound_retention_seconds,
             effective_unref_seconds,status)
            VALUES (?,?,?,?,?,?,?,?,'default','server_stream',86400,86400,?)""",
            (reference, scope, object_key.value, version, "report.pdf", "application/pdf",
             10, 1000, status))
        await db.execute("""INSERT INTO teaql_blob_upload
            (upload_id,scope,replay_key,request_hash,key,entity,entity_id,field,file_name,
             extension,declared_size,expires_ms,state,written_etag)
            VALUES (?,?,?,?,?,'Asset','1','document','report.pdf','pdf',10,9000,
                    'completed',?)""",
            ("bu_" + reference, scope, "replay_" + reference, "hash_" + reference,
             reference, version))
        await db.commit()


@pytest.mark.asyncio
async def test_catalog_file_sweep_covers_deleted_rows_preserves_current_and_retries(tmp_path):
    path = str(tmp_path / "catalog.db")
    catalog = SqliteBlobCatalog(SqliteTransport(path))
    await catalog.ensure_schema()
    provider = FailOnceFileStorage(tmp_path / "objects", os.urandom(32))
    actor = RuntimeModule.new().into_context().with_object_storage(provider)
    actor.with_object_storage_observer(lambda event: None)
    store = actor.object_storage("catalog File sweep")
    authority = MaintenanceAuthority()
    service = SqliteBlobFileGenerationSweepService(catalog, authority, True, 1)
    original = b"first data"
    replacement = b"replacement data"
    keys = [ObjectKey("objects/blob_a"), ObjectKey("objects/blob_b"),
            ObjectKey("objects/blob_other")]
    try:
        assert provider is actor.get_resource("object_storage_provider")
        for key, reference, scope, status in zip(
                keys, ("blob_a", "blob_b", "blob_other"),
                ("tenant-a", "tenant-a", "tenant-b"),
                ("deleted", "uploaded_unbound", "uploaded_unbound")):
            store.put_bytes(key, original,
                            PutOptions(len(original), WriteMode.CREATE_ONLY))
            current = store.put_bytes(key, replacement,
                                      PutOptions(len(replacement), WriteMode.REPLACE))
            if status == "deleted":
                assert store.delete_if_version(key, current.etag) == "deleted"
            await seed(path, reference, scope, key, current.etag, status)

        with pytest.raises(RuntimeError, match="BLOB_POLICY_INVALID"):
            SqliteBlobFileGenerationSweepService(catalog, authority, False)
        authority.allowed = False
        with pytest.raises(RuntimeError, match="BLOB_MAINTENANCE_DENIED"):
            await service.run_batch(actor, provider)
        authority.allowed = True
        with pytest.raises(RuntimeError, match="BLOB_MAINTENANCE_DENIED"):
            await service.run_batch(actor, provider, BlobMaintenanceCursor("tenant-b", ""))
        token = actor._graph_save_guard.set({"active": True})
        try:
            with pytest.raises(RuntimeError, match="BLOB_TRANSACTION_REQUIRED"):
                await service.run_batch(actor, provider)
        finally:
            actor._graph_save_guard.reset(token)
        with pytest.raises(RuntimeError, match="BLOB_CAPABILITY_MISSING"):
            await service.run_batch(actor, FileObjectStorage(tmp_path / "objects", os.urandom(32)))

        provider.fail_next_sweep = True
        failed = await service.run_batch(actor, provider)
        assert [(entry.status, entry.error) for entry in failed.outcomes] == [
            ("failed", "BLOB_STORE_FAILED")]
        outcomes = []
        cursor = None
        while True:
            batch = await service.run_batch(actor, provider, cursor)
            outcomes.extend(batch.outcomes)
            if batch.next is None:
                break
            cursor = batch.next
        assert len(outcomes) == 2
        assert [entry.status for entry in outcomes] == ["swept", "swept"]
        assert [entry.removed_generations for entry in outcomes] == [1, 1]
        assert store.head(keys[0]) is None
        assert store.get_bytes(keys[1], 100) == replacement
        assert store.get_bytes(keys[2], 100) == replacement
        assert provider.sweep_old_generations(keys[0]) == 0
        assert provider.sweep_old_generations(keys[1]) == 0
        assert provider.sweep_old_generations(keys[2]) == 1  # Other tenant was not scanned.
    finally:
        provider.close()
