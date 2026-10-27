"""Actual PDF parser and SQLite/File upload promotion boundary."""

from hashlib import sha256
from io import BytesIO
from threading import Event, Thread
import os

import aiosqlite
import pytest

pypdf = pytest.importorskip("pypdf")

from pypdf.generic import DecodedStreamObject, NameObject
from teaql.core.blob_ref import BlobFieldSpec
from teaql.provider.sqlite.transport import SqliteTransport
from teaql.runtime import RuntimeModule
from teaql_blob_reference import (
    BlobUploadInput, BlobUploadTarget, FileObjectStorage, SqliteBlobCatalog,
    SqliteBlobUploadService,
)
from teaql_blob_reference.content_pypdf import PypdfBlobContentVerifier


def pdf_fixture(pages=1):
    writer = pypdf.PdfWriter()
    for _ in range(pages):
        page = writer.add_blank_page(width=72, height=72)
        content = DecodedStreamObject()
        content.set_data(b"q 1 0 0 1 0 0 cm Q")
        page[NameObject("/Contents")] = writer._add_object(content)
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


def test_real_pdf_structure_content_and_limits():
    data = pdf_fixture()
    verifier = PypdfBlobContentVerifier()
    verifier.validate_ready()
    checked = verifier.verify(BytesIO(data), "pdf", 10_000)
    assert (checked.size_bytes, checked.sha256, checked.content_type) == (
        len(data), sha256(data).hexdigest(), "application/pdf")
    for invalid in (data[:-12], b"%PDF-1.7\nnot a real document\n%%EOF",
                    b"", b"\x89PNG\r\n\x1a\n%%EOF"):
        with pytest.raises(RuntimeError, match="BLOB_FORMAT_NOT_ALLOWED"):
            verifier.verify(BytesIO(invalid), "pdf", 10_000)
    with pytest.raises(RuntimeError, match="BLOB_FORMAT_NOT_ALLOWED"):
        verifier.verify(BytesIO(data), "png", 10_000)
    with pytest.raises(RuntimeError, match="BLOB_SIZE_EXCEEDED"):
        verifier.verify(BytesIO(data), "pdf", len(data) - 1)
    with pytest.raises(RuntimeError, match="BLOB_FORMAT_NOT_ALLOWED"):
        PypdfBlobContentVerifier(maximum_decoded_bytes=5).verify(
            BytesIO(data), "pdf", 10_000)
    with pytest.raises(RuntimeError, match="BLOB_FORMAT_NOT_ALLOWED"):
        PypdfBlobContentVerifier(maximum_pages=1).verify(
            BytesIO(pdf_fixture(2)), "pdf", 10_000)


def test_concurrent_admission_releases_slot():
    entered, release = Event(), Event()
    data = pdf_fixture()

    class PausedInput(BytesIO):
        def read(self, size=-1):
            entered.set()
            assert release.wait(5)
            return super().read(size)

    verifier = PypdfBlobContentVerifier(concurrent_verifications=1)
    outcome = []
    first = Thread(target=lambda: outcome.append(verifier.verify(PausedInput(data), "pdf", 10_000)))
    first.start()
    try:
        assert entered.wait(5)
        with pytest.raises(RuntimeError, match="BLOB_VERIFICATION_BUSY"):
            verifier.verify(BytesIO(data), "pdf", 10_000)
    finally:
        release.set()
        first.join(5)
    assert not first.is_alive()
    assert outcome[0].content_type == "application/pdf"
    assert verifier.verify(BytesIO(data), "pdf", 10_000).size_bytes == len(data)


class PdfAuthority:
    def scope(self, _context):
        return "tenant-a"

    def field(self, _context, _target):
        return BlobFieldSpec("Asset", "document", ["pdf"], True, "default")

    async def authorize(self, _context, target, action, _input):
        return target.entity == "Asset" and target.field == "document" and action in (
            "Begin", "Write", "Confirm")


@pytest.mark.asyncio
async def test_actual_pdf_upload_promotes_and_truncated_file_stays_initiated(tmp_path):
    path = str(tmp_path / "pdf.db")
    catalog = SqliteBlobCatalog(SqliteTransport(path))
    provider = FileObjectStorage(tmp_path / "objects", os.urandom(32))
    actor = RuntimeModule.new().into_context().with_object_storage(provider)
    actor.with_object_storage_observer(lambda event: None)
    service = SqliteBlobUploadService(catalog, PdfAuthority(),
                                      PypdfBlobContentVerifier(), 10_000)
    target = BlobUploadTarget("Asset", "1", "document")
    try:
        await catalog.ensure_schema()
        good = pdf_fixture()
        upload = await service.begin(actor, target, BlobUploadInput("valid.pdf", len(good)), "pdf-good")
        assert await service.write(actor, upload.upload_id, BytesIO(good)) == len(good)
        assert await service.complete(actor, upload.upload_id) == upload.reference
        async with aiosqlite.connect(path) as db:
            async with db.execute("SELECT status,content_type,size_bytes FROM teaql_blob_catalog WHERE key=?",
                                  (upload.reference.key,)) as cursor:
                assert await cursor.fetchone() == ("uploaded_unbound", "application/pdf", len(good))
        bad = good[:-12]
        rejected = await service.begin(actor, target, BlobUploadInput("broken.pdf", len(bad)),
                                       "pdf-bad")
        await service.write(actor, rejected.upload_id, BytesIO(bad))
        with pytest.raises(RuntimeError, match="BLOB_FORMAT_NOT_ALLOWED"):
            await service.complete(actor, rejected.upload_id)
        async with aiosqlite.connect(path) as db:
            async with db.execute("SELECT status FROM teaql_blob_catalog WHERE key=?",
                                  (rejected.reference.key,)) as cursor:
                assert (await cursor.fetchone())[0] == "initiated"
    finally:
        provider.close()
