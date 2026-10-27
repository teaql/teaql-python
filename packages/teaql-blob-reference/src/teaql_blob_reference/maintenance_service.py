"""Explicit SQLite cleanup of expired, uncompleted server-stream uploads."""

from __future__ import annotations

import asyncio
from contextlib import suppress
from dataclasses import dataclass
import time
from typing import Callable, Protocol

from teaql.core.blob_ref import BlobRef
from teaql.core.object_storage import ObjectKey, StorageError
from teaql.core.value import Value
from teaql.sql.executor import SqlTransactionTransport
from teaql.sql.types import CompiledQuery

from .sqlite_catalog import SqliteBlobCatalog, _scope


class BlobMaintenanceAuthorization(Protocol):
    def scope(self, context) -> str: ...
    async def can_maintain(self, context, scope: str) -> bool: ...


@dataclass(frozen=True, repr=False)
class BlobMaintenanceCursor:
    scope: str
    after: str

    def __repr__(self):
        return "BlobMaintenanceCursor[masked]"


@dataclass(frozen=True)
class BlobMaintenanceOutcome:
    reference: BlobRef
    status: str
    error: str | None = None


@dataclass(frozen=True)
class BlobMaintenanceBatch:
    outcomes: tuple[BlobMaintenanceOutcome, ...]
    next: BlobMaintenanceCursor | None


def _query(sql, *params):
    return CompiledQuery(sql, list(params))


def _version(value):
    return (isinstance(value, str) and value and value != "*"
            and len(value) <= 256 and value == value.strip()
            and not any(ord(ch) < 32 or 127 <= ord(ch) <= 159 for ch in value))


