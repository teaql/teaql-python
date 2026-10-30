"""Optional bounded PDF structure/content parser for the Blob upload verifier SPI."""

from __future__ import annotations

from hashlib import sha256
from io import BytesIO
from math import isfinite
from threading import BoundedSemaphore

from .upload_service import BlobVerifiedContent


class PypdfBlobContentVerifier:
    """Host-selected PDF parser; construction does no parser I/O or imports."""

    supported_extensions = frozenset(("pdf",))

    def __init__(self, maximum_input_bytes: int = 32 * 1024 * 1024,
                 maximum_decoded_bytes: int = 64 * 1024 * 1024,
                 maximum_pages: int = 1000, concurrent_verifications: int = 2):
        if (type(maximum_input_bytes) is not int or not 1 <= maximum_input_bytes <= 100 * 1024 * 1024
                or type(maximum_decoded_bytes) is not int
                or not 1 <= maximum_decoded_bytes <= 64 * 1024 * 1024
                or type(maximum_pages) is not int or not 1 <= maximum_pages <= 1000
                or type(concurrent_verifications) is not int
                or not 1 <= concurrent_verifications <= 32):
            raise RuntimeError("BLOB_POLICY_INVALID")
        self.maximum_input_bytes = maximum_input_bytes
        self.maximum_decoded_bytes = maximum_decoded_bytes
        self.maximum_pages = maximum_pages
        self._permits = BoundedSemaphore(concurrent_verifications)

    def validate_ready(self) -> None:
        try:
            from pypdf import PdfReader  # noqa: F401
        except ImportError:
            raise RuntimeError("BLOB_CAPABILITY_MISSING") from None

    def verify(self, stream, extension: str, maximum_bytes: int) -> BlobVerifiedContent:
        if extension != "pdf":
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
            data = b"".join(chunks)
            if not data.startswith(b"%PDF-") or not data.rstrip(b" \t\r\n\f").endswith(b"%%EOF"):
                raise RuntimeError("BLOB_FORMAT_NOT_ALLOWED")
            try:
                from pypdf import PdfReader
            except ImportError:
                raise RuntimeError("BLOB_CAPABILITY_MISSING") from None
            try:
                reader = PdfReader(BytesIO(data), strict=True, root_object_recovery_limit=256)
                if reader.is_encrypted or not 1 <= len(reader.pages) <= self.maximum_pages:
                    raise ValueError("invalid PDF page set")
                decoded = 0
                for page in reader.pages:
                    width = float(page.mediabox.width)
                    height = float(page.mediabox.height)
                    if (not isfinite(width) or not isfinite(height)
                            or not 0 < width <= 14400 or not 0 < height <= 14400):
                        raise ValueError("invalid PDF media box")
                    contents = page.get_contents()
                    if contents is not None:
                        payload = contents.get_data()
                        decoded += len(payload)
                        if decoded > self.maximum_decoded_bytes:
                            raise ValueError("PDF decoded content limit")
                        _ = contents.operations  # Parse content operators, not only the header.
            except Exception:
                raise RuntimeError("BLOB_FORMAT_NOT_ALLOWED") from None
            return BlobVerifiedContent(size, digest.hexdigest(), "application/pdf")
        finally:
            self._permits.release()
