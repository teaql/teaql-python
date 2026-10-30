"""A real SQLite application host exercises the optional secure-document service."""

from dataclasses import replace
from datetime import datetime, timezone
import hashlib
import json
import time

import aiosqlite
import pytest

from teaql.core.value import Value
from teaql.core.blob_ref import BlobRef
from teaql.provider.sqlite.dialect import SqliteDialect
from teaql.provider.sqlite.transport import SqliteTransport
from teaql.runtime import RuntimeModule
from teaql.runtime.graph_session import GraphCommittedError
from teaql.sql.executor import SqlDataServiceExecutor
from teaql.sql.types import CompiledQuery
from teaql.provider.sqlite import SimpleSchemaProvider
from teaql_secure_document_reference import (
    BlobSelectionClaim, BlobSelectionTarget, BoundDocumentSnapshot,
    ContextualDocument, CurrentBoundDocument, DocumentBlobBindingSnapshot,
    DocumentBlobSelectionSubmission,
    DocumentEntitySnapshot, DocumentRelationSnapshot, DocumentSnapshot, ReferenceDocumentScope,
    ReferenceIdentity, ReferenceKey, RoundTripReferenceError,
    SecureDocumentReferenceModule,
    SQLiteContextBoundDocumentService, SQLiteDocumentCommandJournal,
    StaticReferenceKeyProvider, SubmittedDocumentCommand, TrustedReferencePrincipal,
)
from teaql_blob_reference import (BlobBindingChange, BlobBindingTarget,
                                  BlobRetentionPolicy, SqliteBlobCatalog)


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


async def fixture(tmp_path, transport_factory=SqliteTransport):
    path = str(tmp_path / "secure-document.sqlite")
    async with aiosqlite.connect(path) as db:
        await db.execute("""CREATE TABLE document_order (id INTEGER PRIMARY KEY,
            business_id TEXT NOT NULL UNIQUE,version INTEGER NOT NULL,quantity INTEGER NOT NULL)""")
        await db.execute("CREATE TABLE document_permission(subject TEXT PRIMARY KEY,can_edit INTEGER NOT NULL)")
        await db.execute("INSERT INTO document_order VALUES (10,'ORD-10',1,1)")
        await db.execute("INSERT INTO document_permission VALUES ('alice',1)")
        await db.commit()
    transport = transport_factory(path)
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
async def test_document_commit_unknown_replays_durable_receipt_under_current_authority(tmp_path):
    class LostReplyTransport(SqliteTransport):
        lose_next = False

        async def begin_sql(self):
            transaction = await super().begin_sql()
            if not self.lose_next:
                return transaction
            self.lose_next = False

            class CommitThenFail:
                def __getattr__(self, name):
                    return getattr(transaction, name)

                async def commit_sql(self):
                    await transaction.commit_sql()
                    raise OSError("document commit acknowledgement unavailable")

            return CommitThenFail()

    transports = []
    def make_transport(path):
        transport = LostReplyTransport(path)
        transports.append(transport)
        return transport

    path, context, host, service = await fixture(tmp_path, make_transport)
    async with aiosqlite.connect(path) as db:
        await db.execute("ALTER TABLE document_order ADD COLUMN hidden_note TEXT NOT NULL DEFAULT 'server-only'")
        await db.commit()
    opened = await service.open(context, "Order", "ORD-10", "edit-order", 60)
    command = SubmittedDocumentCommand("ORD-10", opened.document_token,
        "command-commit-unknown", {"quantity": 3})
    transports[0].lose_next = True
    with pytest.raises(OSError, match="commit acknowledgement unavailable"):
        await service.accept(context, "Order", "edit-order", command)
    assert await row(path) == (2, 3) and await receipts(path) == 1
    assert host.mutations == 1

    async def durable_receipt():
        async with aiosqlite.connect(path) as db:
            async with db.execute("SELECT * FROM teaql_document_command_receipt") as cursor:
                return await cursor.fetchall()

    original = await durable_receipt()
    async with aiosqlite.connect(path) as db:
        await db.execute("UPDATE document_permission SET can_edit=0 WHERE subject='alice'")
        await db.commit()
    with pytest.raises(RuntimeError, match="DOCUMENT_AUTHORIZATION_REQUIRED"):
        await service.accept(context, "Order", "edit-order", command)
    async with aiosqlite.connect(path) as db:
        await db.execute("UPDATE document_permission SET can_edit=1 WHERE subject='alice'")
        await db.commit()
    with pytest.raises(RuntimeError, match="DOCUMENT_REPLAY_CONFLICT"):
        await service.accept(context, "Order", "edit-order", replace(command, body={"quantity": 4}))
    recovered = await service.accept(context, "Order", "edit-order", command)
    assert recovered.replayed and recovered.new_revision == 2
    assert host.mutations == 1 and await row(path) == (2, 3)
    assert await durable_receipt() == original
    async with aiosqlite.connect(path) as db:
        async with db.execute("SELECT hidden_note FROM document_order WHERE id=10") as cursor:
            assert await cursor.fetchone() == ("server-only",)


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


