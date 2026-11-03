# Checker, E API and partial-graph saving

Run `python examples/fix-e-alignment/verify-local.py` against the repository's
local runtime. Set `TEAQL_FIX_E_EVIDENCE_DIR` to an unused absolute directory to
retain compact logs, receipts and synthetic databases at a known location.
The main scenarios run twice without deleting or resetting their databases.
The input-admission probe uses one new database and retries the same graph in place.

The three-entity model is deliberately small. All setup and mutations use the
generated Q API and audited save; E API checks distinguish NotLoaded from null.
The generated fixture is hash-bound to its evaluated model and producer. Do not
edit it to fix an example: repair generation, regenerate, then verify its hashes.

`partial_graph_loading.py` covers complete modified descendants behind two
untouched partial ancestors, incomplete modified descendants, projection and
version preservation, and managed cascade wiring.

`partial_root_loading.py` adds the independent ownership check: a complete
modified leaf is reached through two unmodified partial ancestors. Saving under
a different persisted active root must fail twice before provider access, ID
allocation, policy lookup/review or audit delivery. Both attempts retain the
same mutation intent, projection and physical rows. Retrying that same graph
with its correct active root writes only the leaf, clears committed intent and
uses the injected BusinessClock. Ancestors remain partial and version 1.

`projection_views.py` checks three independent-view boundaries twice on one
SQLite file: a later complete query cannot widen an earlier sparse view; two
views of one row retain independent pending edits and reject a stale save; a
sparse root and its full nested alias retain different projections and JSON.
E/JSON inspection performs no provider work or mutation. The rejected stale
save rolls back without commit audit, preserves its original version/business
edit, and may retain only its successful BusinessClock-derived `update_time` Fix.
The existing runtime reports this rejection as a `RuntimeError` for missing
authoritative persisted state, not a dedicated optimistic-conflict exception.
This example does not claim richer error classification or cyclic-graph coverage.

`unchanged_views.py` adds five generated Q/E/audited-save cases twice on one
unreset SQLite store. Restored scalar/null edits and clean saves preserve sparse
fields, loaded sparse relations, readonly null/zero/empty properties, row-owned
values, JSON, lineage and optimistic versions with zero provider/policy/audit
effects. One row's save cannot consume another row's pending intent. A genuine
write returns authoritative fixed fields and invalidates its old query-property
snapshot after commit; expressions are not silently recomputed. Rollback retains
the snapshot for retry, and clean rows are not invalidated. A separate read-only
SQLite oracle checks stored values and versions. Expression/raw/dynamic aliases
share aggregate alias validation, including collision/missing/duplicate rejection
without partially installing a graph. This does not add typed dynamic schemas,
persistent dynamic fields or a public enclosing-transaction API.

## Once per entity graph preparation

`python_graph_fix_probe.py` saves both a normal parent/child graph and a graph
containing the same child instance twice. Each entity must run Checker/Fix and
persist exactly once, with one BusinessClock capture for the graph and no
provider access inside Fix. Both scenarios run twice on their original stores.

`python_graph_once_update.py` adds a customer Checker that increases a child's
price by one cent. Create and update retain that correction exactly once;
the repeated child finishes at `23.45`, not `23.46`. A policy callback that edits
the reviewed child must reject and roll back, preserving the committed value
and optimistic version. The complete probe runs twice on one database.

`required_graph.py` rejects missing child input before provider access, ID
reservation or a Fix clock read. It then saves the corrected graph, rejects an
invalid child update, and moves the existing child to a new parent whose ID is
not yet allocated during preparation. All writes use generated audited saves.
The receipt binds these three application files, their logs and four databases.

The generated fixture requires the paired runtime graph-preparation repair;
do not run it with an older installed runtime or edit generated entities locally.

The service **and its real transaction** are observed. Every counter, including
rollback, is calibrated before the rejected saves. Read-only immutable SQLite
queries are an independent storage oracle, never an alternative write path.
The active root is application-defined; the runtime does not prescribe tenancy.
