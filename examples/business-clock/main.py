from datetime import date, datetime, timezone

from teaql.runtime import FixedBusinessClock, UserContext


expected = datetime(2026, 10, 1, 14, 20, tzinfo=timezone.utc)
context = UserContext.new().with_business_clock(FixedBusinessClock(expected))

assert context.business_time() == expected
assert context.business_date() == date(2026, 10, 1)
print("PASS Python context-owned Business Clock example")
