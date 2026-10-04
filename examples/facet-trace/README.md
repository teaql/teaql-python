# Generated Facet Trace Chain acceptance

Run `bash examples/facet-trace/verify.sh` from the runtime repository. The script
uses local `src`, retains a fresh SQLite database and logs, executes twice without
cleanup, and verifies that the 13 generated library files remain unchanged.
It is included in `scripts/verify-examples.sh`.

This three-object School model isolates `TC-SQL-09`: root Facets, nested Facets,
and nested Facets inside an already-loaded reverse relation. Twenty scenarios
exercise include-all/matched-only, empty parents/results, limit-one display with
full matching counts, and SQL logging on/off. Generated Q/E and audited mutation
APIs seed and traverse the graph. Real database reads, count SQL, safe diagnostics,
request immutability, raw policy intent, future-binding masking, and independent
next-request `NotLoaded` semantics are asserted. `FACET_OBSERVED` records actual
counts/results and diagnostic routes, not just a success marker.

`lib/` is read-only generated output retained from producer commit
`c7407c93c186fa9f0e2ff9599952f333a5963020` (Python issue #43 / producer #251).
Do not inspect generated source for API discovery. For new operations, use
model-aware `python-assist-query/school.school_type` or other action/entity/field
Assist against `model.xml`; report `MISSING_ASSIST` rather than guessing.

To test a downloaded artifact, copy this example into a separate workspace and
invoke `main.py` with `PYTHONPATH` containing only that workspace's `lib`, the
artifact's interpreter, and an explicit `TEAQL_FACET_TRACE_DB`. Verify actual
runtime module paths and package hashes. Do not change this local-source gate
to silently consume an installed release. This fixture does not prove all Trace
Chain cases, external database support, or public-release parity.
