"""Business Clock must not become a TTL, security or operational timeout clock."""
from array import array
from datetime import datetime, timedelta, timezone
import importlib.util
import inspect
import json
from pathlib import Path
from time import monotonic
from uuid import uuid4

import pytest

from teaql.runtime import (AeadEntityReferenceCodec, EntityReferenceTokenError,
                           UNSAFE_RAW_ENTITY_REFERENCES_ACKNOWLEDGEMENT,
                           UNSAFE_RAW_ENTITY_REFERENCES_ENVIRONMENT, UserContext)
from teaql.runtime.context import InMemoryIdSetStore, RetainedIdSet
from teaql.runtime.telemetry_queue import ExportQueue


HELPER = Path(__file__).resolve().parents[2] / "examples/business-clock/operational_verification.py"
spec = importlib.util.spec_from_file_location("clock_example_verification", HELPER)
example = importlib.util.module_from_spec(spec)
spec.loader.exec_module(example)
FUTURE = datetime(2199, 1, 1, tzinfo=timezone.utc)
PAST = datetime(1900, 1, 1, tzinfo=timezone.utc)
SECURITY_NOW = datetime(2030, 1, 1, tzinfo=timezone.utc)


def fixture(unreadable=False):
    clock = example.ProbeBusinessClock(unreadable)
    context = UserContext().with_business_clock(clock)
    if unreadable:
        with pytest.raises(RuntimeError, match="BUSINESS_CLOCK_UNAVAILABLE"):
            context.business_time()
    else:
        assert context.business_time() == clock.value
    assert clock.calls == 1
    return context, clock


def emit(case, clock, facts, real_time=False):
    assert clock.calls == 1
    assert all(value is True for value in facts.values())
    print("\nPYTHON_OPERATIONAL_CLOCK_CASE=" + json.dumps({"case": case, "passed": True,
          "calibrationCalls": 1, "additionalBusinessReads": 0, "realTime": real_time,
          "runtimeOrigin": str(Path(inspect.getfile(UserContext)).resolve()),
          "facts": facts}, sort_keys=True))


def test_cache_uses_monotonic_ttl_and_never_business_time(monkeypatch):
    context, clock = fixture()
    now = 100.0
    monkeypatch.setattr("teaql.runtime.context.time.monotonic", lambda: now)
    key = uuid4().hex
    try:
        context.put_to_local_cache(key, "live", 1)
        clock.value = FUTURE
        assert context.get_from_local_cache(key) == "live"
        now += .999
        assert context.get_from_local_cache(key) == "live"
        now = 101.0
        assert context.get_from_local_cache(key) is None
        clock.value, now = PAST, 100.0
        assert context.get_from_local_cache(key) is None
        emit("cache-monotonic-expiry", clock, {"futureBusinessDoesNotExpire": True,
             "inclusiveExpiry": True, "discardedEntryCannotRevive": True})
    finally:
        context.remove_from_local_cache(key)


def test_falsey_values_and_no_expiry_do_not_need_business_clock(monkeypatch):
    context, clock = fixture(True)
    now = 100.0
    monkeypatch.setattr("teaql.runtime.context.time.monotonic", lambda: now)
    keys = [uuid4().hex for _ in range(5)]
    try:
        for key, value, ttl in zip(keys, [0, False, "", None, "finite"], [0, None, None, None, 1]):
            context.put_to_local_cache(key, value, ttl)
        now += 1
        assert [context.get_from_local_cache(key) for key in keys] == [0, False, "", None, None]
        assert type(context.get_from_local_cache(keys[0])) is int
        assert context.get_from_local_cache(keys[1]) is False
        assert context.get_from_local_cache(keys[0], int) == 0
        assert context.get_from_local_cache(keys[0], str) is None
        emit("cache-falsey-values", clock, {"unreadableBusinessCalibrated": True,
             "finiteEntryExpires": True, "zeroAndOmittedTtlRemain": True,
             "zeroFalseEmptyPreserved": True, "noneReadSemanticsPreserved": True,
             "typeFilterPreserved": True})
    finally:
        for key in keys:
            context.remove_from_local_cache(key)


def test_real_ttl_example_runs_the_public_context():
    result = example.verify_operational_clock(UserContext())
    assert result["passed"] and result["calibrationCalls"] == 2
    assert result["additionalBusinessReads"] == 0
    print("\nPYTHON_OPERATIONAL_CLOCK_CASE=" + json.dumps({"case": "cache-real-example",
          "passed": True, "calibrationCalls": 2, "additionalBusinessReads": 0,
          "runtimeOrigin": str(Path(inspect.getfile(UserContext)).resolve()),
          "realTime": True, "facts": result["facts"]}, sort_keys=True))


def test_local_lock_lease_and_owner_rules_do_not_use_business_time(monkeypatch):
    first, clock = fixture(True)
    second, other = fixture(True)
    now = 100.0
    monkeypatch.setattr("teaql.runtime.context.time.monotonic", lambda: now)
    key = uuid4().hex
    try:
        assert first.try_local_lock(key, 0, 1000)
        clock.value = FUTURE
        assert not second.try_local_lock(key, 0, 1000)
        second.unlock_local(key)
        assert not second.try_local_lock(key, 0, 1000)
        now = 101.0
        assert second.try_local_lock(key, 0, 1000)
        first.unlock_local(key)
        assert not first.try_local_lock(key, 0, 1000)
        second.unlock_local(key)
        clock.value = PAST
        assert first.try_local_lock(key, 0, 0)
        assert first.try_local_lock(key, 0, 0)
        assert not second.try_local_lock(key, 0, 0)
        assert other.calls == 1
        emit("local-lock-lease-owner", clock, {"unreadableBusinessCalibrated": True,
             "businessFutureCannotStealLease": True, "wrongOwnerCannotUnlock": True,
             "inclusiveLeaseExpiry": True, "noExpiryAndReentryPreserved": True})
    finally:
        first.unlock_local(key)
        second.unlock_local(key)


