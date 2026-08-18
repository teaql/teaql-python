from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, Generic, Optional, Protocol, TypeVar


AttributeValue = str | int | float | bool
T = TypeVar("T")

FORBIDDEN_ATTRIBUTES = frozenset({
    "teaql.entity.id",
    "teaql.user.id",
    "teaql.tenant.id",
    "teaql.query.parameters",
    "teaql.field.values",
    "teaql.audit.reason",
    "db.query.parameter_values",
    "http.request.body",
    "url.full",
})


@dataclass(frozen=True)
class RuntimeOperation:
    family: str
    name: str
    attributes: Dict[str, AttributeValue] = field(default_factory=dict)

    def safe(self) -> "RuntimeOperation":
        attributes: Dict[str, AttributeValue] = {
            "teaql.operation.family": self.family,
            "teaql.operation.name": self.name,
        }
        attributes.update({
            key: value for key, value in self.attributes.items()
            if key not in FORBIDDEN_ATTRIBUTES
            and isinstance(value, (str, int, float, bool))
        })
        return RuntimeOperation(self.family, self.name, attributes)


class RuntimeTelemetryScope(Protocol):
    def success(self, attributes: Optional[Dict[str, AttributeValue]] = None) -> None: ...
    def failure(self, error: BaseException) -> None: ...


class RuntimeTelemetry(Protocol):
    def start(self, operation: RuntimeOperation) -> RuntimeTelemetryScope: ...


class _NoopScope:
    def success(self, attributes: Optional[Dict[str, AttributeValue]] = None) -> None:
        pass

    def failure(self, error: BaseException) -> None:
        pass


class NoopRuntimeTelemetry:
    def start(self, operation: RuntimeOperation) -> RuntimeTelemetryScope:
        return _NoopScope()


NOOP_RUNTIME_TELEMETRY = NoopRuntimeTelemetry()


class _FailOpenScope:
    def __init__(self, delegate: RuntimeTelemetryScope):
        self._delegate = delegate
        self._ended = False

    def success(self, attributes: Optional[Dict[str, AttributeValue]] = None) -> None:
        if self._ended:
            return
        self._ended = True
        try:
            self._delegate.success(attributes)
        except BaseException:
            pass

    def failure(self, error: BaseException) -> None:
        if self._ended:
            return
        self._ended = True
        try:
            self._delegate.failure(error)
        except BaseException:
            pass


def start_runtime_operation(
    telemetry: Optional[RuntimeTelemetry], operation: RuntimeOperation,
) -> RuntimeTelemetryScope:
    if telemetry is None:
        return _NoopScope()
    try:
        return _FailOpenScope(telemetry.start(operation.safe()))
    except BaseException:
        return _NoopScope()


async def observe_runtime_operation(
    telemetry: Optional[RuntimeTelemetry],
    operation: RuntimeOperation,
    work: Callable[[], Awaitable[T]],
    completion: Optional[Callable[[T], Dict[str, AttributeValue]]] = None,
) -> T:
    scope = start_runtime_operation(telemetry, operation)
    try:
        result = await work()
        scope.success(completion(result) if completion else None)
        return result
    except BaseException as error:
        scope.failure(error)
        raise


def observe_runtime_operation_sync(
    telemetry: Optional[RuntimeTelemetry],
    operation: RuntimeOperation,
    work: Callable[[], T],
    completion: Optional[Callable[[T], Dict[str, AttributeValue]]] = None,
) -> T:
    """Observe synchronous runtime work without changing its result or failure."""
    scope = start_runtime_operation(telemetry, operation)
    try:
        result = work()
        scope.success(completion(result) if completion else None)
        return result
    except BaseException as error:
        scope.failure(error)
        raise
