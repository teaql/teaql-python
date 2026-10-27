"""Scoped SQLite Blob upload journal and full-byte confirmation.

The host supplies current authorization and a trusted format parser. This module
does not treat a client MIME hint or storage metadata as format verification.
"""

from __future__ import annotations

from contextlib import suppress
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from typing import BinaryIO, Callable, Protocol
import asyncio
import base64
import json
import re
import secrets
import time

from teaql.core.blob_ref import BlobFieldSpec, BlobRef, blob_mime_for_extension
from teaql.core.object_storage import MAX_PUT_SIZE, ObjectKey, PutOptions, WriteMode
from teaql.core.value import Value
from teaql.sql.executor import SqlTransactionTransport
from teaql.sql.types import CompiledQuery

from .sqlite_catalog import SqliteBlobCatalog, _entity_id, _name, _scope


@dataclass(frozen=True)
class BlobUploadTarget:
    entity: str
    entity_id: str
    field: str


@dataclass(frozen=True)
class BlobUploadInput:
    file_name: str
    declared_size: int
    declared_content_type: str = ""


@dataclass(frozen=True)
class BlobVerifiedContent:
    size_bytes: int
    sha256: str
    content_type: str


@dataclass(frozen=True, repr=False)
class BlobUploadSession:
    upload_id: str
    reference: BlobRef
    expires_at: datetime

    def __repr__(self):
        return "BlobUploadSession[masked]"


class BlobUploadAuthorization(Protocol):
    def scope(self, context) -> str: ...
    def field(self, context, target: BlobUploadTarget) -> BlobFieldSpec: ...
    async def authorize(self, context, target: BlobUploadTarget, action: str,
                        input: BlobUploadInput) -> bool: ...


class BlobContentVerifier(Protocol):
    def verify(self, stream: BinaryIO, extension: str, maximum_bytes: int) -> BlobVerifiedContent: ...


def _token():
    return base64.urlsafe_b64encode(secrets.token_bytes(24)).rstrip(b"=").decode("ascii")


def _text(value, maximum):
    if not isinstance(value, str) or not value or value != value.strip():
        return False
    try:
        return len(value.encode("utf-8")) <= maximum and not any(
            ord(c) < 32 or 127 <= ord(c) <= 159 for c in value)
    except UnicodeEncodeError:
        return False


def _query(sql, *params):
    return CompiledQuery(sql, list(params))


class _CountingReader:
    def __init__(self, stream: BinaryIO, maximum: int):
        self.stream = stream
        self.maximum = maximum
        self.digest = sha256()
        self.count = 0
        self.eof = False

    def read(self, size=-1):
        block = self.stream.read(size)
        if not isinstance(block, bytes):
            raise RuntimeError("BLOB_UPLOAD_INCOMPLETE")
        self.count += len(block)
        if self.count > self.maximum:
            raise RuntimeError("BLOB_SIZE_EXCEEDED")
        self.digest.update(block)
        if not block and size != 0:
            self.eof = True
        return block

    def close(self):
        self.stream.close()


