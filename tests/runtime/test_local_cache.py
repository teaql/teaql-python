import time
from unittest.mock import patch

from teaql.runtime.context import UserContext


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


def test_local_cache_is_process_shared_and_honors_ttl():
    first = UserContext()
    second = UserContext()
    key = "local-cache-conformance"

    first.put_to_local_cache(key, {"id": 7})
    assert second.get_from_local_cache(key, dict) == {"id": 7}
    second.remove_from_local_cache(key)
    assert first.get_from_local_cache(key) is None

    with patch("teaql.runtime.context.time.monotonic", side_effect=[100.0, 101.0]):
        first.put_to_local_cache(key, "temporary", 1)
        assert second.get_from_local_cache(key) is None


def test_local_lock_enforces_ownership_timeout_and_lease_expiry():
    first = UserContext()
    second = UserContext()
    key = "local-lock-conformance"

    assert first.try_local_lock(key, 0, 50)
    assert not second.try_local_lock(key, 0, 50)
    second.unlock_local(key)
    assert not second.try_local_lock(key, 0, 50)
    time.sleep(0.06)
    assert second.try_local_lock(key, 0, 50)
    second.unlock_local(key)
    assert first.try_local_lock(key, 0, 50)
    first.unlock_local(key)


def test_local_and_remote_cache_emit_balanced_low_cardinality_events():
    class RemoteCache:
        def __init__(self):
            self.value = None

        def put_to_remote_cache(self, key, value, ttl):
            self.value = value

        def get_from_remote_cache(self, key, clazz):
            return self.value

        def remove_from_remote_cache(self, key):
            self.value = None

    telemetry = RecordingTelemetry()
    context = UserContext().with_runtime_telemetry(telemetry)
    context.insert_resource("RemoteCacheProvider", RemoteCache())

    context.put_to_local_cache("secret-key", "local")
    assert context.get_from_local_cache("secret-key") == "local"
    context.remove_from_local_cache("secret-key")
    assert context.get_from_local_cache("secret-key") is None
    context.put_to_remote_cache("secret-key", "remote")
    assert context.get_from_remote_cache("secret-key") == "remote"
    context.remove_from_remote_cache("secret-key")
    assert context.get_from_remote_cache("secret-key") is None

    starts = [event for phase, event in telemetry.events if phase == "start"]
    completions = [event for phase, event in telemetry.events if phase == "success"]
    assert len(starts) == len(completions) == 8
    assert [operation.name for operation in starts] == [
        "local.put", "local.get", "local.remove", "local.get",
        "remote.put", "remote.get", "remote.remove", "remote.get",
    ]
    assert all(operation.family == "cache" for operation in starts)
    assert all("secret-key" not in str(operation.attributes) for operation in starts)
    assert [attributes["teaql.cache.result"] for attributes in completions] == [
        "stored", "hit", "removed", "miss",
        "stored", "hit", "removed", "miss",
    ]


def test_remote_cache_failure_is_observed_and_rethrown_unchanged():
    original = RuntimeError("remote cache unavailable")

    class BrokenRemoteCache:
        def get_from_remote_cache(self, key, clazz):
            raise original

    telemetry = RecordingTelemetry()
    context = UserContext().with_runtime_telemetry(telemetry)
    context.insert_resource("RemoteCacheProvider", BrokenRemoteCache())

    try:
        context.get_from_remote_cache("key")
        assert False, "expected the provider error"
    except RuntimeError as caught:
        assert caught is original
    assert telemetry.events[-1] == ("failure", original)
