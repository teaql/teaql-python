"""Host-backed secure documents and durable command receipts on a physical SQLite graph."""

from __future__ import annotations

import hashlib
import json
import unicodedata
from dataclasses import dataclass
from typing import Any, Protocol

from teaql.core.value import Value
from teaql.runtime.graph_session import GraphCommittedError
from teaql.sql.types import CompiledQuery

from .document_round_trip import (
    BlobSelectionTarget, BoundDocumentSnapshot, SecureDocumentReferenceModule,
    _bindings, _encode_snapshot,
)
from .round_trip_reference import ReferenceDocumentScope, TrustedReferencePrincipal

_MAX_BYTES = 256000
_MAX_SAFE_INTEGER = (1 << 53) - 1


def _invalid(code: str) -> None:
    raise RuntimeError(code)


def _text(value: Any, maximum: int) -> bool:
    return (isinstance(value, str) and bool(value) and value == value.strip() and
            all(not unicodedata.category(ch).startswith("C") for ch in value) and
            len(value.encode("utf-8")) <= maximum)


def _copy_body(value: Any) -> dict[str, Any]:
    remaining = 100000

    def check(item: Any, depth: int) -> None:
        nonlocal remaining
        remaining -= 1
        if remaining < 0 or depth > 64:
            _invalid("DOCUMENT_COMMAND_INVALID")
        if item is None or type(item) is bool:
            return
        if type(item) is str:
            if len(item.encode("utf-8")) > _MAX_BYTES:
                _invalid("DOCUMENT_COMMAND_INVALID")
            return
        if type(item) is int:
            if abs(item) > _MAX_SAFE_INTEGER:
                _invalid("DOCUMENT_COMMAND_INVALID")
            return
        if type(item) is list:
            for child in item:
                check(child, depth + 1)
            return
        if type(item) is dict:
            for key, child in item.items():
                if not _text(key, 16384) or key in {"__proto__", "constructor", "prototype"}:
                    _invalid("DOCUMENT_COMMAND_INVALID")
                check(child, depth + 1)
            return
        _invalid("DOCUMENT_COMMAND_INVALID")

    if type(value) is not dict:
        _invalid("DOCUMENT_COMMAND_INVALID")
    check(value, 0)
    try:
        encoded = json.dumps(value, sort_keys=True, ensure_ascii=False,
                             separators=(",", ":"), allow_nan=False).encode("utf-8")
    except (UnicodeError, ValueError, TypeError, RecursionError):
        _invalid("DOCUMENT_COMMAND_INVALID")
    if len(encoded) > _MAX_BYTES:
        _invalid("DOCUMENT_COMMAND_INVALID")
    return json.loads(encoded)


def _hash_parts(*parts: Any) -> str:
    encoded = json.dumps(parts, ensure_ascii=False, separators=(",", ":"),
                         sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True, repr=False)
class SubmittedDocumentCommand:
    business_id: str
    document_token: str
    command_id: str
    body: dict[str, Any]
    blob_selections: tuple[DocumentBlobSelectionSubmission, ...] | None = None

    def __repr__(self) -> str:
        return "SubmittedDocumentCommand[redacted]"


@dataclass(frozen=True, repr=False)
class DocumentBlobSelectionSubmission:
    token: str
    target_entity: str
    canonical_field: str
    kind: str
    target_key: str

    def __repr__(self) -> str:
        return "DocumentBlobSelectionSubmission[redacted]"


@dataclass(frozen=True, repr=False)
class DocumentCommandReceipt:
    previous_revision: int
    new_revision: int
    response: str

    def __repr__(self) -> str:
        return "DocumentCommandReceipt[redacted]"


