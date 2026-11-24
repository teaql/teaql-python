# Place delivery orders across a business-day cutover

A delivery desk accepts orders immediately before and after its business day
changes. `model.xml` defines the delivery platform, reference and order date.
The generated `python-lib-core/` is consumed by `python-app-console/app/main.py`.
The console sets a trusted Context clock, uses the generated API to place both
orders, and reloads both dates through Q and E. An unavailable business clock
rejects the next order before it is written. The prior order keeps its date.

The SDK's example inventory runs this workspace and the original operational
cache and clock calibration below. The focused Conformance gate repeats the
workspace on one SQLite file and independently reads all four persisted orders.

## Original clock and cache calibration

This minimal example proves that a fixed provider, scoped to one `UserContext`,
drives both business time and business date. It does not change the process
clock used by cache expiry, telemetry, or security-token lifetimes.

It also calibrates, then makes Business Clock unavailable and performs **real
one-second cache expiry** through the public Context API. Moving business time
forwards cannot expire a live entry; moving it backwards cannot revive an expired
one. Zero/omitted TTL and zero/false/empty values remain unchanged. Cache operations
make no additional Business Clock reads. Only this probe's unique keys are removed
on exit; no shared-cache sweep or database cleanup occurs.

The `PYTHON_OPERATIONAL_CLOCK_EXAMPLE` JSON line is deterministic acceptance
evidence (not a log parser guessing success). Focused native tests additionally
cover local-lock ownership/lease/finite waits, wide/empty ID Set expiry, default
encrypted and explicitly acknowledged development/raw reference clocks, and
telemetry queue prefix/idle deadlines. Those tests use the actual runtime; internal
queue probes do not introduce a new public API. No remote backend is implied.

Run it from the repository root:

```bash
PYTHONPATH=src python examples/business-clock/python-app-console/calibration/main.py
```
