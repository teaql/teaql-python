"""Versioned encrypted document snapshots and document-bound Blob selection."""

from __future__ import annotations

import base64
import binascii
import hmac
import re
import struct
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Generic, Protocol, TypeVar

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from teaql.runtime.capability import install_runtime_capability
from teaql.runtime.view_preparation import PreparedSecureDocument, ViewPreparationError

from .round_trip_reference import (
    ContextBoundReferenceRuntime, ReferenceDocumentScope, ReferenceIdentity,
    ReferenceKey, RoundTripReferenceError, TrustedReferencePrincipal,
    _BASE64URL, _KEY_ID, _i64, _u64,
)

_MUTATIONS = {"UPDATE": 1, "CREATE_CHILD": 2, "REMOVE_CHILD": 3}
_REVERSE_MUTATIONS = {value: key for key, value in _MUTATIONS.items()}
_MAX_I64 = (1 << 63) - 1
_BLOB_KEY = re.compile(r"blob_[A-Za-z0-9_-]{1,123}\Z", re.ASCII)


def _fail(code="ROUND_TRIP_REFERENCE_INVALID"):
    raise RoundTripReferenceError(code)


def _text(value: str) -> bytes:
    if not isinstance(value, str) or not value.strip():
        _fail()
    try:
        encoded = value.encode("utf-8", errors="strict")
    except UnicodeError:
        _fail()
    if len(encoded) > 16384:
        _fail()
    return encoded


def _str(value: str) -> bytes:
    data = _text(value)
    return struct.pack(">I", len(data)) + data


def _count(value: int, maximum: int) -> bytes:
    if type(value) is not int or value < 0 or value > maximum:
        _fail("DOCUMENT_PROJECTION_VIOLATION")
    return struct.pack(">I", value)


def _flag(value: bool) -> bytes:
    if type(value) is not bool:
        _fail()
    return bytes((int(value),))


def _blob_key(value: str) -> str:
    if not isinstance(value, str) or not _BLOB_KEY.fullmatch(value):
        _fail()
    return value


def _scope(scope: ReferenceDocumentScope) -> bytes:
    scope.validate()
    return b"".join((_str(scope.document_id), _str(scope.purpose), _str(scope.aggregate_type),
                     _u64(scope.aggregate_id), _i64(scope.aggregate_revision)))


def _identity(identity: ReferenceIdentity) -> bytes:
    identity.validate()
    return b"".join((_str(identity.entity_type), _u64(identity.id), _i64(identity.version)))


def _set(values: frozenset[str], maximum: int) -> bytes:
    if not isinstance(values, frozenset):
        _fail("DOCUMENT_PROJECTION_VIOLATION")
    return _count(len(values), maximum) + b"".join(_str(value) for value in sorted(values, key=lambda x: x.encode("utf-8")))


def _mutations(values: frozenset[str]) -> bytes:
    if not isinstance(values, frozenset) or any(value not in _MUTATIONS for value in values):
        _fail("DOCUMENT_PROJECTION_VIOLATION")
    return _count(len(values), 3) + bytes(_MUTATIONS[value] for value in sorted(values, key=_MUTATIONS.get))


@dataclass(frozen=True)
class DocumentEntitySnapshot:
    row_key: str
    identity: ReferenceIdentity
    loaded_fields: frozenset[str]
    writable_fields: frozenset[str]
    allowed_mutations: frozenset[str]


@dataclass(frozen=True)
class DocumentRelationSnapshot:
    name: str
    row_keys: tuple[str, ...]
    completeness: str
    writable: bool
    allowed_mutations: frozenset[str]


@dataclass(frozen=True)
class DocumentSnapshot:
    model_fingerprint: str
    business_id: str
    scope: ReferenceDocumentScope
    aggregate: ReferenceIdentity
    entities: tuple[DocumentEntitySnapshot, ...]
    relations: tuple[DocumentRelationSnapshot, ...]


@dataclass(frozen=True)
class DocumentBlobBindingSnapshot:
    row_key: str
    canonical_field: str
    entity_type: str
    stable_key: str | None
    binding_version: int
    nullable: bool
    writable: bool


