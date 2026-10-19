"""Typed, trusted Context extension contracts.

Protocols describe the minimum runtime-consumed shape. Optional lifecycle
hooks are not required just to install an adapter.
"""

from __future__ import annotations

from inspect import iscoroutinefunction
from typing import Any, Awaitable, Callable, Protocol, TYPE_CHECKING, runtime_checkable

from teaql.core.query import SelectQuery
from teaql.core.value import Value
from .audit import SafeAuditEvent
from .i18n import CheckResult, ObjectLocation
from .telemetry import (
    AttributeValue, NOOP_RUNTIME_TELEMETRY, RuntimeOperation, RuntimeTelemetryScope,
)

if TYPE_CHECKING:
    from .context import UserContext


@runtime_checkable
class RequestPolicy(Protocol):
    def apply(self, query: SelectQuery) -> SelectQuery | None: ...


RequestPolicyInput = RequestPolicy | Callable[[SelectQuery], SelectQuery | None]


@runtime_checkable
class Checker(Protocol):
    def check_and_fix(self, context: UserContext, record: dict[str, Value],
                      location: ObjectLocation | None, results: list[CheckResult]) -> None: ...


@runtime_checkable
class CheckerRegistry(Protocol):
    def checker(self, entity: str) -> Checker | None: ...


@runtime_checkable
class SchemaCapability(Protocol):
    async def _ensure_schema(self, context: UserContext, capability: object) -> None: ...


@runtime_checkable
class SafeAuditEventSink(Protocol):
    def on_safe_event(self, context: UserContext, event: SafeAuditEvent) -> None | Awaitable[None]: ...


@runtime_checkable
class RuntimeTelemetryAdapter(Protocol):
    def start(self, operation: RuntimeOperation) -> RuntimeTelemetryScope: ...


@runtime_checkable
class DiagnosticTelemetryAdapter(Protocol):
    def record_diagnostic(self, attributes: dict[str, AttributeValue], correlation: Any) -> None: ...


RuntimeTelemetryInput = RuntimeTelemetryAdapter | DiagnosticTelemetryAdapter


class _DiagnosticOnlyTelemetry:
    """Keep legacy diagnostic-only sinks while preserving a start-capable type."""

    def __init__(self, delegate: DiagnosticTelemetryAdapter):
        self._delegate = delegate

    def start(self, operation: RuntimeOperation) -> RuntimeTelemetryScope:
        return NOOP_RUNTIME_TELEMETRY.start(operation)

    def record_diagnostic(self, attributes: dict[str, AttributeValue], correlation: Any) -> None:
        self._delegate.record_diagnostic(attributes, correlation)


def validate_request_policy(policy: RequestPolicyInput) -> RequestPolicyInput:
    if not callable(policy) and not isinstance(policy, RequestPolicy):
        raise TypeError("request policy must be callable or expose apply(query)")
    return policy


def validate_checker_registry(registry: CheckerRegistry) -> CheckerRegistry:
    if not isinstance(registry, CheckerRegistry):
        raise TypeError("checker registry must provide checker(entity)")
    return registry


def validate_schema_capability(provider: SchemaCapability) -> SchemaCapability:
    if not isinstance(provider, SchemaCapability) or not iscoroutinefunction(provider._ensure_schema):
        raise TypeError("schema capability must provide async _ensure_schema(context, capability)")
    return provider


def validate_safe_audit_sink(sink: SafeAuditEventSink) -> SafeAuditEventSink:
    if not isinstance(sink, SafeAuditEventSink):
        raise TypeError("application audit sink must provide on_safe_event(context, event)")
    return sink


def validate_runtime_telemetry(telemetry: RuntimeTelemetryInput) -> RuntimeTelemetryAdapter:
    if isinstance(telemetry, RuntimeTelemetryAdapter):
        return telemetry
    if isinstance(telemetry, DiagnosticTelemetryAdapter):
        return _DiagnosticOnlyTelemetry(telemetry)
    raise TypeError("runtime telemetry adapter must provide start(operation) or record_diagnostic")
