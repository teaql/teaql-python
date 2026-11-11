# Context Fix over generated Q/E and audited SQLite saves

Run from the runtime checkout:

```sh
PYTHONPATH=src python examples/context-derived/verify-local.py
```

The verifier binds the actual repository runtime and immutable generated library,
checks their origins/hashes, and runs twice against the same isolated SQLite
database. `TEAQL_CONTEXT_FIX_EVIDENCE_DIR` chooses a new evidence directory;
otherwise a compact temporary evidence directory is retained. No build tree or
virtual environment is created by the verifier. Logs, receipts and the synthetic
database are retained; generated sources are never patched.

The example proves unchanged Context A rows are not refreshed under Context B;
real business changes enable update-scoped clock/IP/actor values while preserving
create-only values. Provider/validation failures carry ObjectLocation; caller
intent survives, earlier sibling Fix rolls back after a later failure, and retry
changes just the independently dirty child. The prepared path also checks a
Context function executes once per entity/operation, not once per planning pass.

IP/actor declarations are an application metadata/Checker SPI customization over
ordinary strings. The synchronous `context_fix_resolver` receives ContextFixInput;
prepare asynchronous external results before save. Raw provider errors and
causes are not part of the public Check failure.

Regenerate this fixture using the generator's `PythonContextFixGenerationTest`
with `-Dteaql.python.context.fixture.output=<absolute fixture directory>`.
The `teaql/model-provenance.json` directory is metadata only, not an embedded
runtime; the canonical verifier checks its manifest hash and rejects Python
source, bytecode, symlinks, unowned metadata or unexpected files there.
