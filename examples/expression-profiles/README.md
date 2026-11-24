# Dispatch order field names

Save a dispatch order, then read its loading instruction through the distribution
center’s generated Q and E APIs. The three model profiles preserve the same
business data across a restart. They choose the external field spellings and
the exact preload diagnostic for an omitted reverse list.

`model.xml` owns the camelCase variant. The snake_case and PascalCase variants
own separate models and native generated workspaces under `profiles/`.
Run `bash examples/expression-profiles/verify-dispatch.sh` to exercise all three
variants and the original expression diagnostics.

## Original expression diagnostics

Run from this runtime repository:

```sh
python3 -B examples/expression-profiles/verify-local.py
```

The same application executes against three evaluated, unmodified generated
libraries: default `camelCase`, `snake_case`, and `PascalCase`. Models differ
only in `json_field_naming`. The local producer identity and file hashes are
recorded in `provenance.json` and `generated/manifest.json`.

The application uses the context's schema bootstrap, a bounded generated Q
query, and the generated E API to traverse a reverse list which was not loaded.
The default error DTO must use the model's JSON naming, while preserving the
canonical KSML path, the full attempted native chain, one first-failure
`<broken>` marker, and preload guidance. It does not override the error profile.
An observed real Q query calibrates the provider counter; E causes no further
provider calls and leaves the selected root name unchanged.

Each model runs twice on the same SQLite database without a reset. Source,
fixture, command, origin and database evidence is retained; only task-owned
build scratch is removed. To choose an output location, set
`TEAQL_GENERATED_E_PROFILE_EVIDENCE_DIR` to a new absolute directory.
Existing reports and databases are never overwritten. No virtual environment or bytecode cache is created.

These are local-source examples, not private/public package qualification,
a new audited-save test, a full example-inventory gate or full P0/P1 acceptance.
Literal punctuation and JSON-pointer escaping are covered by the separate
native expression-path tests; modeled names here are legal multiword fields.