class BlobOrderHost(OrderHost):
    def __init__(self, catalog):
        super().__init__()
        self.catalog = catalog

    async def load(self, context, business_id, sql):
        current = await super().load(context, business_id, sql)
        rows = await sql.fetch_all_sql(CompiledQuery(
            "SELECT blob_key FROM document_order WHERE business_id=?", [Value.Text(business_id)]))
        bindings = await sql.fetch_all_sql(CompiledQuery(
            "SELECT key,version FROM teaql_blob_binding WHERE scope=? AND entity=? "
            "AND entity_id=? AND field=?", [Value.Text("merchant:7"), Value.Text("Order"),
                Value.Text("10"), Value.Text("attachment")]))
        assert len(rows) == 1 and len(bindings) <= 1
        binding = bindings[0] if bindings else {"key": None, "version": 0}
        assert rows[0]["blob_key"] == binding["key"]
        entity = current.document.snapshot.entities[0]
        entity = replace(entity, loaded_fields=frozenset({"attachment", "quantity"}),
                         writable_fields=frozenset({"attachment", "quantity"}))
        snapshot = replace(current.document.snapshot, entities=(entity,))
        bound = DocumentBlobBindingSnapshot("order:10", "attachment", "Order",
                                            binding["key"], binding["version"], True, True)
        return replace(current, document=BoundDocumentSnapshot(snapshot, (bound,)))

    async def bind_blob_selection(self, _context, graph, selection, sql):
        assert (selection.target.target_entity, selection.target.target_key,
                selection.target.canonical_field, selection.entity_id) == (
                    "Order", "order:10", "attachment", "10")
        affected, _ = await sql.execute_sql(CompiledQuery(
            "UPDATE document_order SET blob_key=? WHERE id=?",
            [Value.Text(selection.stable_key), Value.I64(10)]))
        assert affected == 1

        class Authorization:
            def scope(self, _actor):
                return "merchant:7"

            async def current_policy_on_lease(self, _actor, lease, _target):
                assert lease is sql
                return BlobRetentionPolicy("default", "server_stream", 86400, 604800, 3600)

            async def authorize(self, _actor, target, _previous, next_ref, _action):
                return (target == BlobBindingTarget("Order", "10", "attachment") and
                        next_ref == BlobRef.from_sql(selection.stable_key))

        await self.catalog.bind_in_graph(graph, graph.context,
            BlobBindingChange(BlobBindingTarget("Order", "10", "attachment"),
                              BlobRef.from_sql(selection.stable_key),
                              selection.expected_version, selection.next_version, "Update"),
            Authorization(), lease=sql)


