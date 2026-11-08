# Python runtime conformance example

This retained SQLite example is generated from `model.xml` and verifies the minimum runtime-owned contract: explicit `ensure_schema`, Create, Update, Delete, typed Q/SmartList, E loaded/null/not-loaded semantics, Checker rejection before persistence, and optimistic-version isolation for different entity types that share a numeric ID.

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e ../..
python -m app.main
python -m app.managed_creation
python -m app.managed_sqlite
```

Run these commands from `examples/conformance`. The editable dependency above is
this repository's runtime, not a public package or a historical embedded copy.

Create with `await Q.work_items().comment(...).purpose(...).new_entity(context)`.
The selected Context allocator reserves a positive ID before initializers run.
Each independent object owns its own mutation ledger. Saving persists that ID;
it does not allocate another one. Allocation gaps after rejection are normal.
Direct entity constructors are rejected. JSON hydration and `refer()` load read
views; they do not grant insert intent. A hydrated mutation needs the version
from its original loaded snapshot, not a version filled afterwards.

`managed_creation` runs six construction/hydration cases twice. `managed_sqlite`
runs eight Q/E/Checker/graph scenarios twice on one unreset database, including
unchanged partial children and rollback/retry with the same reserved IDs. It
prints the retained database path; set `TEAQL_MANAGED_CREATION_DB` to choose it.
Only changed objects must be fully loaded before save.

Regenerate only the domain-library files through the local generator's
`python-lib-core` target. Keep the application-owned regression scripts and
their assertions; do not replace them with a newly generated workspace entry.
