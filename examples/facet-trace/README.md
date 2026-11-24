# Generated Facet Trace Chain acceptance

`model.xml` owns the exact native `python-lib-core` library and `python-app-console` workspace. Application code lives in the workspace; the named sibling library stays generator-managed. See `showcase.json` for source-build provenance. The focused gate runs the original business assertions twice on one retained SQLite database, records independent database checks, and removes owned build scratch. It qualifies this SDK source.

Run `bash examples/facet-trace/verify.sh` from the runtime repository. The script
uses local `src`, retains a fresh SQLite database and logs, executes twice without
cleanup, and verifies that all generated scope files remain unchanged.
It is included in `scripts/verify-examples.sh`.

This three-object School model isolates `TC-SQL-09`: root Facets, nested Facets,
and nested Facets inside an already-loaded reverse relation. Twenty scenarios
exercise include-all/matched-only, empty parents/results, limit-one display with
full matching counts, and SQL logging on/off. Generated Q/E and audited mutation
APIs seed and traverse the graph. Real database reads, count SQL, safe diagnostics,
request immutability, raw policy intent, future-binding masking, and independent
next-request `NotLoaded` semantics are asserted. `FACET_OBSERVED` records actual
counts/results and diagnostic routes, not just a success marker. The transport
and Context metadata boundary are observed separately: every SELECT retains
its full original root/ancestor path and raw request-owned intent even with
logging disabled, safe diagnostics emit nothing when disabled, and query
execution performs no writes. Expected frames are never injected into runtime
requests by the fixture.

The previous flat library contained generated output from producer commit
`c7407c93c186fa9f0e2ff9599952f333a5963020` (Python issue #43 / producer #251).
Do not inspect generated source for API discovery. For new operations, use
model-aware `python-assist-query/school.school_type` or other action/entity/field
Assist against `model.xml`; report `MISSING_ASSIST` rather than guessing.

To test a downloaded artifact, copy this example into a separate workspace and
invoke `main.py` with `PYTHONPATH` containing only that workspace's `python-lib-core`, the
artifact's interpreter, and an explicit `TEAQL_FACET_TRACE_DB`. Verify actual
runtime module paths and package hashes. Do not change this local-source gate
to silently consume an installed release. This fixture does not prove all Trace
Chain cases, external database support, or public-release parity.
