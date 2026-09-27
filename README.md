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
*   **Dependencies**: `pydantic` >= 2.0, `aiosqlite`, `aiomysql`, `asyncpg`

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

Portable `UserContext` opaque entity references are not implemented in the
Python runtime yet. Until that capability is added, applications must not
invent a Python-specific token format or serialize internal ID/version pairs as
if they were the TeaQL portable contract. A Python TFP client may carry an
opaque token issued by a trusted Java, Rust, Go, or .NET backend, but it must
not decode, rewrite, or mint that token.

The planned wire format, fail-closed behavior, shared golden vector, and exact
development-only acknowledgement are maintained in the canonical
[opaque entity reference contract](https://github.com/teaql/teaql-conformance/blob/main/design/opaque-entity-references.md).
Opaque tokens never replace the backend's authorization, tenant, ownership,
role, or optimistic-version checks.

---
To run test validations and business logic simulations locally, simply run `pytest` in the project root.
