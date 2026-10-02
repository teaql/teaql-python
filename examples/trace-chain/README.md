# Python Trace Chain Example

This example uses an evaluated six-entity KSML definition and an unchanged
generated library. Application code uses generated Q for loading, E for loaded
traversal, and audited save for the composed graph. A transparent observer
captures actual requests and SQL metadata; the safe audit sink asserts that
database commit has already completed. No expected trace frames are supplied
to the planner or provider.

```bash
cd /path/to/teaql-python
bash examples/trace-chain/verify.sh
```

The verifier uses this repository's runtime source and executes all three suites
twice without cleanup, then checks the generated library hashes. The normative
graph and ownership fixtures require separate SQLite files because their graph
sizes differ. Set `TEAQL_TRACE_CHAIN_DB` and `TEAQL_TRACE_CHAIN_SHARED_DB` to retain
and replay those files. The page/stream suite has its own
`TEAQL_TRACE_CHAIN_PAGE_STREAM_DB` file. Each suite reuses its file across both runs. Unique
business labels avoid deleting existing demo records.

Seven scenario groups verify missing root reason before transaction access,
six-item branch/deletion lineage at request/SQL/audit boundaries, Q/E reload and
retained soft deletion, three relation levels with inherited query intent, two
concurrent graph saves in one Context, failed mutation, and failed authoritative
readback. Failures retain SQL evidence and emit no committed audits.

Four additional ownership cases use generated Q/E/save: two independent loaded
roots share the same provider-returned Platform record without sharing mutable
ledgers; adoption imports only a reached changed child; a clean ancestor emits
no write while retaining its changed child's audit scope; and conflicting loaded
versions reject before business SQL. Public async saves overlap but transactions
and Checker preparation serialize at the Context gate. The shared record is a
mutable dictionary deliberately used read-only and checked unchanged, not a
structurally immutable snapshot. JSON observations retain actual commands,
optimistic versions, SQL metadata and committed audits.

Eight page/stream phases use the same model and current list-page/field Assist.
Offset 1 / limit 2 returns two independent roots with original versions 2/1 and
exact total 3. Changing the caller's builder while COUNT is paused does not
change later row/relation intent. Root and child saves emit only their actual
changed operations in the customer policy's reviewed plan, SQL and committed
audit. Shared Platform data remains unchanged.

Count safely retains private bindings declared by removed descendants, without
executing those descendants or storing privacy on Context. The next independent
query does not inherit that privacy. Two scalar streams retain creation-time
intent across delayed consumption, with two actual SQLite driver generators
live while an independent query runs. Explicit close releases both nested
iterators immediately; successful exhaustion and early cancellation retain
distinct outcomes/cardinalities. Streamed rows own independent ledgers; saving
one row does not write or clear another row's pending changes. Relation hydration
is not supported by scalar streaming; use list or page for relation graphs.

`PAGE_STREAM_OBSERVED` records actual SQL, policy-reviewed operations, commands,
optimistic versions and safe audits. Native tests additionally cover COUNT
failure and trusted policy removing the private child. Current generation also
rekeys a new object's ledger when an explicit positive integer ID is assigned,
rejecting invalid IDs before changing object/ledger state.

The model evaluation reports zero errors, warnings and suggestions, with
seventeen Solids. Current model-aware Assist and evaluation evidence are retained
under `evidence/`. `AGENTS.md` governs application implementation. The library is
regenerated only by the upstream `PythonTraceChainExampleGenerationTest`; do not
edit generated files to fix application usage.

Prepared batch grouping, generated ledger override, complete mutation privacy,
external database acceptance and immutable Registry consumer replay are not
established by this example. Local tests do not prove any published version.
