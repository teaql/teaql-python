"""Explicit catalog-driven cleanup of inaccessible fenced File generations."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

from teaql.core.blob_ref import BlobRef
from teaql.core.object_storage import ObjectKey, StorageError
from teaql.core.value import Value
from teaql.sql.executor import SqlTransactionTransport
from teaql.sql.types import CompiledQuery

from .file_storage import FileObjectStorage
from .maintenance_service import BlobMaintenanceAuthorization, BlobMaintenanceCursor
from .sqlite_catalog import SqliteBlobCatalog, _scope


@dataclass(frozen=True)
class BlobFileGenerationSweepOutcome:
    reference: BlobRef
    status: str
    removed_generations: int | None = None
    error: str | None = None


@dataclass(frozen=True)
class BlobFileGenerationSweepBatch:
    outcomes: tuple[BlobFileGenerationSweepOutcome, ...]
    next: BlobMaintenanceCursor | None


class SqliteBlobFileGenerationSweepService:
    """Host-scheduled sweep; the host must first upgrade every root writer."""

    def __init__(self, catalog: SqliteBlobCatalog,
                 authorization: BlobMaintenanceAuthorization,
                 all_writers_upgraded: bool, batch_size: int = 100):
        if (not isinstance(catalog, SqliteBlobCatalog)
                or not isinstance(catalog.transport, SqlTransactionTransport)
                or authorization is None
                or not callable(getattr(authorization, "scope", None))
                or not callable(getattr(authorization, "can_maintain", None))
                or all_writers_upgraded is not True
                or type(batch_size) is not int or not 1 <= batch_size <= 1000):
            raise RuntimeError("BLOB_POLICY_INVALID")
        self.catalog = catalog
        self.authorization = authorization
        self.batch_size = batch_size

    async def _authorize(self, actor, expected: str | None = None) -> str:
        if actor is None:
            raise RuntimeError("BLOB_MAINTENANCE_DENIED")
        try:
            scope = self.authorization.scope(actor)
            allowed = await self.authorization.can_maintain(actor, scope)
        except Exception:
            raise RuntimeError("BLOB_MAINTENANCE_DENIED") from None
        if not _scope(scope) or expected is not None and scope != expected or not allowed:
            raise RuntimeError("BLOB_MAINTENANCE_DENIED")
        return scope

    async def run_batch(self, actor, provider: FileObjectStorage,
                        cursor: BlobMaintenanceCursor | None = None) -> BlobFileGenerationSweepBatch:
        scope = await self._authorize(actor)
        if cursor is not None and (not isinstance(cursor, BlobMaintenanceCursor)
                                   or cursor.scope != scope):
            raise RuntimeError("BLOB_MAINTENANCE_DENIED")
        actor.require_no_active_graph_sql()
        if (not isinstance(provider, FileObjectStorage)
                or actor.get_resource("object_storage_provider") is not provider):
            raise RuntimeError("BLOB_CAPABILITY_MISSING")
        await self.catalog.validate_schema()
        try:
            rows = await self.catalog.transport.fetch_all_sql(CompiledQuery(
                "SELECT key,object_key FROM teaql_blob_catalog "
                "WHERE scope=? AND key>? AND upload_mode='server_stream' "
                "ORDER BY key LIMIT ?",
                [Value.Text(scope), Value.Text(cursor.after if cursor else ""),
                 Value.I64(self.batch_size)]))
        except Exception:
            raise RuntimeError("BLOB_CATALOG_FAILED") from None
        candidates = []
        for row in rows:
            try:
                reference = BlobRef.from_sql(row.get("key"))
                object_key = ObjectKey(row.get("object_key"))
            except (ValueError, TypeError, StorageError):
                raise RuntimeError("BLOB_CATALOG_FAILED") from None
            candidates.append((reference, object_key))
        outcomes = []
        for reference, object_key in candidates:
            await self._authorize(actor, scope)
            try:
                removed = await asyncio.to_thread(provider.sweep_old_generations, object_key)
                if type(removed) is not int or removed < 0:
                    raise RuntimeError("BLOB_STORE_FAILED")
                outcomes.append(BlobFileGenerationSweepOutcome(reference, "swept", removed))
            except Exception:
                outcomes.append(BlobFileGenerationSweepOutcome(reference, "failed", None,
                                                                "BLOB_STORE_FAILED"))
        next_cursor = (BlobMaintenanceCursor(scope, candidates[-1][0].key)
                       if len(candidates) == self.batch_size else None)
        return BlobFileGenerationSweepBatch(tuple(outcomes), next_cursor)
