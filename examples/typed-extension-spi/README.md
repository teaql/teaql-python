# Typed Context extension SPI example

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