def test_local_lock_real_timeout_remains_finite_with_unavailable_clock():
    first, clock = fixture(True)
    second, other = fixture(True)
    key = uuid4().hex
    try:
        assert first.try_local_lock(key, 0, 0)
        start = monotonic()
        assert not second.try_local_lock(key, 25, 0)
        elapsed = monotonic() - start
        assert .01 <= elapsed < 2
        assert not second.try_local_lock(key, 0, 0)
        first.unlock_local(key)
        assert second.try_local_lock(key, 0, 0)
        assert other.calls == 1
        emit("local-lock-real-timeout", clock, {"unreadableBusinessCalibrated": True,
             "finiteTimeout": True, "timeoutDoesNotReleaseOwner": True,
             "acquireAfterOwnerRelease": True}, True)
    finally:
        first.unlock_local(key)
        second.unlock_local(key)


@pytest.mark.parametrize("empty", [False, True], ids=["wide", "empty"])
def test_id_set_retains_exact_snapshot_until_operational_expiry(monkeypatch, empty):
    context, clock = fixture(True)
    store = InMemoryIdSetStore()
    context.set_id_set_store(store)
    now = 100.0
    monkeypatch.setattr("teaql.runtime.context.time.time", lambda: now)
    ids = array("q", [] if empty else [9007199254740993])
    store.put(RetainedIdSet("query", ids, 101.0))
    clock.value = FUTURE
    assert context.id_set_store().get("query").ids.tolist() == ids.tolist()
    assert context.id_set_store().get("other-query") is None
    now = 101.0
    assert store.get("query") is None
    clock.value, now = PAST, 100.0
    assert store.get("query") is None
    emit("id-set-empty" if empty else "id-set-wide", clock,
         {"unreadableBusinessCalibrated": True, "exactSnapshotPreserved": True,
          "queryKeyIsolation": True, "inclusiveExpiry": True,
          "discardedSnapshotCannotRevive": True})


@pytest.mark.parametrize("raw", [False, True], ids=["default-aead", "acknowledged-raw"])
def test_context_reference_clock_stays_separate_from_business_time(monkeypatch, raw):
    context, clock = fixture(True)
    security_now = SECURITY_NOW

    class SecurityDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return security_now if tz else security_now.replace(tzinfo=None)

    monkeypatch.setattr("teaql.runtime.context.datetime", SecurityDateTime)
    monkeypatch.setattr("teaql.runtime.entity_reference.datetime", SecurityDateTime)
    monkeypatch.delenv(UNSAFE_RAW_ENTITY_REFERENCES_ENVIRONMENT, raising=False)
    if raw:
        monkeypatch.setenv(UNSAFE_RAW_ENTITY_REFERENCES_ENVIRONMENT,
                           UNSAFE_RAW_ENTITY_REFERENCES_ACKNOWLEDGEMENT)
    else:
        # Default security clock: deliberately do not call codec.with_clock().
        context.with_entity_reference_codec(AeadEntityReferenceCodec(1, {1: b"\x11" * 32}))
    token = context.encode_entity_reference("ClockProbe", 42, 7, "edit", timedelta(seconds=1))
    assert token.startswith("tqr0." if raw else "tqr1.")
    clock.value = FUTURE
    claims = context.decode_entity_reference(token, "ClockProbe", "edit")
    assert (claims.id, claims.version) == (42, 7)
    assert claims.issued_at == SECURITY_NOW
    assert claims.expires_at == SECURITY_NOW + timedelta(seconds=1)
    with pytest.raises(EntityReferenceTokenError, match="ENTITY_REFERENCE_INVALID"):
        context.decode_entity_reference(token, "ClockProbe", "wrong-purpose")
    security_now += timedelta(seconds=1)
    for business in [FUTURE, PAST]:
        clock.value = business
        with pytest.raises(EntityReferenceTokenError, match="ENTITY_REFERENCE_INVALID"):
            context.decode_entity_reference(token, "ClockProbe", "edit")
    emit("raw-reference-security-clock" if raw else "default-aead-security-clock", clock,
         {"unreadableBusinessCalibrated": True, "issuedAtUsesSecurityClock": True,
          "businessFutureDoesNotExpire": True, "purposeBindingPreserved": True,
          "inclusiveSecurityExpiry": True, "businessPastCannotRevive": True})


@pytest.mark.parametrize("prefix", [True, False], ids=["prefix", "idle"])
def test_telemetry_queue_deadline_is_finite_without_business_clock(prefix):
    _, clock = fixture(True)
    lost = []
    queue = ExportQueue("logs", 2, lambda *event: lost.append(event))
    record = object()
    queue.handoff(record, lambda: None)
    target = queue.prefix()
    start = monotonic()
    assert not (queue.wait_prefix(target, .025) if prefix else queue.wait_idle(.025))
    assert .01 <= monotonic() - start < 2
    assert queue.snapshot()["outstanding"] == 1 and not lost
    queue.begin_export([record])(False)
    assert queue.wait_prefix(target, .025) and queue.wait_idle(.025)
    assert queue.snapshot()["completed"] == 1 and not lost
    emit("telemetry-prefix-deadline" if prefix else "telemetry-idle-deadline", clock,
         {"unreadableBusinessCalibrated": True, "finiteTimeout": True,
          "timeoutDoesNotConsumeAdmission": True, "completionPreserved": True}, True)
