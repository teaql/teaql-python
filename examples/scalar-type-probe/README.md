# Generated scalar type probe: exact SQLite Decimal

Run from the repository root after installing the runtime's development dependencies:

```bash
bash examples/scalar-type-probe/verify.sh
```

The verifier imports this repository's `src/teaql` and runs the same generated
Q/E/Checker/Mutation consumer twice against one unique SQLite file, without
cleanup between rounds. `TEAQL_SCALAR_PROBE_DB` can select an explicit file.
The canonical single-entity scalar model and generated library are frozen with
their generator commit and file hashes in `fixture-manifest.json`; application
code does not modify the generated library.

The example proves high-precision Decimal create/update/readback, scale-preserving
storage, numeric equality and ordering, exact SUM, nullable values, sparse
NotLoaded behavior and Checker rejection before persistence. Native Date and
Time values are populated alongside the remaining modeled scalar types. This
focused example does not qualify every scalar value class or JSON wire path.

SQLite exact Decimal columns use `TEAQL_DECIMAL_TEXT COLLATE TEAQL_DECIMAL`
and a generated value check. The provider registers the collation, validator
and exact SUM on every connection. SUM ignores SQL NULL and returns NULL for
an empty input. AVG and statistical Decimal aggregates require an explicit
precision policy and are rejected by this profile. Finite values are bounded
to a 10,000-character plain representation before arithmetic or expansion.

Existing NUMERIC/REAL or unqualified TEXT columns require an explicit migration;
`ensure_schema()` rejects them before bootstrap. Previously rounded values
cannot be recovered automatically. Raw SQL remains the caller's responsibility.
