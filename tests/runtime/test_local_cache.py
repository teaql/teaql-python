import time
from unittest.mock import patch

from teaql.runtime.context import UserContext


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
