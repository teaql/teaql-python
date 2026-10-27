"""Authoritative SQLite binding component under an explicit native graph owner."""

from dataclasses import dataclass
from typing import Protocol
import unicodedata

from teaql.core.blob_ref import BlobRef
from teaql.core.value import Value
from teaql.sql.types import CompiledQuery
from teaql.runtime.view_preparation import AuthorizedBlobSlot


@dataclass(frozen=True)
class BlobBindingTarget:
    entity: str
    entity_id: str
    field: str


@dataclass(frozen=True)
class BlobBindingChange:
    target: BlobBindingTarget
    next: BlobRef | None
    expected_version: int
    next_version: int
    action: str


@dataclass(frozen=True)
class BlobCatalogRead:
    object_key: str
    content_version: str
    file_name: str
    content_type: str
    size_bytes: int


class BlobBindingAuthorization(Protocol):
    def scope(self, context) -> str: ...

    async def authorize(self, context, target: BlobBindingTarget,
                        previous: BlobRef | None, next_ref: BlobRef | None,
                        action: str) -> bool: ...


def _name(value):
    return (isinstance(value, str) and value and value == value.strip()
            and len(value) <= 128 and not any(unicodedata.category(ch) == "Cc" for ch in value))


def _scope(value):
    if not isinstance(value, str) or not value or value != value.strip():
        return False
    try:
        return (len(value.encode("utf-8")) <= 256
                and not any(unicodedata.category(ch) == "Cc" for ch in value))
    except UnicodeEncodeError:
        return False


def _entity_id(value):
    return (isinstance(value, str) and 1 <= len(value) <= 20 and value.isascii()
            and value.isdecimal() and 0 < int(value) <= 2**64 - 1
            and str(int(value)) == value)


