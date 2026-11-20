# Supplier application review

The supplier review desk approves a generated vendor application. A trusted
Context installs an independent schema provider, policy, Checker/Fix, audit
sink, telemetry adapter and ID allocator. The Checker normalizes the accepted
legal name and refuses a blank one. The policy denies a generated lookup, and
an optional telemetry outage leaves the authorized lookup available. The next
process reads both accepted records from the same SQLite file.

`model.xml` owns the supplier model. The generated `python-app-console`
uses Q and E from `python-lib-core`. Run both launches and the original
six-extension calibration with `bash examples/typed-extension-spi/verify.sh`.

## Original extension calibration

This focused SQLite example installs six independent Context capabilities:
request policy, Checker/Fix registry, schema-only provider, safe application
audit sink, runtime telemetry, and Internal ID allocator. The schema provider
has no query/mutation methods. The example verifies accepted and denied
operations, twice-run schema ordering, and a persisted ID from the installed
allocator.

```bash
PYTHONPATH=src python examples/typed-extension-spi/main.py
```

Extensions are trusted application wiring. Registration rejects missing
methods before business execution; a policy or Checker denial still fails
closed. Optional telemetry adapter failures do not change a business result.
