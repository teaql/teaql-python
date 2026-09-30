# Context-owned Business Clock example

This minimal example proves that a fixed provider, scoped to one `UserContext`,
drives both business time and business date. It does not change the process
clock used by cache expiry, telemetry, or security-token lifetimes.

Run it from the repository root:

```bash
PYTHONPATH=src python examples/business-clock/main.py
```