def _prepared(command: SubmittedDocumentCommand) -> tuple[str, SubmittedDocumentCommand]:
    if (not isinstance(command, SubmittedDocumentCommand) or
            not _text(command.business_id, 16384) or
            not _text(command.document_token, _MAX_BYTES) or
            not _text(command.command_id, 256)):
        _invalid("DOCUMENT_COMMAND_INVALID")
    copied = _copy_body(command.body)
    selections = command.blob_selections
    if selections is not None:
        if type(selections) is not tuple or len(selections) > 100:
            _invalid("DOCUMENT_COMMAND_INVALID")
        for selection in selections:
            if (not isinstance(selection, DocumentBlobSelectionSubmission) or
                    not all(_text(value, _MAX_BYTES if index == 0 else 16384)
                            for index, value in enumerate((selection.token,
                                selection.target_entity, selection.canonical_field,
                                selection.target_key))) or
                    selection.kind not in {"EXISTING_ROW", "NEW_CLIENT_KEY"}):
                _invalid("DOCUMENT_COMMAND_INVALID")
    # Keep the original digest for receipts written without selections.
    parts = [command.business_id, command.document_token, command.command_id, copied]
    if selections is not None:
        parts.append([selection.__dict__ for selection in selections])
    return _hash_parts(*parts), SubmittedDocumentCommand(
        command.business_id, command.document_token, command.command_id, copied, selections)


def _receipt(value: DocumentCommandReceipt) -> DocumentCommandReceipt:
    if (not isinstance(value, DocumentCommandReceipt) or
            type(value.previous_revision) is not int or
            type(value.new_revision) is not int or
            value.previous_revision < 0 or value.new_revision < value.previous_revision or
            not _text(value.response, _MAX_BYTES)):
        _invalid("DOCUMENT_COMMAND_INVALID")
    return value


def _scope_key(scope: ReferenceDocumentScope) -> str:
    scope.validate()
    return _hash_parts(scope.document_id, scope.purpose, scope.aggregate_type,
                       str(scope.aggregate_id))


def _actor_key(principal: TrustedReferencePrincipal) -> str:
    principal.wire()
    return _hash_parts(principal.authentication_realm, principal.subject,
                       principal.domain_root_type, str(principal.domain_root_id))


class SQLiteDocumentCommandJournal:
    """Receipt table installation is explicit; writes borrow a live graph SQL lease."""

    def __init__(self, transport) -> None:
        if transport is None:
            _invalid("DOCUMENT_CAPABILITY_MISSING")
        self.transport = transport

    async def ensure_schema(self) -> None:
        try:
            await self.transport.execute_sql(CompiledQuery("""CREATE TABLE IF NOT EXISTS
                teaql_document_command_receipt (
                scope_hash TEXT NOT NULL, actor_hash TEXT NOT NULL, command_id TEXT NOT NULL,
                request_hash TEXT NOT NULL, previous_revision BIGINT NOT NULL,
                new_revision BIGINT NOT NULL, response TEXT NOT NULL,
                PRIMARY KEY (scope_hash, actor_hash, command_id))""", []))
        except Exception:
            _invalid("DOCUMENT_CATALOG_FAILED")

    async def validate_schema(self) -> None:
        try:
            rows = await self.transport.fetch_all_sql(CompiledQuery(
                "PRAGMA table_info(teaql_document_command_receipt)", []))
        except Exception:
            _invalid("DOCUMENT_SCHEMA_MISSING")
        names = ("scope_hash", "actor_hash", "command_id", "request_hash",
                 "previous_revision", "new_revision", "response")
        if len(rows) != len(names):
            _invalid("DOCUMENT_SCHEMA_MISSING")
        for index, name in enumerate(names):
            row = rows[index]
            if (row.get("name") != name or row.get("notnull") != 1 or
                    row.get("pk") != (index + 1 if index < 3 else 0)):
                _invalid("DOCUMENT_SCHEMA_MISSING")

    async def apply_in_graph(self, graph, scope: ReferenceDocumentScope,
                             command: SubmittedDocumentCommand, authority, mutate
                             ) -> tuple[DocumentCommandReceipt, bool]:
        if graph is None or not callable(getattr(graph, "with_sql_transport", None)):
            _invalid("DOCUMENT_TRANSACTION_REQUIRED")
        scope_key = _scope_key(scope)
        request_hash, frozen = _prepared(command)

        async def work(sql):
            async def current_actor():
                try:
                    principal = await authority(graph.context, scope, sql)
                    return _actor_key(principal)
                except Exception:
                    _invalid("DOCUMENT_AUTHORIZATION_REQUIRED")

            actor_key = await current_actor()
            params = [Value.Text(scope_key), Value.Text(actor_key), Value.Text(command.command_id)]
            try:
                rows = await sql.fetch_all_sql(CompiledQuery("""SELECT request_hash,
                    previous_revision,new_revision,response FROM teaql_document_command_receipt
                    WHERE scope_hash=? AND actor_hash=? AND command_id=?""", params))
            except Exception:
                _invalid("DOCUMENT_CATALOG_FAILED")
            if len(rows) > 1:
                _invalid("DOCUMENT_CATALOG_FAILED")
            if rows:
                row = rows[0]
                if row.get("request_hash") != request_hash:
                    _invalid("DOCUMENT_REPLAY_CONFLICT")
                try:
                    found = _receipt(DocumentCommandReceipt(row["previous_revision"],
                                                            row["new_revision"], row["response"]))
                except (KeyError, RuntimeError):
                    _invalid("DOCUMENT_CATALOG_FAILED")
                if await current_actor() != actor_key:
                    _invalid("DOCUMENT_AUTHORIZATION_REQUIRED")
                return found, True
            produced = _receipt(await mutate(sql, frozen))
            if _prepared(frozen)[0] != request_hash or _prepared(command)[0] != request_hash:
                _invalid("DOCUMENT_COMMAND_INVALID")
            if await current_actor() != actor_key:
                _invalid("DOCUMENT_AUTHORIZATION_REQUIRED")
            try:
                affected, _ = await sql.execute_sql(CompiledQuery("""INSERT INTO
                    teaql_document_command_receipt
                    (scope_hash,actor_hash,command_id,request_hash,previous_revision,new_revision,response)
                    VALUES (?,?,?,?,?,?,?)""", [*params, Value.Text(request_hash),
                        Value.I64(produced.previous_revision), Value.I64(produced.new_revision),
                        Value.Text(produced.response)]))
            except Exception:
                _invalid("DOCUMENT_CATALOG_FAILED")
            if affected != 1:
                _invalid("DOCUMENT_CATALOG_FAILED")
            return produced, False

        return await graph.with_sql_transport(work)


