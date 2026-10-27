"""A real SQLite application host exercises the optional secure-document service."""

from dataclasses import replace
from datetime import datetime, timezone

import aiosqlite
import pytest

from teaql.core.value import Value
from teaql.provider.sqlite.dialect import SqliteDialect
from teaql.provider.sqlite.transport import SqliteTransport
from teaql.runtime import RuntimeModule
from teaql.runtime.graph_session import GraphCommittedError
from teaql.sql.executor import SqlDataServiceExecutor
from teaql.sql.types import CompiledQuery
from teaql.provider.sqlite import SimpleSchemaProvider
from teaql_secure_document_reference import (
    BoundDocumentSnapshot, ContextualDocument, CurrentBoundDocument,
    DocumentEntitySnapshot, DocumentSnapshot, ReferenceDocumentScope,
    ReferenceIdentity, ReferenceKey, SecureDocumentReferenceModule,
    SQLiteContextBoundDocumentService, SQLiteDocumentCommandJournal,
    StaticReferenceKeyProvider, SubmittedDocumentCommand, TrustedReferencePrincipal,
)


class OrderHost:
    def __init__(self):
        self.actor = TrustedReferencePrincipal("oidc", "alice", "Merchant", 7)
        self.mutations = 0
        self.fail_present = False
        self.switch_actor_on_apply = False

    def principal(self, _context):
        return self.actor

    async def authorize(self, _context, principal, _scope, sql):
        rows = await sql.fetch_all_sql(CompiledQuery(
            "SELECT can_edit FROM document_permission WHERE subject=?",
            [Value.Text(principal.subject)]))
        if len(rows) != 1 or rows[0]["can_edit"] != 1:
            raise PermissionError("revoked")

    async def load(self, _context, business_id, sql):
        rows = await sql.fetch_all_sql(CompiledQuery(
            "SELECT id,version,quantity FROM document_order WHERE business_id=?",
            [Value.Text(business_id)]))
        if len(rows) != 1:
            raise LookupError("order missing")
        row = rows[0]
        identity = ReferenceIdentity("Order", row["id"], row["version"])
        scope = ReferenceDocumentScope("edit-10", "edit-order", "Order",
                                       row["id"], row["version"])
        snapshot = DocumentSnapshot("model-v1", business_id, scope, identity,
                                    (DocumentEntitySnapshot(
                                        "order:10", identity, frozenset({"quantity"}),
                                        frozenset({"quantity"}), frozenset({"UPDATE"})),), ())
        return CurrentBoundDocument(BoundDocumentSnapshot(snapshot, ()),
                                    {"quantity": row["quantity"]}, 300)

    async def apply(self, _context, issued, submitted, sql):
        self.mutations += 1
        if submitted.body != {"quantity": 3}:
            raise ValueError("invalid quantity")
        affected, _ = await sql.execute_sql(CompiledQuery(
            "UPDATE document_order SET quantity=?,version=version+1 WHERE id=? AND version=?",
            [Value.I64(3), Value.I64(10),
             Value.I64(issued.snapshot.scope.aggregate_revision)]))
        if affected != 1:
            raise RuntimeError("stale order")
        if self.switch_actor_on_apply:
            self.actor = replace(self.actor, subject="bob")

    async def present(self, _context, document: ContextualDocument):
        assert document.business_id == "ORD-10"
        if self.fail_present:
            raise RuntimeError("presentation failed")


async def fixture(tmp_path):
    path = str(tmp_path / "secure-document.sqlite")
    async with aiosqlite.connect(path) as db:
        await db.execute("""CREATE TABLE document_order (id INTEGER PRIMARY KEY,
            business_id TEXT NOT NULL UNIQUE,version INTEGER NOT NULL,quantity INTEGER NOT NULL)""")
        await db.execute("CREATE TABLE document_permission(subject TEXT PRIMARY KEY,can_edit INTEGER NOT NULL)")
        await db.execute("INSERT INTO document_order VALUES (10,'ORD-10',1,1)")
        await db.execute("INSERT INTO document_permission VALUES ('alice',1)")
        await db.commit()
    transport = SqliteTransport(path)
    context = RuntimeModule.new().into_context()
    context.insert_resource("dataService", SqlDataServiceExecutor(
        SqliteDialect(), transport, SimpleSchemaProvider()))
    keys = StaticReferenceKeyProvider("k1", (ReferenceKey("k1", bytes([0x42]) * 32),))
    module = SecureDocumentReferenceModule(
        "order-service", "test", keys, lambda *_: None,
        lambda: datetime.fromtimestamp(1800000000, timezone.utc),
        lambda: bytes([0x33]) * 12)
    host = OrderHost()
    journal = SQLiteDocumentCommandJournal(transport)
    await journal.ensure_schema()
    await journal.validate_schema()
    service = SQLiteContextBoundDocumentService(context, transport, module, journal, host)
    return path, context, host, service


