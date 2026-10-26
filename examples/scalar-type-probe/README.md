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

## Canonical names and atomic graph saves

`name_probe.py` runs eight `NAME-01`–`NAME-08` vectors against a separate
`*.names.sqlite` file, twice without resetting it. It checks canonical model
keys in the actual mutation ledger and Checker/policy inputs, physical column
names, native Q/E methods, loaded/null/NotLoaded values, and typed nested JSON
under all three naming profiles. Equal duplicate JSON keys are rejected.

Twelve deliberately malformed ledger payloads and two required-value negatives
must fail before provider calls or SQLite authorization activity. In particular,
new-entity payload construction must not silently discard unknown ledger keys.
The raw ledger access is explicit fault injection, not application API guidance.

A real SQLite authorizer denies the second child UPDATE after the first UPDATE
has executed. No commit audit may escape that rollback. The same loaded graph
must retain its pending intent and retry successfully with two canonical audit
events and the correct per-entity versions. The test connection reinstalls its
authorizer before each execution so prepared-statement reuse cannot bypass the
fault; production provider behavior is unchanged. No generated source is edited.
This single-runtime example does not establish full cross-runtime schema parity
or qualify a previously published package for the newer generator/runtime pair.

SQLite exact Decimal columns use `TEAQL_DECIMAL_TEXT COLLATE TEAQL_DECIMAL`
and a generated value check. The provider registers the collation, validator
and exact SUM on every connection. SUM ignores SQL NULL and returns NULL for
an empty input. AVG and statistical Decimal aggregates require an explicit
precision policy and are rejected by this profile. Finite values are bounded
to a 10,000-character plain representation before arithmetic or expansion.

Existing NUMERIC/REAL or unqualified TEXT columns require an explicit migration;
`ensure_schema()` rejects them before bootstrap. Previously rounded values
cannot be recovered automatically. Raw SQL remains the caller's responsibility.
