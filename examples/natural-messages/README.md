# Natural Checker messages through a generated SQLite graph

Run `python examples/natural-messages/verify-local.py` from this checkout. The
example runs twice on one isolated database, using the evaluated generated
Catalog/Entry library under `python-lib-core/` and this repository's local runtime.
Set `TEAQL_NATURAL_MESSAGES_EVIDENCE_DIR` to a new absolute path to retain evidence
at a chosen location. The verifier otherwise prints its temporary evidence path.

Generated bounded Q, loaded E and audited graph saves demonstrate:

- English and Chinese required messages locating the second child.
- The actual generated 100-scalar name bound and an original 101-scalar length.
- A customer renderer called once, with masked arguments and safe text retained
  when the child error receives its final graph path.
- Zero provider/transaction activity and no audit on rejection.
- A corrected save that writes/audits only the second child, with independent
  SQLite readback at version 2.

The generated module installs passive model vocabulary, native Checkers and
model-declared name sensitivity. The application does not install presentation
metadata, replace Checkers, or alter generated field constraints. Null-name
failures are rejected before graph admission; their final messages use the
explicit Catalog origin even though only children are modified. Length failures
retain the same origin through normal graph preparation. The unchanged parent
does not gain a version or an audit event.

`python-lib-core/generated-files.json` records the generated implementation hashes.
`python-lib-core/evaluation.json` is the model evaluation, and
`python-lib-core/generation.json` pins its generator/source receipt. Regenerate using
the upstream test named there; never patch generated implementation files.

Run the complete native suite and shared golden/negative cases with:

```bash
python scripts/verify-natural-messages.py --full --example --output /new/evidence/path
```

The full source gate installs pinned optional S3 test dependencies only into
owned scratch, retains compact source/command/resource hashes, responses and the
database, and cleans disposable outputs after owned children exit. It never
executes or follows the repository's three historical tracked `venv` links;
their exact link text and baseline Git bytes are separately checked.

## Current model and workspace

`model.xml` defines the Catalog and Entry business graph. The exact generated
domain library is read-only in `python-lib-core/`; its current provenance points to
the qualified generator source build, with the prior generation identity retained
separately in its metadata. The application lives in `python-app-console/showcase/verify.py`.

Run this focused business entry from the SDK repository root:

```bash
python examples/natural-messages/verify-local.py
```

The same graph is rejected before writes for an invalid second Entry, then
corrected and saved through generated Q/E and audited Save. Two runs check
actual stored values, precise machine locations, English/Chinese messages and
private-value redaction. Language-specific native length rules remain intact.
The verifier preserves result stores and compact receipts and removes owned
build outputs. Full runtime example qualification remains a separate gate.
