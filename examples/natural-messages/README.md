# Natural Checker messages through a generated SQLite graph

Run `python examples/natural-messages/verify-local.py` from this checkout. The
example runs twice on one isolated database, using the unchanged generated
Catalog/Entry library under `../context-derived/fixture` and this local runtime.
Set `TEAQL_NATURAL_MESSAGES_EVIDENCE_DIR` to a new absolute path to retain evidence
at a chosen location. The verifier otherwise prints its temporary evidence path.

Generated bounded Q, loaded E and audited graph saves demonstrate:

- English and Chinese required messages locating the second child.
- A masked name with an eight-scalar bound and its original nine-scalar length.
- Zero provider/transaction activity and no audit on rejection.
- A corrected save that writes/audits only the second child, with independent
  SQLite readback at version 2.

Application-owned metadata supplies passive presentation labels, sensitivity
and a small name constraint; the generated fixture is not edited. Required
IP/actor example fields use the existing Context Fix customization seam. This
does not claim automatic generation of the new presentation resources.

Run the complete native suite and shared golden/negative cases with:

```bash
python scripts/verify-natural-messages.py --full --example --output /new/evidence/path
```

The full source gate installs pinned optional S3 test dependencies only into
owned scratch, retains compact source/command/resource hashes, responses and the
database, and cleans disposable outputs after owned children exit. It never
executes or follows the repository's three historical tracked `venv` links;
their exact link text and baseline Git bytes are separately checked.
