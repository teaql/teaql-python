"""Provider-neutral binary storage values. Private values have masked reprs."""
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from types import MappingProxyType
from typing import BinaryIO, Mapping, Optional
from urllib.parse import quote
import unicodedata

MAX_PUT_SIZE = 5 * 1024**3


class StorageErrorCode(str, Enum):
    INVALID_INPUT = "InvalidInput"
    NOT_CONFIGURED = "NotConfigured"
    NOT_FOUND = "NotFound"
    ACCESS_DENIED = "AccessDenied"
    CONFLICT = "Conflict"
    TIMEOUT = "Timeout"
    UNAVAILABLE = "Unavailable"
    UNSUPPORTED = "Unsupported"
    TOO_LARGE = "TooLarge"
    IO = "Io"


class StorageError(Exception):
    def __init__(self, code: StorageErrorCode):
        self.code = code
        super().__init__(f"Object storage: {code.value}")


def _header(value: str) -> str:
    if not isinstance(value, str) or not value or any(ord(c) < 32 or ord(c) > 126 for c in value):
        raise StorageError(StorageErrorCode.INVALID_INPUT)
    return value


@dataclass(frozen=True, repr=False)
class ObjectKey:
    value: str

    def __post_init__(self):
        invalid = not isinstance(self.value, str) or not self.value
        if not invalid:
            try:
                invalid = len(self.value.encode("utf-8")) > 1024
            except UnicodeEncodeError:
                invalid = True
            invalid |= any(unicodedata.category(c) == "Cc" for c in self.value)
        if invalid:
            raise StorageError(StorageErrorCode.INVALID_INPUT)

    def __repr__(self):
        return "ObjectKey[masked]"


class WriteMode(str, Enum):
    CREATE_ONLY = "create_only"
    REPLACE = "replace"


@dataclass(frozen=True, repr=False)
class PutOptions:
    size: int
    mode: WriteMode
    content_type: str = "application/octet-stream"
    metadata: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self):
        if type(self.size) is not int or self.size < 0 or not isinstance(self.mode, WriteMode):
            raise StorageError(StorageErrorCode.INVALID_INPUT)
        if self.size > MAX_PUT_SIZE:
            raise StorageError(StorageErrorCode.TOO_LARGE)
        _header(self.content_type)
        values = dict(self.metadata)
        for key, value in values.items():
            if not isinstance(key, str) or not key or not key[0].isascii() or not key[0].isalnum() \
                    or any(c not in "abcdefghijklmnopqrstuvwxyz0123456789-" for c in key):
                raise StorageError(StorageErrorCode.INVALID_INPUT)
            _header(value)
        object.__setattr__(self, "metadata", MappingProxyType(values))

    def __repr__(self):
        return f"PutOptions[size={self.size}, mode={self.mode.value}, metadata=masked]"


@dataclass(frozen=True, repr=False)
class ObjectMetadata:
    key: ObjectKey
    size: int
    content_type: Optional[str] = None
    etag: Optional[str] = None
    last_modified: Optional[datetime] = None
    custom_metadata: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self):
        if type(self.size) is not int or self.size < 0:
            raise StorageError(StorageErrorCode.UNAVAILABLE)
        object.__setattr__(self, "custom_metadata", MappingProxyType(dict(self.custom_metadata)))

    def __repr__(self):
        return f"ObjectMetadata[size={self.size}, details=masked]"


@dataclass(frozen=True, repr=False)
class ReadUrlOptions:
    lifetime: timedelta = timedelta(minutes=5)
    disposition: Optional[str] = None
    filename: Optional[str] = None

    def __post_init__(self):
        if not isinstance(self.lifetime, timedelta):
            raise StorageError(StorageErrorCode.INVALID_INPUT)
        seconds = self.lifetime.total_seconds()
        if seconds <= 0 or seconds > 604800 or not seconds.is_integer():
            raise StorageError(StorageErrorCode.INVALID_INPUT)
        if self.disposition not in (None, "inline", "attachment"):
            raise StorageError(StorageErrorCode.INVALID_INPUT)
        if self.filename is not None:
            try:
                valid_length = 0 < len(self.filename.encode("utf-8")) <= 1024
            except (AttributeError, UnicodeEncodeError):
                valid_length = False
            if (self.disposition is None or not valid_length or
                    any(c in '/\\"' or ord(c) < 32 or 127 <= ord(c) <= 159
                        for c in self.filename)):
                raise StorageError(StorageErrorCode.INVALID_INPUT)

    def content_disposition(self):
        if self.disposition is None:
            return None
        if self.filename is None:
            return self.disposition
        if all(ord(c) <= 126 for c in self.filename):
            return f'{self.disposition}; filename="{self.filename}"'
        fallback = "".join(c if ord(c) <= 126 else "_" for c in self.filename)
        return (f'{self.disposition}; filename="{fallback}"; '
                f"filename*=UTF-8''{quote(self.filename, safe='')}")

    def __repr__(self):
        return "ReadUrlOptions[details=masked]"


@dataclass(frozen=True, repr=False)
class ObjectReadUrl:
    url: str
    expires_at: datetime

    def __repr__(self):
        return "ObjectReadUrl[url=masked]"


@dataclass(repr=False)
class ObjectContent:
    metadata: ObjectMetadata
    stream: BinaryIO

    def close(self):
        self.stream.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def __repr__(self):
        return "ObjectContent[masked]"