@dataclass(frozen=True)
class BoundDocumentSnapshot:
    snapshot: DocumentSnapshot
    bindings: tuple[DocumentBlobBindingSnapshot, ...]


@dataclass(frozen=True)
class BlobSelectionTarget:
    scope: ReferenceDocumentScope
    target_entity: str
    canonical_field: str
    kind: str  # EXISTING_ROW or NEW_CLIENT_KEY
    target_key: str
    command_id: str


@dataclass(frozen=True)
class BlobSelectionClaim:
    target: BlobSelectionTarget
    stable_key: str


T = TypeVar("T")


@dataclass(frozen=True)
class VerifiedDocument(Generic[T]):
    document: T
    key_id: str
    issued_at: datetime
    expires_at: datetime


@dataclass(frozen=True)
class PreparedBoundDocument:
    document: BoundDocumentSnapshot
    lifetime_seconds: int


class SecureDocumentAssembly(Protocol):
    def principal(self, context) -> TrustedReferencePrincipal: ...

    async def snapshot(self, context, graph) -> PreparedBoundDocument: ...


class _SecureCapability:
    capability = "secure_document.v1"

    def __init__(self, contributor) -> None:
        self.contributor = contributor

    def validate_ready(self, context) -> None:
        if context.get_resource("secure_document_contributor") is not self.contributor:
            raise RuntimeError("DOCUMENT_CONFIGURATION")


class _SecureContributor:
    def __init__(self, module, context, assembly: SecureDocumentAssembly) -> None:
        self.module, self.context, self.assembly = module, context, assembly

    async def prepare(self, context, graph, options) -> PreparedSecureDocument:
        if context is not self.context or options.mode != "governed":
            raise ViewPreparationError("DOCUMENT_CONFIGURATION")
        capability = context.get_resource("teaql.runtime.capability:secure_document.v1")
        if not isinstance(capability, _SecureCapability):
            raise ViewPreparationError("DOCUMENT_CONFIGURATION")
        try:
            capability.validate_ready(context)
        except Exception:
            raise ViewPreparationError("DOCUMENT_CONFIGURATION") from None
        principal = self.assembly.principal(context)
        prepared = await self.assembly.snapshot(context, graph)
        document = prepared.document
        try:
            for slot in graph.blob_slots:
                if not slot.entity_id.isascii() or not slot.entity_id.isdecimal() or \
                        slot.entity_id.startswith("0"):
                    raise ViewPreparationError("DOCUMENT_PROJECTION_VIOLATION")
                row = next((entity for entity in document.snapshot.entities
                            if entity.identity.entity_type == slot.entity and
                            entity.identity.id == int(slot.entity_id)), None)
                binding = next((item for item in document.bindings
                                if item.row_key == (row.row_key if row else None) and
                                item.canonical_field == slot.field), None)
                if binding is None or binding.stable_key != slot.reference.key or \
                        binding.binding_version != slot.binding_version:
                    raise ViewPreparationError("DOCUMENT_PROJECTION_VIOLATION")
            token = self.module.issue_bound_document_snapshot(principal, document,
                                                               prepared.lifetime_seconds)
            verified = self.module.consume_bound_document_snapshot(
                principal, token, document.snapshot.scope.aggregate_type, document.snapshot.scope.purpose)
        except RoundTripReferenceError as error:
            raise ViewPreparationError(error.code) from None
        return PreparedSecureDocument(graph, {"businessId": document.snapshot.business_id,
                                              "documentToken": token}, verified.expires_at)


class _Reader:
    def __init__(self, data: bytes) -> None:
        self.data, self.offset = data, 0

    def take(self, count: int) -> bytes:
        if count < 0 or self.offset + count > len(self.data):
            _fail()
        value = self.data[self.offset:self.offset + count]
        self.offset += count
        return value

    def byte(self) -> int:
        return self.take(1)[0]

    def flag(self) -> bool:
        value = self.byte()
        if value not in (0, 1):
            _fail()
        return value == 1

    def count(self, maximum: int) -> int:
        value = struct.unpack(">I", self.take(4))[0]
        if value > maximum:
            _fail()
        return value

    def text(self) -> str:
        value = self.take(self.count(16384))
        try:
            result = value.decode("utf-8", errors="strict")
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


