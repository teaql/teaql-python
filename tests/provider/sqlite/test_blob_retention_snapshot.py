"""Trusted Blob retention facts on a real SQLite lease and File provider."""

from hashlib import sha256
from io import BytesIO
from pathlib import Path
import json
import os

import aiosqlite
import pytest

from teaql.core.blob_ref import BlobFieldSpec
from teaql.provider.sqlite.transport import SqliteTransport
from teaql.runtime import RuntimeModule
from teaql.sql.types import CompiledQuery
from teaql_blob_reference import (
    BlobRetentionPolicy, BlobUploadInput, BlobUploadTarget, BlobVerifiedContent,
    FileObjectStorage, SqliteBlobCatalog, SqliteBlobUploadService,
)
from teaql_blob_reference.retention import (
    effective_retention, require_bindable, retention_deadline,
    unreferenced_eligible_at,
)


class Authority:
    def __init__(self):
        self.policy = BlobRetentionPolicy("default", "server_stream", 86400, 604800, 3600)
        self.policy_calls = 0

    def scope(self, _actor):
        return "tenant-a"

    def field(self, _actor, _target):
        return BlobFieldSpec("Asset", "document", ("pdf",), True, "default")

    async def authorize(self, _actor, _target, _action, _input):
        return True

    async def current_policy_on_lease(self, _actor, lease, _target):
        rows = await lease.fetch_all_sql(CompiledQuery("SELECT 1 AS alive", []))
        assert rows == [{"alive": 1}]
        self.policy_calls += 1
        return self.policy


class Verifier:
    def verify(self, stream, extension, maximum_bytes):
        data = stream.read(maximum_bytes + 1)
        assert extension == "pdf" and data.startswith(b"%PDF-")
        assert stream.read(1) == b""
        return BlobVerifiedContent(len(data), sha256(data).hexdigest(), "application/pdf")


@pytest.mark.asyncio
async def test_policy_snapshotted_on_lease_completion_time_and_replay(tmp_path):
    path = str(tmp_path / "catalog.db")
    catalog = SqliteBlobCatalog(SqliteTransport(path))
    await catalog.ensure_schema()
    await catalog.validate_schema()
    authority = Authority()
    clock = [1_700_000_000_000]
    actor = RuntimeModule.new().into_context().with_object_storage(
        FileObjectStorage(tmp_path / "private", os.urandom(32)))
    actor.with_object_storage_observer(lambda _event: None)
    service = SqliteBlobUploadService(catalog, authority, Verifier(), 10_000,
                                      now_ms=lambda: clock[0])
    data = b"%PDF-1.7\nretention snapshot\n%%EOF"
    target = BlobUploadTarget("Asset", "1", "document")
    request = BlobUploadInput("report.pdf", len(data))
    session = await service.begin(actor, target, request, "snapshot-1")
    assert authority.policy_calls == 1
    async with aiosqlite.connect(path) as db:
        async with db.execute("SELECT policy_profile,upload_mode,unbound_retention_seconds,"
                              "effective_unref_seconds,completed_at_ms,last_unbound_at_ms "
                              "FROM teaql_blob_catalog WHERE key=?", (session.reference.key,)) as cursor:
            assert await cursor.fetchone() == ("default", "server_stream", 86400, 604800, None, None)
    authority.policy = BlobRetentionPolicy("new-profile", "server_stream", 1, 1, 1)
    assert (await service.begin(actor, target, request, "snapshot-1")).upload_id == session.upload_id
    assert authority.policy_calls == 1
    await service.write(actor, session.upload_id, BytesIO(data))
    clock[0] += 30_000
    assert await service.complete(actor, session.upload_id) == session.reference
    assert await service.complete(actor, session.upload_id) == session.reference
    async with aiosqlite.connect(path) as db:
        async with db.execute("SELECT policy_profile,unbound_retention_seconds,"
                              "effective_unref_seconds,completed_at_ms,status "
                              "FROM teaql_blob_catalog WHERE key=?", (session.reference.key,)) as cursor:
            assert await cursor.fetchone() == ("default", 86400, 604800, clock[0], "uploaded_unbound")


