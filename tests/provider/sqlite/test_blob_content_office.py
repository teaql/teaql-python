"""Actual DOCX/XLSX parsers and SQLite/File upload promotion boundary."""

from hashlib import sha256
from io import BytesIO
from threading import Event, Thread
from zipfile import ZIP_DEFLATED, ZipFile
import os

import aiosqlite
import pytest

docx = pytest.importorskip("docx")
openpyxl = pytest.importorskip("openpyxl")

from teaql.core.blob_ref import BlobFieldSpec
from teaql.provider.sqlite.transport import SqliteTransport
from teaql.runtime import RuntimeModule
from teaql_blob_reference import (
    BlobUploadInput, BlobUploadTarget, FileObjectStorage, SqliteBlobCatalog,
    SqliteBlobUploadService,
)
from teaql_blob_reference.content_office import OfficeBlobContentVerifier


def office_fixture(extension):
    output = BytesIO()
    if extension == "docx":
        document = docx.Document()
        document.add_paragraph("TeaQL Office parser")
        document.save(output)
    else:
        workbook = openpyxl.Workbook()
        workbook.active["A1"] = "TeaQL Office parser"
        workbook.active["B1"] = 42
        workbook.save(output)
    return output.getvalue()


def replace_part(data, name, replacement):
    output = BytesIO()
    with ZipFile(BytesIO(data)) as source, ZipFile(output, "w", ZIP_DEFLATED) as target:
        for part in source.infolist():
            target.writestr(part.filename, replacement if part.filename == name
                            else source.read(part.filename))
    return output.getvalue()


@pytest.mark.parametrize("extension,mime", [
    ("docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
    ("xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
])
def test_real_office_structure_content_and_limits(extension, mime):
    data = office_fixture(extension)
    verifier = OfficeBlobContentVerifier()
    verifier.validate_ready()
    checked = verifier.verify(BytesIO(data), extension, len(data))
    assert (checked.size_bytes, checked.sha256, checked.content_type) == (
        len(data), sha256(data).hexdigest(), mime)
    main = "word/document.xml" if extension == "docx" else "xl/workbook.xml"
    wrong_type = replace_part(data, "[Content_Types].xml",
                              b"<Types xmlns='http://schemas.openxmlformats.org/package/2006/content-types' />")
    wrong_relationship = replace_part(data, "_rels/.rels",
                                      b"<Relationships xmlns='http://schemas.openxmlformats.org/package/2006/relationships' />")
    for invalid in (data[:-12], b"PK\x03\x04not Office", b"",
                    replace_part(data, main, b"<broken>"), wrong_type,
                    wrong_relationship):
        with pytest.raises(RuntimeError, match="BLOB_FORMAT_NOT_ALLOWED"):
            verifier.verify(BytesIO(invalid), extension, len(data) + 10000)
    with pytest.raises(RuntimeError, match="BLOB_FORMAT_NOT_ALLOWED"):
        verifier.verify(BytesIO(data), "pdf", len(data))
    with pytest.raises(RuntimeError, match="BLOB_SIZE_EXCEEDED"):
        verifier.verify(BytesIO(data), extension, len(data) - 1)
    with pytest.raises(RuntimeError, match="BLOB_FORMAT_NOT_ALLOWED"):
        OfficeBlobContentVerifier(maximum_decoded_bytes=1024).verify(
            BytesIO(data), extension, len(data))
    with pytest.raises(RuntimeError, match="BLOB_FORMAT_NOT_ALLOWED"):
        OfficeBlobContentVerifier(maximum_elements=1).verify(
            BytesIO(data), extension, len(data))


def test_concurrent_admission_releases_slot():
    entered, release = Event(), Event()
    data = office_fixture("xlsx")

    class PausedInput(BytesIO):
        def read(self, size=-1):
            entered.set()
            assert release.wait(5)
            return super().read(size)

    verifier = OfficeBlobContentVerifier(concurrent_verifications=1)
    outcome = []
    first = Thread(target=lambda: outcome.append(verifier.verify(PausedInput(data), "xlsx", 100_000)))
    first.start()
    try:
        assert entered.wait(5)
        with pytest.raises(RuntimeError, match="BLOB_VERIFICATION_BUSY"):
            verifier.verify(BytesIO(data), "xlsx", 100_000)
    finally:
        release.set()
        first.join(5)
    assert not first.is_alive()
    assert outcome[0].content_type.endswith("sheet")
    assert verifier.verify(BytesIO(data), "xlsx", 100_000).size_bytes == len(data)


class OfficeAuthority:
    def scope(self, _context):
        return "tenant-a"

    def field(self, _context, _target):
        return BlobFieldSpec("Asset", "document", ["docx", "xlsx"], True, "default")

    async def authorize(self, _context, target, action, _input):
        return target.entity == "Asset" and target.field == "document" and action in (
            "Begin", "Write", "Confirm")


@pytest.mark.asyncio
async def test_real_office_upload_promotes_both_formats_and_rejects_broken_copy(tmp_path):
    path = str(tmp_path / "office.db")
    catalog = SqliteBlobCatalog(SqliteTransport(path))
    provider = FileObjectStorage(tmp_path / "objects", os.urandom(32))
    actor = RuntimeModule.new().into_context().with_object_storage(provider)
    actor.with_object_storage_observer(lambda event: None)
    service = SqliteBlobUploadService(catalog, OfficeAuthority(),
                                      OfficeBlobContentVerifier(), 100_000)
    target = BlobUploadTarget("Asset", "1", "document")
    try:
        await catalog.ensure_schema()
        for extension in ("docx", "xlsx"):
            good = office_fixture(extension)
            upload = await service.begin(actor, target,
                                         BlobUploadInput("valid." + extension, len(good)),
                                         "office-good-" + extension)
            assert await service.write(actor, upload.upload_id, BytesIO(good)) == len(good)
            assert await service.complete(actor, upload.upload_id) == upload.reference
            async with aiosqlite.connect(path) as db:
                async with db.execute(
                        "SELECT status,content_type,size_bytes FROM teaql_blob_catalog WHERE key=?",
                        (upload.reference.key,)) as cursor:
                    status, content_type, size = await cursor.fetchone()
            assert status == "uploaded_unbound" and size == len(good)
            assert content_type == OfficeBlobContentVerifier().verify(
                BytesIO(good), extension, len(good)).content_type
        broken = office_fixture("xlsx")[:-12]
        rejected = await service.begin(actor, target, BlobUploadInput("broken.xlsx", len(broken)),
                                       "office-bad")
        await service.write(actor, rejected.upload_id, BytesIO(broken))
        with pytest.raises(RuntimeError, match="BLOB_FORMAT_NOT_ALLOWED"):
            await service.complete(actor, rejected.upload_id)
        async with aiosqlite.connect(path) as db:
            async with db.execute("SELECT status FROM teaql_blob_catalog WHERE key=?",
                                  (rejected.reference.key,)) as cursor:
                assert (await cursor.fetchone())[0] == "initiated"
    finally:
        provider.close()
