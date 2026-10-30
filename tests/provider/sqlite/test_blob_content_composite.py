"""One upload verifier dispatches real optional image and media parsers."""

from hashlib import sha256
from io import BytesIO
from pathlib import Path
from shutil import which

import pytest

from teaql_blob_reference import CompositeBlobContentVerifier
from teaql_blob_reference.content_ffmpeg import FfmpegBlobContentVerifier
from teaql_blob_reference.content_pillow import PillowBlobContentVerifier


class Unreadable:
    def read(self, *_):
        raise AssertionError("unregistered route read source")


def test_real_image_and_media_share_trusted_upload_verifier():
    ffprobe, ffmpeg = which("ffprobe"), which("ffmpeg")
    if not ffprobe or not ffmpeg:
        pytest.skip("host FFmpeg tools required")
    image = PillowBlobContentVerifier()
    media = FfmpegBlobContentVerifier(ffprobe, ffmpeg)
    routes = {"jpg": image, "jpeg": image, "png": image, "mp3": media, "mp4": media}
    verifier = CompositeBlobContentVerifier(routes)
    routes.clear()
    assert verifier.supported_extensions == {"jpg", "jpeg", "png", "mp3", "mp4"}
    verifier.validate_ready()
    fixture = Path(__file__).resolve().parents[2] / "fixtures"
    for extension, path, mime in (
        ("jpg", fixture / "blob-sample.jpg", "image/jpeg"),
        ("mp3", fixture / "reference-modules" / "sample.mp3", "audio/mpeg"),
    ):
        data = path.read_bytes()
        result = verifier.verify(BytesIO(data), extension, len(data))
        assert (result.size_bytes, result.sha256, result.content_type) == (
            len(data), sha256(data).hexdigest(), mime)
    with pytest.raises(RuntimeError, match="BLOB_FORMAT_NOT_ALLOWED"):
        verifier.verify(Unreadable(), "docx", 1024)
    with pytest.raises(RuntimeError, match="BLOB_POLICY_INVALID"):
        CompositeBlobContentVerifier({"PDF": image})
