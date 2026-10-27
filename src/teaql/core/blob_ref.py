"""Stable Blob catalog values shared with the Java/Rust reference contract."""

from __future__ import annotations

import re

_KEY = re.compile(r"blob_[A-Za-z0-9_-]{1,123}", re.ASCII)
_MIME = {
    "jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png",
    "mp4": "video/mp4", "mp3": "audio/mpeg",
    "doc": "application/msword",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "xls": "application/vnd.ms-excel",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "pdf": "application/pdf",
}


class BlobRef:
    """A Key identifies catalog state; it never conveys read or bind authority."""

    __slots__ = ("_key",)

    def __init__(self, key: str) -> None:
        if not isinstance(key, str) or _KEY.fullmatch(key) is None:
            raise ValueError("BLOB_REFERENCE_INVALID")
        object.__setattr__(self, "_key", key)

    def __setattr__(self, name: str, value: object) -> None:
        raise AttributeError("BlobRef is immutable")

    @property
    def key(self) -> str:
        return self._key

    @classmethod
    def from_json(cls, value: object) -> "BlobRef":
        if not isinstance(value, str):
            raise ValueError("BLOB_REFERENCE_INVALID")
        return cls(value)

    @classmethod
    def from_sql(cls, value: object) -> "BlobRef":
        if not isinstance(value, str):
            raise ValueError("BLOB_REFERENCE_INVALID")
        return cls(value)

    def to_sql(self) -> str:
        return self._key

    def __repr__(self) -> str:
        return "BlobRef[masked]"

    __str__ = __repr__

    def __eq__(self, other: object) -> bool:
        return isinstance(other, BlobRef) and self._key == other._key

    def __hash__(self) -> int:
        return hash(self._key)


class BlobFieldSpec:
    """Trusted model restriction; server-selected policy may narrow formats."""

    __slots__ = ("entity", "field", "nullable", "policy_profile", "allowed_extensions",
                 "allowed_content_types")
    CAPABILITY = "blob.v1"

    def __init__(self, entity: str, field: str, extensions: list[str] | tuple[str, ...],
                 nullable: bool, policy_profile: str) -> None:
        if (not isinstance(entity, str) or not entity or entity != entity.strip()
                or not isinstance(field, str) or not field or field != field.strip()
                or not isinstance(policy_profile, str) or not policy_profile
                or policy_profile != policy_profile.strip()):
            raise ValueError("BLOB_POLICY_INVALID")
        try:
            normalized = tuple(sorted(set(extensions)))
        except (TypeError, ValueError):
            raise ValueError("BLOB_FORMAT_NOT_ALLOWED") from None
        if not normalized or any(extension not in _MIME for extension in normalized):
            raise ValueError("BLOB_FORMAT_NOT_ALLOWED")
        object.__setattr__(self, "entity", entity)
        object.__setattr__(self, "field", field)
        object.__setattr__(self, "nullable", nullable)
        object.__setattr__(self, "policy_profile", policy_profile)
        object.__setattr__(self, "allowed_extensions", normalized)
        object.__setattr__(self, "allowed_content_types",
                           tuple(sorted({_MIME[extension] for extension in normalized})))

    def __setattr__(self, name: str, value: object) -> None:
        raise AttributeError("BlobFieldSpec is immutable")

    @property
    def protocol_version(self) -> str:
        return self.CAPABILITY

    @property
    def max_files(self) -> int:
        return 1
