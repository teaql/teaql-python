"""Real shared JPEG/PNG decoder and SQLite/File upload boundary checks."""

from hashlib import sha256
from io import BytesIO
from pathlib import Path
from threading import Event, Thread
import os

import aiosqlite
import pytest

pytest.importorskip("PIL")

from teaql.core.blob_ref import BlobFieldSpec
from teaql.runtime import RuntimeModule
from teaql.provider.sqlite.transport import SqliteTransport
from teaql_blob_reference import (
    BlobUploadInput, BlobUploadTarget, FileObjectStorage, SqliteBlobCatalog,
    SqliteBlobUploadService,
)
from teaql_blob_reference.content_pillow import PillowBlobContentVerifier


def fixture(extension):
    return (Path(__file__).parents[2] / "fixtures" / f"blob-sample.{extension}").read_bytes()


def test_real_images_and_malformed_or_bounded_input():
    verifier = PillowBlobContentVerifier()
    verifier.validate_ready()
    for extension in ("jpg", "png"):
        data = fixture(extension)
        checked = verifier.verify(BytesIO(data), extension, 10_000)
        assert checked.size_bytes == len(data)
        assert checked.sha256 == sha256(data).hexdigest()
        assert checked.content_type == ("image/jpeg" if extension == "jpg" else "image/png")
        wrong = "png" if extension == "jpg" else "jpg"
        with pytest.raises(RuntimeError, match="BLOB_FORMAT_NOT_ALLOWED"):
            verifier.verify(BytesIO(data), wrong, 10_000)
        with pytest.raises(RuntimeError, match="BLOB_FORMAT_NOT_ALLOWED"):
            verifier.verify(BytesIO(data[:-12]), extension, 10_000)
        with pytest.raises(RuntimeError, match="BLOB_SIZE_EXCEEDED"):
            verifier.verify(BytesIO(data), extension, len(data) - 1)
    corrupt = bytearray(fixture("png"))
    corrupt[-25] ^= 1
    with pytest.raises(RuntimeError, match="BLOB_FORMAT_NOT_ALLOWED"):
        verifier.verify(BytesIO(corrupt), "png", 10_000)
    with pytest.raises(RuntimeError, match="BLOB_FORMAT_NOT_ALLOWED"):
        verifier.verify(BytesIO(b"not an image"), "jpg", 10_000)
    with pytest.raises(RuntimeError, match="BLOB_FORMAT_NOT_ALLOWED"):
        verifier.verify(BytesIO(b""), "png", 10_000)
    limited = PillowBlobContentVerifier(maximum_input_bytes=10_000,
                                         maximum_decoded_bytes=4)
    with pytest.raises(RuntimeError, match="BLOB_FORMAT_NOT_ALLOWED"):
        limited.verify(BytesIO(fixture("png")), "png", 10_000)


def test_concurrent_admission_releases_slot_after_decode():
    entered, release = Event(), Event()
    data = fixture("jpg")

    class PausedInput(BytesIO):
        def read(self, size=-1):
            entered.set()
            assert release.wait(5)
            return super().read(size)

    verifier = PillowBlobContentVerifier(concurrent_verifications=1)
    outcome = []
    first = Thread(target=lambda: outcome.append(verifier.verify(PausedInput(data), "jpg", 10_000)))
    first.start()
    try:
        assert entered.wait(5)
        with pytest.raises(RuntimeError, match="BLOB_VERIFICATION_BUSY"):
            verifier.verify(BytesIO(data), "jpg", 10_000)
    finally:
        release.set()
        first.join(5)
    assert not first.is_alive()
    assert outcome[0].content_type == "image/jpeg"
    assert verifier.verify(BytesIO(data), "jpg", 10_000).size_bytes == len(data)


class ImageAuthority:
    def scope(self, _context):
        return "tenant-a"

    def field(self, _context, _target):
        return BlobFieldSpec("Asset", "image", ["jpg"], True, "default")

    async def authorize(self, _context, target, action, _input):
        return target.entity == "Asset" and target.field == "image" and action in (
            "Begin", "Write", "Confirm")


@pytest.mark.asyncio
async def test_actual_jpeg_upload_promotes_and_truncated_file_stays_initiated(tmp_path):
    path = str(tmp_path / "image.db")
    catalog = SqliteBlobCatalog(SqliteTransport(path))
    provider = FileObjectStorage(tmp_path / "objects", os.urandom(32))
    actor = RuntimeModule.new().into_context().with_object_storage(provider)
    actor.with_object_storage_observer(lambda event: None)
    service = SqliteBlobUploadService(catalog, ImageAuthority(),
                                      PillowBlobContentVerifier(), 10_000)
    target = BlobUploadTarget("Asset", "1", "image")
    try:
        await catalog.ensure_schema()
        good = fixture("jpg")
        upload = await service.begin(actor, target, BlobUploadInput("image.jpg", len(good)), "image-good")
        assert await service.write(actor, upload.upload_id, BytesIO(good)) == len(good)
        assert await service.complete(actor, upload.upload_id) == upload.reference
        async with aiosqlite.connect(path) as db:
            async with db.execute("SELECT status,content_type,size_bytes FROM teaql_blob_catalog WHERE key=?",
                                  (upload.reference.key,)) as cursor:
                assert await cursor.fetchone() == ("uploaded_unbound", "image/jpeg", len(good))
        bad = good[:-12]
        rejected = await service.begin(actor, target, BlobUploadInput("broken.jpg", len(bad)),
                                       "image-bad")
        await service.write(actor, rejected.upload_id, BytesIO(bad))
        with pytest.raises(RuntimeError, match="BLOB_FORMAT_NOT_ALLOWED"):
            await service.complete(actor, rejected.upload_id)
        async with aiosqlite.connect(path) as db:
            async with db.execute("SELECT status FROM teaql_blob_catalog WHERE key=?",
                                  (rejected.reference.key,)) as cursor:
                assert (await cursor.fetchone())[0] == "initiated"
    finally:
        provider.close()
