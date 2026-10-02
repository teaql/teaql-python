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

The verifier uses this repository's runtime source, executes twice on one unique
SQLite file without cleanup, and checks the generated library hashes afterward.
Set `TEAQL_TRACE_CHAIN_DB` to retain and replay a particular database. It uses
unique business labels; it does not delete existing demo records.

Seven scenario groups verify missing root reason before transaction access,
six-item branch/deletion lineage at request/SQL/audit boundaries, Q/E reload and
retained soft deletion, three relation levels with inherited query intent, two
concurrent graph saves in one Context, failed mutation, and failed authoritative
readback. Failures retain SQL evidence and emit no committed audits.

The model evaluation reports zero errors, warnings and suggestions, with
seventeen Solids. Current model-aware Assist and evaluation evidence are retained
under `evidence/`. `AGENTS.md` governs application implementation. The library is
regenerated only by the upstream `PythonTraceChainExampleGenerationTest`; do not
edit generated files to fix application usage.

Prepared batch grouping, generated ledger override, complete mutation privacy,
external database acceptance and immutable Registry consumer replay are not
established by this example. Local tests do not prove any published version.