async def row(path):
    async with aiosqlite.connect(path) as db:
        async with db.execute("SELECT version,quantity FROM document_order WHERE id=10") as cursor:
            return await cursor.fetchone()


async def receipts(path):
    async with aiosqlite.connect(path) as db:
        async with db.execute("SELECT COUNT(*) FROM teaql_document_command_receipt") as cursor:
            return (await cursor.fetchone())[0]


@pytest.mark.asyncio
async def test_sqlite_open_accept_replay_authority_and_rollback(tmp_path):
    path, context, host, service = await fixture(tmp_path)
    opened = await service.open(context, "Order", "ORD-10", "edit-order", 60)
    assert opened.document_token.startswith("tqd2.") and opened.body == {"quantity": 1}
    assert opened.document_token not in repr(opened)
    command = SubmittedDocumentCommand("ORD-10", opened.document_token,
                                       "command-1", {"quantity": 3})
    first = await service.accept(context, "Order", "edit-order", command)
    assert (first.previous_revision, first.new_revision, first.replayed) == (1, 2, False)
    assert first.document.body == {"quantity": 3}
    assert first.document.document_token not in repr(first)
    assert await row(path) == (2, 3) and await receipts(path) == 1

    replay = await service.accept(context, "Order", "edit-order", command)
    assert replay.replayed and replay.document.document_token == first.document.document_token
    assert host.mutations == 1
    with pytest.raises(RuntimeError, match="DOCUMENT_REPLAY_CONFLICT"):
        await service.accept(context, "Order", "edit-order",
                             replace(command, body={"quantity": 4}))
    with pytest.raises(RuntimeError, match="DOCUMENT_REVISION_CONFLICT"):
        await service.accept(context, "Order", "edit-order",
                             replace(command, command_id="command-stale"))

    async with aiosqlite.connect(path) as db:
        await db.execute("UPDATE document_permission SET can_edit=0 WHERE subject='alice'")
        await db.commit()
    with pytest.raises(RuntimeError, match="DOCUMENT_AUTHORIZATION_REQUIRED"):
        await service.accept(context, "Order", "edit-order", command)
    with pytest.raises(RuntimeError, match="DOCUMENT_AUTHORIZATION_REQUIRED"):
        await service.open(context, "Order", "ORD-10", "edit-order", 60)
    async with aiosqlite.connect(path) as db:
        await db.execute("UPDATE document_permission SET can_edit=1 WHERE subject='alice'")
        await db.commit()

    latest = await service.open(context, "Order", "ORD-10", "edit-order", 60)
    followup = SubmittedDocumentCommand("ORD-10", latest.document_token,
                                        "command-2", {"quantity": 3})
    host.fail_present = True
    with pytest.raises(GraphCommittedError):
        await service.accept(context, "Order", "edit-order", followup)
    host.fail_present = False
    recovered = await service.accept(context, "Order", "edit-order", followup)
    assert recovered.replayed and recovered.new_revision == 3 and host.mutations == 2

    async with aiosqlite.connect(path) as db:
        await db.execute("""CREATE TRIGGER reject_document_receipt BEFORE INSERT
            ON teaql_document_command_receipt WHEN NEW.command_id='command-trigger'
            BEGIN SELECT RAISE(ABORT, 'receipt rejected'); END""")
        await db.commit()
    latest = await service.open(context, "Order", "ORD-10", "edit-order", 60)
    with pytest.raises(RuntimeError, match="DOCUMENT_CATALOG_FAILED"):
        await service.accept(context, "Order", "edit-order", SubmittedDocumentCommand(
            "ORD-10", latest.document_token, "command-trigger", {"quantity": 3}))
    assert await row(path) == (3, 3) and await receipts(path) == 2

    host.switch_actor_on_apply = True
    with pytest.raises(RuntimeError, match="DOCUMENT_AUTHORIZATION_REQUIRED"):
        await service.accept(context, "Order", "edit-order", SubmittedDocumentCommand(
            "ORD-10", latest.document_token, "command-actor-drift", {"quantity": 3}))
    host.actor = replace(host.actor, subject="alice")
    assert await row(path) == (3, 3) and await receipts(path) == 2


@pytest.mark.asyncio
async def test_sqlite_document_journal_rejects_missing_replay_primary_key(tmp_path):
    path = str(tmp_path / "broken-receipt.sqlite")
    transport = SqliteTransport(path)
    await transport.execute_sql(CompiledQuery("""CREATE TABLE teaql_document_command_receipt (
        scope_hash TEXT NOT NULL,actor_hash TEXT NOT NULL,command_id TEXT NOT NULL,
        request_hash TEXT NOT NULL,previous_revision BIGINT NOT NULL,
        new_revision BIGINT NOT NULL,response TEXT NOT NULL)""", []))
    journal = SQLiteDocumentCommandJournal(transport)
    await journal.ensure_schema()
    with pytest.raises(RuntimeError, match="DOCUMENT_SCHEMA_MISSING"):
        await journal.validate_schema()
