"""Detached, context-authorized view preparation after business completion."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Protocol
from urllib.parse import urlsplit

from teaql.core.blob_ref import BlobRef

from .context import UserContext


@dataclass(frozen=True)
class ViewOptions:
    mode: str  # ordinary or governed; selected by the trusted host
    business_outcome: str  # read_only or committed
    expires_at: datetime | None = None


@dataclass(frozen=True)
class AuthorizedBlobSlot:
    path: tuple[str | int, ...]
    entity: str
    entity_id: str
    field: str
    scope: str
    binding_version: int
    reference: BlobRef


@dataclass(frozen=True)
class AuthorizedResponseGraph:
    presentation: Any
    blob_slots: tuple[AuthorizedBlobSlot, ...]


class ResponseGraphAuthorizer(Protocol):
    async def authorize(self, context: UserContext, result: Any,
                        options: ViewOptions) -> AuthorizedResponseGraph: ...


@dataclass(frozen=True)
class PreparedSecureDocument:
    graph: AuthorizedResponseGraph
    envelope: Any
    expires_at: datetime


class SecureDocumentContributor(Protocol):
    async def prepare(self, context: UserContext, graph: AuthorizedResponseGraph,
                      options: ViewOptions) -> PreparedSecureDocument: ...


@dataclass(frozen=True)
class ProjectedBlobURL:
    url: str
    expires_at: datetime


class BlobResponseContributor(Protocol):
    async def project_batch(self, context: UserContext, graph: AuthorizedResponseGraph,
                            expires_at: datetime | None) -> tuple[ProjectedBlobURL, ...]: ...


@dataclass(frozen=True)
class PreparedView:
    presentation: Any
    document: Any
    expires_at: datetime | None
    cache_control: str = "private, no-store"


_SAFE_CODES = frozenset({
    "VIEW_OPTIONS_INVALID", "VIEW_AUTHORIZER_MISSING", "VIEW_GRAPH_INVALID",
    "DOCUMENT_CONFIGURATION", "BLOB_CAPABILITY_MISSING", "BLOB_SIGN_FAILED",
    "BLOB_READ_DENIED", "BLOB_REFERENCE_EXPIRED", "BLOB_SCHEMA_MISSING",
    "BLOB_CATALOG_FAILED",
})


class ViewPreparationError(Exception):
    def __init__(self, code: str, business_state: str = "read_only") -> None:
        self.code = code
        self.business_state = business_state
        super().__init__(code)

    @property
    def retry(self) -> str:
        return "read" if self.business_state == "committed" else "prepare"


def _fail(code: str) -> None:
    raise ViewPreparationError(code)


def _detached(value: Any, depth: int = 0, budget: list[int] | None = None) -> Any:
    if budget is None:
        budget = [100_000]
    budget[0] -= 1
    if budget[0] < 0 or depth > 64:
        _fail("VIEW_GRAPH_INVALID")
    if value is None or type(value) in (bool, int, float, str, BlobRef, datetime):
        return value
    if type(value) is dict:
        if len(value) > budget[0] or any(type(key) is not str for key in value):
            _fail("VIEW_GRAPH_INVALID")
        return {key: _detached(child, depth + 1, budget) for key, child in value.items()}
    if type(value) is list:
        if len(value) > budget[0]:
            _fail("VIEW_GRAPH_INVALID")
        return [_detached(child, depth + 1, budget) for child in value]
    _fail("VIEW_GRAPH_INVALID")


def _path_key(path: tuple[str | int, ...]) -> tuple[tuple[str, str | int], ...]:
    if not path or len(path) > 64:
        _fail("VIEW_GRAPH_INVALID")
    key = []
    for part in path:
        if type(part) is str and part:
            key.append(("s", part))
        elif type(part) is int and part >= 0:
            key.append(("i", part))
        else:
            _fail("VIEW_GRAPH_INVALID")
    return tuple(key)


def _at_path(root: Any, path: tuple[str | int, ...]) -> Any:
    value = root
    for part in path:
        if type(part) is str and type(value) is dict and part in value:
            value = value[part]
        elif type(part) is int and type(value) is list and 0 <= part < len(value):
            value = value[part]
        else:
            _fail("VIEW_GRAPH_INVALID")
    return value


def _replace(root: Any, path: tuple[str | int, ...], value: str) -> None:
    _at_path(root, path)
    parent = _at_path(root, path[:-1])
    parent[path[-1]] = value


def _contains_blob(value: Any, depth: int = 0, budget: list[int] | None = None) -> bool:
    if budget is None:
        budget = [100_000]
    budget[0] -= 1
    if budget[0] < 0 or depth > 64:
        return True
    if type(value) is BlobRef:
        return True
    if type(value) is dict:
        return any(_contains_blob(child, depth + 1, budget) for child in value.values())
    if type(value) is list:
        return any(_contains_blob(child, depth + 1, budget) for child in value)
    return False


def _earlier(left: datetime | None, right: datetime) -> datetime:
    if left is None:
        return right
    return min(left, right)


def _future(value: datetime) -> bool:
    return value.tzinfo is not None and value > datetime.now(timezone.utc)


class ViewPreparationService:
    async def prepare(self, context: UserContext, result: Any,
                      options: ViewOptions) -> PreparedView:
        state = "committed" if getattr(options, "business_outcome", None) == "committed" else "read_only"
        try:
            if (context is None or not isinstance(options, ViewOptions)
                    or options.mode not in ("ordinary", "governed")
                    or options.business_outcome not in ("read_only", "committed")
                    or (options.expires_at is not None and not _future(options.expires_at))):
                _fail("VIEW_OPTIONS_INVALID")
            authorizer = context.get_resource("response_graph_authorizer")
            if authorizer is None:
                _fail("VIEW_AUTHORIZER_MISSING")
            graph = await authorizer.authorize(context, result, options)
            if type(graph.blob_slots) not in (tuple, list) or len(graph.blob_slots) > 10_000:
                _fail("VIEW_GRAPH_INVALID")
            graph = AuthorizedResponseGraph(_detached(graph.presentation),
                                            tuple(graph.blob_slots))
            expiry = options.expires_at
            document = None
            if options.mode == "governed":
                secure = context.get_resource("secure_document_contributor")
                if secure is None:
                    _fail("DOCUMENT_CONFIGURATION")
                prepared = await secure.prepare(context, graph, options)
                if not _future(prepared.expires_at):
                    _fail("DOCUMENT_CONFIGURATION")
                graph, document = prepared.graph, prepared.envelope
                if type(graph.blob_slots) not in (tuple, list) or len(graph.blob_slots) > 10_000:
                    _fail("VIEW_GRAPH_INVALID")
                expiry = _earlier(expiry, prepared.expires_at)
            presentation = _detached(graph.presentation)
            paths: set[tuple[tuple[str, str | int], ...]] = set()
            for slot in graph.blob_slots:
                path = _path_key(slot.path)
                if path in paths or _at_path(presentation, slot.path) != slot.reference or \
                        type(_at_path(presentation, slot.path)) is not BlobRef:
                    _fail("VIEW_GRAPH_INVALID")
                paths.add(path)
            if graph.blob_slots:
                contributor = context.get_resource("blob_response_contributor")
                if contributor is None:
                    _fail("BLOB_CAPABILITY_MISSING")
                ceiling = expiry
                urls = await contributor.project_batch(context, graph, ceiling)
                if len(urls) != len(graph.blob_slots):
                    _fail("BLOB_SIGN_FAILED")
                for slot, signed in zip(graph.blob_slots, urls):
                    parsed = urlsplit(signed.url)
                    if (parsed.scheme not in ("http", "https") or not parsed.hostname
                            or not _future(signed.expires_at)
                            or (ceiling is not None and signed.expires_at > ceiling)):
                        _fail("BLOB_SIGN_FAILED")
                    _replace(presentation, slot.path, signed.url)
                    expiry = _earlier(expiry, signed.expires_at)
            if _contains_blob(presentation):
                _fail("BLOB_CAPABILITY_MISSING")
            return PreparedView(presentation, document, expiry)
        except Exception as exc:
            code = exc.code if isinstance(exc, ViewPreparationError) and exc.code in _SAFE_CODES \
                else "VIEW_PREPARATION_FAILED"
            raise ViewPreparationError(code, state) from None