def _read_scope(reader: _Reader) -> ReferenceDocumentScope:
    value = ReferenceDocumentScope(reader.text(), reader.text(), reader.text(), reader.u64(), reader.i64())
    value.validate()
    return value


def _read_identity(reader: _Reader) -> ReferenceIdentity:
    value = ReferenceIdentity(reader.text(), reader.u64(), reader.i64())
    value.validate()
    return value


def _read_set(reader: _Reader, maximum: int) -> frozenset[str]:
    count = reader.count(maximum)
    values = [reader.text() for _ in range(count)]
    if len(set(values)) != count:
        _fail()
    return frozenset(values)


def _read_mutations(reader: _Reader) -> frozenset[str]:
    count = reader.count(3)
    values = []
    for _ in range(count):
        value = _REVERSE_MUTATIONS.get(reader.byte())
        if value is None or value in values:
            _fail()
        values.append(value)
    return frozenset(values)


def _encode_snapshot(snapshot: DocumentSnapshot, version: int, actor: bytes,
                     issued: int, expires: int) -> bytes:
    if snapshot.aggregate.entity_type != snapshot.scope.aggregate_type or \
            snapshot.aggregate.id != snapshot.scope.aggregate_id or \
            snapshot.aggregate.version != snapshot.scope.aggregate_revision:
        _fail("DOCUMENT_PROJECTION_VIOLATION")
    parts = [bytes((version,)), actor, _i64(issued), _i64(expires), _str(snapshot.model_fingerprint),
             _str(snapshot.business_id), _scope(snapshot.scope), _identity(snapshot.aggregate),
             _count(len(snapshot.entities), 10000)]
    row_keys = set()
    for entity in snapshot.entities:
        if entity.row_key in row_keys or not entity.writable_fields.issubset(entity.loaded_fields) or \
                not entity.allowed_mutations:
            _fail("DOCUMENT_PROJECTION_VIOLATION")
        row_keys.add(entity.row_key)
        parts.extend((_str(entity.row_key), _identity(entity.identity),
                      _set(entity.loaded_fields, 1024), _set(entity.writable_fields, 1024),
                      _mutations(entity.allowed_mutations)))
    parts.append(_count(len(snapshot.relations), 1024))
    for relation in snapshot.relations:
        if relation.completeness not in ("COMPLETE", "PARTIAL") or \
                (not relation.writable and relation.allowed_mutations) or \
                len(set(relation.row_keys)) != len(relation.row_keys) or \
                any(key not in row_keys for key in relation.row_keys):
            _fail("DOCUMENT_PROJECTION_VIOLATION")
        parts.extend((_str(relation.name), bytes((1 if relation.completeness == "COMPLETE" else 2,)),
                      _flag(relation.writable), _mutations(relation.allowed_mutations),
                      _count(len(relation.row_keys), 10000),
                      *(_str(key) for key in relation.row_keys)))
    return b"".join(parts)


def _decode_snapshot(reader: _Reader, version: int):
    if reader.byte() != version:
        _fail()
    actor, issued, expires = reader.take(32), reader.i64(), reader.i64()
    model_fingerprint, business_id = reader.text(), reader.text()
    scope, aggregate = _read_scope(reader), _read_identity(reader)
    entities = []
    for _ in range(reader.count(10000)):
        entities.append(DocumentEntitySnapshot(reader.text(), _read_identity(reader),
                                               _read_set(reader, 1024), _read_set(reader, 1024),
                                               _read_mutations(reader)))
    relations = []
    for _ in range(reader.count(1024)):
        name, completeness = reader.text(), reader.byte()
        if completeness not in (1, 2):
            _fail()
        writable, mutations = reader.flag(), _read_mutations(reader)
        rows = tuple(reader.text() for _ in range(reader.count(10000)))
        relations.append(DocumentRelationSnapshot(name, rows,
                                                  "COMPLETE" if completeness == 1 else "PARTIAL",
                                                  writable, mutations))
    snapshot = DocumentSnapshot(model_fingerprint, business_id, scope, aggregate,
                                tuple(entities), tuple(relations))
    _encode_snapshot(snapshot, version, actor, issued, expires)
    return actor, issued, expires, snapshot


