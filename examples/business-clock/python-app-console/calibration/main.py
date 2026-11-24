from datetime import date, datetime, timezone
import json

from teaql.runtime import FixedBusinessClock, UserContext
from operational_verification import verify_operational_clock


expected = datetime(2026, 10, 1, 14, 20, tzinfo=timezone.utc)
context = UserContext.new().with_business_clock(FixedBusinessClock(expected))

assert context.business_time() == expected
assert context.business_date() == date(2026, 10, 1)
print("PASS Python context-owned Business Clock example")

print("PYTHON_OPERATIONAL_CLOCK_EXAMPLE=" + json.dumps(verify_operational_clock(UserContext()), sort_keys=True))