class ChildBlobOrderHost(BlobOrderHost):
    def __init__(self, catalog):
        super().__init__(catalog)
        self.wrong_resolve = False

    async def load(self, context, business_id, sql):
        current = await super().load(context, business_id, sql)
        children = await sql.fetch_all_sql(CompiledQuery(
            "SELECT id,version,blob_key FROM document_order_line WHERE order_id=? ORDER BY id",
            [Value.I64(10)]))
        entities = list(current.document.snapshot.entities)
        bindings = list(current.document.bindings)
        row_keys = []
        for child in children:
            row_key = f"line:{child['id']}"
            row_keys.append(row_key)
            actual = await sql.fetch_all_sql(CompiledQuery(
                "SELECT key,version FROM teaql_blob_binding WHERE scope=? AND entity=? "
                "AND entity_id=? AND field=?", [Value.Text("merchant:7"), Value.Text("OrderLine"),
                    Value.Text(str(child["id"])), Value.Text("attachment")]))
            assert len(actual) <= 1
            binding = actual[0] if actual else {"key": None, "version": 0}
            assert child["blob_key"] == binding["key"]
            entities.append(DocumentEntitySnapshot(row_key,
                ReferenceIdentity("OrderLine", child["id"], child["version"]),
                frozenset({"attachment"}), frozenset({"attachment"}),
                frozenset({"UPDATE"})))
            bindings.append(DocumentBlobBindingSnapshot(row_key, "attachment", "OrderLine",
                binding["key"], binding["version"], True, True))
        relation = DocumentRelationSnapshot("lines", tuple(row_keys), "COMPLETE", True,
                                            frozenset({"CREATE_CHILD"}))
        snapshot = replace(current.document.snapshot, entities=tuple(entities),
                           relations=(relation,))
        return replace(current, document=BoundDocumentSnapshot(snapshot, tuple(bindings)))

    async def apply(self, context, issued, submitted, sql):
        await super().apply(context, issued, submitted, sql)
        for selection in submitted.blob_selections or ():
            if selection.kind != "NEW_CLIENT_KEY":
                continue
            assert selection.target_entity == "OrderLine" and selection.canonical_field == "attachment"
            assert selection.target_key in {"client-line-1", "client-line-2"}
            child_id = 21 if selection.target_key == "client-line-1" else 22
            affected, _ = await sql.execute_sql(CompiledQuery(
                "INSERT INTO document_order_line(id,order_id,client_key,version,blob_key) "
                "VALUES (?,?,?,?,NULL)", [Value.I64(child_id), Value.I64(10),
                    Value.Text(selection.target_key), Value.I64(1)]))
            assert affected == 1

    async def resolve_new_blob_selection(self, _context, _issued, _submitted, selection, sql):
        if self.wrong_resolve:
            return "order:10", "10"
        children = await sql.fetch_all_sql(CompiledQuery(
            "SELECT id FROM document_order_line WHERE order_id=? AND client_key=?",
            [Value.I64(10), Value.Text(selection.target.target_key)]))
        assert len(children) == 1
        return f"line:{children[0]['id']}", str(children[0]["id"])

    async def bind_blob_selection(self, context, graph, selection, sql):
        if selection.target.kind != "NEW_CLIENT_KEY":
            return await super().bind_blob_selection(context, graph, selection, sql)
        assert selection.target.target_entity == "OrderLine" and selection.row_key == f"line:{selection.entity_id}"
        affected, _ = await sql.execute_sql(CompiledQuery(
            "UPDATE document_order_line SET blob_key=? WHERE id=?",
            [Value.Text(selection.stable_key), Value.I64(int(selection.entity_id))]))
        assert affected == 1

        class Authorization:
            def scope(self, _actor):
                return "merchant:7"

            async def current_policy_on_lease(self, _actor, lease, _target):
                assert lease is sql
                return BlobRetentionPolicy("default", "server_stream", 86400, 604800, 3600)

            async def authorize(self, _actor, target, _previous, next_ref, action):
                return (target == BlobBindingTarget("OrderLine", selection.entity_id, "attachment")
                        and next_ref == BlobRef.from_sql(selection.stable_key) and action == "Create")

        await self.catalog.bind_in_graph(graph, graph.context,
            BlobBindingChange(BlobBindingTarget("OrderLine", selection.entity_id, "attachment"),
                              BlobRef.from_sql(selection.stable_key),
                              selection.expected_version, selection.next_version, "Create"),
            Authorization(), lease=sql)


