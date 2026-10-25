# Generated scalar type probe: exact SQLite values and typed entity JSON

Run from the repository root after installing the runtime's development dependencies:

```bash
bash examples/scalar-type-probe/verify.sh
```

The verifier imports this repository's `src/teaql` and runs the same generated
Q/E/Checker/Mutation and typed-JSON consumers twice against one unique SQLite file, without
cleanup between rounds. `TEAQL_SCALAR_PROBE_DB` can select an explicit file.
The canonical single-entity scalar model and generated library are frozen with
their generator commit and file hashes in `fixture-manifest.json`; application
code does not modify the generated library.

The example proves high-precision Decimal create/update/readback, scale-preserving
storage, numeric equality and ordering, exact SUM, nullable values, sparse
NotLoaded behavior and Checker rejection before persistence. Native Date and
Time values are populated alongside the remaining modeled scalar types. This
focused example does not qualify every scalar value class or every transport boundary.

## Typed JSON from the same generated entities

`json_roundtrip.py` uses generated `ScalarTypeProbe.to_json()` and
`ScalarTypeProbe.from_json(payload)`, not a handwritten DTO. It verifies all 21
business scalar fields through E, plus ID, version, foreign identity and managed
timestamps, in `camelCase`, `snake_case` and `PascalCase` profiles.

Long, ID, version and exact Decimal are JSON strings; Integer is a JSON number.
Date is an ISO calendar date, Time retains microseconds, and DateTime uses UTC
milliseconds. The codec rejects unsupported precision and nonfinite numbers;
it does not silently truncate or coerce them. Explicit null stays loaded null;
an omitted property stays NotLoaded.

The same SQLite flow checks sparse entities, typed forward and reverse trees,
and filtered details. A filtered target's identity remains known from the FK,
but its unreturned name is NotLoaded both before and after JSON. No encode,
decode or E access calls the provider. A modified sparse entity is rejected
before query, mutation, transaction begin or ID allocation.

Decoded full entities still require an audited save, Checker and policy. Two
independently decoded copies retain separate mutation boundaries: saving one
does not silently clear the other's pending mutation; the stale save is rejected
and committed state stays unchanged. The current generic stale-save error is
not a complete structured conflict diagnostic and is not claimed as one.

The verifier retains two compact `*.json-*.report.json` files beside the database.
They record the checks and provider counters, not generated private ledgers.
Entity JSON excludes query/facet metadata and does not replace transport
authorization or the context-bound reference adapter. Cyclic graphs require an
explicit reference representation rather than implicit database reads.

SQLite exact Decimal columns use `TEAQL_DECIMAL_TEXT COLLATE TEAQL_DECIMAL`
and a generated value check. The provider registers the collation, validator
and exact SUM on every connection. SUM ignores SQL NULL and returns NULL for
an empty input. AVG and statistical Decimal aggregates require an explicit
precision policy and are rejected by this profile. Finite values are bounded
to a 10,000-character plain representation before arithmetic or expansion.

Existing NUMERIC/REAL or unqualified TEXT columns require an explicit migration;
`ensure_schema()` rejects them before bootstrap. Previously rounded values
cannot be recovered automatically. Raw SQL remains the caller's responsibility.
