# TeaQL Python SDK

## Sensitive log data

Runtime diagnostic logs redact payload values by default, before delivery to
file, console, buffers, or custom logging sinks. Selecting a diagnostic sink
alone does not authorize plaintext. For controlled troubleshooting only:

```bash
export TEAQL_ALLOW_SENSITIVE_PLAINTEXT_LOGS=I_UNDERSTAND_SENSITIVE_DATA_MAY_BE_WRITTEN_TO_DISK
```

Only this exact value enables plaintext permission; empty values, `true`, and
whitespace variants do not. Enabling it emits a warning. Credential-classified
fields remain redacted. The flag does not force every sink to expose values.
SQL without reliable field/literal provenance may be suppressed and marked
`NOT REPLAYABLE`. Execution parameters and persisted business data are unchanged.

Do not put sensitive data in free-text comments or purpose declarations.
TeaQL cannot govern arbitrary application prints or independent driver loggers;
configure those separately. This setting does not erase older plaintext files.
Restrict access and retention when using plaintext diagnostics, then unset the
variable and restart processes when troubleshooting is complete.

TeaQL Python SDK is a runtime engine and toolkit for building data-driven business applications. It uses `teaql-rs` as the cross-language design baseline; verified coverage and remaining gaps are tracked in [conformance](https://github.com/teaql/teaql-conformance).

## Recommended Agent Harness

When building database-backed applications with the TeaQL Python runtime, we
recommend using it together with the [TeaQL Agent Kit](https://github.com/teaql/teaql-agent-kit).
The Agent Kit is TeaQL's continuously evolving **Harness Engineering** method.
It gives coding agents a model-mediated, executable workflow for domain
modeling, deterministic evaluation and repair, code generation, implementation,
and evidence-based verification as the generator and runtimes evolve.

## 1. Minimum Version Requirements

*   **Python**: 3.10+ (Recommended 3.12+)
*   **Testing**: `pytest` 7.4+
*   **Dependencies**: `pydantic` >= 2.0, `aiosqlite`, `aiomysql`, `asyncpg`, `cryptography` >= 42

## 2. Tests Performed

The SDK includes tests in the following areas. These suites do not establish complete Rust parity or acceptance of every external provider:
*   **Cross-language contracts**: Shared fixtures and integration tests verify individual portable behaviors; unresolved coverage stays explicit in conformance.
*   ✅ **`teaql.core` Core Tests**: Extensively tested attribute extraction, safe nullability checks, and relationship building for `Value`, `GraphNode`, `Entity`, `Mutation`, `Query`, `Expr`, and `SafeExpression`.
*   ✅ **`teaql.runtime` Runtime Tests**: Verified the context propagation of `UserContext` and the complete lifecycle hooking for `record_sql_log` and `record_metadata_log`.
*   ✅ **`teaql.sql` / `teaql.data_service` Tests**: Tested the SQL AST compilation engine and the underlying command dispatch mechanism.
*   ✅ **Provider & External Integrations**: Includes integration tests for the SQLite driver and FastAPI web endpoints.

## 3. Available Modules

The SDK's organizational architecture strictly mirrors the Rust version:
*   `teaql.core`: Provides core underlying data structures (e.g., `Value`, `GraphNode`, `Entity`, `SelectQuery`, `MutationRequest`).
*   `teaql.data_service`: Defines universal data service abstractions, handling structured inputs and outputs.
*   `teaql.sql`: Provides a cross-dialect SQL compilation executor, translating ASTs into physical queries for various databases.
*   `teaql.runtime`: Contains the pipeline and application context mechanisms (e.g., `UserContext`, environment mounts).
*   `teaql.provider`: Packages for physical database drivers and the canonical TeaQL Federal Protocol client.
*   `teaql.web`: Web framework integration middleware (e.g., `FastAPI` / `Starlette`).

## 4. Features

*   **Entity & Value Mapping**: Provides type-safe mapping between native Python types and TeaQL core primitives (I64, Text, F64, Null, etc.).
*   **SQL Compilation & AST Building**: A dynamic, secure SQL query builder that generates standardized `INSERT`, `UPDATE`, `DELETE`, and `SELECT` statements while abstracting away dialect differences.
*   **Facet Aggregation & Grouping**: Out-of-the-box support for multi-dimensional facet aggregations, group-bys, and hierarchical data processing.
*   **Provider Support**: Highly extensible asynchronous database connectivity (integrating third-party async drivers like `aiosqlite` through a unified Transport layer).
*   **Context & Logging Management**: Built-in support for lifecycle context passing, end-to-end tracing, and SQL execution log interception and dispatch.
*   **Governed Mutation Policy**: An application-owned policy can review an
    immutable whole-graph plan after Checker/Fix and before the first provider
    mutation. Exact policy identity and approval state are retained with audit
    evidence. Missing customer policy or approval emits stable warnings without
    changing persistence semantics; an explicit denial fails closed.
*   **Governed Business ID Lifecycle**: Core model contracts, a context-owned
    profile/key/service boundary, retry-safe assignment, an in-memory allocator,
    and explicit-schema durable SQLite allocation extend the portable
    `daily-permuted-v1` encoder without exposing its internal sequence.
*   **TeaQL Federal Protocol Client**: `TeaQLFederalClient` and `TfpHttpProvider`
    execute governed canonical TFP v1 queries and audited mutations against a
    remote TeaQL endpoint such as Rust. Direct query execution returns
    `SmartList`; Python intentionally does not expose a TFP server endpoint.

```python
from teaql.provider.tfp_client import FederalQuery, TeaQLFederalClient

client = TeaQLFederalClient("https://orders.example.com/tfp")
orders = await client.execute_query(FederalQuery(
    entity="CustomerOrder",
    filter_condition={"status": {"$eq": "NEW"}},
    comment="List new orders",
    purpose="Render operations queue",
))
await client.aclose()
```

## Trace Chain Local Source Status

Query and Mutation Requests own their required non-blank intent independently
of logging. Physical SQL paths use the Rust canonical algorithm, with twelve
byte-identical frozen vectors, owned query origins and qualified relation frames.
Native SQLite tests observe three real relation levels without inserting expected
frames, including a deepest-query failure. A successful write and a failed
authoritative readback keep separate canonical paths and statement outcomes;
the failed transaction rolls back.

Parent query diagnostics include declared descendant binding provenance before
safe projection. The existing mask algorithm, expanded SQL and execution values
are unchanged; provenance is not stored on Context or exposed in log entries.
This additional compilation has not been performance benchmarked.

Graph saves now use an explicit invocation-owned `GraphMutationSession` and an
immutable persistent parent scope. The original Context's data service is never
swapped; child saves receive the session and their parent scope explicitly.
Unannotated children inherit, local reasons append once, and deletion creates its
scope before execution. The typed ledger can store an owned complete replacement
chain. Five shared graph fixtures verify fifteen per-entity expectations; these
helper tests are separate from generated traversal evidence.

[The generated Trace Chain example](examples/trace-chain/) drives six mutations
through actual Q/E/save APIs and SQLite, observing request lineage, SQL metadata
and safe audits after commit. It also verifies three query relation levels,
concurrent independent saves in one Context, write/readback failure rollback,
and missing root intent before transaction access. Its verifier executes twice
on one SQLite file without cleanup and checks all generated-library hashes.
All ten example groups and the source suite pass twice locally (424 tests and
eight explicit external-provider skips per source run).

SQL transactions queue owned audit snapshots until commit, including explicit
transactions and automatic batches. Rollback discards them. A completion failure
is reported with `GraphCommittedError.committed == True`; all remaining audit
deliveries and graph cleanup callbacks are still attempted, with no postcommit
rollback. Reentrant independent root saves fail instead of silently joining.
The private generated save implementation has changed; old generated libraries
must be regenerated, while public `audit_as(...).save(context)` stays unchanged.

The aggregate follow-up adds runtime-owned query projection snapshots and generated
`query_projection(alias)` / `has_query_projection(alias)` accessors. Missing aliases
raise `KeyError`; zero and null are present values. Projections are owned snapshots,
not writable model fields, live calculations or part of a mutation payload. The
generated example covers root/nested counts, original Trace Chain ancestry,
masked descendant intent, logging on/off, provider failure recovery and saving
only a modeled field. An alias named `save` cannot replace the save method.
Regenerate libraries to acquire this projection API; related aggregate streaming
remains unsupported and rejects before provider I/O.

Relation attachment retains original scalar keys in invocation-local runtime
state. It does not infer membership from hydrated objects: a forward reference
filtered to `None` must not remove its child from a separately loaded parent
list, and a later sibling can still load using the same FK. Keys are not added
to returned records or mutation payloads. Native SQLite cases exercise these
boundaries with related counts, nested ancestry and logging both on and off.

This is local-source/generated-consumer evidence, not complete Trace Chain.
Prepared-batch grouping, generated ledger overrides, complete entry-point and
inherited mutation privacy coverage, successful readback diagnostic alignment,
live PostgreSQL/MySQL graph acceptance, and immutable internal Registry replay
remain open. No released-package parity is claimed.

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m pytest -q
PYTHONDONTWRITEBYTECODE=1 bash scripts/verify-examples.sh
# Repeat both commands without source changes.
```

## Security Foundation Status

Python currently provides governed local SQL execution and a **TFP client**;
it does not claim a public TFP server endpoint. Application queries retain
non-empty comment/purpose and audited mutations retain their audit reason.
Runtime logging should keep parameterized SQL and intent separate from any
restricted value-bearing diagnostic output.

Python implements the portable `tqr1` tuple codec shared with Go and .NET. It
encrypts and authenticates entity type, internal ID, optimistic version,
issued/expiry time, and purpose with AES-256-GCM. Key rings permit rotation;
encoding always uses the active key while decoding can accept retained keys.

```python
import os
from datetime import timedelta
from teaql.runtime import AeadEntityReferenceCodec, UserContext

codec = AeadEntityReferenceCodec(2, {
    1: bytes.fromhex(os.environ["TEAQL_ENTITY_REFERENCE_KEY_V1_HEX"]),
    2: bytes.fromhex(os.environ["TEAQL_ENTITY_REFERENCE_KEY_V2_HEX"]),
})
context = UserContext().with_entity_reference_codec(codec)
token = context.encode_entity_reference(
    "OrderItem", 42, 7, "edit-order", timedelta(minutes=30)
)
claims = context.decode_entity_reference(token, "OrderItem", "edit-order")
```

Without a configured codec the runtime fails closed. Local debugging can use
the canonical long `TEAQL_UNSAFE_RAW_ENTITY_REFERENCES` acknowledgement, which
emits visibly distinct `tqr0` references. It must not be enabled in production.

The wire format, fail-closed behavior, shared golden vector, and exact
development-only acknowledgement are maintained in the canonical
[opaque entity reference contract](https://github.com/teaql/teaql-conformance/blob/main/design/opaque-entity-references.md).
Opaque tokens never replace the backend's authorization, tenant, ownership,
role, or optimistic-version checks.

The repeatable [`examples/opaque-entity-reference`](examples/opaque-entity-reference)
example proves the exact cross-language golden vector and purpose-substitution
rejection.

## Business ID V1 Foundation

The pure runtime encoder maps a durable internal sequence into the canonical
six-character, scope-specific Base36 code:

```python
from teaql.core import BusinessIdEncodingKey, BusinessIdScope
from teaql.runtime import encode_business_id_permutation_v1

scope = BusinessIdScope(
    "tenant-a", "commerce_order", "order_number", "20260925"
)
key = BusinessIdEncodingKey(1, key_from_secret_manager)
code = encode_business_id_permutation_v1(0, scope, key)
```

The retained [`examples/business-id`](examples/business-id) flow proves durable
concurrent allocation infrastructure and aggregate retry reuse. Generated
strongly typed fields and external lookup remain a separate generator
capability. Secret key material is application-owned and must not be placed in
KSML or generated source.

### Mutation Policy installation

Policy implementations are installed from trusted application startup through
`UserContext`; request JSON cannot select or replace them. Built-in SQL and TFP
providers enter the same governed boundary.

```python
context = (
    UserContext.new()
    .with_mutation_policy_registry(policy_registry)
    .with_mutation_policy_approval_provider(approval_provider)
    .with_mutation_governance_sink(warning_sink)
)
```

Generated graph saves call `preflight_mutation(...)` for every operation before
the first provider write. See the repeatable
[`examples/mutation-policy`](examples/mutation-policy) example for allow,
approval, audit propagation, and zero-write denial evidence.

---
To run test validations and business logic simulations locally, simply run `pytest` in the project root.