class SqliteBlobCatalog:
    """SQLite-only catalog; install and schema migration are separate host actions."""

    def __init__(self, transport):
        if (transport is None or not callable(getattr(transport, "execute_sql", None))
                or not callable(getattr(transport, "fetch_all_sql", None))):
            raise RuntimeError("BLOB_CAPABILITY_MISSING")
        self.transport = transport

    async def ensure_schema(self):
        statements = (
            """CREATE TABLE IF NOT EXISTS teaql_blob_catalog (
                key TEXT PRIMARY KEY, scope TEXT NOT NULL, object_key TEXT NOT NULL,
                content_version TEXT NOT NULL, file_name TEXT NOT NULL,
                content_type TEXT NOT NULL, size_bytes BIGINT NOT NULL,
                status TEXT NOT NULL CHECK (status IN
                  ('initiated','uploaded_unbound','available','deleting','deleted')))
            """,
            """CREATE TABLE IF NOT EXISTS teaql_blob_binding (
                scope TEXT NOT NULL, entity TEXT NOT NULL, entity_id TEXT NOT NULL,
                field TEXT NOT NULL, key TEXT, version BIGINT NOT NULL,
                PRIMARY KEY (scope,entity,entity_id,field),
                FOREIGN KEY (key) REFERENCES teaql_blob_catalog(key))
            """,
            "CREATE INDEX IF NOT EXISTS teaql_blob_binding_key ON teaql_blob_binding(key)",
            """CREATE TABLE IF NOT EXISTS teaql_blob_upload (
                upload_id TEXT PRIMARY KEY, scope TEXT NOT NULL, replay_key TEXT NOT NULL,
                request_hash TEXT NOT NULL, key TEXT NOT NULL, entity TEXT NOT NULL,
                entity_id TEXT NOT NULL, field TEXT NOT NULL, file_name TEXT NOT NULL,
                extension TEXT NOT NULL, declared_size BIGINT NOT NULL,
                expires_ms BIGINT NOT NULL, state TEXT NOT NULL CHECK
                  (state IN ('initiated','written','completed')),
                written_sha256 TEXT, written_etag TEXT,
                UNIQUE(scope,replay_key), FOREIGN KEY(key) REFERENCES teaql_blob_catalog(key))
            """,
        )
        for sql in statements:
            try:
                await self.transport.execute_sql(CompiledQuery(sql, []))
            except Exception:
                raise RuntimeError("BLOB_CATALOG_FAILED") from None

    async def validate_schema(self):
        for sql in (
            "SELECT key, scope, object_key, content_version, file_name, content_type, size_bytes, status "
            "FROM teaql_blob_catalog WHERE 1 = 0",
            "SELECT scope, entity, entity_id, field, key, version "
            "FROM teaql_blob_binding WHERE 1 = 0",
            "SELECT upload_id, scope, replay_key, request_hash, key, entity, entity_id, "
            "field, file_name, extension, declared_size, expires_ms, state, "
            "written_sha256, written_etag FROM teaql_blob_upload WHERE 1 = 0",
        ):
            try:
                await self.transport.fetch_all_sql(CompiledQuery(sql, []))
            except Exception:
                raise RuntimeError("BLOB_SCHEMA_MISSING") from None
        try:
            columns = await self.transport.fetch_all_sql(CompiledQuery("PRAGMA table_info(teaql_blob_binding)", []))
            names = {row["name"]: row for row in columns}
            if names["key"]["notnull"] != 0 or names["version"]["notnull"] != 1:
                raise RuntimeError("BLOB_SCHEMA_MISSING")
        except Exception:
            raise RuntimeError("BLOB_SCHEMA_MISSING") from None

    async def current_read(self, slot: AuthorizedBlobSlot) -> BlobCatalogRead:
        """Reread the exact current binding; possession of the stable Key grants no read."""
        if (not isinstance(slot, AuthorizedBlobSlot) or not _scope(slot.scope)
                or not _name(slot.entity) or not _entity_id(slot.entity_id)
                or not _name(slot.field) or type(slot.binding_version) is not int
                or slot.binding_version < 1 or not isinstance(slot.reference, BlobRef)):
            raise RuntimeError("BLOB_READ_DENIED")
        try:
            rows = await self.transport.fetch_all_sql(CompiledQuery(
                "SELECT c.object_key,c.content_version,c.file_name,c.content_type,c.size_bytes "
                "FROM teaql_blob_binding b JOIN teaql_blob_catalog c ON c.key = b.key "
                "WHERE b.scope = ? AND b.entity = ? AND b.entity_id = ? AND b.field = ? "
                "AND b.key = ? AND b.version = ? AND c.scope = b.scope AND c.status = 'available'",
                [Value.Text(slot.scope), Value.Text(slot.entity), Value.Text(slot.entity_id),
                 Value.Text(slot.field), Value.Text(slot.reference.key), Value.I64(slot.binding_version)]))
        except Exception:
            raise RuntimeError("BLOB_CATALOG_FAILED") from None
        if len(rows) != 1:
            raise RuntimeError("BLOB_READ_DENIED")
        row = rows[0]
        values = (row.get("object_key"), row.get("content_version"),
                  row.get("file_name"), row.get("content_type"))
        size = row.get("size_bytes")
        if (any(not isinstance(value, str) or not value for value in values)
                or type(size) is not int or size < 0):
            raise RuntimeError("BLOB_CATALOG_FAILED")
        return BlobCatalogRead(*values, size)

    async def bind_in_graph(self, graph, actor, change: BlobBindingChange,
                            authorization: BlobBindingAuthorization) -> int:
        if graph is None or not callable(getattr(graph, "with_sql_transport", None)):
            raise RuntimeError("BLOB_TRANSACTION_REQUIRED")

        async def bind(sql):
            if actor is not graph.context:
                raise RuntimeError("BLOB_BIND_DENIED")
            if (not isinstance(change, BlobBindingChange) or not isinstance(change.target, BlobBindingTarget)
                    or not _name(change.target.entity) or not _entity_id(change.target.entity_id)
                    or not _name(change.target.field) or not isinstance(change.expected_version, int)
                    or isinstance(change.expected_version, bool) or change.expected_version < 0
                    or not isinstance(change.next_version, int) or isinstance(change.next_version, bool)
                    or change.next_version <= change.expected_version
                    or change.action not in ("Create", "Update", "Delete")
                    or change.action == "Create" and change.expected_version != 0
                    or change.action == "Delete" and change.next is not None
                    or change.next is not None and not isinstance(change.next, BlobRef)
                    or authorization is None):
                raise RuntimeError("BLOB_REFERENCE_INVALID")
            try:
                scope = authorization.scope(actor)
            except Exception:
                raise RuntimeError("BLOB_BIND_DENIED") from None
            if not _scope(scope):
                raise RuntimeError("BLOB_BIND_DENIED")
            target = change.target
            identity = [Value.Text(scope), Value.Text(target.entity),
                        Value.Text(target.entity_id), Value.Text(target.field)]
            try:
                rows = await sql.fetch_all_sql(CompiledQuery(
                    "SELECT key, version FROM teaql_blob_binding WHERE scope = ? AND entity = ? "
                    "AND entity_id = ? AND field = ?", identity))
            except Exception:
                raise RuntimeError("BLOB_CATALOG_FAILED") from None
            if len(rows) > 1:
                raise RuntimeError("BLOB_CATALOG_FAILED")
            row = rows[0] if rows else None
            version = row["version"] if row else 0
            if not isinstance(version, int) or version < 0:
                raise RuntimeError("BLOB_CATALOG_FAILED")
            if version != change.expected_version:
                raise RuntimeError("BLOB_BIND_DENIED")
            try:
                previous = BlobRef.from_sql(row["key"]) if row and row["key"] is not None else None
            except ValueError:
                raise RuntimeError("BLOB_CATALOG_FAILED") from None
            try:
                allowed = await authorization.authorize(actor, target, previous, change.next, change.action)
            except Exception:
                raise RuntimeError("BLOB_BIND_DENIED") from None
            if not allowed:
                raise RuntimeError("BLOB_BIND_DENIED")
            if change.next:
                try:
                    available = await sql.fetch_all_sql(CompiledQuery(
                        "SELECT key FROM teaql_blob_catalog WHERE key = ? AND scope = ? "
                        "AND status IN ('uploaded_unbound','available')",
                        [Value.Text(change.next.key), Value.Text(scope)]))
                except Exception:
                    raise RuntimeError("BLOB_CATALOG_FAILED") from None
                if len(available) != 1:
                    raise RuntimeError("BLOB_BIND_DENIED")
            key = Value.Text(change.next.key) if change.next else Value.Null()
            try:
                if row:
                    affected, _ = await sql.execute_sql(CompiledQuery(
                        "UPDATE teaql_blob_binding SET key = ?, version = ? WHERE scope = ? "
                        "AND entity = ? AND entity_id = ? AND field = ? AND version = ?",
                        [key, Value.I64(change.next_version), *identity, Value.I64(version)]))
                else:
                    affected, _ = await sql.execute_sql(CompiledQuery(
                        "INSERT INTO teaql_blob_binding (scope, entity, entity_id, field, key, version) "
                        "VALUES (?, ?, ?, ?, ?, ?)",
                        [*identity, key, Value.I64(change.next_version)]))
            except Exception:
                raise RuntimeError("BLOB_CATALOG_FAILED") from None
            if affected != 1:
                raise RuntimeError("BLOB_BIND_DENIED")
            if change.next:
                try:
                    promoted, _ = await sql.execute_sql(CompiledQuery(
                        "UPDATE teaql_blob_catalog SET status = 'available' WHERE key = ? AND scope = ? "
                        "AND status IN ('uploaded_unbound','available')",
                        [Value.Text(change.next.key), Value.Text(scope)]))
                except Exception:
                    raise RuntimeError("BLOB_CATALOG_FAILED") from None
                if promoted != 1:
                    raise RuntimeError("BLOB_BIND_DENIED")
            if previous and previous != change.next:
                try:
                    await sql.execute_sql(CompiledQuery(
                        "UPDATE teaql_blob_catalog SET status = 'uploaded_unbound' "
                        "WHERE key = ? AND scope = ? AND status = 'available' "
                        "AND NOT EXISTS (SELECT 1 FROM teaql_blob_binding WHERE key = ?)",
                        [Value.Text(previous.key), Value.Text(scope), Value.Text(previous.key)]))
                except Exception:
                    raise RuntimeError("BLOB_CATALOG_FAILED") from None
            return change.next_version

        return await graph.with_sql_transport(bind)