@dataclass(frozen=True, repr=False)
class ContextualDocument:
    business_id: str
    document_token: str
    body: dict[str, Any]

    def __repr__(self) -> str:
        return "ContextualDocument[redacted]"


@dataclass(frozen=True, repr=False)
class AcceptedDocument:
    document: ContextualDocument
    previous_revision: int
    new_revision: int
    replayed: bool

    def __repr__(self) -> str:
        return "AcceptedDocument[redacted]"


@dataclass(frozen=True)
class CurrentBoundDocument:
    document: BoundDocumentSnapshot
    body: dict[str, Any]
    lifetime_seconds: int


@dataclass(frozen=True, repr=False)
class VerifiedDocumentBlobSelection:
    target: BlobSelectionTarget
    stable_key: str
    entity_id: str
    expected_version: int
    next_version: int

    def __repr__(self) -> str:
        return "VerifiedDocumentBlobSelection[redacted]"


def _verified_selections(module: SecureDocumentReferenceModule,
                         principal: TrustedReferencePrincipal, issued: BoundDocumentSnapshot,
                         command: SubmittedDocumentCommand) -> tuple[VerifiedDocumentBlobSelection, ...]:
    result = []
    seen = set()
    for selected in command.blob_selections or ():
        target = BlobSelectionTarget(issued.snapshot.scope, selected.target_entity,
                                     selected.canonical_field, selected.kind,
                                     selected.target_key, command.command_id)
        pair = (target.target_key, target.canonical_field)
        if pair in seen:
            _invalid("DOCUMENT_COMMAND_INVALID")
        seen.add(pair)
        claim = module.consume_blob_selection(principal, command.document_token,
                                              selected.token, target).document
        if target.kind != "EXISTING_ROW":
            _invalid("DOCUMENT_CAPABILITY_MISSING")
        row = next((item for item in issued.snapshot.entities
                    if item.row_key == target.target_key), None)
        binding = next((item for item in issued.bindings
                        if item.row_key == target.target_key and
                        item.canonical_field == target.canonical_field), None)
        if (row is None or binding is None or row.identity.entity_type != target.target_entity or
                not binding.writable or binding.binding_version >= (1 << 63) - 1):
            _invalid("DOCUMENT_PROJECTION_VIOLATION")
        result.append(VerifiedDocumentBlobSelection(target, claim.stable_key,
                      str(row.identity.id), binding.binding_version,
                      binding.binding_version + 1))
    return tuple(result)


