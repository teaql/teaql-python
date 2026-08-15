from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from typing import Any, Awaitable, Callable, Generic, Protocol, TypeVar, cast

from .context import UserContext

T = TypeVar("T")


class ToolRisk(str, Enum):
    MEMORY_ONLY = "MEMORY_ONLY"
    EXTERNAL_RESOURCE = "EXTERNAL_RESOURCE"
    PRIVILEGED = "PRIVILEGED"


@dataclass(frozen=True)
class ToolToken(Generic[T]):
    id: str
    risk: ToolRisk


class ToolProvider(Protocol[T]):
    token: ToolToken[T]

    def create(self, context: UserContext) -> T: ...


class ToolError(RuntimeError):
    pass


class ToolUnavailableError(ToolError):
    pass


class ToolDeniedError(ToolError):
    pass


@dataclass(frozen=True)
class ToolPolicy:
    allowed: frozenset[str] = frozenset()
    allow_memory_only: bool = True

    @classmethod
    def standard(cls) -> ToolPolicy:
        return cls()

    @classmethod
    def deny_all(cls) -> ToolPolicy:
        return cls(allow_memory_only=False)

    @classmethod
    def allowing(cls, *tokens: ToolToken[Any]) -> ToolPolicy:
        return cls(frozenset(token.id for token in tokens))

    def allows(self, token: ToolToken[Any]) -> bool:
        return ((token.risk is ToolRisk.MEMORY_ONLY and self.allow_memory_only)
                or token.id in self.allowed)


class Tools:
    def __init__(self, context: UserContext, policy: ToolPolicy,
                 providers: list[ToolProvider[Any]]) -> None:
        self._context = context
        self._policy = policy
        self._providers = {provider.token.id: provider for provider in providers}

    def has(self, token: ToolToken[Any]) -> bool:
        return token.id in self._providers

    def get(self, token: ToolToken[T]) -> T:
        provider = self._providers.get(token.id)
        if provider is None:
            raise ToolUnavailableError(f"Tool not available: {token.id}")
        if not self._policy.allows(token):
            raise ToolDeniedError(f"Tool denied by policy: {token.id}")
        return cast(T, provider.create(self._context))

    def descriptors(self) -> tuple[ToolToken[Any], ...]:
        return tuple(provider.token for provider in self._providers.values())


class ContextTools:
    @staticmethod
    def builder(context: UserContext) -> ContextToolsBuilder:
        return ContextToolsBuilder(context)

    @staticmethod
    def of(context: UserContext) -> Tools:
        return ContextTools.builder(context).build()


class ContextToolsBuilder:
    def __init__(self, context: UserContext) -> None:
        self._context = context
        self._policy = ToolPolicy.standard()
        self._providers: list[ToolProvider[Any]] = []

    def policy(self, policy: ToolPolicy) -> ContextToolsBuilder:
        self._policy = policy
        return self

    def provider(self, provider: ToolProvider[Any]) -> ContextToolsBuilder:
        self._providers.append(provider)
        return self

    def build(self) -> Tools:
        return Tools(self._context, self._policy, list(self._providers))


HTTPTransport = Callable[[str, str, bytes | None], Awaitable[tuple[int, bytes]]]


class ExecutableHttpTool:
    def __init__(self, transport: HTTPTransport, method: str, url: str,
                 body: bytes | None, intent: str) -> None:
        self._transport = transport
        self._method = method
        self._url = url
        self._body = body
        self._intent = intent

    async def execute(self) -> str:
        if not self._intent.strip():
            raise ToolError("HTTP tool execution requires non-empty intent")
        status, data = await self._transport(self._method, self._url, self._body)
        if status < 200 or status >= 300:
            raise ToolError(f"HTTP tool failed: {status}")
        return data.decode("utf-8")


class HttpIntentPhase:
    def __init__(self, transport: HTTPTransport, method: str, url: str,
                 body: bytes | None) -> None:
        self._transport = transport
        self._method = method
        self._url = url
        self._body = body

    def purpose(self, intent: str) -> ExecutableHttpTool:
        return ExecutableHttpTool(self._transport, self._method, self._url, self._body, intent)

    def audit_as(self, intent: str) -> ExecutableHttpTool:
        return ExecutableHttpTool(self._transport, self._method, self._url, self._body, intent)


class HttpTool:
    def __init__(self, transport: HTTPTransport) -> None:
        self._transport = transport

    def get(self, url: str) -> HttpIntentPhase:
        return HttpIntentPhase(self._transport, "GET", url, None)

    def post(self, url: str, body: Any) -> HttpIntentPhase:
        return HttpIntentPhase(self._transport, "POST", url,
                               json.dumps(body, separators=(",", ":")).encode())


HTTP_TOOL: ToolToken[HttpTool] = ToolToken("http", ToolRisk.EXTERNAL_RESOURCE)


class HttpToolProvider:
    token = HTTP_TOOL

    def __init__(self, transport: HTTPTransport) -> None:
        self._transport = transport

    def create(self, context: UserContext) -> HttpTool:
        del context
        return HttpTool(self._transport)
