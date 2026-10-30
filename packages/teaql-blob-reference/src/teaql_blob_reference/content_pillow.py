"""Optional bounded JPEG/PNG parser for the trusted Blob upload verifier SPI."""

from __future__ import annotations

from hashlib import sha256
from io import BytesIO
from threading import BoundedSemaphore
from warnings import catch_warnings, simplefilter
import struct
import zlib

from .upload_service import BlobVerifiedContent


_MIME = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png"}
_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def _complete_png(data: bytes) -> bool:
    if len(data) < 45 or not data.startswith(_PNG_SIGNATURE):
        return False
    offset = 8
    count = 0
    image_data = False
    while offset <= len(data) - 12:
        length = struct.unpack_from(">I", data, offset)[0]
        if length > len(data) - offset - 12:
            return False
        kind = data[offset + 4:offset + 8]
        if len(kind) != 4 or not all(65 <= c <= 90 or 97 <= c <= 122 for c in kind):
            return False
        if count == 0 and (kind != b"IHDR" or length != 13):
            return False
        expected = struct.unpack_from(">I", data, offset + 8 + length)[0]
        if zlib.crc32(data[offset + 4:offset + 8 + length]) != expected:
            return False
        offset += length + 12
        count += 1
        if kind == b"IDAT":
            image_data = True
        if kind == b"IEND":
            return length == 0 and image_data and offset == len(data)
    return False


class PillowBlobContentVerifier:
    """Passive optional adapter; no Pillow import or parser work at construction."""

    supported_extensions = frozenset(_MIME)

    def __init__(self, maximum_input_bytes: int = 32 * 1024 * 1024,
                 maximum_decoded_bytes: int = 100 * 1024 * 1024,
                 concurrent_verifications: int = 2):
        if (type(maximum_input_bytes) is not int or not 1 <= maximum_input_bytes <= 100 * 1024 * 1024
                or type(maximum_decoded_bytes) is not int
                or not 4 <= maximum_decoded_bytes <= 512 * 1024 * 1024
                or type(concurrent_verifications) is not int
                or not 1 <= concurrent_verifications <= 32):
            raise RuntimeError("BLOB_POLICY_INVALID")
        self.maximum_input_bytes = maximum_input_bytes
        self.maximum_decoded_bytes = maximum_decoded_bytes
        self._permits = BoundedSemaphore(concurrent_verifications)

    def validate_ready(self) -> None:
        try:
            from PIL import ImageFile, features
            if ImageFile.LOAD_TRUNCATED_IMAGES:
                raise RuntimeError("BLOB_CAPABILITY_MISSING")
            if not features.check("jpg") or not features.check("zlib"):
                raise RuntimeError("BLOB_CAPABILITY_MISSING")
        except Exception:
            raise RuntimeError("BLOB_CAPABILITY_MISSING") from None

    def verify(self, stream, extension: str, maximum_bytes: int) -> BlobVerifiedContent:
        if extension not in _MIME:
            raise RuntimeError("BLOB_FORMAT_NOT_ALLOWED")
        if type(maximum_bytes) is not int or maximum_bytes < 1:
            raise RuntimeError("BLOB_POLICY_INVALID")
        if not self._permits.acquire(blocking=False):
            raise RuntimeError("BLOB_VERIFICATION_BUSY")
        try:
            maximum = min(maximum_bytes, self.maximum_input_bytes)
            chunks = []
            size = 0
            digest = sha256()
            while True:
                try:
                    block = stream.read(65536)
                except Exception:
                    raise RuntimeError("BLOB_STORE_FAILED") from None
                if not isinstance(block, bytes):
                    raise RuntimeError("BLOB_STORE_FAILED")
                if not block:
                    break
                if len(block) > maximum - size:
                    raise RuntimeError("BLOB_SIZE_EXCEEDED")
                chunks.append(block)
                digest.update(block)
                size += len(block)
            if not size:
                raise RuntimeError("BLOB_FORMAT_NOT_ALLOWED")
            data = b"".join(chunks)
            if extension == "png":
                complete = _complete_png(data)
            else:
                complete = len(data) >= 4 and data.startswith(b"\xff\xd8") and data.endswith(b"\xff\xd9")
            if not complete:
                raise RuntimeError("BLOB_FORMAT_NOT_ALLOWED")
            try:
                from PIL import Image, ImageFile
                if ImageFile.LOAD_TRUNCATED_IMAGES:
                    raise RuntimeError("BLOB_CAPABILITY_MISSING")
                expected = "PNG" if extension == "png" else "JPEG"
                with catch_warnings():
                    simplefilter("error", Image.DecompressionBombWarning)
                    with Image.open(BytesIO(data), formats=[expected]) as image:
                        width, height = image.size
                        if (image.format != expected or width < 1 or height < 1
                                or width * height > self.maximum_decoded_bytes // 4
                                or getattr(image, "n_frames", 1) != 1):
                            raise RuntimeError("BLOB_FORMAT_NOT_ALLOWED")
                        image.load()  # Header detection alone is insufficient.
            except RuntimeError as error:
                if str(error) == "BLOB_CAPABILITY_MISSING":
                    raise
                raise RuntimeError("BLOB_FORMAT_NOT_ALLOWED") from None
            except ImportError:
                raise RuntimeError("BLOB_CAPABILITY_MISSING") from None
            except Exception:
                raise RuntimeError("BLOB_FORMAT_NOT_ALLOWED") from None
            return BlobVerifiedContent(size, digest.hexdigest(), _MIME[extension])
        finally:
            self._permits.release()
