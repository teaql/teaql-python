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

## Current business model and workspace

`model.xml` defines Catalog and Entry. Trusted Context supplies collection/edit
times, IP and actor fields; the example shows why saving an unchanged entry
must leave those business values untouched. `python-lib-core/` is the exact, read-only
current generated domain library. The application is in `python-app-console/showcase/verify.py`.
The historical `fixture/` remains byte-identical and retains all of its original
fingerprint checks; a separate guard verifies the current library before and
after business execution.

Run the focused source qualifier entry from the SDK repository root:

```bash
python examples/context-derived/verify-local.py
```

The original assertions run twice on retained stores: no-op saves produce no
updates, genuine edits consume the trusted Context, failed validation/provider
work preserves edits, and a later invalid child rolls back staged graph fields.
Current managed creation results are explicitly awaited or checked. No generated
implementation is hand-edited. Compact receipts and result stores are retained;
owned build output is removed. Full runtime inventories remain separate gates.

The current model adds only `_audit_mask_fields="guarded_token"` to satisfy the
current evaluator. Business fields/defaults and the frozen model are unchanged.