class SQLiteContextBoundDocumentHost(Protocol):
    def principal(self, context) -> TrustedReferencePrincipal: ...
    async def authorize(self, context, principal: TrustedReferencePrincipal,
                        scope: ReferenceDocumentScope, sql) -> None: ...
    async def load(self, context, business_id: str, sql) -> CurrentBoundDocument: ...
    async def apply(self, context, issued: BoundDocumentSnapshot,
                    submitted: SubmittedDocumentCommand, sql) -> None: ...
    async def present(self, context, document: ContextualDocument) -> None: ...


def _valid_current(current: CurrentBoundDocument, business_id: str,
                   aggregate_type: str, purpose: str) -> None:
    if (not isinstance(current, CurrentBoundDocument) or
            current.document.snapshot.business_id != business_id or
            current.document.snapshot.scope.aggregate_type != aggregate_type or
            current.document.snapshot.scope.purpose != purpose or
            type(current.lifetime_seconds) is not int or current.lifetime_seconds <= 0):
        _invalid("DOCUMENT_PROJECTION_VIOLATION")
    try:
        _bound_fingerprint(current.document)
        _copy_body(current.body)
    except Exception:
        _invalid("DOCUMENT_PROJECTION_VIOLATION")


def _bound_fingerprint(document: BoundDocumentSnapshot):
    return (_encode_snapshot(document.snapshot, 2, bytes(32), 0, 1),
            _bindings(document))


