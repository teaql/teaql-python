"""Passive host-selected routes for independently optional Blob parsers."""

from __future__ import annotations

from collections.abc import Mapping

from .upload_service import BlobContentVerifier, BlobVerifiedContent


class CompositeBlobContentVerifier:
    """Connect multiple parsers to the single trusted upload verifier SPI."""

    def __init__(self, routes: Mapping[str, BlobContentVerifier]):
        if not isinstance(routes, Mapping):
            raise RuntimeError("BLOB_POLICY_INVALID")
        selected = dict(routes)
        if (not 1 <= len(selected) <= 32
                or any(not isinstance(extension, str) or not 1 <= len(extension) <= 16
                       or not extension.isascii() or not extension.isalnum()
                       or extension != extension.lower() or verifier is None
                       or not callable(getattr(verifier, "verify", None))
                       for extension, verifier in selected.items())):
            raise RuntimeError("BLOB_POLICY_INVALID")
        self._routes = selected
        self.supported_extensions = frozenset(self._routes)

    def validate_ready(self) -> None:
        seen: set[int] = set()
        for verifier in self._routes.values():
            identity = id(verifier)
            if identity in seen:
                continue
            seen.add(identity)
            ready = getattr(verifier, "validate_ready", None)
            if callable(ready):
                ready()

    def verify(self, stream, extension: str, maximum_bytes: int) -> BlobVerifiedContent:
        verifier = self._routes.get(extension)
        if verifier is None:
            raise RuntimeError("BLOB_FORMAT_NOT_ALLOWED")
        return verifier.verify(stream, extension, maximum_bytes)