def _bindings(document: BoundDocumentSnapshot) -> tuple[DocumentBlobBindingSnapshot, ...]:
    values = tuple(sorted(document.bindings, key=lambda x: (x.row_key.encode(), x.canonical_field.encode())))
    if len(values) > 10000:
        _fail("DOCUMENT_PROJECTION_VIOLATION")
    previous = None
    for binding in values:
        for value in (binding.row_key, binding.canonical_field, binding.entity_type):
            _text(value)
            if value != value.strip():
                _fail("DOCUMENT_PROJECTION_VIOLATION")
        pair = (binding.row_key, binding.canonical_field)
        if pair == previous:
            _fail("DOCUMENT_PROJECTION_VIOLATION")
        previous = pair
        entity = next((row for row in document.snapshot.entities if row.row_key == binding.row_key), None)
        if entity is None or entity.identity.entity_type != binding.entity_type or \
                binding.canonical_field not in entity.loaded_fields or \
                (binding.writable and binding.canonical_field not in entity.writable_fields):
            _fail("DOCUMENT_PROJECTION_VIOLATION")
        if binding.stable_key is not None:
            _blob_key(binding.stable_key)
        _u64(binding.binding_version)
        _flag(binding.nullable)
        _flag(binding.writable)
    return values


def _target_allowed(document: BoundDocumentSnapshot, target: BlobSelectionTarget) -> None:
    target.scope.validate()
    for value in (target.target_entity, target.canonical_field, target.target_key, target.command_id):
        _text(value)
        if value != value.strip():
            _fail()
    if document.snapshot.scope != target.scope:
        _fail("ROUND_TRIP_REFERENCE_SCOPE_MISMATCH")
    if target.kind == "EXISTING_ROW":
        entity = next((row for row in document.snapshot.entities if row.row_key == target.target_key), None)
        if entity is None or entity.identity.entity_type != target.target_entity or \
                target.canonical_field not in entity.writable_fields or \
                not any(binding.row_key == target.target_key and
                        binding.canonical_field == target.canonical_field and binding.writable
                        for binding in document.bindings):
            _fail("DOCUMENT_PROJECTION_VIOLATION")
    elif target.kind == "NEW_CLIENT_KEY":
        if not any(relation.completeness == "COMPLETE" and relation.writable and
                   "CREATE_CHILD" in relation.allowed_mutations for relation in document.snapshot.relations):
            _fail("DOCUMENT_PROJECTION_VIOLATION")
    else:
        _fail()


