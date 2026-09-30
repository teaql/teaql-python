"""Opaque boundary references for internal entity identity tuples."""

from __future__ import annotations

import base64
import os
import struct
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from typing import Callable, Mapping, Protocol

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


ENTITY_REFERENCE_AAD = b"teaql.entity-reference.v1"
ENTITY_REFERENCE_PREFIX = "tqr1."
UNSAFE_RAW_REFERENCE_PREFIX = "tqr0."
UNSAFE_RAW_ENTITY_REFERENCES_ENVIRONMENT = "TEAQL_UNSAFE_RAW_ENTITY_REFERENCES"
UNSAFE_RAW_ENTITY_REFERENCES_ACKNOWLEDGEMENT = (
    "I_UNDERSTAND_RAW_ENTITY_IDS_ARE_VISIBLE_FOR_LOCAL_DEVELOPMENT_ONLY"
)


class EntityReferenceTokenError(ValueError):
    """Stable public failure without cryptographic-oracle details."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class EntityReferenceClaims:
    entity_type: str
    id: int
    version: int
    issued_at: datetime
    expires_at: datetime
    purpose: str
    key_version: int = 0


class EntityReferenceCodec(Protocol):
    def encode_entity_reference(
        self,
        entity_type: str,
        entity_id: int,
        version: int,
        purpose: str,
        lifetime: timedelta,
    ) -> str: ...

    def decode_entity_reference(
        self, token: str, expected_entity_type: str, purpose: str
    ) -> EntityReferenceClaims: ...


def _invalid() -> EntityReferenceTokenError:
    return EntityReferenceTokenError("ENTITY_REFERENCE_INVALID")


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _write_text(value: str) -> bytes:
    encoded = value.encode("utf-8")
    if len(encoded) > 0xFFFF:
        raise ValueError("entity reference text exceeds 65535 bytes")
    return struct.pack(">H", len(encoded)) + encoded


def _read_text(payload: bytes, offset: int) -> tuple[str, int]:
    if offset + 2 > len(payload):
        raise _invalid()
    length = struct.unpack_from(">H", payload, offset)[0]
    offset += 2
    if offset + length > len(payload):
        raise _invalid()
    try:
        return payload[offset : offset + length].decode("utf-8"), offset + length
    except UnicodeDecodeError as error:
        raise _invalid() from error


def encode_claims(claims: EntityReferenceClaims) -> bytes:
    return b"".join(
        (
            _write_text(claims.entity_type),
            struct.pack(
                ">Qqqq",
                claims.id,
                claims.version,
                int(claims.issued_at.timestamp()),
                int(claims.expires_at.timestamp()),
            ),
            _write_text(claims.purpose),
        )
    )


def decode_claims(payload: bytes) -> EntityReferenceClaims:
    entity_type, offset = _read_text(payload, 0)
    if offset + 32 > len(payload):
        raise _invalid()
    entity_id, version, issued_at, expires_at = struct.unpack_from(">Qqqq", payload, offset)
    purpose, offset = _read_text(payload, offset + 32)
    if offset != len(payload) or not entity_type or entity_id == 0:
        raise _invalid()
    try:
        return EntityReferenceClaims(
            entity_type=entity_type,
            id=entity_id,
            version=version,
            issued_at=datetime.fromtimestamp(issued_at, timezone.utc),
            expires_at=datetime.fromtimestamp(expires_at, timezone.utc),
            purpose=purpose,
        )
    except (OverflowError, OSError, ValueError) as error:
        raise _invalid() from error


def _base64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _base64url_decode(value: str) -> bytes:
    try:
        return base64.b64decode(
            value + "=" * (-len(value) % 4), altchars=b"-_", validate=True
        )
    except (ValueError, base64.binascii.Error) as error:
        raise _invalid() from error


def validate_reference_request(
    entity_type: str, entity_id: int, version: int, purpose: str, lifetime: timedelta
) -> None:
    if (
        not isinstance(entity_type, str)
        or not entity_type.strip()
        or not isinstance(entity_id, int)
        or isinstance(entity_id, bool)
        or entity_id <= 0
        or entity_id > 0xFFFFFFFFFFFFFFFF
        or not isinstance(version, int)
        or isinstance(version, bool)
        or version < -(1 << 63)
        or version >= (1 << 63)
        or not isinstance(purpose, str)
        or not isinstance(lifetime, timedelta)
        or lifetime <= timedelta(0)
    ):
        raise _invalid()


def validate_decoded_reference(
    claims: EntityReferenceClaims,
    now: datetime,
    expected_entity_type: str,
    purpose: str,
) -> None:
    if (
        claims.expires_at <= now
        or claims.issued_at > now + timedelta(minutes=1)
        or claims.entity_type != expected_entity_type
        or claims.purpose != purpose
    ):
        raise _invalid()


class AeadEntityReferenceCodec:
    """Portable tuple-codec v1 using AES-256-GCM and a rotating key ring."""

    def __init__(self, active_key_version: int, keys: Mapping[int, bytes]):
        copied = {version: bytes(key) for version, key in keys.items()}
        if active_key_version not in copied or len(copied[active_key_version]) != 32:
            raise ValueError("active entity reference key must contain 32 bytes")
        for version, key in copied.items():
            if version < 0 or version > 0xFFFFFFFF or len(key) != 32:
                raise ValueError(f"entity reference key {version} must contain 32 bytes")
        self._active_key_version = active_key_version
        self._keys = copied
        self._clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc)
        self._nonce_source: Callable[[], bytes] = lambda: os.urandom(12)

    def with_clock(self, clock: Callable[[], datetime]) -> "AeadEntityReferenceCodec":
        self._clock = clock
        return self

    def with_nonce_source(
        self, nonce_source: Callable[[], bytes]
    ) -> "AeadEntityReferenceCodec":
        self._nonce_source = nonce_source
        return self

    def encode_entity_reference(
        self,
        entity_type: str,
        entity_id: int,
        version: int,
        purpose: str,
        lifetime: timedelta,
    ) -> str:
        validate_reference_request(entity_type, entity_id, version, purpose, lifetime)
        now = _utc(self._clock())
        nonce = bytes(self._nonce_source())
        if len(nonce) != 12:
            raise ValueError("entity reference nonce must contain 12 bytes")
        claims = EntityReferenceClaims(
            entity_type, entity_id, version, now, now + lifetime, purpose
        )
        encrypted = AESGCM(self._keys[self._active_key_version]).encrypt(
            nonce, encode_claims(claims), ENTITY_REFERENCE_AAD
        )
        envelope = struct.pack(">I", self._active_key_version) + nonce + encrypted
        return ENTITY_REFERENCE_PREFIX + _base64url_encode(envelope)

    def decode_entity_reference(
        self, token: str, expected_entity_type: str, purpose: str
    ) -> EntityReferenceClaims:
        try:
            if not isinstance(token, str) or not token.startswith(ENTITY_REFERENCE_PREFIX):
                raise _invalid()
            envelope = _base64url_decode(token[len(ENTITY_REFERENCE_PREFIX) :])
            if len(envelope) < 4 + 12 + 16:
                raise _invalid()
            key_version = struct.unpack_from(">I", envelope)[0]
            key = self._keys.get(key_version)
            if key is None:
                raise _invalid()
            plaintext = AESGCM(key).decrypt(
                envelope[4:16], envelope[16:], ENTITY_REFERENCE_AAD
            )
            claims = replace(decode_claims(plaintext), key_version=key_version)
            validate_decoded_reference(
                claims, _utc(self._clock()), expected_entity_type, purpose
            )
            return claims
        except EntityReferenceTokenError:
            raise
        except (InvalidTag, ValueError, TypeError, struct.error) as error:
            raise _invalid() from error


def raw_entity_references_enabled() -> bool:
    return os.environ.get(UNSAFE_RAW_ENTITY_REFERENCES_ENVIRONMENT) == (
        UNSAFE_RAW_ENTITY_REFERENCES_ACKNOWLEDGEMENT
    )


def encode_raw_entity_reference(claims: EntityReferenceClaims) -> str:
    return UNSAFE_RAW_REFERENCE_PREFIX + _base64url_encode(encode_claims(claims))


def decode_raw_entity_reference(token: str) -> EntityReferenceClaims:
    if not token.startswith(UNSAFE_RAW_REFERENCE_PREFIX):
        raise EntityReferenceTokenError("ENTITY_REFERENCE_CODEC_REQUIRED")
    return decode_claims(_base64url_decode(token[len(UNSAFE_RAW_REFERENCE_PREFIX) :]))
