"""Sandboxed binary DOC/XLS parsing and real SQLite/File promotion."""

from hashlib import sha256
from io import BytesIO
from pathlib import Path
from shutil import which
from threading import Event, Thread
import os
import sys

import aiosqlite
import pytest

pytest.importorskip("docx")
pytest.importorskip("openpyxl")

from teaql.core.blob_ref import BlobFieldSpec
from teaql.provider.sqlite.transport import SqliteTransport
from teaql.runtime import RuntimeModule
from teaql_blob_reference import (BlobUploadInput, BlobUploadTarget, FileObjectStorage,
                                  SqliteBlobCatalog, SqliteBlobUploadService)
from teaql_blob_reference.content_composite import CompositeBlobContentVerifier
from teaql_blob_reference.content_legacy_office import LegacyOfficeBlobContentVerifier


TOOLS = tuple(which(name) for name in ("soffice", "bwrap", "prlimit"))
pytestmark = pytest.mark.skipif(sys.platform != "linux" or not all(TOOLS),
                                reason="Linux LibreOffice, bubblewrap and prlimit required")
FIXTURES = Path(__file__).parents[2] / "fixtures" / "reference-modules"


def verifier(tmp_path, **overrides):
    scratch = tmp_path / "scratch"
    scratch.mkdir(mode=0o700)
    scratch.chmod(0o700)
    return LegacyOfficeBlobContentVerifier(*TOOLS, scratch,
                                           maximum_input_bytes=100_000,
                                           maximum_converted_bytes=overrides.get("output", 100_000),
                                           concurrent_verifications=1), scratch


@pytest.mark.parametrize("extension,mime,digest", [
    ("doc", "application/msword", "9fca8d262d2aa905d58b1cc1c8914d1a8069c16c340f24cd3c4a77daff9c8b73"),
    ("xls", "application/vnd.ms-excel", "7f387858aaa3ed39d3c7c692aa865b36ac6620462714f3d0daa96388424cf75d"),
])
def test_legacy_office_original_facts_and_structural_rejection(tmp_path, extension, mime, digest):
    parser, scratch = verifier(tmp_path)
    parser.validate_ready()
    data = (FIXTURES / ("sample." + extension)).read_bytes()
    assert sha256(data).hexdigest() == digest
    result = parser.verify(BytesIO(data), extension, len(data))
    assert (result.size_bytes, result.sha256, result.content_type) == (len(data), digest, mime)
    for damaged in (data[:-12], data[:512], bytes([data[0] ^ 1]) + data[1:]):
        with pytest.raises(RuntimeError, match="BLOB_FORMAT_NOT_ALLOWED"):
            parser.verify(BytesIO(damaged), extension, len(data))
    with pytest.raises(RuntimeError, match="BLOB_SIZE_EXCEEDED"):
        parser.verify(BytesIO(data), extension, len(data) - 1)
    assert list(scratch.iterdir()) == []


