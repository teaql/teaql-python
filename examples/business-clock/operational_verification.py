"""Public Context operations with a calibrated, deliberately unreadable clock."""
from datetime import datetime, timezone
from time import monotonic, sleep
from uuid import uuid4


class ProbeBusinessClock:
    def __init__(self, unreadable=False):
        self.value = datetime(2099, 12, 31, tzinfo=timezone.utc)
        self.unreadable = unreadable
        self.calls = 0

    def now(self):
        self.calls += 1
        if self.unreadable:
            raise RuntimeError("BUSINESS_CLOCK_UNAVAILABLE_FOR_OPERATIONAL_WORK")
        return self.value


def verify_operational_clock(context):
    """Inject a real Context; do not replace its cache or inspect private state."""
    clock = ProbeBusinessClock()
    context.with_business_clock(clock)
    assert context.business_time() == clock.value
    clock.unreadable = True
    try:
        context.business_time()
    except RuntimeError as error:
        assert str(error) == "BUSINESS_CLOCK_UNAVAILABLE_FOR_OPERATIONAL_WORK"
    else:
        raise AssertionError("calibration must observe the unavailable clock")
    assert clock.calls == 2
    prefix = "operational-clock-example-" + uuid4().hex
    keys = [prefix + suffix for suffix in ("-finite", "-zero", "-false", "-empty")]
    finite, zero, false, empty = keys
    try:
        context.put_to_local_cache(zero, 0, 0)
        context.put_to_local_cache(false, False)
        context.put_to_local_cache(empty, "")
        context.put_to_local_cache(finite, "live", 1)
        assert context.get_from_local_cache(finite) == "live"
        clock.value = datetime(2199, 1, 1, tzinfo=timezone.utc)
        assert context.get_from_local_cache(finite) == "live"
        deadline = monotonic() + 3
        while context.get_from_local_cache(finite) is not None and monotonic() < deadline:
            sleep(.01)
        assert context.get_from_local_cache(finite) is None, "real operational TTL must expire"
        clock.value = datetime(1900, 1, 1, tzinfo=timezone.utc)
        assert context.get_from_local_cache(finite) is None, "business time cannot revive an expired entry"
        assert type(context.get_from_local_cache(zero)) is int
        assert context.get_from_local_cache(zero) == 0
        assert context.get_from_local_cache(false) is False
        assert context.get_from_local_cache(empty) == ""
        assert clock.calls == 2, "cache operations must not consume Business Clock"
        return {"passed": True, "calibrationCalls": 2, "additionalBusinessReads": 0,
                "facts": {"realExpiry": True, "unavailableBusinessCalibrated": True,
                          "forwardCannotExpire": True, "backwardCannotRevive": True,
                          "zeroTtlRemains": True, "zeroFalseEmptyRemainValues": True}}
    finally:
        for key in keys:
            context.remove_from_local_cache(key)