class SqliteBlobUploadService:
    """Host-invoked upload path; schema migration remains explicit."""

    def __init__(self, catalog: SqliteBlobCatalog, authorization: BlobUploadAuthorization,
                 verifier: BlobContentVerifier, maximum_bytes: int, lease_seconds: int = 900,
                 now_ms: Callable[[], int] | None = None):
        if (not isinstance(catalog, SqliteBlobCatalog)
                or not isinstance(catalog.transport, SqlTransactionTransport)
                or authorization is None or verifier is None
                or not callable(getattr(verifier, "verify", None))
                or type(maximum_bytes) is not int or not 1 <= maximum_bytes <= MAX_PUT_SIZE
                or type(lease_seconds) is not int or not 1 <= lease_seconds <= 3600):
            raise RuntimeError("BLOB_POLICY_INVALID")
        self.catalog = catalog
        self.authorization = authorization
        self.verifier = verifier
        self.maximum_bytes = maximum_bytes
        self.lease_seconds = lease_seconds
        self.now_ms = now_ms or (lambda: time.time_ns() // 1_000_000)

    def _normalize(self, input: BlobUploadInput):
        if (not isinstance(input, BlobUploadInput) or type(input.declared_size) is not int
                or not 0 <= input.declared_size <= self.maximum_bytes):
            raise RuntimeError("BLOB_SIZE_EXCEEDED")
        if not _text(input.file_name, 1024):
            raise RuntimeError("BLOB_FORMAT_NOT_ALLOWED")
        name = input.file_name.replace("\\", "/").rsplit("/", 1)[-1]
        if not _text(name, 512):
            raise RuntimeError("BLOB_FORMAT_NOT_ALLOWED")
        extension = name.rsplit(".", 1)[-1].lower()
        if blob_mime_for_extension(extension) is None:
            raise RuntimeError("BLOB_FORMAT_NOT_ALLOWED")
        declared = input.declared_content_type.strip().lower() if isinstance(
            input.declared_content_type, str) else None
        if declared is None or declared and not _text(declared, 128):
            raise RuntimeError("BLOB_FORMAT_NOT_ALLOWED")
        return BlobUploadInput(name, input.declared_size, declared), extension

    async def _current(self, actor, target, action, input, expected_scope=None):
        if (actor is None or not isinstance(target, BlobUploadTarget)
                or not _name(target.entity) or not _name(target.field)
                or target.entity_id != "" and not _entity_id(target.entity_id)):
            raise RuntimeError("BLOB_REFERENCE_INVALID")
        try:
            scope = self.authorization.scope(actor)
            field = self.authorization.field(actor, target)
            allowed = await self.authorization.authorize(actor, target, action, input)
        except Exception:
            raise RuntimeError("BLOB_UPLOAD_DENIED") from None
        if (not _scope(scope) or expected_scope is not None and scope != expected_scope
                or not isinstance(field, BlobFieldSpec) or field.entity != target.entity
                or field.field != target.field or not allowed):
            raise RuntimeError("BLOB_UPLOAD_DENIED")
        extension = input.file_name.rsplit(".", 1)[-1].lower()
        if extension not in field.allowed_extensions:
            raise RuntimeError("BLOB_FORMAT_NOT_ALLOWED")
        return scope

    async def _transaction(self, work):
        try:
            tx = await self.catalog.transport.begin_sql()
        except Exception:
            raise RuntimeError("BLOB_CATALOG_FAILED") from None
        committed = False
        try:
            result = await work(tx)
            try:
                await tx.commit_sql()
            except Exception:
                raise RuntimeError("BLOB_CATALOG_FAILED") from None
            committed = True
            return result
        finally:
            if not committed:
                with suppress(Exception):
                    await tx.rollback_sql()

    async def begin(self, actor, target: BlobUploadTarget, input: BlobUploadInput,
                    replay_key: str) -> BlobUploadSession:
        normalized, extension = self._normalize(input)
        if not _text(replay_key, 256):
            raise RuntimeError("BLOB_REFERENCE_INVALID")
        scope = await self._current(actor, target, "Begin", normalized)
        request = json.dumps([target.entity, target.entity_id, target.field, normalized.file_name,
                              normalized.declared_size, normalized.declared_content_type],
                             ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        request_hash = sha256(request).hexdigest()

        async def work(tx):
            try:
                rows = await tx.fetch_all_sql(_query(
                    "SELECT upload_id,key,request_hash,expires_ms FROM teaql_blob_upload "
                    "WHERE scope = ? AND replay_key = ?", Value.Text(scope), Value.Text(replay_key)))
            except Exception:
                raise RuntimeError("BLOB_CATALOG_FAILED") from None
            if len(rows) > 1:
                raise RuntimeError("BLOB_CATALOG_FAILED")
            if rows:
                row = rows[0]
                if row.get("request_hash") != request_hash:
                    raise RuntimeError("BLOB_IDEMPOTENCY_CONFLICT")
                await self._current(actor, target, "Begin", normalized, scope)
                try:
                    expires_ms = row["expires_ms"]
                    if type(expires_ms) is not int:
                        raise RuntimeError("BLOB_CATALOG_FAILED")
                    if self.now_ms() >= expires_ms:
                        raise RuntimeError("BLOB_UPLOAD_EXPIRED")
                    return BlobUploadSession(row["upload_id"], BlobRef(row["key"]),
                        datetime.fromtimestamp(expires_ms / 1000, timezone.utc))
                except (KeyError, TypeError, ValueError, OverflowError):
                    raise RuntimeError("BLOB_CATALOG_FAILED") from None
            reference = BlobRef("blob_" + _token())
            upload_id = "bu_" + _token()
            object_key = "blob/" + _token()
            expires_ms = self.now_ms() + self.lease_seconds * 1000
            await self._current(actor, target, "Begin", normalized, scope)
            try:
                await tx.execute_sql(_query(
                    "INSERT INTO teaql_blob_catalog "
                    "(key,scope,object_key,content_version,file_name,content_type,size_bytes,status) "
                    "VALUES (?,?,?,?,?,?,?,?)", Value.Text(reference.key), Value.Text(scope),
                    Value.Text(object_key), Value.Text(""), Value.Text(normalized.file_name),
                    Value.Text(""), Value.I64(0), Value.Text("initiated")))
                await tx.execute_sql(_query(
                    "INSERT INTO teaql_blob_upload "
                    "(upload_id,scope,replay_key,request_hash,key,entity,entity_id,field,file_name,"
                    "extension,declared_size,expires_ms,state) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    Value.Text(upload_id), Value.Text(scope), Value.Text(replay_key),
                    Value.Text(request_hash), Value.Text(reference.key), Value.Text(target.entity),
                    Value.Text(target.entity_id), Value.Text(target.field),
                    Value.Text(normalized.file_name), Value.Text(extension),
                    Value.I64(normalized.declared_size), Value.I64(expires_ms),
                    Value.Text("initiated")))
            except Exception:
                raise RuntimeError("BLOB_CATALOG_FAILED") from None
            return BlobUploadSession(upload_id, reference,
                datetime.fromtimestamp(expires_ms / 1000, timezone.utc))

        return await self._transaction(work)

    async def _row(self, actor, upload_id: str, action: str):
        if not isinstance(upload_id, str) or re.fullmatch(r"bu_[A-Za-z0-9_-]{32}", upload_id) is None:
            raise RuntimeError("BLOB_UPLOAD_DENIED")
        try:
            scope = self.authorization.scope(actor)
        except Exception:
            raise RuntimeError("BLOB_UPLOAD_DENIED") from None
        if not _scope(scope):
            raise RuntimeError("BLOB_UPLOAD_DENIED")
        try:
            rows = await self.catalog.transport.fetch_all_sql(_query(
                "SELECT upload_id,scope,key,entity,entity_id,field,file_name,extension,"
                "declared_size,expires_ms,state,written_sha256,written_etag "
                "FROM teaql_blob_upload WHERE scope = ? AND upload_id = ?",
                Value.Text(scope), Value.Text(upload_id)))
        except Exception:
            raise RuntimeError("BLOB_CATALOG_FAILED") from None
        if len(rows) != 1:
            raise RuntimeError("BLOB_UPLOAD_DENIED")
        row = rows[0]
        try:
            target = BlobUploadTarget(row["entity"], row["entity_id"], row["field"])
            input = BlobUploadInput(row["file_name"], row["declared_size"])
            await self._current(actor, target, action, input, scope)
            if type(row["expires_ms"]) is not int or self.now_ms() >= row["expires_ms"]:
                raise RuntimeError("BLOB_UPLOAD_EXPIRED")
            if type(row["declared_size"]) is not int or not 0 <= row["declared_size"] <= self.maximum_bytes:
                raise RuntimeError("BLOB_SIZE_EXCEEDED")
            if row["extension"] != row["file_name"].rsplit(".", 1)[-1].lower():
                raise RuntimeError("BLOB_CATALOG_FAILED")
        except (KeyError, TypeError, AttributeError):
            raise RuntimeError("BLOB_CATALOG_FAILED") from None
        return row

    async def _object_key(self, actor, row):
        try:
            rows = await self.catalog.transport.fetch_all_sql(_query(
                "SELECT object_key FROM teaql_blob_catalog WHERE key = ? AND scope = ?",
                Value.Text(row["key"]), Value.Text(row["scope"])))
            if len(rows) == 1:
                return ObjectKey(rows[0]["object_key"])
        except Exception:
            pass
        raise RuntimeError("BLOB_CATALOG_FAILED")

    async def write(self, actor, upload_id: str, source: BinaryIO) -> int:
        if source is None or not callable(getattr(source, "read", None)):
            raise RuntimeError("BLOB_UPLOAD_INCOMPLETE")
        try:
            row = await self._row(actor, upload_id, "Write")
            if row["state"] != "initiated":
                raise RuntimeError("BLOB_IDEMPOTENCY_CONFLICT")
            key = await self._object_key(actor, row)
            mime = blob_mime_for_extension(row["extension"])
            reader = _CountingReader(source, row["declared_size"])
            target = BlobUploadTarget(row["entity"], row["entity_id"], row["field"])

            async def work(tx):
                # BEGIN IMMEDIATE remains owned until the File write and journal
                # transition finish. A second writer or collector must recheck
                # the authoritative row after this owner commits.
                try:
                    current = await tx.fetch_all_sql(_query(
                        "SELECT state,expires_ms,key FROM teaql_blob_upload "
                        "WHERE upload_id=? AND scope=?", Value.Text(upload_id),
                        Value.Text(row["scope"])))
                    catalog = await tx.fetch_all_sql(_query(
                        "SELECT object_key,status FROM teaql_blob_catalog WHERE key=? AND scope=?",
                        Value.Text(row["key"]), Value.Text(row["scope"])))
                except Exception:
                    raise RuntimeError("BLOB_CATALOG_FAILED") from None
                if (len(current) != 1 or current[0]["state"] != "initiated" or
                        current[0]["key"] != row["key"] or
                        current[0]["expires_ms"] != row["expires_ms"] or
                        len(catalog) != 1 or catalog[0]["status"] != "initiated" or
                        catalog[0]["object_key"] != key.value):
                    raise RuntimeError("BLOB_IDEMPOTENCY_CONFLICT")
                await self._current(actor, target, "Write",
                                    BlobUploadInput(row["file_name"], row["declared_size"]),
                                    row["scope"])
                if self.now_ms() >= row["expires_ms"]:
                    raise RuntimeError("BLOB_UPLOAD_EXPIRED")
                try:
                    metadata = await asyncio.to_thread(
                        actor.object_storage("write Blob upload").put, key, reader,
                        PutOptions(row["declared_size"], WriteMode.CREATE_ONLY, mime))
                except Exception:
                    raise RuntimeError("BLOB_STORE_FAILED") from None
                await self._current(actor, target, "Write",
                                    BlobUploadInput(row["file_name"], row["declared_size"]),
                                    row["scope"])
                now = self.now_ms()
                if now >= row["expires_ms"]:
                    raise RuntimeError("BLOB_UPLOAD_EXPIRED")
                if (not reader.eof or reader.count != row["declared_size"] or
                        metadata.size != reader.count or not metadata.etag):
                    raise RuntimeError("BLOB_UPLOAD_INCOMPLETE")
                digest = reader.digest.hexdigest()
                try:
                    affected, _ = await tx.execute_sql(_query(
                        "UPDATE teaql_blob_upload SET state='written', written_sha256=?, written_etag=? "
                        "WHERE upload_id=? AND scope=? AND state='initiated' AND expires_ms > ? "
                        "AND EXISTS (SELECT 1 FROM teaql_blob_catalog "
                        "WHERE key=teaql_blob_upload.key AND scope=teaql_blob_upload.scope "
                        "AND status='initiated')",
                        Value.Text(digest), Value.Text(metadata.etag),
                        Value.Text(upload_id), Value.Text(row["scope"]), Value.I64(now)))
                except Exception:
                    raise RuntimeError("BLOB_CATALOG_FAILED") from None
                if affected != 1:
                    raise RuntimeError("BLOB_IDEMPOTENCY_CONFLICT")
                return reader.count
            return await self._transaction(work)
        finally:
            with suppress(Exception):
                source.close()

    async def complete(self, actor, upload_id: str) -> BlobRef:
        row = await self._row(actor, upload_id, "Confirm")
        if row["state"] == "completed":
            if (not isinstance(row["written_sha256"], str) or
                    re.fullmatch(r"[0-9a-f]{64}", row["written_sha256"]) is None or
                    not row["written_etag"]):
                raise RuntimeError("BLOB_UPLOAD_INCOMPLETE")
            try:
                rows = await self.catalog.transport.fetch_all_sql(_query(
                    "SELECT object_key,content_version,content_type,size_bytes,status "
                    "FROM teaql_blob_catalog WHERE key=? AND scope=?",
                    Value.Text(row["key"]), Value.Text(row["scope"])))
                if len(rows) != 1:
                    raise RuntimeError("BLOB_UPLOAD_INCOMPLETE")
                catalog = rows[0]
                mime = blob_mime_for_extension(row["extension"])
                if (catalog["status"] not in ("uploaded_unbound", "available") or
                        catalog["content_version"] != row["written_etag"] or
                        catalog["content_type"] != mime or
                        type(catalog["size_bytes"]) is not int or
                        catalog["size_bytes"] != row["declared_size"]):
                    raise RuntimeError("BLOB_UPLOAD_INCOMPLETE")
                key = ObjectKey(catalog["object_key"])
            except Exception:
                raise RuntimeError("BLOB_UPLOAD_INCOMPLETE") from None

            def recheck_stored():
                try:
                    metadata = actor.object_storage("recheck completed Blob upload").head(key)
                    if (metadata is None or metadata.size != row["declared_size"] or
                            metadata.etag != row["written_etag"]):
                        raise RuntimeError("BLOB_UPLOAD_INCOMPLETE")
                except Exception:
                    raise RuntimeError("BLOB_UPLOAD_INCOMPLETE") from None

            await asyncio.to_thread(recheck_stored)
            target = BlobUploadTarget(row["entity"], row["entity_id"], row["field"])
            await self._current(actor, target, "Confirm",
                                BlobUploadInput(row["file_name"], row["declared_size"], mime),
                                row["scope"])
            if self.now_ms() >= row["expires_ms"]:
                raise RuntimeError("BLOB_UPLOAD_EXPIRED")
            return BlobRef(row["key"])
        if row["state"] != "written" or not row["written_sha256"] or not row["written_etag"]:
            raise RuntimeError("BLOB_UPLOAD_INCOMPLETE")
        key = await self._object_key(actor, row)

        def verify_stored():
            try:
                store = actor.object_storage("verify Blob upload")
                before = store.head(key)
                if (before is None or before.size != row["declared_size"]
                        or before.etag != row["written_etag"]):
                    raise RuntimeError("BLOB_UPLOAD_INCOMPLETE")
                with store.get(key) as content:
                    if (content.metadata.size != before.size or
                            content.metadata.etag != before.etag):
                        raise RuntimeError("BLOB_UPLOAD_INCOMPLETE")
                    reader = _CountingReader(content.stream, self.maximum_bytes)
                    verified = self.verifier.verify(reader, row["extension"], self.maximum_bytes)
                    digest = reader.digest.hexdigest()
                    mime = blob_mime_for_extension(row["extension"])
                    if (not isinstance(verified, BlobVerifiedContent) or not reader.eof
                            or reader.count != before.size or verified.size_bytes != reader.count
                            or verified.sha256 != digest or verified.sha256 != row["written_sha256"]
                            or verified.content_type != mime):
                        raise RuntimeError("BLOB_UPLOAD_INCOMPLETE")
                after = store.head(key)
                if after is None or after.size != before.size or after.etag != before.etag:
                    raise RuntimeError("BLOB_UPLOAD_INCOMPLETE")
                return verified
            except Exception:
                raise RuntimeError("BLOB_UPLOAD_INCOMPLETE") from None

        target = BlobUploadTarget(row["entity"], row["entity_id"], row["field"])

        async def work(tx):
            # Keep the same physical SQLite owner through parser I/O and both
            # journal promotions. A concurrent confirmation rechecks after it.
            try:
                current = await tx.fetch_all_sql(_query(
                    "SELECT state,expires_ms,key,written_sha256,written_etag "
                    "FROM teaql_blob_upload WHERE upload_id=? AND scope=?",
                    Value.Text(upload_id), Value.Text(row["scope"])))
                catalog = await tx.fetch_all_sql(_query(
                    "SELECT object_key,status FROM teaql_blob_catalog WHERE key=? AND scope=?",
                    Value.Text(row["key"]), Value.Text(row["scope"])))
            except Exception:
                raise RuntimeError("BLOB_CATALOG_FAILED") from None
            if (len(current) == 1 and current[0]["state"] == "completed" and
                    current[0]["expires_ms"] == row["expires_ms"] and
                    current[0]["key"] == row["key"] and
                    current[0]["written_sha256"] == row["written_sha256"] and
                    current[0]["written_etag"] == row["written_etag"]):
                # Another confirmer won the lease. Reenter the regular replay
                # path after releasing this SQL owner so catalog, generation,
                # authorization and expiry are checked against current state.
                return None
            if (len(current) != 1 or current[0]["state"] != "written" or
                    current[0]["expires_ms"] != row["expires_ms"] or
                    current[0]["key"] != row["key"] or
                    current[0]["written_sha256"] != row["written_sha256"] or
                    current[0]["written_etag"] != row["written_etag"] or
                    len(catalog) != 1 or catalog[0]["status"] != "initiated" or
                    catalog[0]["object_key"] != key.value):
                raise RuntimeError("BLOB_IDEMPOTENCY_CONFLICT")
            await self._current(actor, target, "Confirm",
                                BlobUploadInput(row["file_name"], row["declared_size"]),
                                row["scope"])
            now = self.now_ms()
            if now >= row["expires_ms"]:
                raise RuntimeError("BLOB_UPLOAD_EXPIRED")
            verified = await asyncio.to_thread(verify_stored)
            await self._current(actor, target, "Confirm",
                                BlobUploadInput(row["file_name"], row["declared_size"],
                                                verified.content_type), row["scope"])
            now = self.now_ms()
            if now >= row["expires_ms"]:
                raise RuntimeError("BLOB_UPLOAD_EXPIRED")
            try:
                affected, _ = await tx.execute_sql(_query(
                    "UPDATE teaql_blob_upload SET state='completed' WHERE upload_id=? AND scope=? "
                    "AND state='written' AND written_sha256=? AND written_etag=? AND expires_ms > ?",
                    Value.Text(upload_id), Value.Text(row["scope"]),
                    Value.Text(row["written_sha256"]), Value.Text(row["written_etag"]), Value.I64(now)))
                if affected != 1:
                    raise RuntimeError("BLOB_IDEMPOTENCY_CONFLICT")
                affected, _ = await tx.execute_sql(_query(
                    "UPDATE teaql_blob_catalog SET content_version=?,content_type=?,size_bytes=?, "
                    "status='uploaded_unbound' WHERE key=? AND scope=? AND status='initiated'",
                    Value.Text(row["written_etag"]), Value.Text(verified.content_type),
                    Value.I64(verified.size_bytes), Value.Text(row["key"]),
                    Value.Text(row["scope"])))
                if affected != 1:
                    raise RuntimeError("BLOB_IDEMPOTENCY_CONFLICT")
            except RuntimeError:
                raise
            except Exception:
                raise RuntimeError("BLOB_CATALOG_FAILED") from None
            return BlobRef(row["key"])
        result = await self._transaction(work)
        return result if result is not None else await self.complete(actor, upload_id)