def test_legacy_office_limits_busy_readiness_and_composite(tmp_path):
    parser, scratch = verifier(tmp_path)
    data = (FIXTURES / "sample.doc").read_bytes()
    limited = LegacyOfficeBlobContentVerifier(*TOOLS, scratch,
                                              maximum_input_bytes=100_000,
                                              maximum_converted_bytes=1,
                                              concurrent_verifications=1)
    with pytest.raises(RuntimeError, match="BLOB_FORMAT_NOT_ALLOWED"):
        limited.verify(BytesIO(data), "doc", len(data))
    entered, release = Event(), Event()

    class PausedInput(BytesIO):
        def read(self, size=-1):
            entered.set()
            assert release.wait(10)
            return super().read(size)

    outcome = []
    first = Thread(target=lambda: outcome.append(parser.verify(PausedInput(data), "doc", len(data))))
    first.start()
    try:
        assert entered.wait(10)
        with pytest.raises(RuntimeError, match="BLOB_VERIFICATION_BUSY"):
            parser.verify(BytesIO(data), "doc", len(data))
    finally:
        release.set()
        first.join(15)
    assert not first.is_alive() and outcome[0].content_type == "application/msword"
    missing = LegacyOfficeBlobContentVerifier(str(scratch / "missing"), TOOLS[1], TOOLS[2], scratch)
    with pytest.raises(RuntimeError, match="BLOB_CAPABILITY_MISSING"):
        missing.validate_ready()
    scratch.chmod(0o755)
    with pytest.raises(RuntimeError, match="BLOB_CAPABILITY_MISSING"):
        parser.validate_ready()
    scratch.chmod(0o700)
    class ForbiddenInput(BytesIO):
        def read(self, size=-1):
            raise AssertionError("wrong extension consumed source")
    with pytest.raises(RuntimeError, match="BLOB_FORMAT_NOT_ALLOWED"):
        parser.verify(ForbiddenInput(data), "pdf", len(data))
    composite = CompositeBlobContentVerifier({"doc": parser, "xls": parser})
    composite.validate_ready()
    assert composite.verify(BytesIO(data), "doc", len(data)).size_bytes == len(data)


class LegacyOfficeAuthority:
    def scope(self, _context):
        return "tenant-a"

    def field(self, _context, _target):
        return BlobFieldSpec("Asset", "document", ["doc", "xls"], True, "default")

    async def authorize(self, _context, target, action, _input):
        return target.entity == "Asset" and target.field == "document" and action in (
            "Begin", "Write", "Confirm")


@pytest.mark.asyncio
async def test_real_legacy_office_upload_promotes_and_rejects(tmp_path):
    parser, _ = verifier(tmp_path)
    path = str(tmp_path / "office.db")
    catalog = SqliteBlobCatalog(SqliteTransport(path))
    provider = FileObjectStorage(tmp_path / "objects", os.urandom(32))
    actor = RuntimeModule.new().into_context().with_object_storage(provider)
    actor.with_object_storage_observer(lambda event: None)
    service = SqliteBlobUploadService(catalog, LegacyOfficeAuthority(), parser, 100_000)
    target = BlobUploadTarget("Asset", "1", "document")
    try:
        await catalog.ensure_schema()
        for extension, mime in (("doc", "application/msword"),
                                ("xls", "application/vnd.ms-excel")):
            data = (FIXTURES / ("sample." + extension)).read_bytes()
            good = await service.begin(actor, target,
                                       BlobUploadInput("sample." + extension, len(data)),
                                       "legacy-good-" + extension)
            assert await service.write(actor, good.upload_id, BytesIO(data)) == len(data)
            assert await service.complete(actor, good.upload_id) == good.reference
            async with aiosqlite.connect(path) as db:
                async with db.execute(
                        "SELECT status,content_type,size_bytes FROM teaql_blob_catalog WHERE key=?",
                        (good.reference.key,)) as cursor:
                    status, actual_mime, size = await cursor.fetchone()
                async with db.execute(
                        "SELECT written_sha256 FROM teaql_blob_upload WHERE upload_id=?",
                        (good.upload_id,)) as cursor:
                    digest = (await cursor.fetchone())[0]
            assert (status, actual_mime, size, digest) == (
                "uploaded_unbound", mime, len(data), sha256(data).hexdigest())
            broken = data[:-12]
            bad = await service.begin(actor, target,
                                      BlobUploadInput("broken." + extension, len(broken)),
                                      "legacy-bad-" + extension)
            await service.write(actor, bad.upload_id, BytesIO(broken))
            with pytest.raises(RuntimeError, match="BLOB_FORMAT_NOT_ALLOWED"):
                await service.complete(actor, bad.upload_id)
            async with aiosqlite.connect(path) as db:
                async with db.execute("SELECT status FROM teaql_blob_catalog WHERE key=?",
                                      (bad.reference.key,)) as cursor:
                    assert (await cursor.fetchone())[0] == "initiated"
    finally:
        provider.close()
