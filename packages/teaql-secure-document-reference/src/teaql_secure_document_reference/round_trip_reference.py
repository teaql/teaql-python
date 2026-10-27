"""Governed tqr1 entity references compatible with the Java/Rust wire contract."""

from __future__ import annotations

import base64
import binascii
import hmac
import math
import os
import re
import struct
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from typing import Callable

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF


_SALT = b"teaql.round-trip-reference.v1"
_KEY_ID = re.compile(r"[A-Za-z0-9_-]{1,64}\Z", re.ASCII)
_BASE64URL = re.compile(r"[A-Za-z0-9_-]+\Z", re.ASCII)
_MAX_U64 = (1 << 64) - 1
_MAX_I64 = (1 << 63) - 1


class RoundTripReferenceError(ValueError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _fail(code: str = "ROUND_TRIP_REFERENCE_INVALID"):
    raise RoundTripReferenceError(code)


def _text(value: str) -> bytes:
    if not isinstance(value, str) or not value or value != value.strip():
        _fail()
    try:
        encoded = value.encode("utf-8", errors="strict")
    except UnicodeError:
        _fail()
    if len(encoded) > 4096:
        _fail()
    return encoded


def _sized(value: bytes) -> bytes:
    if len(value) > 65535:
        _fail()
    return struct.pack(">H", len(value)) + value


def _string(value: str) -> bytes:
    return _sized(_text(value))


def _u64(value: int, positive: bool = False) -> bytes:
    if type(value) is not int or value < (1 if positive else 0) or value > _MAX_U64:
        _fail()
    return struct.pack(">Q", value)


def _i64(value: int, nonnegative: bool = False) -> bytes:
    if type(value) is not int or value < (0 if nonnegative else -1 << 63) or value > _MAX_I64:
        _fail()
    return struct.pack(">q", value)


@dataclass(frozen=True)
class TrustedReferencePrincipal:
    authentication_realm: str
    subject: str
    domain_root_type: str
    domain_root_id: int

    def wire(self) -> bytes:
        return b"".join((_string(self.authentication_realm), _string(self.subject),
                         _string(self.domain_root_type), _u64(self.domain_root_id, True)))


@dataclass(frozen=True)
class ReferenceDocumentScope:
    document_id: str
    purpose: str
    aggregate_type: str
    aggregate_id: int
    aggregate_revision: int

    def validate(self) -> None:
        _text(self.document_id)
        _text(self.purpose)
        _text(self.aggregate_type)
        _u64(self.aggregate_id, True)
        _i64(self.aggregate_revision, True)


@dataclass(frozen=True)
class ReferenceIdentity:
    entity_type: str
    id: int
    version: int

    def validate(self) -> None:
        _text(self.entity_type)
        _u64(self.id, True)
        _i64(self.version, True)


@dataclass(frozen=True)
class ReferenceKey:
    key_id: str
    master_key: bytes

    def __post_init__(self) -> None:
        if not isinstance(self.key_id, str) or not _KEY_ID.fullmatch(self.key_id) or \
                not isinstance(self.master_key, bytes) or len(self.master_key) != 32:
            _fail("ROUND_TRIP_REFERENCE_CONFIGURATION_INVALID")

    def __repr__(self) -> str:
        return f"ReferenceKey(key_id={self.key_id!r}, master_key=[REDACTED])"


class StaticReferenceKeyProvider:
    def __init__(self, current_key_id: str, keys: tuple[ReferenceKey, ...]) -> None:
        if not isinstance(current_key_id, str) or not _KEY_ID.fullmatch(current_key_id):
            _fail("ROUND_TRIP_REFERENCE_CONFIGURATION_INVALID")
        retained: dict[str, ReferenceKey] = {}
        for key in keys:
            if not isinstance(key, ReferenceKey) or key.key_id in retained:
                _fail("ROUND_TRIP_REFERENCE_CONFIGURATION_INVALID")
            retained[key.key_id] = key
        if current_key_id not in retained:
            _fail("ROUND_TRIP_REFERENCE_CONFIGURATION_INVALID")
        self._keys = retained
        self._current = current_key_id

    def current_key(self) -> ReferenceKey:
        return self._keys[self._current]

    def key_by_id(self, key_id: str) -> ReferenceKey | None:
        return self._keys.get(key_id)


@dataclass(frozen=True)
class VerifiedEntityReference:
    identity: ReferenceIdentity
    key_id: str
    issued_at: datetime
    expires_at: datetime


class _Reader:
    def __init__(self, data: bytes) -> None:
        self.data = data
        self.offset = 0

    def take(self, count: int) -> bytes:
        if count < 0 or self.offset + count > len(self.data):
            _fail()
        result = self.data[self.offset:self.offset + count]
        self.offset += count
        return result

    def text(self) -> str:
        length = struct.unpack(">H", self.take(2))[0]
        try:
            result = self.take(length).decode("utf-8", errors="strict")
        except UnicodeError:
            _fail()
        _text(result)
        return result

    def u64(self) -> int:
        return struct.unpack(">Q", self.take(8))[0]

    def i64(self) -> int:
        return struct.unpack(">q", self.take(8))[0]

    def end(self) -> None:
        if self.offset != len(self.data):
            _fail()


class ContextBoundReferenceRuntime:
    def __init__(self, service: str, environment: str, keys: StaticReferenceKeyProvider,
                 authorize: Callable[[TrustedReferencePrincipal, ReferenceDocumentScope,
                                      ReferenceIdentity], None],
                 now: Callable[[], datetime] | None = None,
                 nonce: Callable[[], bytes] | None = None) -> None:
        _text(service)
        _text(environment)
        if not keys or not callable(authorize):
            _fail("ROUND_TRIP_REFERENCE_CONFIGURATION_INVALID")
        keys.current_key()
        self.service, self.environment = service, environment
        self.keys, self.authorize = keys, authorize
        self.now = now or (lambda: datetime.now(timezone.utc))
        self.nonce = nonce or (lambda: os.urandom(12))

    def _timestamp(self) -> int:
        value = self.now()
        if not isinstance(value, datetime) or value.tzinfo is None:
            _fail("ROUND_TRIP_REFERENCE_CONFIGURATION_INVALID")
        return math.floor(value.timestamp())

    def _derive(self, key: ReferenceKey, label: bytes) -> bytes:
        info = b"".join((_sized(label), _string(self.service), _string(self.environment),
                         _string(key.key_id)))
        return HKDF(algorithm=hashes.SHA256(),
                    length=32, salt=_SALT, info=info).derive(key.master_key)

    def _actor(self, key: ReferenceKey, principal: TrustedReferencePrincipal) -> bytes:
        return hmac.new(self._derive(key, b"actor-fingerprint"), principal.wire(), sha256).digest()

    def _aad(self, key: ReferenceKey, purpose: str) -> bytes:
        return b"".join(_string(value) for value in
                        ("tqr1", key.key_id, self.service, self.environment, purpose))

    def _authorize(self, principal: TrustedReferencePrincipal, scope: ReferenceDocumentScope,
                   identity: ReferenceIdentity) -> None:
        try:
            self.authorize(principal, scope, identity)
        except Exception:
            _fail("ROUND_TRIP_REFERENCE_AUTHORIZATION_REQUIRED")

    def issue(self, principal: TrustedReferencePrincipal, scope: ReferenceDocumentScope,
              identity: ReferenceIdentity, lifetime_seconds: int) -> str:
        principal.wire()
        scope.validate()
        identity.validate()
        if type(lifetime_seconds) is not int or lifetime_seconds <= 0:
            _fail()
        self._authorize(principal, scope, identity)
        key = self.keys.current_key()
        issued = self._timestamp()
        expires = issued + lifetime_seconds
        _i64(expires)
        plaintext = b"".join((self._actor(key, principal), _string(identity.entity_type),
                              _u64(identity.id), _i64(identity.version),
                              _string(scope.document_id), _string(scope.aggregate_type),
                              _u64(scope.aggregate_id), _i64(scope.aggregate_revision),
                              _i64(issued), _i64(expires)))
        nonce = self.nonce()
        if not isinstance(nonce, bytes) or len(nonce) != 12:
            _fail("ROUND_TRIP_REFERENCE_CONFIGURATION_INVALID")
        encrypted = AESGCM(self._derive(key, b"entity-reference-encryption")).encrypt(
            nonce, plaintext, self._aad(key, scope.purpose))
        body = base64.urlsafe_b64encode(nonce + encrypted).rstrip(b"=").decode("ascii")
        token = f"tqr1.{key.key_id}.{body}"
        if len(token) > 24000:
            _fail()
        return token

    def consume(self, principal: TrustedReferencePrincipal, scope: ReferenceDocumentScope,
                token: str, expected_entity_type: str) -> VerifiedEntityReference:
        principal.wire()
        scope.validate()
        _text(expected_entity_type)
        if not isinstance(token, str) or len(token) > 24000:
            _fail()
        parts = token.split(".")
        if len(parts) != 3 or parts[0] != "tqr1" or not _KEY_ID.fullmatch(parts[1]) or \
                not _BASE64URL.fullmatch(parts[2]):
            _fail()
        key = self.keys.key_by_id(parts[1])
        if key is None:
            _fail()
        try:
            envelope = base64.urlsafe_b64decode(parts[2] + "=" * (-len(parts[2]) % 4))
        except (ValueError, binascii.Error):
            _fail()
        if len(envelope) < 28 or base64.urlsafe_b64encode(envelope).rstrip(b"=").decode() != parts[2]:
            _fail()
        try:
            plaintext = AESGCM(self._derive(key, b"entity-reference-encryption")).decrypt(
                envelope[:12], envelope[12:], self._aad(key, scope.purpose))
        except InvalidTag:
            _fail()
        reader = _Reader(plaintext)
        actor = reader.take(32)
        identity = ReferenceIdentity(reader.text(), reader.u64(), reader.i64())
        document_id, aggregate_type = reader.text(), reader.text()
        aggregate_id, aggregate_revision = reader.u64(), reader.i64()
        issued, expires = reader.i64(), reader.i64()
        reader.end()
        identity.validate()
        now = self._timestamp()
        if expires <= now:
            _fail("ROUND_TRIP_REFERENCE_EXPIRED")
        if issued > now + 60:
            _fail()
        if not hmac.compare_digest(actor, self._actor(key, principal)) or \
                document_id != scope.document_id or aggregate_type != scope.aggregate_type or \
                aggregate_id != scope.aggregate_id or aggregate_revision != scope.aggregate_revision or \
                identity.entity_type != expected_entity_type:
            _fail("ROUND_TRIP_REFERENCE_SCOPE_MISMATCH")
        self._authorize(principal, scope, identity)
        try:
            issued_at = datetime.fromtimestamp(issued, timezone.utc)
            expires_at = datetime.fromtimestamp(expires, timezone.utc)
        except (OverflowError, OSError, ValueError):
            _fail()
        return VerifiedEntityReference(identity, key.key_id, issued_at, expires_at)