@pytest.mark.asyncio
async def test_migration_keeps_legacy_policy_unknown_and_direct_mode_rejected(tmp_path):
    path = str(tmp_path / "old.db")
    async with aiosqlite.connect(path) as db:
        await db.execute("CREATE TABLE teaql_blob_catalog (key TEXT PRIMARY KEY, scope TEXT NOT NULL, "
                         "object_key TEXT NOT NULL, content_version TEXT NOT NULL, file_name TEXT NOT NULL, "
                         "content_type TEXT NOT NULL, size_bytes BIGINT NOT NULL, status TEXT NOT NULL)")
        await db.execute("INSERT INTO teaql_blob_catalog VALUES (?,?,?,?,?,?,?,?)",
                         ("blob_legacy", "tenant-a", "blob/legacy", "v1", "old.pdf", "application/pdf", 10, "available"))
        await db.commit()
    catalog = SqliteBlobCatalog(SqliteTransport(path))
    await catalog.ensure_schema()
    await catalog.ensure_schema()
    await catalog.validate_schema()
    async with aiosqlite.connect(path) as db:
        async with db.execute("SELECT completed_at_ms,last_unbound_at_ms,policy_profile,upload_mode,"
                              "unbound_retention_seconds,effective_unref_seconds,retention_floor_until_ms "
                              "FROM teaql_blob_catalog WHERE key='blob_legacy'") as cursor:
            assert await cursor.fetchone() == (None,) * 7
    authority = Authority()
    authority.policy = BlobRetentionPolicy("default", "direct", 1, 1, 1)
    service = SqliteBlobUploadService(catalog, authority, Verifier(), 10_000)
    with pytest.raises(RuntimeError, match="^BLOB_CAPABILITY_MISSING$"):
        await service.begin(RuntimeModule.new().into_context(), BlobUploadTarget("Asset", "1", "document"),
                            BlobUploadInput("direct.pdf", 4), "direct-mode")
    assert authority.policy_calls == 1
    async with aiosqlite.connect(path) as db:
        async with db.execute("SELECT count(*) FROM teaql_blob_upload") as cursor:
            assert await cursor.fetchone() == (0,)


def test_shared_retention_vectors():
    fixture = Path(__file__).with_name("testdata") / "blob-policy-cases.json"
    assert sha256(fixture.read_bytes()).hexdigest() == (
        "b93cff3f8dabd5690aac5f8f2096633dcd4e158d3aa0424b9a902a16f6d3c2b6")
    cases = {case["id"]: case for case in json.loads(fixture.read_text())["cases"]}
    upload = cases["upload-clock-independent"]
    assert upload["input"]["nowSeconds"] >= 3600
    assert retention_deadline(upload["input"]["completedAtSeconds"] * 1000, 86400) == (
        upload["expected"]["unboundEligibleAtSeconds"] * 1000)
    expired = cases["unbound-deadline-rejects-bind-before-gc"]
    with pytest.raises(RuntimeError, match="^BLOB_REFERENCE_EXPIRED$"):
        require_bindable("uploaded_unbound", expired["input"]["nowSeconds"] * 1000,
                         expired["input"]["completedAtSeconds"] * 1000,
                         expired["input"]["unboundRetentionSeconds"], None)
    maximum = cases["maximum-retention-across-fields"]
    seconds = effective_retention(tuple(maximum["input"]["acceptedRetentionSeconds"]), 0)
    assert seconds == maximum["expected"]["effectiveUnreferencedRetentionSeconds"]
    assert unreferenced_eligible_at(maximum["input"]["lastUnboundAtSeconds"] * 1000,
                                    seconds, maximum["input"]["retentionFloorUntilSeconds"] * 1000) == (
        maximum["expected"]["unreferencedEligibleAtSeconds"] * 1000)
    shorter = cases["profile-update-does-not-shorten"]
    assert effective_retention((shorter["input"]["acceptedUnreferencedRetentionSeconds"],),
                               shorter["input"]["currentProfileRetentionSeconds"]) == (
        shorter["expected"]["effectiveUnreferencedRetentionSeconds"])