class SecureDocumentReferenceModule(ContextBoundReferenceRuntime):
    """Protocol implementation. Host document open/accept and SQL replay remain separate gates."""

    def install(self, context, assembly: SecureDocumentAssembly) -> None:
        if context is None or assembly is None or not callable(getattr(assembly, "principal", None)) or \
                not callable(getattr(assembly, "snapshot", None)) or \
                context.get_resource("secure_document_contributor") is not None or \
                context.get_resource("teaql.runtime.capability:secure_document.v1") is not None:
            raise RuntimeError("DOCUMENT_CONFIGURATION")
        contributor = _SecureContributor(self, context, assembly)
        install_runtime_capability(context, _SecureCapability(contributor))
        context.insert_resource("secure_document_contributor", contributor)

    def _seal(self, prefix: str, label: bytes, purpose: str, plaintext: bytes,
              key: ReferenceKey) -> str:
        nonce = self.nonce()
        if not isinstance(nonce, bytes) or len(nonce) != 12:
            _fail("ROUND_TRIP_REFERENCE_CONFIGURATION_INVALID")
        aad = b"".join(_str(value) for value in (prefix, key.key_id, self.service, self.environment, purpose))
        encrypted = AESGCM(self._derive(key, label)).encrypt(nonce, plaintext, aad)
        token = f"{prefix}.{key.key_id}." + base64.urlsafe_b64encode(nonce + encrypted).rstrip(b"=").decode()
        if len(token) > 256000:
            _fail()
        return token

    def _open(self, prefix: str, label: bytes, purpose: str, token: str) -> tuple[ReferenceKey, bytes]:
        if not isinstance(token, str) or len(token) > 256000:
            _fail()
        parts = token.split(".")
        if len(parts) != 3 or parts[0] != prefix or not _KEY_ID.fullmatch(parts[1]) or \
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
        aad = b"".join(_str(value) for value in (prefix, key.key_id, self.service, self.environment, purpose))
        try:
            return key, AESGCM(self._derive(key, label)).decrypt(envelope[:12], envelope[12:], aad)
        except InvalidTag:
            _fail()

    def _times(self, lifetime_seconds: int) -> tuple[int, int]:
        if type(lifetime_seconds) is not int or lifetime_seconds <= 0:
            _fail()
        issued = self._timestamp()
        expires = issued + lifetime_seconds
        if expires > _MAX_I64:
            _fail()
        return issued, expires

    def _authorize_snapshot(self, principal: TrustedReferencePrincipal,
                            snapshot: DocumentSnapshot) -> None:
        self._authorize(principal, snapshot.scope, snapshot.aggregate)
        for entity in snapshot.entities:
            self._authorize(principal, snapshot.scope, entity.identity)

    def _verify(self, principal: TrustedReferencePrincipal, key: ReferenceKey, actor: bytes,
                issued: int, expires: int, scope: ReferenceDocumentScope,
                aggregate_type: str, purpose: str, document: T) -> VerifiedDocument[T]:
        now = self._timestamp()
        if expires <= now:
            _fail("ROUND_TRIP_REFERENCE_EXPIRED")
        if issued > now + 60:
            _fail()
        if not hmac.compare_digest(actor, self._actor(key, principal)) or \
                scope.purpose != purpose or scope.aggregate_type != aggregate_type:
            _fail("ROUND_TRIP_REFERENCE_SCOPE_MISMATCH")
        try:
            return VerifiedDocument(document, key.key_id,
                                    datetime.fromtimestamp(issued, timezone.utc),
                                    datetime.fromtimestamp(expires, timezone.utc))
        except (OverflowError, OSError, ValueError):
            _fail()

    def issue_document_snapshot(self, principal: TrustedReferencePrincipal,
                                snapshot: DocumentSnapshot, lifetime_seconds: int) -> str:
        issued, expires = self._times(lifetime_seconds)
        key = self.keys.current_key()
        plaintext = _encode_snapshot(snapshot, 1, self._actor(key, principal), issued, expires)
        self._authorize_snapshot(principal, snapshot)
        return self._seal("tqd1", b"document-snapshot-encryption", snapshot.scope.purpose, plaintext, key)

    def consume_document_snapshot(self, principal: TrustedReferencePrincipal, token: str,
                                  aggregate_type: str, purpose: str) -> VerifiedDocument[DocumentSnapshot]:
        key, plaintext = self._open("tqd1", b"document-snapshot-encryption", purpose, token)
        reader = _Reader(plaintext)
        actor, issued, expires, snapshot = _decode_snapshot(reader, 1)
        reader.end()
        verified = self._verify(principal, key, actor, issued, expires, snapshot.scope,
                                aggregate_type, purpose, snapshot)
        self._authorize_snapshot(principal, snapshot)
        return verified

    def issue_bound_document_snapshot(self, principal: TrustedReferencePrincipal,
                                      document: BoundDocumentSnapshot, lifetime_seconds: int) -> str:
        issued, expires = self._times(lifetime_seconds)
        key = self.keys.current_key()
        bindings = _bindings(document)
        parts = [_encode_snapshot(document.snapshot, 2, self._actor(key, principal), issued, expires),
                 _count(len(bindings), 10000)]
        for binding in bindings:
            parts.extend((_str(binding.row_key), _str(binding.canonical_field), _str(binding.entity_type),
                          _flag(binding.stable_key is not None)))
            if binding.stable_key is not None:
                parts.append(_str(binding.stable_key))
            parts.extend((_u64(binding.binding_version), _flag(binding.nullable), _flag(binding.writable)))
        self._authorize_snapshot(principal, document.snapshot)
        return self._seal("tqd2", b"document-snapshot-v2-encryption", document.snapshot.scope.purpose,
                          b"".join(parts), key)

    def consume_bound_document_snapshot(self, principal: TrustedReferencePrincipal, token: str,
                                        aggregate_type: str, purpose: str) -> VerifiedDocument[BoundDocumentSnapshot]:
        key, plaintext = self._open("tqd2", b"document-snapshot-v2-encryption", purpose, token)
        reader = _Reader(plaintext)
        actor, issued, expires, snapshot = _decode_snapshot(reader, 2)
        bindings = []
        for _ in range(reader.count(10000)):
            row_key, field, entity_type = reader.text(), reader.text(), reader.text()
            stable_key = reader.text() if reader.flag() else None
            bindings.append(DocumentBlobBindingSnapshot(row_key, field, entity_type, stable_key,
                                                        reader.u64(), reader.flag(), reader.flag()))
        reader.end()
        document = BoundDocumentSnapshot(snapshot, tuple(bindings))
        if document.bindings != _bindings(document):
            _fail()
        verified = self._verify(principal, key, actor, issued, expires, snapshot.scope,
                                aggregate_type, purpose, document)
        self._authorize_snapshot(principal, snapshot)
        return verified

    def issue_blob_selection(self, principal: TrustedReferencePrincipal, document_token: str,
                             claim: BlobSelectionClaim, lifetime_seconds: int) -> str:
        document = self.consume_bound_document_snapshot(principal, document_token,
                                                        claim.target.scope.aggregate_type,
                                                        claim.target.scope.purpose)
        _target_allowed(document.document, claim.target)
        _blob_key(claim.stable_key)
        issued, expires = self._times(lifetime_seconds)
        if expires > int(document.expires_at.timestamp()):
            _fail()
        key = self.keys.current_key()
        payload = b"".join((b"\x01", self._actor(key, principal), _i64(issued), _i64(expires),
                            _scope(claim.target.scope), _str(claim.target.target_entity),
                            _str(claim.target.canonical_field),
                            bytes((1 if claim.target.kind == "EXISTING_ROW" else 2,)),
                            _str(claim.target.target_key), _str(claim.stable_key),
                            _str(claim.target.command_id)))
        return self._seal("tqs1", b"blob-selection-v1-encryption", claim.target.scope.purpose,
                          payload, key)

    def consume_blob_selection(self, principal: TrustedReferencePrincipal, document_token: str,
                               token: str, expected_target: BlobSelectionTarget) -> VerifiedDocument[BlobSelectionClaim]:
        document = self.consume_bound_document_snapshot(principal, document_token,
                                                        expected_target.scope.aggregate_type,
                                                        expected_target.scope.purpose)
        _target_allowed(document.document, expected_target)
        key, plaintext = self._open("tqs1", b"blob-selection-v1-encryption",
                                    expected_target.scope.purpose, token)
        reader = _Reader(plaintext)
        if reader.byte() != 1:
            _fail()
        actor, issued, expires = reader.take(32), reader.i64(), reader.i64()
        scope, target_entity, field = _read_scope(reader), reader.text(), reader.text()
        kind_byte = reader.byte()
        if kind_byte not in (1, 2):
            _fail()
        target_key, stable_key, command_id = reader.text(), _blob_key(reader.text()), reader.text()
        reader.end()
        target = BlobSelectionTarget(scope, target_entity, field,
                                     "EXISTING_ROW" if kind_byte == 1 else "NEW_CLIENT_KEY",
                                     target_key, command_id)
        if target != expected_target:
            _fail("ROUND_TRIP_REFERENCE_SCOPE_MISMATCH")
        if expires > int(document.expires_at.timestamp()):
            _fail()
        return self._verify(principal, key, actor, issued, expires, scope,
                            expected_target.scope.aggregate_type, expected_target.scope.purpose,
                            BlobSelectionClaim(target, stable_key))
