# Checker, E API and partial-graph saving

Run `python examples/fix-e-alignment/verify-local.py` against the repository's
local runtime. Set `TEAQL_FIX_E_EVIDENCE_DIR` to an unused absolute directory to
retain compact logs, receipts and synthetic databases at a known location.
Each scenario runs twice without deleting or resetting its database.

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

The service **and its real transaction** are observed. Every counter, including
rollback, is calibrated before the rejected saves. Read-only immutable SQLite
queries are an independent storage oracle, never an alternative write path.
The active root is application-defined; the runtime does not prescribe tenancy.
