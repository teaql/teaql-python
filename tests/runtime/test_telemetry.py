import pytest

from teaql.runtime.telemetry import (
    RuntimeOperation,
    observe_runtime_operation,
    observe_runtime_operation_sync,
    start_runtime_operation,
)


class RecordingTelemetry:
    def __init__(self):
        self.events = []

    def start(self, operation):
        self.events.append(("start", operation))
        events = self.events

        class Scope:
            def success(self, attributes=None):
                events.append(("success", attributes))

            def failure(self, error):
                events.append(("failure", error))

        return Scope()


@pytest.mark.asyncio
async def test_balanced_safe_lifecycle_and_original_failure():
    telemetry = RecordingTelemetry()
    result = await observe_runtime_operation(
        telemetry,
        RuntimeOperation("query", "School.list", {
            "teaql.entity.type": "School", "teaql.entity.id": 42,
        }),
        lambda: _value(["school"]),
        lambda rows: {"teaql.result.cardinality": len(rows)},
    )
    assert result == ["school"]
    assert [phase for phase, _ in telemetry.events] == ["start", "success"]
    assert "teaql.entity.id" not in telemetry.events[0][1].attributes

    original = RuntimeError("database unavailable")
    with pytest.raises(RuntimeError) as caught:
        await observe_runtime_operation(
            telemetry, RuntimeOperation("provider", "sqlite.query"),
            lambda: _raise(original),
        )
    assert caught.value is original


def test_adapter_failures_are_isolated_and_completion_is_idempotent():
    class Broken:
        def start(self, operation):
            raise RuntimeError("adapter failed")

    start_runtime_operation(Broken(), RuntimeOperation("cache", "get")).success()

    telemetry = RecordingTelemetry()
    scope = start_runtime_operation(telemetry, RuntimeOperation("audit", "School.audit"))
    scope.success()
    scope.failure(RuntimeError("late"))
    assert [phase for phase, _ in telemetry.events] == ["start", "success"]


def test_sync_observation_preserves_result_and_original_failure():
    telemetry = RecordingTelemetry()
    assert observe_runtime_operation_sync(
        telemetry, RuntimeOperation("cache", "local.get"), lambda: "value",
    ) == "value"

    original = RuntimeError("cache unavailable")
    with pytest.raises(RuntimeError) as caught:
        observe_runtime_operation_sync(
            telemetry, RuntimeOperation("cache", "remote.get"),
            lambda: (_ for _ in ()).throw(original),
        )
    assert caught.value is original


async def _value(value):
    return value


async def _raise(error):
    raise error