class SqliteBlobMaintenanceService:
    """The host schedules this service; installing a Blob module never runs it."""

    def __init__(self, catalog: SqliteBlobCatalog, authorization: BlobMaintenanceAuthorization,
                 batch_size: int = 100, now_ms: Callable[[], int] | None = None):
        if (not isinstance(catalog, SqliteBlobCatalog)
                or not isinstance(catalog.transport, SqlTransactionTransport)
                or authorization is None
                or not callable(getattr(authorization, "scope", None))
                or not callable(getattr(authorization, "can_maintain", None))
                or type(batch_size) is not int or not 1 <= batch_size <= 1000):
            raise RuntimeError("BLOB_POLICY_INVALID")
        self.catalog = catalog
        self.authorization = authorization
        self.batch_size = batch_size
        self.now_ms = now_ms or (lambda: time.time_ns() // 1_000_000)

    async def _authorize(self, actor, expected: str | None = None) -> str:
        if actor is None:
            raise RuntimeError("BLOB_MAINTENANCE_DENIED")
        try:
            scope = self.authorization.scope(actor)
            allowed = await self.authorization.can_maintain(actor, scope)
        except Exception:
            raise RuntimeError("BLOB_MAINTENANCE_DENIED") from None
        if not _scope(scope) or (expected is not None and scope != expected) or not allowed:
            raise RuntimeError("BLOB_MAINTENANCE_DENIED")
        return scope

    def _now(self) -> int:
        value = self.now_ms()
        if type(value) is not int or value < 0:
            raise RuntimeError("BLOB_POLICY_INVALID")
        return value

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

    async def _row(self, sql, scope: str, key: str):
        try:
            rows = await sql.fetch_all_sql(_query(
                "SELECT c.object_key,c.content_version,c.status,u.state,u.expires_ms,u.written_etag "
                "FROM teaql_blob_catalog c JOIN teaql_blob_upload u "
                "ON u.key=c.key AND u.scope=c.scope WHERE c.scope=? AND c.key=?",
                Value.Text(scope), Value.Text(key)))
        except Exception:
            raise RuntimeError("BLOB_CATALOG_FAILED") from None
        if not rows:
            return None
        if len(rows) != 1:
            raise RuntimeError("BLOB_CATALOG_FAILED")
        row = rows[0]
        object_key, version = row.get("object_key"), row.get("content_version")
        raw_written = row.get("written_etag")
        written = "" if raw_written is None else raw_written
        if (not isinstance(object_key, str) or not object_key
                or not isinstance(version, str) or version and not _version(version)
                or not isinstance(row.get("status"), str)
                or not isinstance(row.get("state"), str)
                or type(row.get("expires_ms")) is not int
                or not isinstance(written, str) or written and not _version(written)
                or row["state"] == "written" and not written):
            raise RuntimeError("BLOB_CATALOG_FAILED")
        return {"key": key, "object_key": object_key, "version": version,
                "status": row["status"], "state": row["state"],
                "expires_ms": row["expires_ms"], "written_etag": written}

    @staticmethod
    def _eligible(row, now):
        return (row is not None and row["expires_ms"] <= now
                and row["state"] in ("initiated", "written")
                and row["status"] in ("initiated", "deleting"))

    async def _count(self, sql, statement, key):
        try:
            rows = await sql.fetch_all_sql(_query(statement, Value.Text(key)))
        except Exception:
            raise RuntimeError("BLOB_CATALOG_FAILED") from None
        if len(rows) != 1 or type(rows[0].get("n")) is not int or rows[0]["n"] < 0:
            raise RuntimeError("BLOB_CATALOG_FAILED")
        return rows[0]["n"]

    async def _claim(self, scope, key, now):
        async def work(sql):
            row = await self._row(sql, scope, key)
            if not self._eligible(row, now):
                return None
            if await self._count(sql, "SELECT count(*) AS n FROM teaql_blob_binding WHERE key=?", key):
                return None
            owners = await self._count(sql, "SELECT count(*) AS n FROM teaql_blob_catalog WHERE object_key=?",
                                       row["object_key"])
            if owners != 1:
                raise RuntimeError("BLOB_CATALOG_FAILED")
            if row["status"] == "initiated":
                try:
                    affected, _ = await sql.execute_sql(_query(
                        "UPDATE teaql_blob_catalog SET status='deleting' "
                        "WHERE key=? AND scope=? AND status='initiated'",
                        Value.Text(key), Value.Text(scope)))
                except Exception:
                    raise RuntimeError("BLOB_CATALOG_FAILED") from None
                if affected != 1:
                    raise RuntimeError("BLOB_CATALOG_FAILED")
            return row
        return await self._transaction(work)

    async def _capture(self, scope, claim, version, now):
        if not _version(version):
            raise RuntimeError("BLOB_IDEMPOTENCY_CONFLICT")
        async def work(sql):
            row = await self._row(sql, scope, claim["key"])
            bound = await self._count(sql, "SELECT count(*) AS n FROM teaql_blob_binding WHERE key=?",
                                      claim["key"])
            if (not self._eligible(row, now) or row["status"] != "deleting"
                    or row["object_key"] != claim["object_key"] or bound
                    or row["written_etag"] and row["written_etag"] != version
                    or row["version"] and row["version"] != version):
                raise RuntimeError("BLOB_IDEMPOTENCY_CONFLICT")
            if not row["version"]:
                try:
                    affected, _ = await sql.execute_sql(_query(
                        "UPDATE teaql_blob_catalog SET content_version=? "
                        "WHERE key=? AND scope=? AND status='deleting' AND content_version=''",
                        Value.Text(version), Value.Text(claim["key"]), Value.Text(scope)))
                except Exception:
                    raise RuntimeError("BLOB_CATALOG_FAILED") from None
                if affected != 1:
                    raise RuntimeError("BLOB_IDEMPOTENCY_CONFLICT")
        await self._transaction(work)

    async def _finish(self, scope, claim, version, now):
        async def work(sql):
            row = await self._row(sql, scope, claim["key"])
            if row is None or row["object_key"] != claim["object_key"] or row["version"] != version:
                raise RuntimeError("BLOB_IDEMPOTENCY_CONFLICT")
            if row["status"] == "deleted":
                return
            bound = await self._count(sql, "SELECT count(*) AS n FROM teaql_blob_binding WHERE key=?",
                                      claim["key"])
            if not self._eligible(row, now) or row["status"] != "deleting" or bound:
                raise RuntimeError("BLOB_IDEMPOTENCY_CONFLICT")
            try:
                affected, _ = await sql.execute_sql(_query(
                    "UPDATE teaql_blob_catalog SET status='deleted' "
                    "WHERE key=? AND scope=? AND status='deleting' AND content_version=?",
                    Value.Text(claim["key"]), Value.Text(scope), Value.Text(version)))
            except Exception:
                raise RuntimeError("BLOB_CATALOG_FAILED") from None
            if affected != 1:
                raise RuntimeError("BLOB_CATALOG_FAILED")
        await self._transaction(work)

    async def _collect(self, actor, scope, key, store):
        try:
            await self._authorize(actor, scope)
            claim = await self._claim(scope, key, self._now())
            if claim is None:
                return BlobMaintenanceOutcome(BlobRef(key), "not_eligible")
            await self._authorize(actor, scope)
            try:
                object_key = ObjectKey(claim["object_key"])
            except StorageError:
                raise RuntimeError("BLOB_CATALOG_FAILED") from None
            version = claim["version"]
            if version and claim["written_etag"] and version != claim["written_etag"]:
                raise RuntimeError("BLOB_IDEMPOTENCY_CONFLICT")
            if not version:
                try:
                    observed = await asyncio.to_thread(store.head, object_key)
                except Exception:
                    raise RuntimeError("BLOB_STORE_FAILED") from None
                if observed is not None:
                    if (not _version(observed.etag)
                            or claim["written_etag"] and observed.etag != claim["written_etag"]):
                        raise RuntimeError("BLOB_IDEMPOTENCY_CONFLICT")
                    version = observed.etag
                    await self._authorize(actor, scope)
                    await self._capture(scope, claim, version, self._now())
            await self._authorize(actor, scope)
            result = "already_missing"
            if version:
                try:
                    deleted = await asyncio.to_thread(store.delete_if_version, object_key, version)
                except Exception:
                    raise RuntimeError("BLOB_STORE_FAILED") from None
                if deleted == "version_mismatch":
                    raise RuntimeError("BLOB_IDEMPOTENCY_CONFLICT")
                result = deleted
            await self._authorize(actor, scope)
            await self._finish(scope, claim, version, self._now())
            return BlobMaintenanceOutcome(BlobRef(key), result)
        except RuntimeError as error:
            code = str(error)
            if code in ("BLOB_MAINTENANCE_DENIED", "BLOB_TRANSACTION_REQUIRED"):
                raise
            if code == "BLOB_IDEMPOTENCY_CONFLICT":
                return BlobMaintenanceOutcome(BlobRef(key), "version_conflict", code)
            if code != "BLOB_CATALOG_FAILED":
                code = "BLOB_STORE_FAILED"
            return BlobMaintenanceOutcome(BlobRef(key), "failed", code)

    async def run_batch(self, actor, cursor: BlobMaintenanceCursor | None = None) -> BlobMaintenanceBatch:
        scope = await self._authorize(actor)
        if cursor is not None and (not isinstance(cursor, BlobMaintenanceCursor)
                                   or cursor.scope != scope):
            raise RuntimeError("BLOB_MAINTENANCE_DENIED")
        actor.require_no_active_graph_sql()
        try:
            store = actor.object_storage("collect expired Blob upload")
        except Exception:
            raise RuntimeError("BLOB_CAPABILITY_MISSING") from None
        if not store.supports_version_conditional_delete():
            raise RuntimeError("BLOB_CAPABILITY_MISSING")
        await self.catalog.validate_schema()
        now = self._now()
        after = cursor.after if cursor else ""
        try:
            rows = await self.catalog.transport.fetch_all_sql(_query(
                "SELECT DISTINCT c.key FROM teaql_blob_catalog c JOIN teaql_blob_upload u "
                "ON u.key=c.key AND u.scope=c.scope WHERE c.scope=? AND c.key>? "
                "AND u.expires_ms<=? AND u.state IN ('initiated','written') "
                "AND c.status IN ('initiated','deleting') "
                "AND NOT EXISTS (SELECT 1 FROM teaql_blob_binding b WHERE b.key=c.key) "
                "ORDER BY c.key LIMIT ?", Value.Text(scope), Value.Text(after),
                Value.I64(now), Value.I64(self.batch_size)))
        except Exception:
            raise RuntimeError("BLOB_CATALOG_FAILED") from None
        keys = []
        for row in rows:
            key = row.get("key")
            try:
                BlobRef.from_sql(key)
            except (ValueError, TypeError):
                raise RuntimeError("BLOB_CATALOG_FAILED") from None
            keys.append(key)
        outcomes = tuple([await self._collect(actor, scope, key, store) for key in keys])
        next_cursor = BlobMaintenanceCursor(scope, keys[-1]) if len(keys) == self.batch_size else None
        return BlobMaintenanceBatch(outcomes, next_cursor)
