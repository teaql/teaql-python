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

TeaQL Python SDK is a runtime engine and toolkit for building data-driven business applications. It provides seamless integration with the TeaQL ecosystem, fully aligned with the `teaql-rs` baseline.

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

After rigorous AST semantic analysis and manual verification, this SDK has successfully passed the following tests:
*   ✅ **100% API Signature and Logic Parity**: Scanned with Tree-Sitter and implemented all internal methods and logic to match the Rust baseline.
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
