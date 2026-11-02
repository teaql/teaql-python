# Context-owned Business Clock example

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
PYTHONPATH=src python examples/business-clock/main.py
```
