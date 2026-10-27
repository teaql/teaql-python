"""Real MP3/MP4 decode and SQLite/File upload promotion boundary."""

from hashlib import sha256
from io import BytesIO
from pathlib import Path
from shutil import which
from threading import Event, Thread
import os

import aiosqlite
import pytest

from teaql.core.blob_ref import BlobFieldSpec
from teaql.provider.sqlite.transport import SqliteTransport
from teaql.runtime import RuntimeModule
from teaql_blob_reference import (
    BlobUploadInput, BlobUploadTarget, FileObjectStorage, SqliteBlobCatalog,
    SqliteBlobUploadService,
)
from teaql_blob_reference.content_ffmpeg import FfmpegBlobContentVerifier


_SHARED_FIXTURE_SHA256 = {
    "mp3": "a4facfc9e36b342c3f7b2de8283ab9f4c9cf53af2dfb2f1959825aa930748d9b",
    "mp4": "5a3665235df157cb9d1cffe53501b86889849a38a5a643f0a64dbc957f4a58af",
}


def media_fixture(extension):
    # Copies of the shared reference files keep this repository's tests standalone.
    root = Path(__file__).resolve().parents[2] / "fixtures" / "reference-modules"
    data = (root / f"sample.{extension}").read_bytes()
    assert sha256(data).hexdigest() == _SHARED_FIXTURE_SHA256[extension]
    return data


@pytest.fixture
def verifier():
    ffprobe, ffmpeg = which("ffprobe"), which("ffmpeg")
    if not ffprobe or not ffmpeg:
        pytest.skip("host FFmpeg command-line tools required")
    parser = FfmpegBlobContentVerifier(ffprobe, ffmpeg)
    parser.validate_ready()
    return parser


@pytest.mark.parametrize("extension,mime", [("mp3", "audio/mpeg"), ("mp4", "video/mp4")])
def test_real_media_decode_container_and_limits(verifier, extension, mime):
    data = media_fixture(extension)
    checked = verifier.verify(BytesIO(data), extension, len(data))
    assert (checked.size_bytes, checked.sha256, checked.content_type) == (
        len(data), sha256(data).hexdigest(), mime)
    for invalid in (data[:-1], data[:-12], data[:len(data) // 2], b"", b"ID3\x04\x00\x00\x00\x00\x00\x00",
                    b"\x00\x00\x00\x20ftypisom" + b"\x00" * 24):
        with pytest.raises(RuntimeError, match="BLOB_FORMAT_NOT_ALLOWED"):
            verifier.verify(BytesIO(invalid), extension, len(data))
    with pytest.raises(RuntimeError, match="BLOB_FORMAT_NOT_ALLOWED"):
        verifier.verify(BytesIO(data), "pdf", len(data))
    with pytest.raises(RuntimeError, match="BLOB_SIZE_EXCEEDED"):
        verifier.verify(BytesIO(data), extension, len(data) - 1)
    if extension == "mp3":
        with pytest.raises(RuntimeError, match="BLOB_FORMAT_NOT_ALLOWED"):
            FfmpegBlobContentVerifier(verifier.ffprobe_path, verifier.ffmpeg_path,
                                      maximum_frames=1).verify(BytesIO(data), extension, len(data))
    else:
        with pytest.raises(RuntimeError, match="BLOB_FORMAT_NOT_ALLOWED"):
            FfmpegBlobContentVerifier(verifier.ffprobe_path, verifier.ffmpeg_path,
                                      maximum_video_pixels=1).verify(BytesIO(data), extension, len(data))


def test_concurrent_admission_releases_slot(verifier):
    entered, release = Event(), Event()
    data = media_fixture("mp3")

    class PausedInput(BytesIO):
        def read(self, size=-1):
            entered.set()
            assert release.wait(5)
            return super().read(size)

    parser = FfmpegBlobContentVerifier(verifier.ffprobe_path, verifier.ffmpeg_path,
                                       concurrent_verifications=1)
    result = []
    first = Thread(target=lambda: result.append(parser.verify(PausedInput(data), "mp3", len(data))))
    first.start()
    try:
        assert entered.wait(5)
        with pytest.raises(RuntimeError, match="BLOB_VERIFICATION_BUSY"):
            parser.verify(BytesIO(data), "mp3", len(data))
    finally:
        release.set()
        first.join(5)
    assert not first.is_alive()
    assert result[0].content_type == "audio/mpeg"


class MediaAuthority:
    def scope(self, _context):
        return "tenant-a"

    def field(self, _context, _target):
        return BlobFieldSpec("Asset", "media", ["mp3", "mp4"], True, "default")

    async def authorize(self, _context, target, action, _input):
        return target.entity == "Asset" and target.field == "media" and action in (
            "Begin", "Write", "Confirm")


@pytest.mark.asyncio
async def test_real_media_upload_promotes_and_truncated_copy_stays_initiated(tmp_path, verifier):
    database = str(tmp_path / "media.db")
    catalog = SqliteBlobCatalog(SqliteTransport(database))
    provider = FileObjectStorage(tmp_path / "objects", os.urandom(32))
    actor = RuntimeModule.new().into_context().with_object_storage(provider)
    actor.with_object_storage_observer(lambda event: None)
    service = SqliteBlobUploadService(catalog, MediaAuthority(), verifier, 100_000)
    target = BlobUploadTarget("Asset", "1", "media")
    try:
        await catalog.ensure_schema()
        for extension, mime in (("mp3", "audio/mpeg"), ("mp4", "video/mp4")):
            good = media_fixture(extension)
            upload = await service.begin(actor, target,
                                         BlobUploadInput("valid." + extension, len(good)),
                                         "media-good-" + extension)
            assert await service.write(actor, upload.upload_id, BytesIO(good)) == len(good)
            assert await service.complete(actor, upload.upload_id) == upload.reference
            async with aiosqlite.connect(database) as db:
                async with db.execute(
                        "SELECT status,content_type,size_bytes FROM teaql_blob_catalog WHERE key=?",
                        (upload.reference.key,)) as cursor:
                    assert await cursor.fetchone() == ("uploaded_unbound", mime, len(good))
            bad = good[:-12]
            rejected = await service.begin(actor, target,
                                           BlobUploadInput("broken." + extension, len(bad)),
                                           "media-bad-" + extension)
            await service.write(actor, rejected.upload_id, BytesIO(bad))
            with pytest.raises(RuntimeError, match="BLOB_FORMAT_NOT_ALLOWED"):
                await service.complete(actor, rejected.upload_id)
            async with aiosqlite.connect(database) as db:
                async with db.execute("SELECT status FROM teaql_blob_catalog WHERE key=?",
                                      (rejected.reference.key,)) as cursor:
                    assert (await cursor.fetchone())[0] == "initiated"
    finally:
        provider.close()