@pytest.mark.asyncio
async def test_sqlite_new_child_blob_selection_commits_and_receipt_failure_rolls_back(tmp_path):
    path, context, _old_host, old_service = await fixture(tmp_path)
    async with aiosqlite.connect(path) as db:
        await db.execute("ALTER TABLE document_order ADD COLUMN blob_key TEXT")
        await db.execute("""CREATE TABLE document_order_line (
            id INTEGER PRIMARY KEY, order_id INTEGER NOT NULL, client_key TEXT UNIQUE NOT NULL,
            version INTEGER NOT NULL, blob_key TEXT)""")
        await db.commit()
    catalog = SqliteBlobCatalog(old_service.transport)
    await catalog.ensure_schema()
    await catalog.validate_schema()
    async with aiosqlite.connect(path) as db:
        for key in ("blob_C", "blob_D"):
            await db.execute("""INSERT INTO teaql_blob_catalog
                (key,scope,object_key,content_version,file_name,content_type,size_bytes,status,
                 completed_at_ms,policy_profile,upload_mode,unbound_retention_seconds,effective_unref_seconds)
                VALUES (?,?,?,?,?,?,?,'uploaded_unbound',?,?,?,?,?)""",
                (key, "merchant:7", "objects/" + key, "v1", key + ".pdf", "application/pdf", 3,
                 time.time_ns() // 1_000_000, "default", "server_stream", 86400, 604800))
        await db.commit()
    host = ChildBlobOrderHost(catalog)
    service = SQLiteContextBoundDocumentService(context, old_service.transport,
        old_service.module, old_service.journal, host)

    async def selected(opened, command_id, client_key, blob_key):
        issued = service.module.consume_bound_document_snapshot(host.actor,
            opened.document_token, "Order", "edit-order").document
        target = BlobSelectionTarget(issued.snapshot.scope, "OrderLine", "attachment",
                                     "NEW_CLIENT_KEY", client_key, command_id)
        token = service.module.issue_blob_selection(host.actor, opened.document_token,
            BlobSelectionClaim(target, blob_key), 60)
        return DocumentBlobSelectionSubmission(token, "OrderLine", "attachment",
                                               "NEW_CLIENT_KEY", client_key)

    opened = await service.open(context, "Order", "ORD-10", "edit-order", 60)
    command = SubmittedDocumentCommand("ORD-10", opened.document_token, "command-child-1",
        {"quantity": 3}, (await selected(opened, "command-child-1", "client-line-1", "blob_C"),))
    host.wrong_resolve = True
    with pytest.raises(RuntimeError, match="DOCUMENT_PROJECTION_VIOLATION"):
        await service.accept(context, "Order", "edit-order", command)
    assert await row(path) == (1, 1) and await receipts(path) == 0
    host.wrong_resolve = False
    first = await service.accept(context, "Order", "edit-order", command)
    assert (first.previous_revision, first.new_revision, first.replayed) == (1, 2, False)
    assert (await service.accept(context, "Order", "edit-order", command)).replayed
    async with aiosqlite.connect(path) as db:
        async with db.execute("SELECT id,version,blob_key FROM document_order_line") as cursor:
            assert await cursor.fetchone() == (21, 1, "blob_C")
        async with db.execute("SELECT key,version FROM teaql_blob_binding WHERE entity='OrderLine'") as cursor:
            assert await cursor.fetchone() == ("blob_C", 1)
        async with db.execute("SELECT status FROM teaql_blob_catalog WHERE key='blob_C'") as cursor:
            assert await cursor.fetchone() == ("available",)
    assert await row(path) == (2, 3) and await receipts(path) == 1

    opened = await service.open(context, "Order", "ORD-10", "edit-order", 60)
    failed = SubmittedDocumentCommand("ORD-10", opened.document_token, "command-child-2",
        {"quantity": 3}, (await selected(opened, "command-child-2", "client-line-2", "blob_D"),))
    async with aiosqlite.connect(path) as db:
        await db.execute("""CREATE TRIGGER reject_child_receipt BEFORE INSERT
            ON teaql_document_command_receipt WHEN NEW.command_id='command-child-2'
            BEGIN SELECT RAISE(ABORT, 'receipt rejected'); END""")
        await db.commit()
    with pytest.raises(RuntimeError, match="DOCUMENT_CATALOG_FAILED"):
        await service.accept(context, "Order", "edit-order", failed)
    async with aiosqlite.connect(path) as db:
        async with db.execute("SELECT COUNT(*) FROM document_order_line") as cursor:
            assert await cursor.fetchone() == (1,)
        async with db.execute("SELECT COUNT(*) FROM teaql_blob_binding WHERE entity_id='22'") as cursor:
            assert await cursor.fetchone() == (0,)
        async with db.execute("SELECT status FROM teaql_blob_catalog WHERE key='blob_D'") as cursor:
            assert await cursor.fetchone() == ("uploaded_unbound",)
    assert await row(path) == (2, 3) and await receipts(path) == 1


@pytest.mark.asyncio
async def test_sqlite_document_blob_selection_shares_business_binding_and_receipt(tmp_path):
    path, context, _old_host, old_service = await fixture(tmp_path)
    async with aiosqlite.connect(path) as db:
        await db.execute("ALTER TABLE document_order ADD COLUMN blob_key TEXT")
        await db.commit()
    catalog = SqliteBlobCatalog(old_service.transport)
    await catalog.ensure_schema()
    await catalog.validate_schema()
    async with aiosqlite.connect(path) as db:
        for key in ("blob_A", "blob_B"):
            await db.execute("""INSERT INTO teaql_blob_catalog
                (key,scope,object_key,content_version,file_name,content_type,size_bytes,status,
                 completed_at_ms,policy_profile,upload_mode,unbound_retention_seconds,effective_unref_seconds)
                VALUES (?,?,?,?,?,?,?,'uploaded_unbound',?,?,?,?,?)""",
                (key, "merchant:7", "objects/" + key, "v1", key + ".pdf", "application/pdf", 3,
                 time.time_ns() // 1_000_000, "default", "server_stream", 86400, 604800))
        await db.commit()
    host = BlobOrderHost(catalog)
    service = SQLiteContextBoundDocumentService(context, old_service.transport,
        old_service.module, old_service.journal, host)

    async def open_document():
        return await service.open(context, "Order", "ORD-10", "edit-order", 60)

    def selection(opened, command_id, key):
        issued = service.module.consume_bound_document_snapshot(host.actor,
            opened.document_token, "Order", "edit-order").document
        target = BlobSelectionTarget(issued.snapshot.scope, "Order", "attachment",
                                     "EXISTING_ROW", "order:10", command_id)
        token = service.module.issue_blob_selection(host.actor, opened.document_token,
            BlobSelectionClaim(target, key), 60)
        return DocumentBlobSelectionSubmission(token, "Order", "attachment",
                                               "EXISTING_ROW", "order:10")

    opened = await open_document()
    command = SubmittedDocumentCommand("ORD-10", opened.document_token, "command-1",
        {"quantity": 3}, (selection(opened, "command-1", "blob_A"),))
    first = await service.accept(context, "Order", "edit-order", command)
    assert (first.previous_revision, first.new_revision, first.replayed) == (1, 2, False)
    async with aiosqlite.connect(path) as db:
        async with db.execute("SELECT version,quantity,blob_key FROM document_order") as cursor:
            assert await cursor.fetchone() == (2, 3, "blob_A")
        async with db.execute("SELECT key,version FROM teaql_blob_binding") as cursor:
            assert await cursor.fetchone() == ("blob_A", 1)
        async with db.execute("SELECT status FROM teaql_blob_catalog WHERE key='blob_A'") as cursor:
            assert await cursor.fetchone() == ("available",)
    assert await receipts(path) == 1
    replayed = await service.accept(context, "Order", "edit-order", command)
    assert replayed.replayed and host.mutations == 1
    legacy_parts = [command.business_id, command.document_token, command.command_id,
                    command.body, [item.__dict__ for item in command.blob_selections]]
    legacy_hash = hashlib.sha256(json.dumps(legacy_parts, ensure_ascii=False,
        separators=(",", ":"), sort_keys=True).encode("utf-8")).hexdigest()
    async with aiosqlite.connect(path) as db:
        async with db.execute("SELECT request_hash FROM teaql_document_command_receipt") as cursor:
            assert (await cursor.fetchone())[0] != legacy_hash
        await db.execute("UPDATE teaql_document_command_receipt SET request_hash=?", (legacy_hash,))
        await db.commit()
    old_replay = await service.accept(context, "Order", "edit-order", command)
    assert old_replay.replayed and host.mutations == 1
    with pytest.raises(RuntimeError, match="DOCUMENT_REPLAY_CONFLICT"):
        await service.accept(context, "Order", "edit-order", replace(command, blob_selections=None))
    oversized = DocumentBlobSelectionSubmission("tqs1." + "A" * (256000 - 5),
        "Order", "attachment", "EXISTING_ROW", "order:10")
    with pytest.raises(RuntimeError, match="DOCUMENT_COMMAND_INVALID"):
        await service.accept(context, "Order", "edit-order",
            replace(command, blob_selections=(oversized,)))

    fresh = await open_document()
    wrong = SubmittedDocumentCommand("ORD-10", fresh.document_token, "command-wrong",
        {"quantity": 3}, (selection(fresh, "other-command", "blob_A"),))
    with pytest.raises(RoundTripReferenceError, match="ROUND_TRIP_REFERENCE_SCOPE_MISMATCH"):
        await service.accept(context, "Order", "edit-order", wrong)
    duplicate = selection(fresh, "command-duplicate", "blob_A")
    with pytest.raises(RuntimeError, match="DOCUMENT_COMMAND_INVALID"):
        await service.accept(context, "Order", "edit-order", SubmittedDocumentCommand(
            "ORD-10", fresh.document_token, "command-duplicate", {"quantity": 3},
            (duplicate, duplicate)))
    with pytest.raises(RuntimeError, match="BLOB_BIND_DENIED"):
        await service.accept(context, "Order", "edit-order", SubmittedDocumentCommand(
            "ORD-10", fresh.document_token, "command-missing", {"quantity": 3},
            (selection(fresh, "command-missing", "blob_missing"),)))
    assert await row(path) == (2, 3) and await receipts(path) == 1

    async with aiosqlite.connect(path) as db:
        await db.execute("""CREATE TRIGGER reject_selected_receipt BEFORE INSERT
            ON teaql_document_command_receipt WHEN NEW.command_id='command-receipt-fail'
            BEGIN SELECT RAISE(ABORT, 'receipt rejected'); END""")
        await db.commit()
    with pytest.raises(RuntimeError, match="DOCUMENT_CATALOG_FAILED"):
        await service.accept(context, "Order", "edit-order", SubmittedDocumentCommand(
            "ORD-10", fresh.document_token, "command-receipt-fail", {"quantity": 3},
            (selection(fresh, "command-receipt-fail", "blob_B"),)))
    async with aiosqlite.connect(path) as db:
        async with db.execute("SELECT version,quantity,blob_key FROM document_order") as cursor:
            assert await cursor.fetchone() == (2, 3, "blob_A")
        async with db.execute("SELECT key,version FROM teaql_blob_binding") as cursor:
            assert await cursor.fetchone() == ("blob_A", 1)
        async with db.execute("SELECT status FROM teaql_blob_catalog WHERE key='blob_B'") as cursor:
            assert await cursor.fetchone() == ("uploaded_unbound",)
    assert await receipts(path) == 1