class SQLiteContextBoundDocumentService:
    def __init__(self, context, transport, module: SecureDocumentReferenceModule,
                 journal: SQLiteDocumentCommandJournal, host: SQLiteContextBoundDocumentHost):
        if (context is None or transport is None or not callable(getattr(transport, "begin_sql", None))
                or not isinstance(module, SecureDocumentReferenceModule) or
                not isinstance(journal, SQLiteDocumentCommandJournal) or host is None):
            _invalid("DOCUMENT_CONFIGURATION")
        self.context, self.transport, self.module = context, transport, module
        self.journal, self.host = journal, host

    def _principal(self, context) -> TrustedReferencePrincipal:
        if context is not self.context:
            _invalid("DOCUMENT_CONFIGURATION")
        try:
            principal = self.host.principal(context)
            principal.wire()
            return principal
        except Exception:
            _invalid("DOCUMENT_AUTHORIZATION_REQUIRED")

    async def open(self, context, aggregate_type: str, business_id: str,
                   purpose: str, lifetime_seconds: int) -> ContextualDocument:
        if (not all(_text(v, 16384) for v in (aggregate_type, business_id, purpose)) or
                type(lifetime_seconds) is not int or lifetime_seconds <= 0):
            _invalid("DOCUMENT_COMMAND_INVALID")
        principal = self._principal(context)
        tx = await self.transport.begin_sql()
        committed = False
        try:
            current = await self.host.load(context, business_id, tx)
            _valid_current(current, business_id, aggregate_type, purpose)
            if self._principal(context) != principal:
                _invalid("DOCUMENT_AUTHORIZATION_REQUIRED")
            try:
                await self.host.authorize(context, principal, current.document.snapshot.scope, tx)
            except Exception:
                _invalid("DOCUMENT_AUTHORIZATION_REQUIRED")
            if self._principal(context) != principal:
                _invalid("DOCUMENT_AUTHORIZATION_REQUIRED")
            token = self.module.issue_bound_document_snapshot(
                principal, current.document, min(lifetime_seconds, current.lifetime_seconds))
            result = ContextualDocument(business_id, token, _copy_body(current.body))
            await tx.commit_sql()
            committed = True
        finally:
            if not committed:
                try:
                    await tx.rollback_sql()
                except Exception:
                    pass
        await self.host.present(context, result)
        return result

    async def accept(self, context, aggregate_type: str, purpose: str,
                     command: SubmittedDocumentCommand) -> AcceptedDocument:
        if not _text(aggregate_type, 16384) or not _text(purpose, 16384):
            _invalid("DOCUMENT_COMMAND_INVALID")
        principal = self._principal(context)
        _prepared(command)
        issued = self.module.consume_bound_document_snapshot(
            principal, command.document_token, aggregate_type, purpose).document
        scope = issued.snapshot.scope
        if issued.snapshot.business_id != command.business_id:
            _invalid("DOCUMENT_PROJECTION_VIOLATION")

        async def graph_work(graph):
            async def authority(_view, expected_scope, sql):
                current = self._principal(context)
                if current != principal or expected_scope != scope:
                    _invalid("DOCUMENT_AUTHORIZATION_REQUIRED")
                await self.host.authorize(context, current, expected_scope, sql)
                return current

            async def mutate(sql, frozen):
                before = await self.host.load(context, frozen.business_id, sql)
                _valid_current(before, frozen.business_id, aggregate_type, purpose)
                if _bound_fingerprint(before.document) != _bound_fingerprint(issued):
                    _invalid("DOCUMENT_REVISION_CONFLICT")
                selections = _verified_selections(self.module, principal, issued, frozen)
                binder = getattr(self.host, "bind_blob_selection", None)
                if selections and not callable(binder):
                    _invalid("DOCUMENT_CAPABILITY_MISSING")
                await self.host.apply(context, issued, frozen, sql)
                for selection in selections:
                    await binder(context, graph, selection, sql)
                after = await self.host.load(context, frozen.business_id, sql)
                _valid_current(after, frozen.business_id, aggregate_type, purpose)
                next_scope = after.document.snapshot.scope
                if (next_scope.document_id != scope.document_id or
                        next_scope.aggregate_id != scope.aggregate_id or
                        next_scope.aggregate_type != scope.aggregate_type or
                        next_scope.purpose != scope.purpose or
                        next_scope.aggregate_revision < scope.aggregate_revision):
                    _invalid("DOCUMENT_PROJECTION_VIOLATION")
                for selection in selections:
                    binding = next((item for item in after.document.bindings
                        if item.row_key == selection.target.target_key and
                        item.canonical_field == selection.target.canonical_field), None)
                    if (binding is None or binding.entity_type != selection.target.target_entity or
                            binding.stable_key != selection.stable_key or
                            binding.binding_version != selection.next_version):
                        _invalid("DOCUMENT_PROJECTION_VIOLATION")
                try:
                    await self.host.authorize(context, principal, next_scope, sql)
                except Exception:
                    _invalid("DOCUMENT_AUTHORIZATION_REQUIRED")
                token = self.module.issue_bound_document_snapshot(
                    principal, after.document, after.lifetime_seconds)
                body = _copy_body(after.body)
                response = json.dumps({"businessId": frozen.business_id,
                                       "documentToken": token, "body": body},
                                      sort_keys=True, ensure_ascii=False, separators=(",", ":"))
                return DocumentCommandReceipt(scope.aggregate_revision,
                                              next_scope.aggregate_revision, response)

            return await self.journal.apply_in_graph(graph, scope, command, authority, mutate)

        receipt, replayed = await context.execute_graph_save(
            graph_work, comment="accept protected document command")
        try:
            data = json.loads(receipt.response)
            if (type(data) is not dict or set(data) != {"businessId", "documentToken", "body"} or
                    data["businessId"] != command.business_id or
                    not _text(data["documentToken"], _MAX_BYTES)):
                _invalid("DOCUMENT_CATALOG_FAILED")
            if self._principal(context) != principal:
                _invalid("DOCUMENT_AUTHORIZATION_REQUIRED")
            verified = self.module.consume_bound_document_snapshot(
                principal, data["documentToken"], aggregate_type, purpose).document
            if (verified.snapshot.business_id != command.business_id or
                    verified.snapshot.scope.document_id != scope.document_id or
                    verified.snapshot.scope.aggregate_id != scope.aggregate_id or
                    verified.snapshot.scope.aggregate_revision != receipt.new_revision or
                    receipt.previous_revision != scope.aggregate_revision):
                _invalid("DOCUMENT_CATALOG_FAILED")
            result = ContextualDocument(command.business_id, data["documentToken"],
                                        _copy_body(data["body"]))
            await self.host.present(context, result)
        except Exception as error:
            raise GraphCommittedError((error,)) from None
        return AcceptedDocument(result, receipt.previous_revision,
                                receipt.new_revision, replayed)
